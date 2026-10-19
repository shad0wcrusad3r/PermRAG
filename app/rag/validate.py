"""Citation validation and answer post-processing."""
import re
from typing import List, Dict, Any


REFUSAL_STRING = "I couldn't find that in the documents available to you."


def extract_citations(answer: str) -> List[str]:
    """Extract citation markers like [S1], [S2] from answer."""
    return re.findall(r'\[S(\d+)\]', answer)


# Matches bracket groups made only of S-refs, tolerating whitespace and
# separators, e.g. "[ S1 ]", "[S 2]", "[S1, S3]", "[S1; S2]".
_LOOSE_CITATION_GROUP = re.compile(r'\[\s*S\s*\d+(?:\s*[,;]\s*S\s*\d+)*\s*\]')


def normalize_citations(answer: str) -> str:
    """Rewrite loosely formatted citation markers into canonical [S#] form.

    LLMs sometimes emit "[ S1 ]" or "[S1, S2]"; these are normalized to
    "[S1]" and "[S1][S2]" so strict validation doesn't misclassify them.
    """
    def _canon(match: re.Match) -> str:
        nums = re.findall(r'S\s*(\d+)', match.group(0))
        return "".join(f"[S{n}]" for n in nums)

    return _LOOSE_CITATION_GROUP.sub(_canon, answer)


def validate_citations(answer: str, valid_refs: List[str]) -> tuple[str, bool]:
    """Validate that all citations are from the provided sources.

    Args:
        answer: Generated answer with citations
        valid_refs: List of valid reference IDs (e.g., ["S1", "S2"])

    Returns:
        (cleaned_answer, has_warning)
    """
    if not answer:
        return REFUSAL_STRING, True

    if answer == REFUSAL_STRING:
        return answer, False

    answer = normalize_citations(answer)
    citations = extract_citations(answer)

    # Check if any citations are invalid
    valid_nums = {ref[1:] for ref in valid_refs}  # Extract numbers from "S1" -> "1"
    invalid = [c for c in citations if c not in valid_nums]

    if invalid:
        # Remove invalid citations
        for inv in invalid:
            answer = re.sub(rf'\[S{inv}\]', '', answer)

    # Check if answer has any valid citations
    remaining_citations = extract_citations(answer)

    if not remaining_citations and answer != REFUSAL_STRING:
        # No valid citations - replace with refusal
        return REFUSAL_STRING, True

    return answer.strip(), len(invalid) > 0
