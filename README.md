# Persyst auto de-identifier

Windows tool that drives Persyst Insight's `PSCLI.exe` to archive and
de-identify EEG studies. It matches a Persyst database export against a
user-supplied list of study codes and dates, converts the matching recordings,
and writes public and private metadata CSVs.

**Running the tool?** See [USER_GUIDE.md](USER_GUIDE.md) — that is the file to
send to whoever operates it.

## Requirements

- Windows, with Persyst installed and licensed at
  `C:\Program Files (x86)\Persyst\Insight` (provides `PSCLI.exe`)
- Python 3 and `cx_Freeze` to build (`pip install -r requirements.txt`)

## Run from source

```
python main.py                                    # interactive prompts
python main.py <input_csv> <output_dir> [db_csv] [-v]
```

## Build and release

```
python setup.py build     # cx_Freeze; output in build\exe.win-amd64-3.x\
python release.py         # clean build + verify bundled files + zip to dist\
```

`release.py` is the one to use. It fails if `main.exe`,
`archive-template.xml`, `verbose.bat`, or the icon is missing from the build —
cx_Freeze omits files silently otherwise. Ship the whole folder or the zip.

## Input formats

**Database CSV** — tab separated, columns in this order:
`Test Date`, `Duration`, `First Name`, `Last Name`, `Patient ID`,
`File Name With Path`, `DOB`. Pasted straight out of Persyst, unedited.

**Input CSV** — comma separated, no header:
`study_code, patient_id, date_of_service`.

Both are read as `utf-8-sig` so Excel's BOM does not corrupt the first field.

## Output

- `<output>\<study>\` — de-identified files plus `*_public.csv`
- `<output>_private\` — `worklog.txt`, `verbose.log`, `errors.csv`,
  `full-report-private.csv`, per-study `*_private.csv`. Contains PII; never
  upload to Pennsieve.

## Verbose mode

Double-click `verbose.bat`, or pass `-v` / `--verbose` on the command line.
Output goes to the screen **and** to `verbose.log` in the `_private` folder.

Per file it records: the resolved path, size, Windows attributes (EFS
encryption, cloud-only/OneDrive placeholders), whether the file can actually be
opened and read, the header in hex, the `.lay` companion data file, the exact
PSCLI command, and PSCLI's exit code, stdout, and stderr.

This is the first thing to turn on when a user reports files that will not
convert.
