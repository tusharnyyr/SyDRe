"""
SyDRe — Systematic Document Retrieval
Entry point for command-line execution.

Usage:
    python main.py                          # processes all ZIPs in input\
    python main.py --zip input\vendor.zip   # processes a single ZIP
    python main.py --top 10                 # override top N (default 5)
    python main.py --rules path\to\rules.txt
"""

import argparse
import sys
import zipfile
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / "src"))

from rules_reader import load_rules
from pipeline import run_pipeline
from excel_writer import write_excel


def write_run_log(run_log: list[str], output_dir: str = r"C:\SyDRe\output"):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = output_path / f"SyDRe_RunLog_{timestamp}.txt"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"SyDRe Run Log — {timestamp}\n")
        f.write("=" * 60 + "\n\n")
        for line in run_log:
            f.write(line + "\n")
    print(f"  Run log : {log_path}")
    return str(log_path)


def main():
    parser = argparse.ArgumentParser(description="SyDRe — Systematic Document Retrieval")
    parser.add_argument("--zip", default=None, help="Path to a single vendor ZIP. Omit to process all ZIPs in input\\")
    parser.add_argument("--top", type=int, default=5, help="Top N pages per rule (default: 5)")
    parser.add_argument("--rules", default=r"C:\SyDRe\rules.txt", help="Path to rules.txt")
    args = parser.parse_args()

    rules_path = Path(args.rules)
    input_dir = Path(r"C:\SyDRe\input")

    # --- Resolve ZIP list ---
    if args.zip:
        zip_files = [Path(args.zip)]
        if not zip_files[0].exists():
            print(f"\nERROR: ZIP file not found: {zip_files[0]}")
            sys.exit(1)
    else:
        zip_files = sorted(input_dir.glob("*.zip"))
        if not zip_files:
            print(f"\nERROR: No ZIP files found in {input_dir}")
            print(f"Place vendor ZIP files in {input_dir} and run again.")
            sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  SyDRe — Systematic Document Retrieval")
    print(f"{'='*60}")
    print(f"  Vendors to process : {len(zip_files)}")
    for z in zip_files:
        print(f"    • {z.name}")

    # --- Load rules ---
    print(f"\nLoading rules from: {rules_path}")
    try:
        rules = load_rules(rules_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"\nERROR: {e}")
        sys.exit(1)

    print(f"Loaded {len(rules)} rule(s):")
    for r in rules:
        print(f"  {r['rule_id']}: {r['rule_text']}")

    # --- Process each vendor ZIP ---
    all_results = []
    all_logs = []
    failed_zips = []

    for idx, zip_path in enumerate(zip_files, start=1):
        print(f"\n[{idx}/{len(zip_files)}] Processing: {zip_path.name}")
        print("-" * 50)
        try:
            results, run_log = run_pipeline(str(zip_path), rules, top_n=args.top)
            all_results.extend(results)
            all_logs.append(f"\n{'='*50}")
            all_logs.append(f"VENDOR: {zip_path.name}")
            all_logs.append(f"{'='*50}")
            all_logs.extend(run_log)
        except FileNotFoundError as e:
            msg = f"SKIPPED {zip_path.name}: File not found — {e}"
            print(f"\nWARNING: {msg}")
            failed_zips.append(zip_path.name)
            all_logs.append(msg)
        except zipfile.BadZipFile as e:
            msg = f"SKIPPED {zip_path.name}: Corrupt ZIP — {e}"
            print(f"\nWARNING: {msg}")
            failed_zips.append(zip_path.name)
            all_logs.append(msg)
        except ValueError as e:
            msg = f"SKIPPED {zip_path.name}: {e}"
            print(f"\nWARNING: {msg}")
            failed_zips.append(zip_path.name)
            all_logs.append(msg)

    if not all_results:
        print("\nERROR: No results generated from any vendor ZIP.")
        sys.exit(1)

    # --- Write combined outputs ---
    print(f"\n{'='*60}")
    print(f"  All vendors processed. Writing combined output...")
    output_file = write_excel(all_results)
    write_run_log(all_logs)

    print(f"\n{'='*60}")
    print(f"  SyDRe run complete.")
    print(f"  Vendors processed  : {len(zip_files) - len(failed_zips)} of {len(zip_files)}")
    if failed_zips:
        print(f"  Failed / skipped   : {', '.join(failed_zips)}")
    print(f"  Total result rows  : {len(all_results)}")
    print(f"  Results            : {output_file}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()