@echo off
REM Runs the de-identifier with detailed logging. Output is written to the
REM screen and to verbose.log in the <output>_private folder.
REM cd /d "%~dp0" is required: the program reads archive-template.xml from the
REM current directory, which is not this folder when launched from elsewhere.
cd /d "%~dp0"
main.exe -v
pause
