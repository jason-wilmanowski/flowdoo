"""Notes writes that addon code sends to the database directly, past the ORM.

Only table, columns and the calling code are kept, never the parameters, which can hold data.
"""

import re
import sys
import threading
from contextlib import contextmanager

from odoo.sql_db import Cursor

from .introspect import source_path

WRITE = re.compile(r"^\s*(UPDATE|INSERT\s+INTO|DELETE\s+FROM)\s+\"?(\w+)\"?", re.IGNORECASE)
SET_COLUMNS = re.compile(
    r"\bSET\s+(.*?)(?:\bWHERE\b|\bFROM\b|\bRETURNING\b|$)", re.IGNORECASE | re.DOTALL
)
INSERT_COLUMNS = re.compile(r"^\s*INSERT\s+INTO\s+\"?\w+\"?\s*\(([^)]*)\)", re.IGNORECASE)
ORM_FILES = ("/odoo/orm/", "/odoo/models/", "/odoo/fields")
SKIPPED_FILES = ("/odoo/sql_db.py", "/odoo/tools/")
MAX_WRITES = 200

_lock = threading.Lock()


@contextmanager
def recording():
    """Yields the list that collects the writes of this thread while the block runs."""
    writes = []
    thread = threading.get_ident()
    original = Cursor.execute

    def execute(self, query, params=None, log_exceptions=True):
        if threading.get_ident() == thread and len(writes) < MAX_WRITES:
            write = _direct_write(str(query))
            if write:
                writes.append(write)
        return original(self, query, params, log_exceptions)

    with _lock:
        Cursor.execute = execute
        try:
            yield writes
        finally:
            Cursor.execute = original


def _direct_write(query):
    found = WRITE.match(query)
    if not found:
        return None
    caller = _addon_caller()
    if caller is None:
        return None
    return {
        "operation": found.group(1).split()[0].upper(),
        "table": found.group(2),
        "columns": _columns(query),
        **caller,
    }


def _addon_caller():
    """The first frame outside the database layer; None if the ORM itself writes."""
    frame = sys._getframe(3)
    while frame is not None:
        filename = frame.f_code.co_filename
        if any(part in filename for part in ORM_FILES):
            return None
        if not any(part in filename for part in SKIPPED_FILES):
            return {
                "method": frame.f_code.co_name,
                "file": source_path(filename),
                "line": frame.f_lineno,
            }
        frame = frame.f_back
    return None


def _columns(query):
    found = INSERT_COLUMNS.match(query)
    if found:
        return [name.strip().strip('"') for name in found.group(1).split(",")]
    found = SET_COLUMNS.search(query)
    if not found:
        return []
    return re.findall(r"\"?(\w+)\"?\s*=", found.group(1))
