"""Tabular query and descriptive statistics over stored datasets.

Query dict keys (all optional): ``select``, ``where``, ``group_by``,
``aggregates``, ``order_by``, ``limit``.

Numeric coercion rule: a value "looks numeric" if it is an int/float
(not bool) or a string that parses as a float. Comparisons coerce both
sides to float when both look numeric; aggregates and ``describe``
operate over the numeric values of a column, skipping the rest.
"""

import math
import statistics

from .access import require
from .audit import actor_name
from .errors import ValidationError
from .store import _maybe_require

WHERE_OPS = ("eq", "ne", "lt", "le", "gt", "ge", "in", "contains")
AGG_FUNCS = ("count", "sum", "avg", "min", "max", "stddev")


def _is_numeric(value):
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return not (isinstance(value, float) and math.isnan(value))
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return False
        try:
            float(text)
        except ValueError:
            return False
        return True
    return False


def _num(value):
    """Return ``float(value)`` if it looks numeric, else None."""
    if not _is_numeric(value):
        return None
    return float(value)


def _clean(number):
    """Return an int for integral floats, else the float unchanged."""
    if isinstance(number, float) and number.is_integer():
        return int(number)
    return number


def _require_column(columns, column, context):
    if not isinstance(column, str) or column not in columns:
        raise ValidationError("unknown column in %s: %r" % (context, column))


def _validate_string_list(value, context):
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
        raise ValidationError("%s must be a list of column names" % (context,))
    return list(value)


# -- filtering --------------------------------------------------------

def _compare(cell, op, value):
    if op == "contains":
        if cell is None:
            return False
        return str(value) in str(cell)
    if op == "in":
        if not isinstance(value, (list, tuple)):
            raise ValidationError("'in' requires a list value")
        return any(_compare(cell, "eq", candidate) for candidate in value)

    cell_num = _num(cell)
    value_num = _num(value)
    if cell_num is not None and value_num is not None:
        left, right = cell_num, value_num
    elif op in ("eq", "ne"):
        left, right = cell, value
    else:
        left, right = ("" if cell is None else str(cell)), str(value)

    if op == "eq":
        return left == right
    if op == "ne":
        return left != right
    if op == "lt":
        return left < right
    if op == "le":
        return left <= right
    if op == "gt":
        return left > right
    if op == "ge":
        return left >= right
    raise ValidationError("unknown operator: %r" % (op,))


def _apply_where(rows, where, columns):
    if where is None:
        return list(rows)
    if not isinstance(where, list):
        raise ValidationError("'where' must be a list of conditions")
    conditions = []
    for cond in where:
        if not isinstance(cond, dict):
            raise ValidationError("each 'where' condition must be an object")
        column = cond.get("column")
        op = cond.get("op")
        _require_column(columns, column, "where")
        if op not in WHERE_OPS:
            raise ValidationError("unknown operator: %r" % (op,))
        if "value" not in cond:
            raise ValidationError("'where' condition is missing 'value'")
        conditions.append((column, op, cond["value"]))
    return [
        row
        for row in rows
        if all(_compare(row.get(col), op, val) for col, op, val in conditions)
    ]


# -- aggregation --------------------------------------------------------

def _aggregate(func, column, group_rows):
    if func == "count":
        if column in (None, "*"):
            return len(group_rows)
        return sum(1 for row in group_rows if row.get(column) is not None)
    numbers = []
    originals = []
    for row in group_rows:
        value = row.get(column)
        number = _num(value)
        if number is not None:
            numbers.append(number)
            originals.append(value)
    if func == "sum":
        return _clean(sum(numbers)) if numbers else 0
    if func == "avg":
        return (sum(numbers) / len(numbers)) if numbers else None
    if func == "min":
        if numbers:
            return _clean(min(numbers))
        values = [row.get(column) for row in group_rows if row.get(column) is not None]
        return min(values, key=lambda v: str(v)) if values else None
    if func == "max":
        if numbers:
            return _clean(max(numbers))
        values = [row.get(column) for row in group_rows if row.get(column) is not None]
        return max(values, key=lambda v: str(v)) if values else None
    if func == "stddev":
        if not numbers:
            return None
        if len(numbers) == 1:
            return 0.0
        return statistics.pstdev(numbers)
    raise ValidationError("unknown aggregate function: %r" % (func,))


def _apply_aggregates(rows, group_by, aggregates, columns):
    for agg in aggregates:
        if not isinstance(agg, dict):
            raise ValidationError("each aggregate must be an object")
        func = agg.get("func")
        if func not in AGG_FUNCS:
            raise ValidationError("unknown aggregate function: %r" % (func,))
        column = agg.get("column")
        if column not in (None, "*"):
            _require_column(columns, column, "aggregates")

    # Group preserving first-appearance order.
    groups = {}
    order = []
    if group_by:
        for row in rows:
            key = tuple(
                json_key(row.get(col)) for col in group_by
            )
            if key not in groups:
                groups[key] = (tuple(row.get(col) for col in group_by), [])
                order.append(key)
            groups[key][1].append(row)
    else:
        key = ()
        groups[key] = ((), list(rows))
        order.append(key)

    out_columns = list(group_by) + [
        agg.get("alias") or _default_alias(agg) for agg in aggregates
    ]
    out_rows = []
    for key in order:
        group_values, group_rows = groups[key]
        out = {}
        for col, val in zip(group_by, group_values):
            out[col] = val
        for agg in aggregates:
            alias = agg.get("alias") or _default_alias(agg)
            out[alias] = _aggregate(agg["func"], agg.get("column"), group_rows)
        out_rows.append(out)
    return out_columns, out_rows


def json_key(value):
    """A hashable grouping key for any stored value."""
    if isinstance(value, (str, int, float, bool)) or value is None:
        return (type(value).__name__, value)
    return ("repr", repr(value))


def _default_alias(agg):
    column = agg.get("column")
    if column in (None, "*"):
        return agg["func"]
    return "%s_%s" % (agg["func"], column)


# -- ordering / limit ---------------------------------------------------

def _apply_order_by(rows, order_by, out_columns):
    if order_by is None:
        return rows
    if not isinstance(order_by, list):
        raise ValidationError("'order_by' must be a list")
    specs = []
    for item in order_by:
        if not isinstance(item, dict):
            raise ValidationError("each 'order_by' entry must be an object")
        column = item.get("column")
        _require_column(out_columns, column, "order_by")
        direction = item.get("direction", "asc")
        if direction not in ("asc", "desc"):
            raise ValidationError("unknown sort direction: %r" % (direction,))
        specs.append((column, direction == "desc"))
    result = list(rows)
    for column, descending in reversed(specs):
        numeric = all(
            _is_numeric(row.get(column)) for row in result if row.get(column) is not None
        ) and any(row.get(column) is not None for row in result)

        def key_fn(row, column=column, numeric=numeric):
            value = row.get(column)
            if value is None:
                return (1, 0.0 if numeric else "")
            if numeric:
                return (0, float(value))
            return (0, str(value))

        result.sort(key=key_fn, reverse=descending)
    return result


def _apply_limit(rows, limit):
    if limit is None:
        return rows
    if isinstance(limit, bool):
        raise ValidationError("'limit' must be a non-negative integer")
    if isinstance(limit, str) and limit.strip().isdigit():
        limit = int(limit.strip())
    if not isinstance(limit, int) or limit < 0:
        raise ValidationError("'limit' must be a non-negative integer")
    return rows[:limit]


# -- public API -----------------------------------------------------------

def run_query(store, dataset_id, query, actor):
    """Run ``query`` over a dataset. Returns {columns, rows, row_count}."""
    _maybe_require(actor, "query")
    dataset = store.get(dataset_id)  # raises NotFoundError
    columns = dataset["columns"]
    if query is None:
        query = {}
    if not isinstance(query, dict):
        raise ValidationError("query must be an object")

    select = _validate_string_list(query.get("select"), "select")
    for col in select:
        _require_column(columns, col, "select")
    group_by = _validate_string_list(query.get("group_by"), "group_by")
    for col in group_by:
        _require_column(columns, col, "group_by")
    aggregates = query.get("aggregates") or []
    if not isinstance(aggregates, list):
        raise ValidationError("'aggregates' must be a list")

    rows = _apply_where(store.rows(dataset_id), query.get("where"), columns)

    if aggregates or group_by:
        # With aggregation present, select is ignored by contract.
        out_columns, out_rows = _apply_aggregates(rows, group_by, aggregates, columns)
    else:
        out_columns = select if select else list(columns)
        out_rows = [{col: row.get(col) for col in out_columns} for row in rows]

    out_rows = _apply_order_by(out_rows, query.get("order_by"), out_columns)
    out_rows = _apply_limit(out_rows, query.get("limit"))

    result = {"columns": out_columns, "rows": out_rows, "row_count": len(out_rows)}
    if getattr(store, "audit", None) is not None:
        store.audit.record(
            actor_name(actor), "query", dataset_id,
            details={"row_count": result["row_count"]},
        )
    return result


def describe(store, dataset_id, column, actor):
    """Descriptive statistics over the numeric values of ``column``.

    Returns {column, count, mean, median, min, max, stddev} with a
    population standard deviation. Raises ValidationError when the
    column is unknown or holds no numeric values.
    """
    _maybe_require(actor, "query")
    dataset = store.get(dataset_id)  # raises NotFoundError
    if column not in dataset["columns"]:
        raise ValidationError("unknown column: %r" % (column,))
    numbers = []
    for row in store.rows(dataset_id):
        number = _num(row.get(column))
        if number is not None:
            numbers.append(number)
    if not numbers:
        raise ValidationError("column %r has no numeric values" % (column,))
    result = {
        "column": column,
        "count": len(numbers),
        "mean": sum(numbers) / len(numbers),
        "median": float(statistics.median(numbers)),
        "min": _clean(min(numbers)),
        "max": _clean(max(numbers)),
        "stddev": statistics.pstdev(numbers) if len(numbers) > 1 else 0.0,
    }
    if getattr(store, "audit", None) is not None:
        store.audit.record(
            actor_name(actor), "describe", dataset_id,
            details={"column": column, "count": result["count"]},
        )
    return result
