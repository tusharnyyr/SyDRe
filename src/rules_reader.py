import re
from pathlib import Path

RULES_FILE_PATH = Path(r"C:\SyDRe\rules.txt")


def load_rules(rules_path: Path = RULES_FILE_PATH) -> list[dict]:
    """
    Read and parse rules.txt.
    Expected format — numbered list, one rule per line:
        1. Rule text here
        2. Another rule here

    Returns a list of dicts:
        [{"rule_id": "R-01", "rule_text": "Rule text here"}, ...]

    Raises ValueError if the file is missing or contains zero valid rules.
    """
    if not rules_path.exists():
        raise FileNotFoundError(
            f"[rules_reader] rules.txt not found at: {rules_path}\n"
            f"Please create it at C:\\SyDRe\\rules.txt before running SyDRe."
        )

    rules = []
    pattern = re.compile(r"^\d+\.\s+(.+)$")

    with open(rules_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        match = pattern.match(line)
        if match:
            rule_text = match.group(1).strip()
            if rule_text:
                rules.append(rule_text)

    if not rules:
        raise ValueError(
            "[rules_reader] rules.txt is empty or incorrectly formatted.\n"
            "Each rule must start with a number, full stop, and space — e.g.:\n"
            "  1. Minimum turnover of 5 crore\n"
            "  2. OEM authorization certificate required"
        )

    # Assign Rule IDs: R-01, R-02, R-03 ...
    rule_objects = [
        {"rule_id": f"R-{str(i+1).zfill(2)}", "rule_text": text}
        for i, text in enumerate(rules)
    ]

    return rule_objects


if __name__ == "__main__":
    print(f"\nReading rules from: {RULES_FILE_PATH}\n")
    try:
        rules = load_rules()
        print(f"Parsed {len(rules)} rule(s):\n")
        for r in rules:
            print(f"  {r['rule_id']}: {r['rule_text']}")
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}")