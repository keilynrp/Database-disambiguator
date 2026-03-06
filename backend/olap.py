import re
import json
import logging

import duckdb
import pandas as pd

from backend.database import engine
from backend.schema_registry import registry

logger = logging.getLogger(__name__)

# Only allow attribute names that are valid SQL identifiers.
# This is a defense-in-depth check on top of the DataFrame column whitelist.
_SAFE_IDENTIFIER_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def _is_safe_identifier(name: str) -> bool:
    """Return True if name is a safe SQL identifier (no injection risk)."""
    return bool(_SAFE_IDENTIFIER_RE.match(name))


class DuckDBOLAPEngine:
    """
    In-Memory OLAP Engine leveraging DuckDB to build Data Cubes out of the
    domain-agnostic entities stored in SQLite.
    """

    @staticmethod
    def generate_cube_metrics(domain_id: str) -> dict:
        domain = registry.get_domain(domain_id)
        if not domain:
            raise ValueError(f"Domain '{domain_id}' not found")

        # 1. Load generic flat data from SQLite into pandas
        df = pd.read_sql_table("raw_entities", engine)

        # 2. Virtualize domain-specific view by unpacking `normalized_json`
        if "normalized_json" in df.columns:
            def safe_parse(val):
                if pd.isna(val) or not val:
                    return {}
                try:
                    return json.loads(val)
                except (ValueError, TypeError):
                    return {}

            json_df = df["normalized_json"].apply(safe_parse)
            for attr in domain.attributes:
                if not attr.is_core:
                    df[attr.name] = json_df.apply(lambda x, n=attr.name: x.get(n))

        # Build the set of columns that actually exist in the DataFrame.
        # This is the primary security whitelist: we only query columns we know exist.
        valid_columns: set[str] = set(df.columns)

        metrics: dict = {
            "domain_id": domain.id,
            "domain_name": domain.name,
            "total_records": 0,
            "distributions": {},
            "cube_metrics": {},
        }

        if len(df) == 0:
            return metrics

        con = duckdb.connect()
        con.register("df", df)

        metrics["total_records"] = con.execute("SELECT COUNT(*) FROM df").fetchone()[0]

        # 4. Multidimensional slice: distributions for all string attributes
        skip_fields = {"entity_name", "title", "sku", "gtin", "doi", "nct_id"}

        for attr in domain.attributes:
            if attr.name in skip_fields:
                continue

            # ── Security: whitelist check ────────────────────────────────────
            if attr.name not in valid_columns:
                # Column doesn't exist in the real data — skip silently
                continue

            if not _is_safe_identifier(attr.name):
                # Attribute name from YAML is not a safe SQL identifier — skip
                logger.warning(f"OLAP: skipping unsafe attribute name '{attr.name}'")
                continue
            # ─────────────────────────────────────────────────────────────────

            if attr.type == "string" or attr.name in df.columns:
                try:
                    # Use quoted identifiers to prevent any residual injection.
                    # attr.name is already validated above.
                    col = f'"{attr.name}"'
                    query = (
                        f"SELECT CAST({col} AS VARCHAR) AS label, "
                        f"COUNT(*) AS value "
                        f"FROM df "
                        f"WHERE {col} IS NOT NULL "
                        f"GROUP BY {col} "
                        f"ORDER BY value DESC "
                        f"LIMIT 8"
                    )
                    res_df = con.execute(query).df()

                    if not res_df.empty:
                        res_df["label"] = res_df["label"].replace(
                            {"None": "Unknown", "nan": "Unknown"}
                        )
                        metrics["distributions"][attr.label] = res_df.to_dict(orient="records")
                except Exception as e:
                    logger.debug(f"OLAP: skipping distribution for '{attr.name}': {e}")

        return metrics


olap_engine = DuckDBOLAPEngine()
