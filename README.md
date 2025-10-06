# Persyst auto de-identifer

This script will deidentify persyst files.

Run main.exe by double clicking.

## Assumptions
Script assumes 
- You have a copy of Persyst installed with a valid license.
- Persyst is installed in the default location (C:\Program Files (x86)\Persyst\Insight)
- PSCLI.exe is available in it's default location (C:\Program Files (x86)\Persyst\Insight). Should be part of default Persyst installation
- Persyst database has the columns `Test Date	Duration	First Name	Last Name	Patient ID	File Name With Path	DOB` in that order as a Tab separated file

## Usage

- Ensure rows in Persyst database are in the order:`Test Date	Duration	First Name	Last Name	Patient ID	File Name With Path	DOB`
- Copy Rows to clipboard from Persyst Database
- Paste into a new file and save it. Do not make any edits to the copied file. Save this file as database.csv to your root C: drive
- Double click the application
- You will be promoted if you want to use the default location the database file is expected to be found: `C:\database.csv`. You can place it elsewhere if needed
- You will be prompted for your input file. Enter its location eg C:\input.csv
- The input csv expects you to have the 3 columns `study_code, patient_id, date_of_service`. Note: you don't need the column headers, just the data that matches those requirements in that order
- The script will search for files from the date of service to 7 days after.
- Enter in the ouput path you created from before: `c:\output`
- Program will run and place output files in your output directory
- Another directory with `_private` will also be generated. This directory should NOT be uploaded to Pennsieve. It contains logs from the conversion process which will have PII.
- full-report.csv contains information about the files converted
- Each sub folder also contains data about the files in that folder
- Errors.csv will show any files which could not be converted
- For EDF output set `output format` to 3 and `FileType` to EDF90 in `archive-template.xml`


## Example of what database.csv should look like

```
Test Date	Duration	First Name	Last Name	Patient ID	File Name With Path	Active	Station DOB
2023.10.21   14:36:50	4d:15:15:35	XXXXXXX	XXXXXX	########	\\natusprodnas.chop.edu\NatusProdArc\NeuroworksArc\dbdata\file.erd, 12/15/1986
2023.02.12   11:01:00	00:26:17	XXXXX	XXXXX	########	\\natusprodnas.chop.edu\NatusProdArc\NeuroworksArc\dbdata\file.erd, 12/15/1986
2023.01.01   04:34:35	00:01:18	XXXXX	XXXXXX	########	\\natusprodnas.chop.edu\NatusProdArc\NeuroworksArc\dbdata\file.erd, 12/15/1986
2023.08.20   07:00:17	23:59:27	XXXXXX	XXXXXX	########	\\natusprodnas.chop.edu\NatusProdArc\NeuroworksArc\dbdata\file.erd, 12/15/1986
2023.08.19   07:00:16	23:56:01	XXXXX	XXXXX	########	\\natusprodnas.chop.edu\NatusProdArc\NeuroworksArc\dbdata\file.erd, 12/15/1986
2023.08.18   07:00:17	23:58:06	XXXXX	XXXXXX	########	\\natusprodnas.chop.edu\NatusProdArc\NeuroworksArc\dbdata\file.erd, 12/15/1986
```

## Example of input.csv
```
a6sd5f14a,1234567,1/11/2020
a35sd61f,7654321,02/09/2024
654asdf,1234567,01/01/2020
a51ds61fa,7654321,12/14/2022
wd6hs3,1234567,03/15/2023
684rth64strh,7654321,03/10/2023
561a68fewa,1234567,06/01/2023
a68148ew4,7654321,12/14/2023
```
