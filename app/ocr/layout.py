"""把检测框按阅读顺序拼成文本。"""
from __future__ import annotations

import statistics
from typing import Iterable, Sequence

Box = Sequence[Sequence[float]]
Item = tuple[Box, str, float]

LINE_MERGE_RATIO = 0.6


def _metrics(box: Box) -> tuple[float, float, float, float]:
    xs = [float(p[0]) for p in box]
    ys = [float(p[1]) for p in box]
    return (min(xs), min(ys), max(xs), max(ys))


def boxes_to_text(items: Iterable[Item]) -> str:
    """按行分组：y 中心接近的并入同一行，行内按 x 排序，行间换行。"""
    entries = []
    for box, text, _score in items:
        if not text:
            continue
        x0, y0, x1, y1 = _metrics(box)
        entries.append({"x": x0, "cy": (y0 + y1) / 2, "h": max(y1 - y0, 1.0), "text": text})
    if not entries:
        return ""

    entries.sort(key=lambda e: e["cy"])

    lines: list[list[dict]] = []
    line_centers: list[float] = []
    line_heights: list[list[float]] = []

    for entry in entries:
        if lines:
            tolerance = LINE_MERGE_RATIO * statistics.median(line_heights[-1])
            if abs(entry["cy"] - line_centers[-1]) <= tolerance:
                lines[-1].append(entry)
                line_heights[-1].append(entry["h"])
                line_centers[-1] = statistics.mean(e["cy"] for e in lines[-1])
                continue
        lines.append([entry])
        line_centers.append(entry["cy"])
        line_heights.append([entry["h"]])

    return "\n".join(
        " ".join(e["text"] for e in sorted(line, key=lambda e: e["x"])) for line in lines
    )
