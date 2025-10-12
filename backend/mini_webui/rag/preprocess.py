from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Tuple

MarkdownSegment = Tuple[str, Dict[str, object]]


def _parse_cells(line: str) -> List[str]:
    body = line.strip().strip("|")
    return [cell.strip() for cell in body.split("|")]


def _is_alignment_row(line: str) -> bool:
    stripped = (
        line.strip()
        .strip("|")
        .replace("|", "")
        .replace(":", "")
        .replace("-", "")
        .replace(" ", "")
        .replace("\t", "")
    )
    return stripped == ""


def preprocess_markdown_tables(text: str, source: str) -> List[MarkdownSegment]:
    """Expand markdown tables into natural language snippets with metadata.

    Returns a list of (text, metadata) pairs ready for downstream chunking.
    """
    lines = text.splitlines()
    segments: List[MarkdownSegment] = []
    buffer: List[str] = []
    current_heading: str | None = None
    path_stem = Path(source).stem

    def flush_buffer() -> None:
        if not buffer:
            return
        block = "\n".join(buffer).strip()
        if block:
            meta: Dict[str, object] = {"source": source}
            if current_heading:
                meta["heading"] = current_heading
            segments.append((block, meta))
        buffer.clear()

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("#"):
            flush_buffer()
            current_heading = stripped.lstrip("#").strip() or current_heading
            i += 1
            continue

        if "|" in line and i + 1 < len(lines) and _is_alignment_row(lines[i + 1]):
            flush_buffer()
            headers = [h or "列" for h in _parse_cells(line)]
            i += 2  # skip header + alignment
            row_index = 0
            while i < len(lines) and "|" in lines[i]:
                row_cells = _parse_cells(lines[i])
                if row_cells and any(cell.strip() for cell in row_cells):
                    row_index += 1
                    label = current_heading or path_stem
                    text_lines = [f"表: {label} 行 {row_index}"]
                    for header, cell in zip(headers, row_cells):
                        cell_value = cell.strip() or "(空欄)"
                        text_lines.append(f"{header}: {cell_value}")
                    meta: Dict[str, object] = {
                        "source": source,
                        "table": label,
                        "row_index": row_index,
                        "columns": headers,
                    }
                    segments.append(("\n".join(text_lines), meta))
                i += 1
            continue

        buffer.append(line)
        i += 1

    flush_buffer()
    return segments
