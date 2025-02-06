import os
import sys
import csv
import uuid
import subprocess
from datetime import datetime

from pathlib import Path
from datetime import datetime, timedelta

# CSV indicies
DATE_TIME = 'Test Date'
DURATION = 'Duration'
FIRST_NAME = 'First Name'
LAST_NAME = 'Last Name'
PATIENT_ID = 'Patient ID'
PATH = 'File Name With Path'

TEMPLATE_SUBSTITUTION_STRING = "$NEW_FILE_NAME"
OUTPUT_SUBSTITUTION_STRING = "$OUTPUT_DIRECTORY"
PSCLI_DIRECTORY = r"C:\Program Files (x86)\Persyst\Insight"

seen_patient_ids = {}

CSV_HEADERS = ["new_name","first_name","last_name","patient_id","date_time","eeg_duration","orignal_eeg_name","runtime"]

def main():
    
    """
    Uses the persyst cli to archive files, deidentifying them
    Script will also create CSVs with metadata about the outputs for future reference
    Script requires an input CSV, and output directory and optionally a path to an xml template as arguments
    If no xml template path is specified it is assumed that there is a file named `archive-template.xml` in the directory the script is running from
    """

    if not os.path.isfile(PSCLI_DIRECTORY +'\\PSCLI.exe' ):
        print(f"Persyst not found in {PSCLI_DIRECTORY}. Exiting")
        input()
        sys.exit()

    if len(sys.argv) == 1:
       csv_path = getUserInput("Please enter complete file path to CSV: ", "file")
       output_base = getUserInput("Please enter output path to save de-identified files: ", "directory")
        
    elif len(sys.argv) > 1:
        # Get input arguments
        csv_path = sys.argv[1]
        output_base = sys.argv[2]
        
        if not os.path.isfile(csv_path) or not os.path.isdir(output_base):
            print("Usage: python persyst_deidentify.py <input_CSV> <output_directory> [xml_template_path]")
            sys.exit(1)

    # Add PSCLI directory to the PATH for this run
    os.environ["PATH"] += os.pathsep + PSCLI_DIRECTORY
    documents_path = Path.home() / "Documents"

    exe_dir = os.path.dirname(os.path.abspath(__file__))
    exe_dir = os.getcwd()
    key_path = os.path.join(exe_dir, r'archive-template.xml')
    xml_template_path = key_path



    print(f"CSV input: {csv_path}")
    print(f"Output path: {output_base}")
    print(f"XML template: {xml_template_path}")

    if not os.path.exists(xml_template_path):
        print(f"XML template not found at {xml_template_path}")
        sys.exit(1)


    write_to_csv(CSV_HEADERS,os.path.join(output_base, "full-report.csv") )
    write_to_csv(CSV_HEADERS,os.path.join(output_base, "errors.csv") )

    inputs = {}

    with open(f"{documents_path}\\input.csv", newline="") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            key = row[0]
            value = row[1]
            inputs[key] = value


    # Open the CSV input file
    with open(csv_path, mode='r') as file:
        csv_reader = csv.DictReader(file,delimiter='\t')

        # Loop through each row in the CSV file
        for row in csv_reader:

            row_date_time = row[DATE_TIME]
            eeg_duration = row[DURATION]
            eeg_first_name = row[FIRST_NAME]
            eeg_last_name = row[LAST_NAME]
            eeg_patient_id = row[PATIENT_ID]
            eeg_path = row [PATH]

            if eeg_patient_id in inputs.keys():    
                two_days_before = None
                two_days_after = None
                if inputs[eeg_patient_id] != None:            
                    date_format = "%Y.%m.%d"
                    row_date, _ = row_date_time.split()
                    row_date_time = datetime.strptime(row_date, date_format)
                    search_date = datetime.strptime(inputs[eeg_patient_id], date_format)
                    
                    two_days_before = search_date - timedelta(days=2)
                    two_days_after = search_date + timedelta(days=2)

                if two_days_before <= row_date_time <= two_days_after or search_date == datetime.strptime("1111.11.11", date_format) :

                    file_counter = ""
                    if eeg_patient_id in seen_patient_ids:
                        seen_patient_ids[eeg_patient_id]['count']+=1
                        file_counter = seen_patient_ids[eeg_patient_id]['count']
                        folder = seen_patient_ids[eeg_patient_id]['filename']
                        encoded_file_name = f"{ seen_patient_ids[eeg_patient_id]['filename']}"
                    else:
                        # never seen before patient ID
                        seen_patient_ids[eeg_patient_id] = {'filename': genShortUUID() , 'count': 1} 
                        encoded_file_name = seen_patient_ids[eeg_patient_id]['filename']
                        folder = seen_patient_ids[eeg_patient_id]['filename']

                    temp_xml_file = os.path.join(output_base, f"{encoded_file_name}-config.xml")
                    output_location = os.path.join(output_base, folder)
                    current_datetime = datetime.now()

                    csv_payload = [encoded_file_name if file_counter=="" else f"{encoded_file_name}_{file_counter}",eeg_first_name,eeg_last_name, eeg_patient_id,row_date_time,eeg_duration, eeg_path,current_datetime]

                    try:
                        os.mkdir(output_location)
                    except FileExistsError:
                        print(f"Directory '{output_location}' already exists.")

                    # write CSV header
                    if os.path.exists(os.path.join(output_location, f"{encoded_file_name}.csv")):
                        pass # do not write header
                    else:
                        write_to_csv(CSV_HEADERS,os.path.join(output_location, f"{encoded_file_name}.csv") )

                    # Read XML template, replace $ with layFileName, and write to temp XML file
                    with open(xml_template_path, 'r') as template_file, open(temp_xml_file, 'w') as output_file:
                        for line in template_file:
                            if file_counter =="":
                                rewrite_name = encoded_file_name
                            else:
                                rewrite_name = f"{encoded_file_name}-{file_counter}"
                            modified_line = line.replace(TEMPLATE_SUBSTITUTION_STRING, f"{rewrite_name}.lay")
                            modified_line = modified_line.replace(OUTPUT_SUBSTITUTION_STRING, output_location)
                            output_file.write(modified_line)
                
                    # Run the PSCLI command using the .lay file as the source and the temp XML as /Options
                    pscli_command = [
                        "PSCLI.exe",                       # PSCLI.exe
                        f'/SourceFile={eeg_path}',   # Input file
                        '/Archive',                       # Archive option
                        f'/Options={temp_xml_file}'       # options file
                    ]

                    result = subprocess.run(pscli_command, capture_output=True, text=True)
                    if result.returncode == 0:
                        write_to_csv(csv_payload,os.path.join(output_base, "full-report.csv") )
                        write_to_csv(csv_payload,os.path.join(output_location, f"{encoded_file_name}.csv") )
                        print(result.stdout)
                        print("Successfully Archived")
                    else:
                        print(f"Failure on archive of: {eeg_path}")
                        write_to_csv(csv_payload,os.path.join(output_base, "errors.csv") )
                        print("done writing CSV")
                        print(result.stderr)
                    os.remove(temp_xml_file)
    input("Converstion complete. See output folder for results. \nHit enter or close this window")

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
        path = input(prompt)
        
        if path_type == "directory" and os.path.isdir(path):
            print(f"Valid directory: {path}")
            return path
        elif path_type == "file" and os.path.isfile(path):
            print(f"Valid file: {path}")
            return path
        else:
            print(f"Invalid {path_type}. Please try again.")


main()