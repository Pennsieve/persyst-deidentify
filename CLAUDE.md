# CLAUDE.md — persyst-deidentify

Windows desktop tool (single `main.py`, frozen with cx_Freeze) that drives
Persyst Insight's `PSCLI.exe` to archive/de-identify EEG studies. It reads a
tab-delimited Persyst database CSV plus a user-supplied input CSV, matches
studies by patient ID and a date window, and writes de-identified output plus
public/private metadata CSVs.

## Run / build

```
python main.py                                  # interactive prompts
python main.py <input_csv> <output_dir> [db_csv] [-v]
python setup.py build                           # cx_Freeze, Windows only
```

The build lands in `build\exe.win-amd64-3.x\` with `archive-template.xml`,
the icon, and `verbose.bat` copied alongside `main.exe`. Ship the whole folder.
`verbose.bat` exists because a double-clicked exe cannot be given `-v`; it also
`cd /d "%~dp0"` first, since the template is read from the current directory.

There are no tests. `main()` is called at import time at the bottom of
`main.py`, so importing the module runs the program — exec the parsed AST with
the trailing call stripped if you need to test helpers.

## Layout of outputs

- `<output_dir>/<study>/` — de-identified EDF + `*_public.csv`
- `<output_dir>_private/` — `worklog.txt`, `verbose.log`, `errors.csv`,
  `full-report-private.csv`, per-study `*_private.csv`

## Gotchas

- **Both CSVs are opened `utf-8-sig`.** Excel's "CSV UTF-8" export prepends a
  BOM that otherwise glues `ï»¿` onto the first field (it corrupted study IDs
  and output filenames). Don't change this back to plain `"r"`.
- **The database CSV is TAB delimited**, the input CSV is comma delimited. A
  comma-delimited database parses as one column and every lookup silently
  misses; verbose mode warns about this.
- **PSCLI failures are opaque.** Non-zero exit with nothing useful on stdout.
  `describe_source_file()` runs first and covers the usual causes: missing
  path, no read permission, EFS-encrypted for another user, cloud-only
  placeholder, zero bytes, `.lay` pointing at a missing `.dat`.
- Video files are deleted after the run unless `ExportEntireVideo` is `1` in
  the XML template.
- The XML template is read from `os.getcwd()`, not the exe directory — run from
  the install folder.

## Questions

- Does PSCLI have its own log or `/Verbose` flag we should be capturing? Not
  checked yet.
