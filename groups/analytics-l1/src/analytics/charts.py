"""Charts rendered as standalone SVG strings.

No JavaScript and no external assets: the returned string is a complete
SVG document fragment rooted at an ``<svg>`` element with an XML
namespace, ready to be served as ``image/svg+xml`` or embedded in a
report. Labels and titles are XML-escaped.
"""

import math
from xml.sax.saxutils import escape

from .errors import ValidationError

KINDS = ("bar", "line", "pie")

_WIDTH = 640
_HEIGHT = 400
_COLORS = [
    "#2563eb", "#dc2626", "#16a34a", "#d97706", "#7c3aed",
    "#0891b2", "#db2777", "#65a30d", "#475569", "#ea580c",
]


def _esc(text):
    return escape(str(text), {'"': "&quot;"})


def _num(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _wrap(parts, title):
    header = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
        'viewBox="0 0 %d %d" role="img">' % (_WIDTH, _HEIGHT, _WIDTH, _HEIGHT)
    )
    body = [header]
    if title:
        body.append(
            '<text x="%d" y="24" text-anchor="middle" font-family="sans-serif" '
            'font-size="16" font-weight="bold">%s</text>' % (_WIDTH // 2, _esc(title))
        )
    body.extend(parts)
    body.append("</svg>")
    return "\n".join(body)


def _no_data_svg(title):
    return _wrap(
        [
            '<text x="%d" y="%d" text-anchor="middle" font-family="sans-serif" '
            'font-size="14" fill="#666666">no data</text>'
            % (_WIDTH // 2, _HEIGHT // 2)
        ],
        title,
    )


def _extract(result, label_column, value_column):
    if not isinstance(result, dict):
        raise ValidationError("chart result must be an object")
    rows = result.get("rows") or []
    if not rows:
        return []
    columns = result.get("columns") or []
    if columns and label_column not in columns:
        raise ValidationError("unknown label column: %r" % (label_column,))
    if columns and value_column not in columns:
        raise ValidationError("unknown value column: %r" % (value_column,))
    pairs = []
    for row in rows:
        if isinstance(row, dict):
            label = row.get(label_column)
            raw_value = row.get(value_column)
        elif isinstance(row, (list, tuple)) and columns:
            label = row[columns.index(label_column)]
            raw_value = row[columns.index(value_column)]
        else:
            raise ValidationError("chart rows must be objects")
        number = _num(raw_value)
        pairs.append((label, number if number is not None else 0.0))
    return pairs


def _bar_chart(pairs, title):
    top = 50 if title else 30
    left, right, bottom = 56, 16, 44
    plot_w = _WIDTH - left - right
    plot_h = _HEIGHT - top - bottom
    baseline_y = top + plot_h
    max_val = max(value for _, value in pairs)
    min_val = min(0.0, min(value for _, value in pairs))
    span = (max_val - min_val) or 1.0
    zero_y = baseline_y - ((0.0 - min_val) / span) * plot_h
    slot = plot_w / len(pairs)
    bar_w = max(4.0, slot * 0.7)
    parts = [
        '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#999999"/>'
        % (left, top, left, baseline_y),
        '<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#999999"/>'
        % (left, zero_y, left + plot_w, zero_y),
    ]
    for i, (label, value) in enumerate(pairs):
        x = left + i * slot + (slot - bar_w) / 2
        height = abs(value) / span * plot_h
        y = zero_y - height if value >= 0 else zero_y
        color = _COLORS[i % len(_COLORS)]
        parts.append(
            '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
            % (x, y, bar_w, height, color)
        )
        parts.append(
            '<text x="%.1f" y="%.1f" text-anchor="middle" font-family="sans-serif" '
            'font-size="11">%s</text>'
            % (x + bar_w / 2, baseline_y + 16, _esc(label))
        )
        parts.append(
            '<text x="%.1f" y="%.1f" text-anchor="middle" font-family="sans-serif" '
            'font-size="11">%s</text>'
            % (x + bar_w / 2, (y - 4) if value >= 0 else (y + height + 13), _esc(value))
        )
    return _wrap(parts, title)


def _line_chart(pairs, title):
    top = 50 if title else 30
    left, right, bottom = 56, 16, 44
    plot_w = _WIDTH - left - right
    plot_h = _HEIGHT - top - bottom
    baseline_y = top + plot_h
    max_val = max(value for _, value in pairs)
    min_val = min(0.0, min(value for _, value in pairs))
    span = (max_val - min_val) or 1.0
    points = []
    for i, (label, value) in enumerate(pairs):
        if len(pairs) == 1:
            x = left + plot_w / 2
        else:
            x = left + i * (plot_w / (len(pairs) - 1))
        y = baseline_y - ((value - min_val) / span) * plot_h
        points.append((x, y, label, value))
    parts = [
        '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#999999"/>'
        % (left, top, left, baseline_y),
        '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#999999"/>'
        % (left, baseline_y, left + plot_w, baseline_y),
        '<polyline fill="none" stroke="%s" stroke-width="2" points="%s"/>'
        % (_COLORS[0], " ".join("%.1f,%.1f" % (x, y) for x, y, _, _ in points)),
    ]
    for x, y, label, value in points:
        parts.append('<circle cx="%.1f" cy="%.1f" r="3.5" fill="%s"/>' % (x, y, _COLORS[0]))
        parts.append(
            '<text x="%.1f" y="%.1f" text-anchor="middle" font-family="sans-serif" '
            'font-size="11">%s</text>' % (x, baseline_y + 16, _esc(label))
        )
    return _wrap(parts, title)


def _pie_chart(pairs, title):
    total = sum(value for _, value in pairs if value > 0)
    if total <= 0:
        return _no_data_svg(title)
    cx, cy, radius = _WIDTH // 2, _HEIGHT // 2 + 10, 140
    parts = []
    start = -math.pi / 2
    positive = [(label, value) for label, value in pairs if value > 0]
    for i, (label, value) in enumerate(positive):
        fraction = value / total
        color = _COLORS[i % len(_COLORS)]
        if len(positive) == 1 or fraction >= 0.999999:
            parts.append(
                '<circle cx="%d" cy="%d" r="%d" fill="%s"/>' % (cx, cy, radius, color)
            )
            end = start + fraction * 2 * math.pi
        else:
            end = start + fraction * 2 * math.pi
            x1 = cx + radius * math.cos(start)
            y1 = cy + radius * math.sin(start)
            x2 = cx + radius * math.cos(end)
            y2 = cy + radius * math.sin(end)
            large = 1 if fraction > 0.5 else 0
            parts.append(
                '<path d="M %d %d L %.1f %.1f A %d %d 0 %d 1 %.1f %.1f Z" fill="%s"/>'
                % (cx, cy, x1, y1, radius, radius, large, x2, y2, color)
            )
        mid = (start + end) / 2
        lx = cx + (radius + 22) * math.cos(mid)
        ly = cy + (radius + 22) * math.sin(mid)
        parts.append(
            '<text x="%.1f" y="%.1f" text-anchor="middle" font-family="sans-serif" '
            'font-size="11">%s</text>' % (lx, ly, _esc(label))
        )
        start = end
    return _wrap(parts, title)


def chart_svg(result, label_column, value_column, kind="bar", title=""):
    """Render ``result`` as a standalone SVG chart string."""
    if kind not in KINDS:
        raise ValidationError("unknown chart kind: %r" % (kind,))
    pairs = _extract(result, label_column, value_column)
    if not pairs:
        return _no_data_svg(title)
    if kind == "bar":
        return _bar_chart(pairs, title)
    if kind == "line":
        return _line_chart(pairs, title)
    return _pie_chart(pairs, title)
