# Data Directory

This directory holds source data files used by the import pipeline.

## Expected Files

Place your Excel product export files here (`.xlsx` format). These files are **gitignored** to avoid committing large binary data to the repository.

## Column Reference

The file `columns.txt` lists the original Spanish column headers found in the source Excel files. These are mapped to normalized database fields via `COLUMN_MAPPING` in `backend/main.py`.
