import re
from typing import Any, Optional
import pandas as pd

def clean_numeric_str(val: Any) -> Optional[float]:
    """Cleans numeric values that may contain quotes (e.g. '-2.02), commas, or missing symbols."""
    if val is None or pd.isna(val):
        return None
    val_str = str(val).strip()
    if not val_str or val_str in ("-", "N/A", "NA", "null", "None"):
        return None
    # Strip single or double quotes, whitespace, and commas
    cleaned = val_str.replace("'", "").replace('"', "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def clean_int(val: Any) -> Optional[int]:
    """Converts a value to int if possible."""
    flt = clean_numeric_str(val)
    return int(round(flt)) if flt is not None else None


def clean_text(val: Any) -> str:
    """Cleans a string by stripping whitespace and BOM artifacts."""
    if val is None or pd.isna(val):
        return ""
    return str(val).strip().replace("\ufeff", "")


def load_clean_csv(filepath: str) -> pd.DataFrame:
    """Loads a CSV file handling UTF-8-SIG to strip BOM and clean column names."""
    df = pd.read_csv(filepath, encoding="utf-8-sig")
    df.columns = [c.strip().replace("\ufeff", "") for c in df.columns]
    return df
