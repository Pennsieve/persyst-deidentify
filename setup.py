import os
from cx_Freeze import setup, Executable

exe_dir = os.path.dirname(os.path.abspath(__file__))
archive_template = os.path.join(exe_dir, r'archive-template.xml')
main = os.path.join(exe_dir, 'main.py')
icon = 'icons/icon.ico'

# Specify the script and additional files to include
additional_files = [(archive_template, r'archive-template.xml')]

# Create an executable
executables = [Executable('main.py',base=None, icon=icon)]

setup(
    name='SEED de-identify and convert',
    version='1.0',
    description='De-identifies convert BDF toEDF files',
    executables=executables,
    options={
        'build_exe': 
        {
            'include_files': additional_files,
            "packages": ["os", "sys","uuid","subprocess","datetime","pathlib"],
        }
    },
)