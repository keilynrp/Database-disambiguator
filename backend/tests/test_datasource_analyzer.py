import pytest
from fastapi.testclient import TestClient
import pandas as pd
import json
import os
import tempfile
import xml.etree.ElementTree as ET

# Import the FastAPI app
from backend.main import app

client = TestClient(app)

# --- Fixture Generators for Multidimensional Scaling ---
# These functions dynamically create temporary data source files with scaling complexities.

def create_temp_csv(rows: int, cols: int) -> str:
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    df = pd.DataFrame(
        data=[[f"val_{r}_{c}" for c in range(cols)] for r in range(rows)],
        columns=[f"col_{c}" for c in range(cols)]
    )
    df.to_csv(path, index=False)
    return path

def create_temp_json(rows: int, nested: bool) -> str:
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    
    data = []
    for r in range(rows):
        if nested:
            obj = {f"key_{i}": {"sub_key": f"val_{r}"} for i in range(5)}
        else:
            obj = {f"key_{i}": f"val_{r}" for i in range(5)}
        data.append(obj)
        
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return path

def create_temp_xml(rows: int) -> str:
    fd, path = tempfile.mkstemp(suffix=".xml")
    os.close(fd)
    
    root = ET.Element("dataset")
    for r in range(rows):
        record = ET.SubElement(root, "record")
        ET.SubElement(record, "id").text = str(r)
        ET.SubElement(record, "name").text = f"Item {r}"
        ET.SubElement(record, "price").text = f"{r * 10.5}"
        
    tree = ET.ElementTree(root)
    tree.write(path, encoding="utf-8", xml_declaration=True)
    return path

def create_temp_parquet(rows: int, cols: int) -> str:
    fd, path = tempfile.mkstemp(suffix=".parquet")
    os.close(fd)
    df = pd.DataFrame(
        data=[[f"val_{r}_{c}" for c in range(cols)] for r in range(rows)],
        columns=[f"col_{c}" for c in range(cols)]
    )
    df.to_parquet(path)
    return path


# --- Parametrization Matrix for Multidimensional Iterative Testing ---
@pytest.mark.parametrize("format_type, rows, cols_or_nested", [
    # (Format, rows scaling, dimensions scaling)
    ("csv", 10, 5),      # Baseline 1D
    ("csv", 1000, 50),   # Scaling 2D: More rows, more cols
    ("json", 10, False), # Baseline Flat JSON
    ("json", 500, True), # Scaling JSON: Nested Large Array
    ("xml", 5, 0),       # Baseline XML
    ("xml", 5000, 0),    # Scaling XML: Testing stream threshold
    ("parquet", 20, 10), # Baseline Binary DataFrame
])
def test_analyze_endpoint_multidimensional_scaling(format_type, rows, cols_or_nested):
    """
    Iterative multidimensional parameter test to ensure the `/analyze` endpoint
    scales appropriately and extracts schema vectors across different formats and depths.
    """
    temp_file = None
    try:
        if format_type == "csv":
            temp_file = create_temp_csv(rows, cols_or_nested)
            expected_count = cols_or_nested
        elif format_type == "json":
            temp_file = create_temp_json(rows, cols_or_nested)
            expected_count = 5 # As statically defined in our generator
        elif format_type == "xml":
            temp_file = create_temp_xml(rows)
            # ROOT + <record> + <id> + <name> + <price> = 5 unique tags
            expected_count = 5 
        elif format_type == "parquet":
            temp_file = create_temp_parquet(rows, cols_or_nested)
            expected_count = cols_or_nested
            
        with open(temp_file, "rb") as f:
            response = client.post("/analyze", files={"file": (os.path.basename(temp_file), f, "application/octet-stream")})
            
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure extraction
        assert "structure" in data, "Response must contain 'structure' metadata"
        assert data["format"] == format_type
        assert data["count"] == expected_count, f"Expected {expected_count} columns/keys, got {data['count']}"
        assert len(data["structure"]) == expected_count

    finally:
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)

def test_analyze_unsupported_format():
    """Validates negative testing constraints"""
    fd, path = tempfile.mkstemp(suffix=".xyz")
    os.close(fd)
    
    try:
        with open(path, "w") as f:
            f.write("fake data")
    
        with open(path, "rb") as f:
            response = client.post("/analyze", files={"file": ("test.xyz", f, "text/plain")})
            
        assert response.status_code == 400
        assert "Unsupported file format" in response.json()["detail"]
    finally:
        os.remove(path)
