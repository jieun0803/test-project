#!/usr/bin/env python3
"""Validate OSS NOTICE HTML structure and library ordering."""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path


class NoticeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.sections: list[dict] = []
        self._current: dict | None = None
        self._in_license_pre = False
        self._license_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "section" and attrs_dict.get("class") == "oss-library":
            self._current = {
                "id": attrs_dict.get("id", ""),
                "name": "",
                "license": "",
                "license_text": "",
            }
        elif tag == "h3" and self._current is not None:
            self._capture_h3 = True
        elif tag == "pre" and self._current is not None:
            class_attr = attrs_dict.get("class", "")
            if class_attr and "license-text" in class_attr:
                self._in_license_pre = True
                self._license_chunks = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "section" and self._current is not None:
            self._current["license_text"] = "".join(self._license_chunks).strip()
            self.sections.append(self._current)
            self._current = None
        elif tag == "pre" and self._in_license_pre:
            self._in_license_pre = False

    def handle_data(self, data: str) -> None:
        if self._current is None:
            return
        if self._in_license_pre:
            self._license_chunks.append(data)
            return
        if getattr(self, "_capture_h3", False):
            self._current["name"] = data.strip()
            self._capture_h3 = False
            return
        m = re.search(r"License:\s*(\S+)", data, re.IGNORECASE)
        if m:
            self._current["license"] = m.group(1)


def validate_notice(path: Path) -> list[str]:
    errors: list[str] = []
    content = path.read_text(encoding="utf-8")
    parser = NoticeParser()
    parser.feed(content)

    if not parser.sections:
        errors.append("No <section class='oss-library'> blocks found")
        return errors

    names = [s["name"] for s in parser.sections]
    sorted_names = sorted(names, key=str.lower)
    if names != sorted_names:
        errors.append(f"Libraries not in alphabetical order: {names}")

    ids = [s["id"] for s in parser.sections if s["id"]]
    if len(ids) != len(set(ids)):
        errors.append("Duplicate section IDs detected")

    for section in parser.sections:
        label = section["name"] or section["id"] or "unknown"
        if not section["name"]:
            errors.append(f"{label}: missing library name (h3)")
        if not section["license"]:
            errors.append(f"{label}: missing License line")
        if len(section["license_text"]) < 20:
            errors.append(f"{label}: license text too short or missing")

    return errors


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: validate-notice.py <notice.html>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"ERROR: File not found: {path}", file=sys.stderr)
        return 2

    errors = validate_notice(path)
    if errors:
        print("VALIDATION FAILED")
        for err in errors:
            print(f"  - {err}")
        return 1

    print(f"VALIDATION PASSED: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
