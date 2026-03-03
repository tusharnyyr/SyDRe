"""
Tests for src/rules_reader.py
Covers: correct parsing, Rule ID assignment, edge cases
"""
import pytest
import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from rules_reader import load_rules


def write_rules_file(content: str) -> Path:
    """Helper — write content to a temp rules.txt and return path."""
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt",
                                      delete=False, encoding="utf-8")
    tmp.write(content)
    tmp.close()
    return Path(tmp.name)


# --- Correct parsing ---

def test_basic_parsing():
    path = write_rules_file(
        "1. Minimum turnover of 5 crore\n"
        "2. OEM authorization certificate\n"
        "3. GST registration certificate\n"
    )
    rules = load_rules(path)
    assert len(rules) == 3
    assert rules[0]["rule_text"] == "Minimum turnover of 5 crore"
    assert rules[1]["rule_text"] == "OEM authorization certificate"
    assert rules[2]["rule_text"] == "GST registration certificate"


def test_rule_ids_assigned_correctly():
    path = write_rules_file(
        "1. First rule\n2. Second rule\n3. Third rule\n"
    )
    rules = load_rules(path)
    assert rules[0]["rule_id"] == "R-01"
    assert rules[1]["rule_id"] == "R-02"
    assert rules[2]["rule_id"] == "R-03"


def test_rule_ids_zero_padded_beyond_nine():
    content = "\n".join(f"{i}. Rule number {i}" for i in range(1, 12))
    path = write_rules_file(content)
    rules = load_rules(path)
    assert rules[9]["rule_id"] == "R-10"
    assert rules[10]["rule_id"] == "R-11"


def test_single_rule_accepted():
    path = write_rules_file("1. Only one rule here\n")
    rules = load_rules(path)
    assert len(rules) == 1
    assert rules[0]["rule_id"] == "R-01"


# --- Edge cases ---

def test_blank_lines_ignored():
    path = write_rules_file(
        "\n1. First rule\n\n\n2. Second rule\n\n"
    )
    rules = load_rules(path)
    assert len(rules) == 2


def test_comment_lines_ignored():
    path = write_rules_file(
        "# This is a comment\n"
        "1. First rule\n"
        "This line has no number\n"
        "2. Second rule\n"
    )
    rules = load_rules(path)
    assert len(rules) == 2
    assert rules[0]["rule_text"] == "First rule"
    assert rules[1]["rule_text"] == "Second rule"


def test_leading_trailing_whitespace_stripped():
    path = write_rules_file("   1.   Rule with extra spaces   \n")
    rules = load_rules(path)
    assert rules[0]["rule_text"] == "Rule with extra spaces"


def test_empty_file_raises_value_error():
    path = write_rules_file("")
    with pytest.raises(ValueError, match="empty or incorrectly formatted"):
        load_rules(path)


def test_no_valid_rules_raises_value_error():
    path = write_rules_file(
        "# Only comments\nNo numbers here\nJust plain text\n"
    )
    with pytest.raises(ValueError, match="empty or incorrectly formatted"):
        load_rules(path)


def test_missing_file_raises_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_rules(Path("/nonexistent/path/rules.txt"))


def test_malformed_lines_skipped():
    path = write_rules_file(
        "1 Missing dot after number\n"
        "2. Valid rule\n"
        ".3 Dot before number\n"
    )
    rules = load_rules(path)
    assert len(rules) == 1
    assert rules[0]["rule_text"] == "Valid rule"
