"""Unit tests for citation validation."""
from app.rag.validate import REFUSAL_STRING, normalize_citations, validate_citations


def test_normalize_spaced_marker():
    assert normalize_citations("Salary is $412,000\u202f[ S1 ].") == "Salary is $412,000\u202f[S1]."


def test_normalize_grouped_markers():
    assert normalize_citations("See [S1, S3] and [S2;S4].") == "See [S1][S3] and [S2][S4]."


def test_spaced_marker_is_not_refused():
    answer, warn = validate_citations("The CFO's base salary is $412,000 [ S1 ].", ["S1", "S2"])
    assert answer == "The CFO's base salary is $412,000 [S1]."
    assert warn is False


def test_invalid_marker_stripped_and_uncited_refused():
    answer, warn = validate_citations("Made up fact [S9].", ["S1"])
    assert answer == REFUSAL_STRING
    assert warn is True


def test_mixed_valid_and_invalid():
    answer, warn = validate_citations("Fact [S1] and fiction [S7].", ["S1"])
    assert "[S1]" in answer and "[S7]" not in answer
    assert warn is True


def test_empty_answer_refused():
    assert validate_citations("", ["S1"])[0] == REFUSAL_STRING
    assert validate_citations(None, ["S1"])[0] == REFUSAL_STRING


def test_refusal_passthrough():
    assert validate_citations(REFUSAL_STRING, ["S1"]) == (REFUSAL_STRING, False)
