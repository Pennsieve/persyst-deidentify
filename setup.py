import os
from cx_Freeze import setup, Executable

exe_dir = os.path.dirname(os.path.abspath(__file__))
archive_template = 'archive-template.xml'
icon = 'icons/icon.ico'

# Specify additional files to include
additional_files = [
    (archive_template, 'archive-template.xml'),
    (icon, 'icons/icon.ico')
]

# Create an executable
executables = [Executable('main.py', base=None, icon=icon, target_name='main.exe')]

setup(
    name='SEED de-identify and convert',
    version='1.0',
    description='De-identifies and converts BDF to EDF files',
    executables=executables,
    options={
        'build_exe': {
            'include_files': additional_files,
            'packages': ["os", "sys", "uuid", "subprocess", "datetime", "pathlib", "shutil", "cx_Freeze","csv", "re"],
            'zip_include_packages': ["os", "sys", "uuid", "subprocess", "datetime", "pathlib", "shutil","csv","cx_Freeze","re"],
            'include_msvcr': True,
        }
    },
)