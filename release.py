"""
Build the Windows release and check that everything the user needs is in it.

Run on Windows:  python release.py

cx_Freeze copies extra files in silently - if one is missing from setup.py's
include_files the build still succeeds and the user gets a broken folder. This
script fails loudly instead, then zips the result.
"""
import os
import glob
import shutil
import subprocess
import sys
from datetime import datetime

# Everything that must exist in the build folder, relative to it.
REQUIRED_FILES = [
    "main.exe",
    "archive-template.xml",
    "verbose.bat",
    os.path.join("icons", "icon.ico"),
]

BUILD_ROOT = "build"
DIST_DIR = "dist"


def main():
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(repo_dir)

    # 1. Build from scratch. A stale build folder hides a file that setup.py
    #    stopped copying.
    if os.path.isdir(BUILD_ROOT):
        print(f"Removing old {BUILD_ROOT}/")
        shutil.rmtree(BUILD_ROOT)

    print("Building...")
    result = subprocess.run([sys.executable, "setup.py", "build"])
    if result.returncode != 0:
        sys.exit(f"Build failed (exit {result.returncode})")

    # 2. Locate the build output. cx_Freeze names it for the platform and
    #    Python version, e.g. build/exe.win-amd64-3.11.
    candidates = glob.glob(os.path.join(BUILD_ROOT, "exe.*"))
    if len(candidates) != 1:
        sys.exit(f"Expected exactly one build folder, found: {candidates}")
    build_dir = candidates[0]
    print(f"Build folder: {build_dir}")

    # 3. Verify the files a user actually needs.
    missing = [f for f in REQUIRED_FILES
               if not os.path.exists(os.path.join(build_dir, f))]
    if missing:
        sys.exit("Missing from the build (add to include_files in setup.py): "
                 + ", ".join(missing))

    for name in REQUIRED_FILES:
        size = os.path.getsize(os.path.join(build_dir, name))
        print(f"  ok  {name} ({size} bytes)")

    # 4. Zip it. This is the file that gets sent out.
    os.makedirs(DIST_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d")
    archive_base = os.path.join(DIST_DIR, f"persyst-deidentify-{stamp}")
    archive_path = shutil.make_archive(archive_base, "zip", build_dir)
    print(f"\nRelease ready: {archive_path}")
    print("Send the whole zip. The user runs verbose.bat for a logged run.")


if __name__ == "__main__":
    main()
