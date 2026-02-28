"""Utility script to extract the structure (columns, keys, tags, predicates)
from various data sources (CSV, JSON, JSON-LD, XML, Logs, DataFrames, RDF).

Usage:
    python scripts/analyze_datasource.py <path_to_file>

Output is printed and saved to data/structure_analysis.txt.
"""

import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

from backend.datasource_analyzer import DataSourceAnalyzer

if len(sys.argv) < 2:
    print("Usage: python scripts/analyze_datasource.py <path_to_file>")
    print("Supported formats: .csv, .xlsx, .json, .jsonld, .xml, .rdf, .ttl, .log, .parquet, .pkl")
    sys.exit(1)

file_path = sys.argv[1]

if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
    sys.exit(1)

print(f"Analyzing: {file_path}...")

try:
    results = DataSourceAnalyzer.analyze(file_path)
    print("\n--- Detected Structure / Keys / Columns ---")
    for r in results:
        print(r)
        
    output_path = os.path.join(ROOT_DIR, "data", "structure_analysis.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(f"{r}\n")
    print(f"\nResults saved to {output_path}")

except Exception as e:
    print(f"\nError analyzing file: {e}")
    sys.exit(1)
