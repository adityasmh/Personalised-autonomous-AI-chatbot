# sql_validator.py
import re
from typing import List, Dict

def get_cased_identifiers(schema_identifiers: Dict[str, List[str]]) -> List[str]:
    cased = set()
    for item_type in ["tables", "columns"]:
        for ident in schema_identifiers.get(item_type, []):
            if not ident.islower():
                cased.add(ident)
    return sorted(list(cased), key=len, reverse=True)

def fix_sql_casing(query: str, cased_identifiers: List[str]) -> str:
    corrected = query

    for ident in cased_identifiers:
        # case-insensitive, whole word, not already in double quotes
        pattern = re.compile(rf'\b(?<!")({re.escape(ident)})\b(?!")', re.IGNORECASE)
        corrected = pattern.sub(f'"{ident}"', corrected)

    return corrected
