import subprocess
import os


PSCLI_DIRECTORY = r"C:\Program Files (x86)\Persyst\Insight"
os.environ["PATH"] += os.pathsep + PSCLI_DIRECTORY
pscli_command = [
    "PSCLI.exe",                       # PSCLI.exe
    # f'/SourceFile=C:\\Users\\defreitasd\\Desktop\\RICH~ MIA_dd20ffc6-03c7-4986-b1bd-833e8b910276',   # Input file
    "/SourceFile=C:\\Users\\defreitasd\\Downloads\\SUNUSIMU.bdf",
    '/FileType=EDF',
    '/Archive',                       # Archive option
    # f'/Options=seed-template.xml',       # options file
    '/OutputFile=C:\\seed\\file.edf'
]

result = subprocess.run(pscli_command, capture_output=True, text=True)
if result.returncode == 0:
    print(result.stdout)
    print("Successfully Archived")
else:
    print(result.stderr)
