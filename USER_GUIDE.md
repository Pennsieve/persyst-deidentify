# De-identifying Persyst EEG files — user guide

This is the step-by-step guide for running the tool. If you are looking for
build or developer notes, see [README.md](README.md).

## Before you start

You need:

- Persyst installed with a valid licence, in the default location
  (`C:\Program Files (x86)\Persyst\Insight`). `PSCLI.exe` comes with it.
- The folder containing `main.exe` (the one we sent you). Keep it together —
  the program needs the other files in that folder.
- An output folder you have created, for example `C:\output`.

## Step 1 — Export the Persyst database

1. In the Persyst database, put the columns in this order:

   `Test Date`, `Duration`, `First Name`, `Last Name`, `Patient ID`,
   `File Name With Path`, `DOB`

2. Select the rows and copy them.
3. Paste into a new file and save it as `C:\database.csv`. **Do not edit
   anything after pasting**, and do not open and re-save it in Excel — Excel
   changes the formatting and the tool will not be able to read it.

The file is tab separated. It should look like this:

```
Test Date	Duration	First Name	Last Name	Patient ID	File Name With Path	DOB
2023.10.21   14:36:50	4d:15:15:35	XXXXXXX	XXXXXX	########	\\server\share\file.erd	12/15/1986
2023.02.12   11:01:00	00:26:17	XXXXX	XXXXX	########	\\server\share\file.erd	12/15/1986
```

## Step 2 — Make your input file

A plain CSV with three columns and **no header row**: study code, patient ID,
date of service.

```
a6sd5f14a,1234567,1/11/2020
a35sd61f,7654321,02/09/2024
654asdf,1234567,01/01/2020
```

Save it somewhere you can find it, for example `C:\input.csv`.

## Step 3 — Run the tool

Double-click **`main.exe`**, then answer the prompts:

- **Database location** — press Enter to accept `C:\database.csv`, or type `y`
  to point somewhere else.
- **Input CSV** — the full path, e.g. `C:\input.csv`.
- **Output folder** — the folder you created, e.g. `C:\output`.
- **Search window** — by default the tool looks for recordings from 1 day
  before to 7 days after each date of service. Type `y` to change it.

The tool then runs. Leave the window open until it says it is finished.

## Step 4 — Collect the results

Two folders are produced:

**`C:\output`** — the de-identified files. Safe to upload to Pennsieve.
Each study gets its own subfolder with a `_public.csv` describing it.

**`C:\output_private`** — ⚠️ **contains patient information. Never upload this
to Pennsieve.** It holds:

| File | What it is |
|---|---|
| `full-report-private.csv` | Every file converted, with original names |
| `errors.csv` | Files that could not be converted |
| `worklog.txt` | Log of the run |
| `verbose.log` | Detailed log, only when logging mode is on (below) |

## If files will not convert

Some files fail — usually because they are encrypted, stored somewhere the
program cannot read, or have been moved since the database was exported. To
help us work out which:

1. Open the program folder.
2. Double-click **`verbose.bat`** instead of `main.exe`.
3. Answer the same prompts as usual.

A lot more text scrolls past. You do not need to read it.

When the run finishes, send us **`verbose.log`** and **`errors.csv`** from the
`_private` folder.

⚠️ Those files contain patient information. Send them the way we normally
exchange patient data — not regular email.

## Notes

- To produce EDF output, set `output format` to `3` and `FileType` to `EDF90`
  in `archive-template.xml`.
- Video files are deleted after conversion unless `ExportEntireVideo` is set to
  `1` in `archive-template.xml`.
