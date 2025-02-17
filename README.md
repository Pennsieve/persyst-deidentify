This script will deidentify persyst files.

## Usage

`python main.py <input_CSV> <output_directory> [xml_template_path]`

or

`C:\>main.exe <input_CSV> <output_directory> [xml_template_path]`

or 

Run main.exe by double clicking.

## Assumptions
Script assumes you have a copy of Persyst installed with a valid license.

It is also assumed that Persyst is installed in the default location (C:\Program Files (x86)\Persyst\Insight)


## Usage

- Copy Rows to clipboard from Persyst Database
- Paste into a new file and save it. Do not make any edits to the copied file. Save this file as input.csv
- Create and output folder (eg `C:\output`)
- Double click the application
- Paste in the file path to the database when prompted. eg : `C:\input_file\database.csv`
- Ensure in your "Documents" folder you have an `input.csv` file which will filter out patients by patient ID and date
- Enter in the ouput path you created from before: `c:\output`
- Program will run and place output files in your output director
- full-report.csv contains information about the files converted
- Each sub folder also contains data about the files in that folder
- A private and public version of the CSV will be created
- Errors.csv will show any files which could not be converted