"""Loaders for different document formats."""
from pathlib import Path


def load_markdown(file_path: Path) -> str:
    """Load a markdown file and return its text content."""
    return file_path.read_text(encoding="utf-8")


def load_text(file_path: Path) -> str:
    """Load a plain text file and return its content."""
    return file_path.read_text(encoding="utf-8")
