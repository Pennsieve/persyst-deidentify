---
description: Build the Windows release, verify the bundled files, and zip it
---

Cut a release of this tool.

1. Run `python release.py` (Windows only — cx_Freeze produces a Windows exe).
   It cleans `build/`, rebuilds, checks that `main.exe`,
   `archive-template.xml`, `verbose.bat`, and `icons/icon.ico` are all present
   in the build folder, then writes a zip to `dist/`.
2. If it reports a missing file, add it to `additional_files` in `setup.py` and
   run again. Do not hand-copy the file into `build/` — the next build drops it.
3. Report the zip path and the verified file list.

If we are not on Windows, say so and stop rather than producing a broken
artifact. Do not commit anything in `build/` or `dist/`.
