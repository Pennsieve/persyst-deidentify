import os
import sys
import csv
import uuid
import subprocess

import pdb

# CSV indicies
DATE_TIME = 0
DURATION = 1
FIRST_NAME = 2
LAST_NAME = 3
PATIENT_ID = 4
PATH = 5

TEMPLATE_SUBSTITUTION_STRING = "$NEW_FILE_NAME"
OUTPUT_SUBSTITUTION_STRING = "$OUTPUT_DIRECTORY"
PSCLI_DIRECTORY = r"C:\Program Files (x86)\Persyst\Insight"

seen_patient_ids = {}



CSV_HEADERS = ["date_time","eeg_duration","first_name","last_name","patient_id","orignal_eeg_name","new_name"]

def main():
    """
    Uses the persyst cli to archive files, deidentifying them
    Script will also create CSVs with metadata about the outputs for future reference
    Script requires an input CSV, and output directory and optionally a path to an xml template as arguments
    If no xml template path is specified it is assumed that there is a file named `archive-template.xml` in the directory the script is running from
    """
    if len(sys.argv) < 2:
        print("Usage: python persyst_deidentify.py <input_CSV> <output_directory> [xml_template_path]")
        sys.exit(1)

    # Add PSCLI directory to the PATH for this run
    os.environ["PATH"] += os.pathsep + PSCLI_DIRECTORY

    # Get input arguments
    csv_path = sys.argv[1]
    output_base = sys.argv[2]

    # Use provided XML template path or fall back to default in script directory
    # Assumes template will be in same folder as this script
    xml_template_path = sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(__file__), "archive-template.xml")

    print(f"CSV input: {csv_path}")
    print(f"Output path: {output_base}")
    print(f"XML template: {csv_path}")

    if not os.path.exists(xml_template_path):
        print(f"XML template not found at {xml_template_path}")
        sys.exit(1)


    write_to_csv(CSV_HEADERS,os.path.join(output_base, "full-report.csv") )
    write_to_csv(CSV_HEADERS,os.path.join(output_base, "errors.csv") )
    # Open the CSV input file
    with open(csv_path, mode='r') as file:
        csv_reader = csv.reader(file)

        # Loop through each row in the CSV file
        for row in csv_reader:

            row_date_time = row[DATE_TIME]
            eeg_duration = row[DURATION]
            eeg_first_name = row[FIRST_NAME]
            eeg_last_name = row[LAST_NAME]
            eeg_patient_id = row[PATIENT_ID]
            eeg_path = row [PATH]

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

            csv_payload = [row_date_time,eeg_duration,eeg_first_name,eeg_last_name, eeg_patient_id, eeg_path,encoded_file_name if file_counter=="" else f"{encoded_file_name}_{file_counter}"]

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


main()