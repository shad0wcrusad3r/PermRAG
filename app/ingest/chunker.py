"""Text chunking with heading awareness."""
import re
from typing import List, Tuple


def extract_headings(text: str) -> List[Tuple[int, str, str]]:
    """Extract markdown headings with their positions and levels.

    Returns list of (position, level_str, heading_text).
    """
    headings = []
    for match in re.finditer(r"^(#{1,6})\s+(.+)$", text, re.MULTILINE):
        headings.append((match.start(), match.group(1), match.group(2).strip()))
    return headings


def chunk_text(text: str, title: str, chunk_size: int = 1800, chunk_overlap: int = 200) -> List[dict]:
    """Chunk text with heading awareness.

    Args:
        text: The document text to chunk
        title: Document title for context
        chunk_size: Maximum characters per chunk
        chunk_overlap: Overlap between chunks

    Returns:
        List of chunk dictionaries with 'text' and 'heading_path'
    """
    # Extract headings
    headings = extract_headings(text)

    if not headings:
        # No headings - just split by size
        return _split_by_size(text, title, chunk_size, chunk_overlap)

    # Split on headings first
    sections = []
    for i, (pos, level, heading) in enumerate(headings):
        next_pos = headings[i + 1][0] if i + 1 < len(headings) else len(text)
        section_text = text[pos:next_pos].strip()
        sections.append((heading, section_text))

    # Now chunk each section
    chunks = []
    for heading, section_text in sections:
        if len(section_text) <= chunk_size:
            chunks.append({"text": section_text, "heading_path": heading})
        else:
            # Split large sections
            sub_chunks = _split_by_size(section_text, title, chunk_size, chunk_overlap)
            for sub_chunk in sub_chunks:
                sub_chunk["heading_path"] = heading
            chunks.extend(sub_chunks)

    return chunks


def _split_by_size(text: str, title: str, chunk_size: int, chunk_overlap: int) -> List[dict]:
    """Split text by size using separators."""
    separators = ["\n\n", "\n", ". ", " "]
    chunks = []

    start = 0
    while start < len(text):
        end = start + chunk_size

        if end >= len(text):
            # Last chunk
            chunks.append({"text": text[start:].strip(), "heading_path": title})
            break

        # Try to find a good break point
        best_break = end
        for sep in separators:
            # Look for separator near the end
            search_start = max(start, end - 100)
            pos = text.rfind(sep, search_start, end)
            if pos != -1:
                best_break = pos + len(sep)
                break

        chunk_text = text[start:best_break].strip()
        if chunk_text:
            chunks.append({"text": chunk_text, "heading_path": title})

        # Move start with overlap
        start = best_break if best_break == end else max(start + 1, best_break - chunk_overlap)

    return chunks
