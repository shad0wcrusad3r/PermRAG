"""Text cleaning and normalization."""
import re
import unicodedata


def clean_text(text: str) -> str:
    """Clean and normalize text content."""
    # Unicode NFKC normalization
    text = unicodedata.normalize("NFKC", text)

    # Collapse 3+ newlines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip trailing whitespace from each line
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)

    return text.strip()
