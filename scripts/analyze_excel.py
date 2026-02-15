"""Utility script to extract column names from a source Excel file.

Usage:
    python scripts/analyze_excel.py <path_to_excel_file>

Output is written to data/columns.txt.
"""

import pandas as pd
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if len(sys.argv) > 1:
    file_path = sys.argv[1]
else:
    # Default: look in data/ for the first .xlsx file
    data_dir = os.path.join(ROOT_DIR, "data")
    xlsx_files = [f for f in os.listdir(data_dir) if f.endswith(".xlsx")]
    if not xlsx_files:
        print("No .xlsx files found in data/. Pass a file path as argument.")
        sys.exit(1)
    file_path = os.path.join(data_dir, xlsx_files[0])
    print(f"Using: {file_path}")

if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
    sys.exit(1)

try:
    df = pd.read_excel(file_path, nrows=5)
    output_path = os.path.join(ROOT_DIR, "data", "columns.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        for col in df.columns:
            f.write(f"{col}\n")
    print(f"Columns saved to {output_path}")
except Exception as e:
    print(f"Error reading Excel file: {e}")
    sys.exit(1)
