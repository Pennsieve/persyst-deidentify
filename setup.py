import os
from cx_Freeze import setup, Executable

exe_dir = os.path.dirname(os.path.abspath(__file__))
archive_template = 'archive-template.xml'
icon = 'icons/icon.ico'
verbose_launcher = 'verbose.bat'

# Specify additional files to include
additional_files = [
    (archive_template, 'archive-template.xml'),
    (icon, 'icons/icon.ico'),
    # Double-clicking main.exe cannot pass -v, so ship a launcher that does.
    (verbose_launcher, 'verbose.bat')
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
            'packages': ["os", "sys", "uuid", "subprocess", "datetime", "pathlib", "shutil", "cx_Freeze","csv", "re","dateutil","xml"],
            'zip_include_packages': ["os", "sys", "uuid", "subprocess", "datetime", "pathlib", "shutil","csv","cx_Freeze","re","dateutil","xml"],
            'include_msvcr': True,
            'replace_paths': [("*", "")],
        }
    },
)