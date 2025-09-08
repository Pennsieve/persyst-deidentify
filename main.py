import os
import sys
import csv
import uuid
import subprocess
import shutil

from datetime import datetime
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
    "pnt": "NihonKohden 2100"
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

def main():
    
    """
    Uses the persyst cli to archive files, deidentifying them
    Script will also create CSVs with metadata about the outputs for future reference
    Script requires an input CSV, and output directory and optionally a path to an xml template as arguments
    If no xml template path is specified it is assumed that there is a file named `archive-template.xml` in the directory the script is running from
    """
    
    search_num_days_before = 1
    search_num_days_after = 7

    if not os.path.isfile(PSCLI_DIRECTORY +'\\PSCLI.exe' ):
        log_and_print(os.path.join(private_files_path, LOG_FILE),f"Persyst not found in {PSCLI_DIRECTORY}. Exiting")
        input()
        sys.exit()

    if len(sys.argv) == 1:
       
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
        
    elif len(sys.argv) > 1:
        # Get input arguments
        input_csv_path = sys.argv[1]
        output_base = sys.argv[2]
        
        if not os.path.isfile(input_csv_path) or not os.path.isdir(output_base):
            log_and_print(os.path.join(private_files_path, LOG_FILE),"Usage: python persyst_deidentify.py <input_CSV> <output_directory> [xml_template_path]")
            sys.exit(1)

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

    # Open the CSV input file
    with open(db_location, mode='r') as file:
        database_reader = csv.DictReader(file,delimiter='\t')

        # Loop through each row in the CSV file
        for row in database_reader:
            if row[PATIENT_ID] not in database:
                database[row[PATIENT_ID]] = []
            database[row[PATIENT_ID]].append(row)

    with open(input_csv_path, newline="") as input_csv_file:
        machine_type = "XLTEK"
        input_csv_reader = csv.reader(input_csv_file)
        
        for row in input_csv_reader:
            print(f"Processing data row: {row}")
            patient_id = row[INPUT_PATIENT_ID]
            inputs[patient_id] = [row[INPUT_STUDY_ID], row[INPUT_DATE]]

            # Find record in database
            if patient_id in database:
                for record in database[patient_id]:
                    row_date_time = record[DATE_TIME]
                    eeg_duration = record[DURATION]
                    eeg_first_name = record[FIRST_NAME]
                    eeg_last_name = record[LAST_NAME]
                    eeg_patient_id = record[PATIENT_ID]
                    eeg_path = record[PATH]
                    dob = record[DOB]

                    _, extension = os.path.splitext(eeg_path)
                    extension = extension[1:]
                    print(f"Found file path with extension: {extension}")
                    if extension in FILE_TYPES:
                        print(f"Setting machine type to: {FILE_TYPES[extension]}")
                        machine_type = FILE_TYPES[extension]
                    else:
                        print(f"No matching file type. Supported options are : {FILE_TYPES}")
                        continue
 
                    dates_before = None
                    days_after = None
                    if eeg_patient_id in inputs:            
                        date_format = "%Y.%m.%d"
                        input_format = "%m/%d/%Y"
                        test_date, test_time = row_date_time.split()
                        datef = datetime.strptime(test_date, date_format)
                        search_datef = datetime.strptime(inputs[eeg_patient_id][1], input_format)

                        dobf = datetime.strptime(dob, "%m/%d/%Y" if re.search(r"\d{4}$", dob) else "%m/%d/%y")


                        age_in_days = (datef - dobf).days
                        
                        dates_before = search_datef - timedelta(days=search_num_days_before)
                        days_after = search_datef + timedelta(days=search_num_days_after)
                        log_and_print(os.path.join(private_files_path, LOG_FILE), f"Days after {days_after}")
                        log_and_print(os.path.join(private_files_path, LOG_FILE),f"Days before {dates_before}")
                        log_and_print(os.path.join(private_files_path, LOG_FILE),datef)
                        
                        if dates_before <= datef <= days_after or search_datef == datetime.strptime("11/11/1111", input_format) :

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
                                f'/FileType={machine_type} ',
                                f'/Archive',                       # Archive option
                                f'/Options={temp_xml_file}'       # options file
                            ]

                            # PSCLI.exe /SourceFile="ENTERED PATH" /Archive / Options ="TEMP XML FILE" 

                            result = subprocess.run(pscli_command, capture_output=True, text=True)
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
                                log_and_print(os.path.join(private_files_path, LOG_FILE),f"Failure on archive of: {eeg_path}")
                                write_to_csv(private_csv_payload,os.path.join(private_files_path, "errors.csv") )
                                log_and_print(os.path.join(private_files_path, LOG_FILE), result.stdout)
                                log_and_print(os.path.join(private_files_path, LOG_FILE), "done writing CSV")
                            
                            os.remove(temp_xml_file)
    remove_video_files(output_base)
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

main()