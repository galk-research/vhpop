#!/usr/bin/env python3
import argparse
import csv
import os
import re
import shutil
import tempfile
import zipfile
import sys
from pathlib import Path
import bz2

# --- Regular Expressions ---
# Flaw Selection Regexes
RE_START = re.compile(r'^Selecting a flaw from')
RE_CANDIDATE_LL = re.compile(
    r'^\s*#<(?P<id>[^>]+)>.*?LL:\s*(?P<ll>X|\d+)\b'
)
RE_CANDIDATE_ADD = re.compile(
    r'^\s*#<(?P<id>[^>]+)>.*?ADD_WORK:\s*(?P<add>\d+)\b'
)
RE_HANDLE = re.compile(r'^\s*handle #<(?P<id>[^>]+)>')
RE_CANDIDATE = re.compile(
    r"#<([^>]+)> LL: (\S+) .*? ADD_WORK: (\d+)"
)

# Log Parsing Regexes
RE_GENERATED = re.compile(r"^Plans generated:\s*(\d+)")
RE_VISITED = re.compile(r"^Plans visited:\s*(\d+)")
RE_DEAD = re.compile(r"^Dead ends encountered:\s*(\d+)")
RE_STEPS = re.compile(r"^Number of steps:\s*(\d+)")
RE_ID = re.compile(r"\(id\s+(\d+)\)")
RE_VISITLINE = re.compile(r"^(\d+):.*CURRENT PLAN")

# --- Constants ---
GOAL_ID = '18446744073709551615'

def parse_flaw(line):
    match = RE_CANDIDATE.search(line)
    if match:
        id_val = match.group(1)
        ll_val = match.group(2)
        add_work_val = int(match.group(3))
        return id_val, ll_val, add_work_val
    else:
        raise ValueError("Line format is invalid")

def parse_trace_file(trace_path):
    """
    Parses a single trace file in one pass to extract all required metrics.

    Args:
        trace_path (Path): The path to the trace log file.

    Returns:
        dict: A dictionary containing all the parsed metrics.
    """
    # --- Metric Initialization ---
    metrics = {
        "plans_until_landmark": None,
        "flaws_reopened": 0,
        "landmarks_reopened": 0,
        "add_work_wins": 0.0,
        "add_work_rounds": 0,
        "gen": None,
        "vis": None,
        "dead": None,
        "steps": None,
        "max_id": 0,
        "max_vis": 0,
    }

    # --- State Variables ---
    in_block = False
    candidates_ll = {}
    candidates_add = {}
    open_flaws = set()
    current_plans = 0
    done = False

    with open(trace_path, 'r', buffering=2**20, encoding='utf-8', errors='ignore') as f:
        for line in f:

            # --- Log Parsing ---
            m_gen = RE_GENERATED.match(line)
            if m_gen: 
                metrics["gen"] = int(m_gen.group(1))
                done = True

            if done:
                m_vis = RE_VISITED.match(line)
                if m_vis: metrics["vis"] = int(m_vis.group(1))

                m_dead = RE_DEAD.match(line)
                if m_dead: metrics["dead"] = int(m_dead.group(1))

                m_steps = RE_STEPS.match(line)
                if m_steps: metrics["steps"] = int(m_steps.group(1))

            for m_id in RE_ID.finditer(line):
                metrics["max_id"] = max(metrics["max_id"], int(m_id.group(1)))

            m_visitline = RE_VISITLINE.match(line)
            if m_visitline:
                metrics["max_vis"] = max(metrics["max_vis"], int(m_visitline.group(1)))

            # --- Flaw Selection Parsing ---
            if RE_START.match(line):
                # Process the end of the *previous* block if RE_HANDLE wasn't found
                if in_block:
                    in_block = False # Reset without processing handle

                # Start a new flaw-selection round
                current_plans += 1
                in_block = True
                candidates_ll.clear()
                candidates_add.clear()
                continue

            if in_block:
                # Collect candidate LL values
                # m_ll = RE_CANDIDATE_LL.match(line)
                # if m_ll and GOAL_ID not in m_ll.group('id'):
                #     candidates_ll[m_ll.group('id')] = m_ll.group('ll')
                #     continue

                # # Collect candidate ADD_WORK values
                # m_add = RE_CANDIDATE_ADD.match(line)
                # if m_add:
                #     candidates_add[m_add.group('id')] = int(m_add.group('add'))
                #     continue
                try:
                    flaw_id, ll, add = parse_flaw(line)
                    if GOAL_ID not in flaw_id:  # Skip the goal ID
                        candidates_ll[flaw_id] = ll
                    candidates_add[flaw_id] = add
                except ValueError:
                    # Look for the actual selection (handle)
                    m_handle = RE_HANDLE.match(line)
                    if m_handle:
                        chosen_id = m_handle.group('id')
                        in_block = False  # End of the current block

                        # --- Calculate metrics for this round ---

                        # 1. Plans Until Landmark
                        chosen_ll = candidates_ll.get(chosen_id)
                        if metrics["plans_until_landmark"] is None and chosen_ll and chosen_ll != 'X':
                            metrics["plans_until_landmark"] = current_plans

                        # 2. Flaws Reopened
                        is_landmark = chosen_ll and chosen_ll != 'X'
                        if chosen_id in open_flaws:    
                            # Only count if it was a candidate in this round (had LL/ADD)
                            if chosen_id in candidates_add:
                                metrics["flaws_reopened"] += 1
                            if is_landmark:
                                metrics["landmarks_reopened"] += 1
                        else:
                            open_flaws.add(chosen_id)

                        # 3. Add Work
                        if chosen_id in candidates_add:
                            chosen_add_val = candidates_add[chosen_id]
                            all_adds = list(candidates_add.values())
                            if all_adds:
                                min_add = min(all_adds)
                                max_add = max(all_adds)
                                # Only count if add_work values differ
                                if max_add > min_add:
                                    metrics["add_work_rounds"] += 1
                                    score = (chosen_add_val - min_add) / (max_add - min_add)
                                    metrics["add_work_wins"] += score

    # --- Final Calculations & Formatting ---
    finished = all(metrics[k] is not None for k in ["gen", "vis", "dead", "steps"])
    gen_val = metrics["gen"] if metrics["gen"] is not None else (metrics["max_id"] or "")
    vis_val = metrics["vis"] if metrics["vis"] is not None else (metrics["max_vis"] or "")

    add_work_val = (
        (metrics["add_work_wins"] / metrics["add_work_rounds"])
        if metrics["add_work_rounds"] > 0
        else None
    )

    return {
        "finished": int(finished),
        "plans_generated": gen_val,
        "plans_visited": vis_val,
        "dead_ends": metrics["dead"] if finished else "",
        "plan_length": metrics["steps"] if finished else "",
        "plans_until_landmark": metrics["plans_until_landmark"],
        "normalized_add_work": add_work_val,
        "flaws_reopened": metrics["flaws_reopened"],
        "landmarks_reopened": metrics["landmarks_reopened"],
    }


def process_zip(zippath, csv_writer):
    """
    Unzips a file, parses all logs inside using the unified parser,
    and writes the results to the CSV writer.
    """
    base = Path(zippath).stem  # Use pathlib for getting the base name
    print(f"Processing archive {base}...")
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            with zipfile.ZipFile(zippath) as zf:
                zf.extractall(tmpdir)
        except zipfile.BadZipFile:
            print(f"[!] Skipping {base}: Not a valid zip file or corrupted.", file=sys.stderr)
            return

        # Walk through the extracted files
        for root, _, files in os.walk(tmpdir):
            for fname in files:
                full_path = Path(root) / fname
                print(f"  - Parsing {full_path.name}...")
                try:
                    results = parse_trace_file(full_path)
                    results["problem"] = base

                    # Format None values for CSV output
                    results["normalized_add_work"] = "" if results["normalized_add_work"] is None else f"{results['normalized_add_work']:.4f}"
                    results["plans_until_landmark"] = "" if results["plans_until_landmark"] is None else results["plans_until_landmark"]

                    csv_writer.writerow(results)
                except Exception as e:
                    print(f"[!] Error processing {full_path.name}: {e}", file=sys.stderr)

def process_bz2(bz2path, csv_writer):
    """
    Decompresses a single .bz2‐compressed log file, parses it,
    and writes the results to the CSV writer.
    """
    base = Path(bz2path).stem  # e.g. "prob01_UCPOP_neutral.vhpop-log"
    print(f"Processing bz2 log {base}...")

    # Create a temporary directory just to hold the one decompressed file:
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / base

        # Decompress into tmpdir/base
        try:
            with bz2.open(bz2path, 'rb') as src, open(out_path, 'wb') as dst:
                dst.write(src.read())
        except OSError as e:
            print(f"[!] Skipping {base}: cannot decompress ({e})", file=sys.stderr)
            return

        # Now parse that one file
        try:
            results = parse_trace_file(out_path)
            results["problem"] = base

            # Format None values for CSV output
            results["normalized_add_work"] = (
                "" if results["normalized_add_work"] is None
                else f"{results['normalized_add_work']:.4f}"
            )
            results["plans_until_landmark"] = (
                "" if results["plans_until_landmark"] is None
                else results["plans_until_landmark"]
            )

            csv_writer.writerow(results)
        except Exception as e:
            print(f"[!] Error processing {base}: {e}", file=sys.stderr)


def main():
    """
    Main function to handle command-line arguments,
    set up the CSV writer, and process directories.
    """
    p = argparse.ArgumentParser(
        description="Process planner logs inside ZIPs and collect stats to CSV"
    )
    p.add_argument("directory",
                   help="Directory containing .zip files to process")
    p.add_argument("output_csv",
                   help="Path to write summary CSV")
    args = p.parse_args()

    input_dir = Path(args.directory)
    output_csv_path = Path(args.output_csv)

    if not input_dir.is_dir():
        print(f"[!] Error: Input directory '{input_dir}' not found.", file=sys.stderr)
        sys.exit(1)

    fieldnames = [
        "problem", "finished", "plans_generated", "plans_visited",
        "dead_ends", "plan_length", "plans_until_landmark",
        "normalized_add_work", "flaws_reopened", "landmarks_reopened"
    ]

    try:
        with open(output_csv_path, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            # Iterate through zip files in the directory
            for item in input_dir.iterdir():
                if item.is_file() and item.name.lower().endswith(".bz2"):
                    process_bz2(item, writer)

        print(f"\nDone! Summary written to {output_csv_path}")

    except IOError as e:
        print(f"[!] Error writing to output CSV '{output_csv_path}': {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()