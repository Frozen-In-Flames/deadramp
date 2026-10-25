"""Dataset store: open-format ingest plus a dataset registry.

Datasets are ingested from CSV or JSON text. CSV values are stored as
strings; JSON values keep their native types. Numeric interpretation is
deliberately deferred to the query / describe layer.

Ingest is all-or-nothing: malformed input raises
:class:`ValidationError` and leaves the store (including the id
sequence) completely unchanged.
"""

import copy
import csv
import io
import json
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, ValidationError


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _maybe_require(actor, action):
    """Enforce permissions when ``actor`` is a User-like object.

    Plain string actors carry identity (for provenance) but no role, so
    there is nothing to enforce against; enforcement for those happens
    in the service layer, which knows the role registry.
    """
    if actor is not None and hasattr(actor, "role"):
        require(actor, action)


def _validate_name(name):
    if not isinstance(name, str) or not name.strip():
        raise ValidationError("dataset name must be a non-empty string")
    return name


def _parse_csv(text):
    """Parse CSV text into (columns, rows). Raises ValidationError."""
    if not isinstance(text, str) or not text.strip():
        raise ValidationError("CSV input must be a non-empty string")
    try:
        reader = csv.reader(io.StringIO(text))
        raw_rows = [row for row in reader if row != []]
    except csv.Error as exc:
        raise ValidationError("malformed CSV: %s" % (exc,)) from exc
    if not raw_rows:
        raise ValidationError("CSV input has no header row")
    columns = raw_rows[0]
    if not columns or any(not isinstance(c, str) or c == "" for c in columns):
        raise ValidationError("CSV header contains an empty column name")
    if len(set(columns)) != len(columns):
        raise ValidationError("CSV header contains duplicate column names")
    rows = []
    for line_no, raw in enumerate(raw_rows[1:], start=2):
        # A completely blank line parses to ['']; treat it as absent only
        # when the dataset has more than one column is unsafe, so instead
        # a short/long row is a hard validation error.
        if len(raw) != len(columns):
            raise ValidationError(
                "CSV row %d has %d fields, expected %d"
                % (line_no, len(raw), len(columns))
            )
        rows.append(dict(zip(columns, raw)))
    return columns, rows


def _columns_from_records(records):
    columns = []
    for record in records:
        for key in record:
            if key not in columns:
                columns.append(key)
    return columns


def _parse_json(text):
    """Parse JSON text into (columns, rows). Raises ValidationError."""
    if not isinstance(text, str) or not text.strip():
        raise ValidationError("JSON input must be a non-empty string")
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ValidationError("malformed JSON: %s" % (exc,)) from exc

    declared_columns = None
    records = None
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict) and "rows" in data:
        if "columns" in data:
            declared_columns = data["columns"]
            if (
                not isinstance(declared_columns, list)
                or any(not isinstance(c, str) or c == "" for c in declared_columns)
                or len(set(declared_columns)) != len(declared_columns)
            ):
                raise ValidationError("JSON 'columns' must be a list of unique names")
        records = data["rows"]
        if not isinstance(records, list):
            raise ValidationError("JSON 'rows' must be a list")
    else:
        raise ValidationError(
            "JSON input must be an array of objects or an object with 'rows'"
        )

    rows = []
    if declared_columns is not None and records and isinstance(records[0], list):
        for raw in records:
            if not isinstance(raw, list) or len(raw) != len(declared_columns):
                raise ValidationError("JSON row does not match declared columns")
            rows.append(dict(zip(declared_columns, raw)))
        return list(declared_columns), rows

    for item in records:
        if not isinstance(item, dict):
            raise ValidationError("JSON rows must be objects")
        rows.append(dict(item))
    columns = list(declared_columns) if declared_columns is not None else _columns_from_records(rows)
    # Normalize: every row carries every column (missing -> None).
    normalized = [{col: row.get(col) for col in columns} for row in rows]
    return columns, normalized


class DatasetStore:
    """In-memory registry of ingested datasets."""

    def __init__(self, audit=None):
        self.audit = audit
        self._datasets = {}  # id -> dataset dict
        self._rows = {}  # id -> list of row dicts
        self._order = []  # ids in ingest order
        self._counter = 0
        self._lock = threading.RLock()

    # -- ingest -----------------------------------------------------

    def ingest_csv(self, name, text, actor):
        """Ingest CSV ``text`` as dataset ``name`` on behalf of ``actor``."""
        columns, rows = _parse_csv(text)
        return self._commit(name, columns, rows, actor)

    def ingest_json(self, name, text, actor):
        """Ingest JSON ``text`` as dataset ``name`` on behalf of ``actor``."""
        columns, rows = _parse_json(text)
        return self._commit(name, columns, rows, actor)

    def _commit(self, name, columns, rows, actor):
        # All parsing/validation happened before this point, so a commit
        # cannot fail part-way: state changes only for valid input.
        _validate_name(name)
        _maybe_require(actor, "ingest")
        with self._lock:
            self._counter += 1
            dataset_id = "ds-%d" % (self._counter,)
            dataset = {
                "id": dataset_id,
                "name": name,
                "columns": list(columns),
                "row_count": len(rows),
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._datasets[dataset_id] = dataset
            self._rows[dataset_id] = copy.deepcopy(rows)
            self._order.append(dataset_id)
            if self.audit is not None:
                self.audit.record(
                    actor_name(actor),
                    "ingest",
                    dataset_id,
                    details={"name": name, "row_count": len(rows)},
                )
            return self._copy_dataset(dataset)

    # -- access -------------------------------------------------------

    @staticmethod
    def _copy_dataset(dataset):
        copied = dict(dataset)
        copied["columns"] = list(dataset["columns"])
        return copied

    def get(self, dataset_id):
        """Return the dataset dict for ``dataset_id``."""
        with self._lock:
            dataset = self._datasets.get(dataset_id)
            if dataset is None:
                raise NotFoundError("dataset not found: %r" % (dataset_id,))
            return self._copy_dataset(dataset)

    def list(self):
        """Return all dataset dicts, in ingest order."""
        with self._lock:
            return [self._copy_dataset(self._datasets[ds_id]) for ds_id in self._order]

    def rows(self, dataset_id):
        """Return a deep copy of the rows of ``dataset_id``."""
        with self._lock:
            if dataset_id not in self._datasets:
                raise NotFoundError("dataset not found: %r" % (dataset_id,))
            return copy.deepcopy(self._rows[dataset_id])
