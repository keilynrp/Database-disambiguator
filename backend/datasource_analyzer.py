import pandas as pd
import json
import xml.etree.ElementTree as ET
import os

class DataSourceAnalyzer:
    """
    A utility class to analyze different data sources and extract their schema, 
    columns, keys, or structural metadata.
    Supported formats: CSV, Excel, XML, JSON, JSON-LD, RDF, Logs, Parquet.
    """

    @staticmethod
    def analyze_csv(file_path: str) -> list[str]:
        df = pd.read_csv(file_path, nrows=5)
        return list(df.columns)

    @staticmethod
    def analyze_excel(file_path: str) -> list[str]:
        df = pd.read_excel(file_path, nrows=5)
        return list(df.columns)

    @staticmethod
    def analyze_json(file_path: str) -> list[str]:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        keys = set()
        if isinstance(data, dict):
            keys.update(data.keys())
        elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            for item in data[:10]:
                keys.update(item.keys())
        return list(keys)

    @staticmethod
    def analyze_jsonld(file_path: str) -> list[str]:
        # JSON-LD structural analysis is similar to JSON, but we highlight typical LD fields
        keys = DataSourceAnalyzer.analyze_json(file_path)
        return keys

    @staticmethod
    def analyze_xml(file_path: str) -> list[str]:
        tree = ET.parse(file_path)
        root = tree.getroot()
        tags = set()
        # Scan first few elements to prevent memory issues on huge XMLs
        for i, elem in enumerate(root.iter()):
            tags.add(elem.tag)
            if i > 1000:  
                break
        return list(tags)

    @staticmethod
    def analyze_rdf(file_path: str) -> list[str]:
        try:
            import rdflib
            g = rdflib.Graph()
            g.parse(file_path)
            predicates = set(g.predicates())
            return [str(p) for p in predicates]
        except ImportError:
            return ["Error: 'rdflib' is missing. Please run 'pip install rdflib' to analyze RDF files."]

    @staticmethod
    def analyze_log(file_path: str) -> list[str]:
        # Logs don't have columns, but we can extract sample lines or common patterns
        lines = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for i in range(5):
                line = f.readline()
                if not line:
                    break
                lines.append(f"Line {i+1}: {line.strip()}")
        return lines

    @staticmethod
    def analyze_dataframe(file_path: str) -> list[str]:
        # For serialized DataFrames like Parquet
        try:
            df = pd.read_parquet(file_path)
            return list(df.columns)
        except Exception:
            try:
                # Fallback to pickle
                df = pd.read_pickle(file_path)
                return list(df.columns)
            except Exception as e:
                return [f"Could not read DataFrame: {e}"]

    @classmethod
    def analyze(cls, file_path: str) -> list[str]:
        """
        Determines the appropriate analyzer based on file extension and returns structural metadata.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        
        routines = {
            '.csv': cls.analyze_csv,
            '.xlsx': cls.analyze_excel,
            '.xls': cls.analyze_excel,
            '.json': cls.analyze_json,
            '.jsonld': cls.analyze_jsonld,
            '.xml': cls.analyze_xml,
            '.rdf': cls.analyze_rdf,
            '.ttl': cls.analyze_rdf,
            '.log': cls.analyze_log,
            '.txt': cls.analyze_log,
            '.parquet': cls.analyze_dataframe,
            '.pkl': cls.analyze_dataframe
        }
        
        if ext in routines:
            return routines[ext](file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
