## How persyst-deidentify Handles De-identification

### Overview

This tool de-identifies EEG recordings by leveraging Persyst's command-line tool (`PSCLI.exe`) to strip patient-identifying information from EEG file headers and uniformly shift all dates by a random offset. It takes in a batch of patient records (via CSV), matches them against a database of EEG files, processes each through PSCLI with de-identification enabled, and produces anonymized output files alongside audit reports.

### De-identification Process

#### 1. Header Scrubbing (via PSCLI)

The core de-identification is performed by `PSCLI.exe`, controlled by the `archive-template.xml` configuration file. The key setting is:

```xml
<Value name="Deindentify">1</Value>
```

When this is set to `1`, PSCLI strips identifiable patient fields from the EEG header. In the resulting `.lay` file, the `[Patient]` section has its fields blanked:

| Field | Result |
|-------|--------|
| First, Last, MI | Blanked |
| Sex, Hand | Blanked |
| ID, MedicalRecordN | Blanked |
| Physician, Technician | Blanked |
| Medications, History | Blanked |
| Comments1, Comments2 | Blanked |
| BirthDate | Replaced with age (e.g., "13 yo") |

#### 2. Date Shifting

PSCLI randomly shifts all dates in the file uniformly. This means every date within a single file is shifted by the same random offset, preserving relative timing between events. The shift amount is determined internally by PSCLI on each invocation — the tool does not control or record the shift amount.

Affected dates include `TestDate`, `StudyDate`, and `[SampleTimes]` values in the `.lay` file.

#### 3. Filename Anonymization

The tool generates a new anonymized filename for each output file using the format:

```
<study_code>_<truncated_uuid>
```

For example: `STUDY001_8d770595`. The study code comes from the input CSV, and a 7-character UUID segment is appended to ensure uniqueness. This replaces the original filename, which may have contained patient names.

For patients with multiple EEG records, subsequent files are suffixed: `STUDY001_8d770595-2`, `STUDY001_8d770595-3`, etc.

### Output

The tool produces two separate output directories to enforce a clear boundary between de-identified data that is safe to share and sensitive data that must remain within the institution's network.

#### Public Folder (`<output_directory>/`)

This folder contains de-identified data that is ready for sharing outside the institution. It includes:

- **De-identified EEG files** (`.dat` + `.lay` pairs) — produced by PSCLI with patient header fields blanked, dates shifted, and filenames anonymized
- **Public CSV** (per study): Contains only non-identifying metadata — `new_name`, `age_in_days_at_time_of_eeg`, `eeg_start_time`, `eeg_duration`, `date_of_csv_creation`

Everything in this folder has been processed to remove patient-identifying information and can be distributed to collaborators or uploaded to external platforms.

#### Private Folder (`<output_directory>_private/`)

This folder contains records that link de-identified data back to original patient information. It is intended solely for internal audit and record-keeping and **must not leave the institution's network**. It includes:

- **Private CSV** (per study): Maps the anonymized filename back to the original patient name, patient ID, original EEG filename, and original EEG date
- **`full-report-private.csv`**: A summary of all successful conversions with full patient details
- **`errors.csv`**: Records of any failed conversions, including patient details for troubleshooting
- **`worklog.txt`**: Detailed processing log

The private folder is created automatically with a `_private` suffix on the output directory name, making it easy to identify and exclude from any data sharing workflows.

### Known Limitations

1. **Annotations/Comments are not scrubbed.** The `[Comments]` section in the `.lay` file passes through unmodified. If technicians or systems record patient-identifying information in annotations (e.g., "Patient John Smith arrived"), that PII will remain in the output.

2. **Date shift amount is not recorded.** Since PSCLI controls the random date shift internally, there is no way to reverse the shift or know the original dates from the output alone. The private CSV does record the original EEG date for audit purposes.

