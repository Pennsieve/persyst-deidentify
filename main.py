import os
import sys
import csv
import uuid
import subprocess
import shutil
import xml.etree.ElementTree as ET

from datetime import datetime
from dateutil import parser
from pathlib import Path
from datetime import datetime, timedelta
import pdb
import re

# CSV indicies
DATE_TIME = 'Test Date'
DURATION = 'Duration'
FIRST_NAME = 'First Name'
LAST_NAME = 'Last Name'
PATIENT_ID = 'Patient ID'
PATH = 'File Name With Path'
DOB = 'DOB'
INPUT_STUDY_ID = 0
INPUT_PATIENT_ID = 1
INPUT_DATE = 2

TEMPLATE_SUBSTITUTION_STRING = "$NEW_FILE_NAME"
OUTPUT_SUBSTITUTION_STRING = "$OUTPUT_DIRECTORY"
PSCLI_DIRECTORY = r"C:\Program Files (x86)\Persyst\Insight"

LOG_FILE = "worklog.txt"

DEFAULT_DATABASE_LOCATION=r"C:\database.csv"

FILE_TYPES = {
    "erd": "XLTEK",
    "lay": "PersystLayout",
    "psx": "PersystLayoutXML",
    "bdf": "BDF",
    "ns": "Blackrock",
    "eeg": "BMSi 3.0+",
    "arc": "Cadwell",
    "ez3": "Cadwell",
    "edf": "EDF90",
    "maf": "MEF",
    "mefd": "MEF3",
    "pnt": "NihonKohden 2100",
    "trc": "Micromed"
}

seen_patient_ids = {}


#  Public output CSV headers
PUBLIC_CSV_HEADERS = [
    "new_name",
    "age_in_days_at_time_of_eeg", # Test Date - DOB
    "eeg_start_time", # Test date time
    "eeg_duration",
    "date_of_csv_creation", 
]

# Private ouput CSV headers
PRIVATE_CSV_HEADERS = [
        "new_name",
        "age_in_days_at_time_of_eeg", # Test Date - DOB
        "eeg_start_time", # Test Date time
        "eeg_duration",
        "original_eeg_date_time", #Test Date
        "first_name",
        "last_name",
        "patient_id",
        "orignal_eeg_name",
        "csv_creation_date",
]

POSITIVE_INPUTS = ['y','yes']

# Set by the -v / --verbose command line flag. When True, vprint() emits
# detailed step-by-step diagnostics.
VERBOSE = False

# Full path to the verbose log, set once the private output folder exists.
# Until then vprint() output only goes to the screen.
VERBOSE_LOG_PATH = None

VERBOSE_LOG_FILE = "verbose.log"

# Windows file attribute bits, from the MSDN "File Attribute Constants" list.
# These are the ones that explain a file we can see but cannot read.
FILE_ATTRIBUTE_ENCRYPTED = 0x4000
FILE_ATTRIBUTE_OFFLINE = 0x1000
FILE_ATTRIBUTE_RECALL_ON_OPEN = 0x40000
FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS = 0x400000


def vprint(*args, **kwargs):
    """
    Print only when verbose mode is enabled (main -v / --verbose), and append
    the same line to verbose.log in the private output folder. The log is what
    a user emails back when a conversion fails, so it must not depend on them
    scrolling the console.
    """
    if not VERBOSE:
        return

    print("[verbose]", *args, **kwargs)

    if VERBOSE_LOG_PATH:
        line = "[verbose] " + " ".join(str(a) for a in args)
        try:
            with open(VERBOSE_LOG_PATH, 'a', encoding='utf-8') as log_file:
                log_file.write(f"{datetime.now().isoformat(timespec='seconds')} {line}\n")
        except OSError as e:
            # Never let logging kill the run.
            print(f"[verbose] (could not write to {VERBOSE_LOG_PATH}: {e})")


def describe_source_file(path):
    """
    Verbose-only inspection of a source EEG file before it is handed to PSCLI.
    Answers the 2AM question "why did this one file fail?" - missing, no read
    permission, EFS-encrypted, still cloud-only, zero bytes, or a .lay whose
    data file has gone missing.
    """
    if not VERBOSE:
        return

    vprint("---- source file check ----")
    vprint(f"  path: {repr(path)}")

    if not os.path.exists(path):
        parent = os.path.dirname(path)
        vprint("  exists: NO  <-- PSCLI will fail. Check the path column in the database CSV.")
        vprint(f"  parent directory: {repr(parent)} exists={os.path.isdir(parent)}")
        vprint("---------------------------")
        return

    vprint("  exists: yes")

    try:
        stats = os.stat(path)
        vprint(f"  size: {stats.st_size} bytes")
        vprint(f"  modified: {datetime.fromtimestamp(stats.st_mtime).isoformat(timespec='seconds')}")
        if stats.st_size == 0:
            vprint("  ZERO BYTES <-- there is nothing here to convert")

        # st_file_attributes only exists on Windows.
        attributes = getattr(stats, "st_file_attributes", None)
        if attributes is not None:
            vprint(f"  windows attributes: 0x{attributes:08x}")
            if attributes & FILE_ATTRIBUTE_ENCRYPTED:
                vprint("  ENCRYPTED (Windows EFS) <-- this tool reads the file as the logged-in "
                       "user. If another account encrypted it, it cannot be opened here.")
            if attributes & (FILE_ATTRIBUTE_OFFLINE
                             | FILE_ATTRIBUTE_RECALL_ON_OPEN
                             | FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS):
                vprint("  OFFLINE / cloud-only (OneDrive, Dropbox, archive tier) <-- the file must "
                       "be downloaded to local disk before conversion.")
    except OSError as e:
        vprint(f"  stat failed: {e}")

    vprint(f"  readable by this user: {os.access(path, os.R_OK)}")

    # Open it ourselves. A failure here is the same failure PSCLI will hit, and
    # the header bytes tell us whether the content is plain or scrambled.
    try:
        with open(path, 'rb') as source_file:
            head = source_file.read(64)
        vprint(f"  first 32 bytes (hex):   {head[:32].hex(' ')}")
        vprint(f"  first 32 bytes (ascii): {repr(head[:32])}")
        printable = sum(1 for b in head if 32 <= b < 127 or b in (9, 10, 13))
        vprint(f"  printable bytes in header: {printable}/{len(head)}")
        if head[:2] == b'PK':
            vprint("  header looks like a ZIP container, not raw EEG data")
    except PermissionError as e:
        vprint(f"  OPEN FAILED - permission denied: {e}")
        vprint("  <-- file is locked by another program, on a share we lack rights to, "
               "or encrypted for a different user")
    except OSError as e:
        vprint(f"  OPEN FAILED: {e}")

    if path.lower().endswith('.lay'):
        describe_lay_file(path)

    vprint("---------------------------")


def describe_lay_file(path):
    """
    A .lay file is plain text that points at the real data file. If that
    pointer is broken, or the .lay itself is not readable text, the conversion
    fails even though the .lay is sitting right there.
    """
    try:
        with open(path, 'r', encoding='utf-8-sig', errors='strict') as lay_file:
            contents = lay_file.read(4096)
    except UnicodeDecodeError:
        vprint("  .lay is NOT readable text <-- expected an INI-style header. "
               "Likely encrypted or corrupt.")
        return
    except OSError as e:
        vprint(f"  .lay could not be read: {e}")
        return

    if '[FileInfo]' not in contents:
        vprint("  .lay is missing the [FileInfo] section <-- not a Persyst layout file")

    match = re.search(r'^\s*File\s*=\s*(.+?)\s*$', contents, re.MULTILINE | re.IGNORECASE)
    if not match:
        vprint("  .lay has no File= entry, cannot check the companion data file")
        return

    data_file = match.group(1)
    # The File= entry is often relative to the .lay's own folder.
    if not os.path.isabs(data_file):
        data_file = os.path.join(os.path.dirname(path), data_file)
    vprint(f"  .lay data file: {repr(data_file)} exists={os.path.exists(data_file)}")
    if os.path.exists(data_file):
        vprint(f"  .lay data file size: {os.path.getsize(data_file)} bytes")
    else:
        vprint("  <-- the .lay points at a data file that is not there")


def main():
    
    """
    Uses the persyst cli to archive files, deidentifying them
    Script will also create CSVs with metadata about the outputs for future reference
    Script requires an input CSV, and output directory and optionally a path to an xml template as arguments
    If no xml template path is specified it is assumed that there is a file named `archive-template.xml` in the directory the script is running from
    """
    
    global VERBOSE, VERBOSE_LOG_PATH

    search_num_days_before = 1
    search_num_days_after = 7

    # Pull the verbose flag out of argv so the remaining positional arguments
    # (input CSV, output directory) keep their existing meaning whether or not
    # -v is present. Supports:  main -v   |   main input.csv output_dir -v
    positional_args = []
    for arg in sys.argv[1:]:
        if arg in ("-v", "--verbose"):
            VERBOSE = True
        else:
            positional_args.append(arg)

    if VERBOSE:
        print("[verbose] Verbose mode enabled.")

    if not os.path.isfile(PSCLI_DIRECTORY +'\\PSCLI.exe' ):
        log_and_print(os.path.join(private_files_path, LOG_FILE),f"Persyst not found in {PSCLI_DIRECTORY}. Exiting")
        input()
        sys.exit()

    if len(positional_args) == 0:
       
       db_location = DEFAULT_DATABASE_LOCATION
       change_database = getUserInput(r"CSV database default location is C:\database.csv. Change? [y/n]: ","string")
       if change_database.lower() in POSITIVE_INPUTS:
            db_location = getUserInput("Please enter location of database: ","file")

       input_csv_path = getUserInput("Please enter complete file path to Input CSV: ", "file")

       output_base = getUserInput("Please enter output path to save de-identified files: ", "directory")
       
       # TODO: Add input requests for days before and days after. Have options for getting every EEG before and after certain dates
       
       custom_search = getUserInput(
            f"Search is set to find records {search_num_days_after} days after date of service "
            f"and {search_num_days_before} before data of service. \n"
            f"Change? [y/n]",
            "string"
           )
       
       if custom_search in POSITIVE_INPUTS:
           search_num_days_after = int(getUserInput("How many days to search after date of service? ", "int"))
           search_num_days_before = int(getUserInput("How many days to search before date of service? ", "int"))

       private_files_path = output_base.rstrip("\\") + "_private"
       if not os.path.exists(private_files_path):
           os.mkdir(private_files_path)

       log_and_print(os.path.join(private_files_path, LOG_FILE),f"Private files will output to: {private_files_path}")

    elif len(positional_args) > 0:
        # Get input arguments
        input_csv_path = positional_args[0]
        output_base = positional_args[1]
        db_location = positional_args[2] if len(positional_args) > 2 else DEFAULT_DATABASE_LOCATION

        if not os.path.isfile(input_csv_path) or not os.path.isdir(output_base):
            print("Usage: python persyst_deidentify.py <input_CSV> <output_directory> [database_csv] [-v]")
            sys.exit(1)

        private_files_path = output_base.rstrip("\\") + "_private"
        if not os.path.exists(private_files_path):
            os.mkdir(private_files_path)

    VERBOSE_LOG_PATH = os.path.join(private_files_path, VERBOSE_LOG_FILE)
    if VERBOSE:
        print(f"[verbose] Writing verbose log to: {VERBOSE_LOG_PATH}")
        vprint(f"Run started {datetime.now().isoformat(timespec='seconds')}")

    # Add PSCLI directory to the PATH for this run
    os.environ["PATH"] += os.pathsep + PSCLI_DIRECTORY
    documents_path = Path.home() / "Documents"

    exe_dir = os.getcwd()
    key_path = os.path.join(exe_dir, r'archive-template.xml')
    xml_template_path = key_path

    log_and_print(os.path.join(private_files_path, LOG_FILE),f"Database location: {db_location}")
    log_and_print(os.path.join(private_files_path, LOG_FILE),f"CSV input: {input_csv_path}")
    log_and_print(os.path.join(private_files_path, LOG_FILE),f"Output path: {output_base}")
    log_and_print(os.path.join(private_files_path, LOG_FILE),f"XML template: {xml_template_path}\n")

    if not os.path.exists(xml_template_path):
        log_and_print(os.path.join(private_files_path, LOG_FILE),f"XML template not found at {xml_template_path}")
        sys.exit(1)


    write_to_csv(PRIVATE_CSV_HEADERS,os.path.join(private_files_path, "full-report-private.csv") )
    write_to_csv(PRIVATE_CSV_HEADERS,os.path.join(private_files_path, "errors.csv") )

    inputs = {}
    database = {}

    # Open the database file.
    # encoding="utf-8-sig" transparently strips a leading UTF-8 BOM (EF BB BF)
    # if one is present. Excel's "CSV UTF-8" export prepends this BOM, which
    # otherwise becomes part of the first column's value (e.g. it shows up in
    # the terminal as the garbled "i>>?"/"ï»¿" prefix). Plain "r" mode does NOT
    # strip it.
    vprint(f"Opening database file: {repr(db_location)}")
    with open(db_location, mode='r', encoding='utf-8-sig') as file:
        database_reader = csv.DictReader(file,delimiter='\t')

        # The database is tab delimited. If it was saved as comma delimited the
        # whole line lands in one column and every lookup below silently misses,
        # so show the parsed header names.
        vprint(f"Database columns: {database_reader.fieldnames}")
        if database_reader.fieldnames is not None and len(database_reader.fieldnames) == 1:
            log_and_print(os.path.join(private_files_path, LOG_FILE),
                          f"Warning: database {db_location} parsed as a single column. "
                          f"It must be TAB delimited.\n")

        # Loop through each row in the CSV file
        for row in database_reader:
            if row[PATIENT_ID] not in database:
                database[row[PATIENT_ID]] = []
            database[row[PATIENT_ID]].append(row)
    vprint(f"Database loaded: {len(database)} unique patient IDs across "
           f"{sum(len(v) for v in database.values())} records")

    # See note above re: utf-8-sig — this is the input CSV the user creates,
    # and is the file that was carrying the BOM in the reported case.
    vprint(f"Opening input CSV: {repr(input_csv_path)}")
    with open(input_csv_path, newline="", encoding='utf-8-sig') as input_csv_file:
        machine_type = "XLTEK"
        input_csv_reader = csv.reader(input_csv_file)

        for row in input_csv_reader:
            print(f"Processing data row: {row}")
            # Show the raw bytes/repr of every field so any stray BOM,
            # whitespace, or non-printable character is visible.
            vprint(f"  row field reprs: {[repr(field) for field in row]}")
            patient_id = row[INPUT_PATIENT_ID]
            vprint(f"  study_id={repr(row[INPUT_STUDY_ID])} "
                   f"patient_id={repr(patient_id)} date={repr(row[INPUT_DATE])}")
            inputs[patient_id] = [row[INPUT_STUDY_ID], row[INPUT_DATE]]

            # Find record in database
            if patient_id not in database:
                vprint(f"  patient_id {repr(patient_id)} NOT found in database "
                       f"({len(database)} IDs loaded). Nothing to convert for this row.")
            if patient_id in database:
                vprint(f"  patient_id {repr(patient_id)} matched "
                       f"{len(database[patient_id])} database record(s)")
                for record in database[patient_id]:
                    row_date_time = record[DATE_TIME]
                    eeg_duration = record[DURATION]
                    eeg_first_name = record[FIRST_NAME]
                    eeg_last_name = record[LAST_NAME]
                    eeg_patient_id = record[PATIENT_ID]
                    eeg_path = record[PATH]
                    dob = record[DOB].strip()

                    # --- VERBOSE FILE-TYPE DEBUGGING ---
                    # repr() is used deliberately so hidden characters (trailing
                    # spaces, tabs, newlines, non-breaking spaces) are visible in
                    # the output instead of being swallowed by the terminal.
                    vprint("---- file-type debug ----")
                    vprint(f"  patient_id (record): {repr(eeg_patient_id)}")
                    vprint(f"  raw eeg_path:         {repr(eeg_path)}")
                    vprint(f"  eeg_path length:      {len(eeg_path)}")

                    root, raw_extension = os.path.splitext(eeg_path)
                    vprint(f"  splitext root:        {repr(root)}")
                    vprint(f"  splitext extension:   {repr(raw_extension)}")

                    extension = raw_extension[1:].lower()
                    vprint(f"  extension (sliced/lower): {repr(extension)}")
                    # Whitespace-stripped variant — if this differs from the value
                    # above, the source CSV field has stray whitespace.
                    vprint(f"  extension (stripped):     {repr(extension.strip())}")
                    vprint(f"  in FILE_TYPES?            {extension in FILE_TYPES}")
                    vprint(f"  in FILE_TYPES (stripped)? {extension.strip() in FILE_TYPES}")
                    vprint("--------------------------")

                    print(f"Found file path with extension: {extension}")
                    if extension in FILE_TYPES:
                        print(f"Setting machine type to: {FILE_TYPES[extension]}")
                        machine_type = FILE_TYPES[extension]
                    else:
                        print(f"No matching file type. Supported options are : {FILE_TYPES}")
                        continue

                    if eeg_patient_id in inputs:
                        vprint(f"Matched record for patient_id={repr(eeg_patient_id)} "
                               f"(row_date_time={repr(row_date_time)}, dob={repr(dob)})")
                        try:
                            datef = datetime.strptime(row_date_time, "%Y.%m.%d %H:%M:%S").date()
                            test_date, test_time = row_date_time.split()
                        except ValueError:
                            try:
                                test_date, test_time = row_date_time.split()
                                datef = datetime.strptime(test_date, "%Y.%m.%d").date()
                            except Exception as e:
                                log_and_print(os.path.join(private_files_path, LOG_FILE),
                                            f"Invalid row_date_time '{row_date_time}': {e}")
                                continue

                        input_format = "%m/%d/%Y"
                        try:
                            search_datef = datetime.strptime(inputs[eeg_patient_id][1], input_format).date()
                        except ValueError as e:
                            log_and_print(os.path.join(private_files_path, LOG_FILE),
                                        f"Invalid search_date '{inputs[eeg_patient_id][1]}': {e}")
                            continue

                        try:
                            dobf = parse_and_standardize(dob)
                        except ValueError as e:
                            log_and_print(os.path.join(private_files_path, LOG_FILE),
                                        f"Invalid DOB '{dob}': {e}")
                            continue

                        today = datetime.today().date()
                        if dobf > today:
                            dobf = dobf.replace(year=dobf.year - 100)

                        # Calculate age in days
                        age_in_days = (datef - dobf).days

                        # Calculate before/after windows
                        dates_before = search_datef - timedelta(days=search_num_days_before)
                        days_after  = search_datef + timedelta(days=search_num_days_after)

                        log_and_print(os.path.join(private_files_path, LOG_FILE), f"Days after: {days_after.isoformat()}")
                        log_and_print(os.path.join(private_files_path, LOG_FILE), f"Days before: {dates_before.isoformat()}")
                        log_and_print(os.path.join(private_files_path, LOG_FILE), f"Test date: {datef.isoformat()}")
                        
                        in_window = dates_before <= datef <= days_after or search_datef == datetime.strptime("11/11/1111", input_format)
                        vprint(f"  age_in_days={age_in_days}, window={dates_before.isoformat()}..{days_after.isoformat()}, "
                               f"test_date={datef.isoformat()}, in_window={in_window}")
                        if in_window:

                            file_counter = ""
                            if eeg_patient_id in seen_patient_ids:
                                seen_patient_ids[eeg_patient_id]['count']+=1
                                file_counter = seen_patient_ids[eeg_patient_id]['count']
                                folder = seen_patient_ids[eeg_patient_id]['filename']
                                encoded_file_name = seen_patient_ids[eeg_patient_id]['filename']
                            else:
                                # never seen before patient ID
                                seen_patient_ids[eeg_patient_id] = {'filename': f'{inputs[eeg_patient_id][0]}_{genShortUUID()}' , 'count': 1} 
                                encoded_file_name = seen_patient_ids[eeg_patient_id]['filename']
                                folder = seen_patient_ids[eeg_patient_id]['filename']

                            temp_xml_file = os.path.join(output_base, f"{encoded_file_name}-config.xml")
                            output_location = os.path.join(output_base, folder)
                            creation_date = datetime.now()

                            private_csv_payload = [encoded_file_name if file_counter=="" else f"{encoded_file_name}_{file_counter}", age_in_days, test_time, eeg_duration, row_date_time, eeg_first_name, eeg_last_name, eeg_patient_id, eeg_path, creation_date]
                            public_csv_payload = [encoded_file_name if file_counter=="" else f"{encoded_file_name}_{file_counter}", age_in_days, test_time, eeg_duration, creation_date]

                            try:
                                os.mkdir(output_location)
                            except FileExistsError:
                                log_and_print(os.path.join(private_files_path, LOG_FILE),f"Directory '{output_location}' already exists.")

                            # write CSV header
                            if os.path.exists(os.path.join(private_files_path, f"{encoded_file_name}_private.csv")):
                                pass # do not write header
                            else:
                                write_to_csv(PRIVATE_CSV_HEADERS,os.path.join(private_files_path, f"{encoded_file_name}_private.csv") )

                            # write CSV header
                            if os.path.exists(os.path.join(output_location, f"{encoded_file_name}_public.csv")):
                                pass # do not write header
                            else:
                                write_to_csv(PUBLIC_CSV_HEADERS,os.path.join(output_location, f"{encoded_file_name}_public.csv") )
                                

                            # Read XML template, replace $ with layFileName, and write to temp XML file
                            with open(xml_template_path, 'r') as template_file, open(temp_xml_file, 'w') as output_file:
                                for line in template_file:
                                    if file_counter =="":
                                        rewrite_name = encoded_file_name
                                    else:
                                        rewrite_name = f"{encoded_file_name}-{file_counter}"
                                    modified_line = line.replace(TEMPLATE_SUBSTITUTION_STRING, f"{rewrite_name}.edf")
                                    modified_line = modified_line.replace(OUTPUT_SUBSTITUTION_STRING, output_location)
                                    output_file.write(modified_line)
                        
                            # Run the PSCLI command using the .lay file as the source and the temp XML as /Options
                            pscli_command = [
                                f'PSCLI.exe',                       # PSCLI.exe
                                f'/SourceFile={eeg_path}',   # Input file
                                f'/FileType={machine_type}',
                                f'/Archive',                       # Archive option
                                f'/Options={temp_xml_file}'       # options file
                            ]

                            # PSCLI.exe /SourceFile="ENTERED PATH" /Archive / Options ="TEMP XML FILE" 

                            vprint(f"  encoded_file_name={repr(encoded_file_name)}")
                            vprint(f"  temp_xml_file={repr(temp_xml_file)}")
                            vprint(f"  output_location={repr(output_location)}")
                            vprint(f"  machine_type={repr(machine_type)}")

                            # Check the source before PSCLI touches it. If the file is
                            # unreadable, encrypted, or cloud-only, PSCLI just returns a
                            # non-zero code with no explanation - this is where we find out why.
                            describe_source_file(eeg_path)

                            vprint(f"  PSCLI command: {pscli_command}")
                            started_at = datetime.now()
                            try:
                                result = subprocess.run(pscli_command, capture_output=True, text=True)
                            except OSError as e:
                                log_and_print(os.path.join(private_files_path, LOG_FILE),
                                              f"Could not run PSCLI for {eeg_path}: {e}\n")
                                write_to_csv(private_csv_payload,os.path.join(private_files_path, "errors.csv") )
                                os.remove(temp_xml_file)
                                continue
                            elapsed = (datetime.now() - started_at).total_seconds()

                            vprint(f"  PSCLI returncode={result.returncode} in {elapsed:.1f}s")
                            vprint(f"  PSCLI stdout: {repr(result.stdout)}")
                            vprint(f"  PSCLI stderr: {repr(result.stderr)}")
                            try:
                                produced = sorted(os.listdir(output_location))
                            except OSError as e:
                                produced = f"(could not list: {e})"
                            vprint(f"  output folder now contains: {produced}")

                            print(result.returncode)
                            print(result.stderr)
                            print(result.stdout)
                            if result.returncode == 0:
                                write_to_csv(private_csv_payload,os.path.join(private_files_path, "full-report-private.csv") )
                                write_to_csv(private_csv_payload,os.path.join(private_files_path, f"{encoded_file_name}_private.csv") )
                                write_to_csv(public_csv_payload,os.path.join(output_location, f"{encoded_file_name}_public.csv") )
                                log_and_print(os.path.join(private_files_path, LOG_FILE), result.stdout)
                                log_and_print(os.path.join(private_files_path, LOG_FILE), "Successfully Archived")
                            else:
                                log_and_print(os.path.join(private_files_path, LOG_FILE),f"Failure on archive of: {eeg_path} (PSCLI exit {result.returncode})\n")
                                write_to_csv(private_csv_payload,os.path.join(private_files_path, "errors.csv") )
                                log_and_print(os.path.join(private_files_path, LOG_FILE), result.stdout)
                                # stderr is where PSCLI reports "cannot open" / decryption errors.
                                if result.stderr:
                                    log_and_print(os.path.join(private_files_path, LOG_FILE), result.stderr)
                                log_and_print(os.path.join(private_files_path, LOG_FILE), "done writing CSV")
                            
                            os.remove(temp_xml_file)
    # Only remove video files if ExportEntireVideo is not set to 1 in the template
    try:
        tree = ET.parse(xml_template_path)
        root = tree.getroot()
        export_video = root.find('.//Value[@name="ExportEntireVideo"]')
        keep_videos = export_video is not None and export_video.text.strip() == '1'
    except Exception:
        keep_videos = False

    if keep_videos:
        log_and_print(os.path.join(private_files_path, LOG_FILE), "ExportEntireVideo is enabled. Keeping video files.")
    else:
        remove_video_files(output_base)
    if VERBOSE_LOG_PATH and VERBOSE:
        print(f"Verbose log written to: {VERBOSE_LOG_PATH}")
    input("Converstion complete. See output folder for results. \nHit enter or close this window\n")

def genShortUUID(length=7):
    """
    Generates a truncated UUID

    :param length: Optional, defaults to 7
    """
    return uuid.uuid4().hex[:length]

def write_to_csv(data, file_path):
    """
    Appends data to a CSV file if it exists; otherwise, creates a new file and writes to it.

    :param data: data to write in array
    :param file_path: Path to the CSV file.
    """
    # Check if the file exists
    file_exists = os.path.isfile(file_path)
    
    with open(file_path, mode='a' if file_exists else 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)

        # Write the data
        writer.writerow(data)

def getUserInput(prompt: str, path_type: str) -> str:
    while True:
        user_input = input(prompt)
        
        if path_type == "directory" and os.path.isdir(user_input):
            print(f"Valid directory: {user_input}")
            return user_input
        elif path_type == "file" and os.path.isfile(user_input):
            print(f"Valid file: {user_input}")
            return user_input
        elif path_type == "string":
            return user_input
        elif path_type == "int":
            return user_input
        else:
            if path_type == "directory":
                os.mkdir(user_input)
                return user_input
            print(f"Invalid {path_type}. Please try again.")

def remove_video_files(path: str):
    if not os.path.exists(path):
        print(f"Path '{path}' does not exist.")
        return
    
    for root, dirs, files in os.walk(path, topdown=False):
        # Delete files containing '_video' in their name
        for file in files:
            if '_video' in file:
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    print(f"Deleted file: {file_path}")
                except Exception as e:
                    print(f"Failed to delete file {file_path}: {e}")
        
        # Delete folders containing '_video' in their name
        for dir in dirs:
            if '_video' in dir:
                dir_path = os.path.join(root, dir)
                try:
                    shutil.rmtree(dir_path)
                    print(f"Deleted folder: {dir_path}")
                except Exception as e:
                    print(f"Failed to delete folder {dir_path}: {e}")

def log_and_print(file_path, text):
    """
    Append text to file log
    """
    with open(file_path, 'a') as file: 
        file.write(str(text))
    
    print(text)
    
def parse_and_standardize(dob_str: str, default_format="MDY") -> str:
    """
    Parse a DOB string and return ISO8601 YYYY-MM-DD.
    default_format: "MDY" or "DMY" when ambiguous.
    """
    dob_str = dob_str.strip()
    if not dob_str:
        raise ValueError("Empty DOB")

    # Use dateutil to handle flexible input
    try:
        if default_format == "DMY":
            dobf = parser.parse(dob_str, dayfirst=True).date()
        else:  # MDY
            dobf = parser.parse(dob_str, dayfirst=False).date()
    except Exception as e:
        raise ValueError(f"Unsupported DOB: {dob_str} ({e})")

    return dobf

main()