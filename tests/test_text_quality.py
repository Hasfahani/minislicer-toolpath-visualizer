"""Repository text-quality checks for demo-facing polish."""

from pathlib import Path

TEXT_EXTENSIONS = {".md", ".py", ".txt"}
SKIPPED_PARTS = {".git", ".pytest_cache", ".venv", "__pycache__"}
MOJIBAKE_MARKERS = ("\u00c3", "\u00c2", "\u00e2")


def _text_files() -> list[Path]:
    root = Path(__file__).resolve().parents[1]
    return [
        path
        for path in root.rglob("*")
        if path.suffix in TEXT_EXTENSIONS
        and not any(part in SKIPPED_PARTS for part in path.parts)
    ]


def test_text_files_are_ascii_clean() -> None:
    offenders: list[str] = []

    for path in _text_files():
        text = path.read_text(encoding="utf-8")
        if any(ord(char) > 127 for char in text):
            offenders.append(str(path))

    assert offenders == []


def test_text_files_do_not_contain_mojibake_markers() -> None:
    offenders: list[str] = []

    for path in _text_files():
        text = path.read_text(encoding="utf-8")
        if any(marker in text for marker in MOJIBAKE_MARKERS):
            offenders.append(str(path))

    assert offenders == []
