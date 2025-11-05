#!/usr/bin/env python3
import argparse
import csv
import re
import subprocess
import sys
import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from collections import defaultdict

TAIL_LINES = 200
DEFAULT_OUT_DIR = "results"
METRICS = ["plans_generated", "makespan", "finished"]

results = [] 
results_lock = threading.Lock()

def extract_metric(chunk, pattern):
    # Search from the end of the chunk backwards for the last match
    for line in reversed(chunk):
        if re.search(pattern, line, re.IGNORECASE):
            match = re.search(r":\s*([\d\.]+)", line)
            if match:
                return match.group(1).strip()
    return ""


def extract_last_id(chunk):
    child_re = re.compile(r"####\s*CHILD\s*\(id\s*(\d+)\)\s*with\s*rank", re.IGNORECASE)
    for line in reversed(chunk):
        m = child_re.search(line)
        if m:
            return m.group(1).strip()
    return ""


def process_directory(dir_path: Path):
    basename_dir = dir_path.name
    lcase_dir = basename_dir.lower()

    log_file = None
    for f in dir_path.glob("*.bz2"):
        try:
            if not f.is_file():
                continue
        except OSError:
            continue

        name_lower = f.name.lower()
        if "time" in name_lower or "err" in name_lower:
            continue

        log_file = f
        break
    

    try:
        cmd = ["bunzip2", "-c", str(log_file)]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        if not process.stdout:
            return

        chunk = deque(process.stdout, maxlen=TAIL_LINES)

        process.wait()
        if process.returncode != 0:
            if not process.stderr:
                return
            stderr_output = process.stderr.read()
            print(f"WARN: failed to decompress {log_file} (ret={process.returncode}): {stderr_output.strip()} — skipping", file=sys.stderr)
            return

    except (IOError, OSError) as e:
        print(f"WARN: failed to execute 'bunzip2' for {log_file}: {e} — skipping", file=sys.stderr)
        return

    plans_generated = extract_metric(chunk, r"Plans generated")
    makespan = extract_metric(chunk, r"Makespan")

    finished = "1" if plans_generated else "0"

    # If not finished, still try to extract the number of plans generated from the last CHILD line
    if finished == "0":
        # plans_generated = extract_last_id(chunk)
        plans_generated = ""
        makespan = ""

    row = {
        "problem": basename_dir,
        "plans_generated": plans_generated,
        "finished": finished,
        "makespan": makespan,
    }

    with results_lock:
        results.append(row)

    print(f"OK: {basename_dir} (pg={plans_generated or 'N/A'} finished={finished} mk={makespan or 'N/A'})")


def parse_problem(problem_name: str, sort_by_flaw_heur):
    """Return (domain_type, problem_id, heuristic)
    """
    
    name = problem_name.strip()
    nl = name.lower()
    name_args = nl.split("_")
    
    domain_type = "strips" if "strips" in nl else "time-simple"
    domain = name_args[0].split("-")[0]
    instance = name_args[1].split("-")[-1]
    plan_heur = name_args[2]
    flaw_heur = name_args[3]

    problem_id = f"{domain}-instance-{instance}"

    return domain_type, problem_id, flaw_heur if sort_by_flaw_heur else plan_heur


def write_csv(out_path: Path, problems_order, heuristics, table):
    with out_path.open("w", newline="") as f:
        writer = csv.writer(f)
        header = ["problem"] + heuristics
        writer.writerow(header)
        for prob in problems_order:
            row = [prob]
            m = table.get(prob, {})
            for h in heuristics:
                row.append(m.get(h, ""))
            writer.writerow(row)

def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("data_dir")
    parser.add_argument(
        "-t", "--threads",
        type=int,
        default=1,
    )
    parser.add_argument(
        "-f", "--flaws",
        action='store_true'
    )
    parser.add_argument(
        "-o", "--output", 
        type=str,
        default=DEFAULT_OUT_DIR,
    )
    args = parser.parse_args()

    sort_by_flaw_heur = args.flaws

    data_dir = Path(args.data_dir)
    out_dir = Path(args.output)

    time_out = out_dir / "time-simple"
    strips_out = out_dir / "strips"
    time_out.mkdir(parents=True, exist_ok=True)
    strips_out.mkdir(parents=True, exist_ok=True)


    try:
        subdirs = [d for d in data_dir.iterdir() if d.is_dir()]
    except FileNotFoundError:
        print(f"Error: Cannot access directory '{data_dir}'.", file=sys.stderr)
        sys.exit(1)

    # Process all directories in parallel using a thread pool
    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = []
        for d in subdirs:
            futures.append(executor.submit(process_directory, d))
        for f in futures:
            try:
                f.result()
            except Exception as e:
                print(f"ERROR: processing raised an unexpected exception: {e}", file=sys.stderr)

    results.sort(key=lambda x: x["problem"])


    # Data structures:
    # domain_data[domain][metric] = dict: problem -> {heur: value}
    domain_data = {
        "time-simple": {m: defaultdict(dict) for m in METRICS},
        "strips": {m: defaultdict(dict) for m in METRICS},
    }
    problems_seen = {"time-simple": [], "strips": []}
    problems_set = {"time-simple": set(), "strips": set()}

    heuristics = []

    for problem in results:
        original_problem = problem["problem"]
        domain_type, problem_id, heuristic = parse_problem(original_problem, sort_by_flaw_heur)
        print(f'{original_problem}: {domain_type}, {problem_id}, {heuristic}')

        if heuristic not in heuristics:
            heuristics.append(heuristic)

        if problem_id not in problems_set[domain_type]:
            problems_set[domain_type].add(problem_id)
            problems_seen[domain_type].append(problem_id)

        # store metrics values (if empty string in source, we keep empty)
        for m in METRICS:
            val = problem.get(m, "") or ""
            domain_data[domain_type][m][problem_id][heuristic] = val


    for domain_type, out_dir in (("time-simple", time_out), ("strips", strips_out)):
        problems_order = problems_seen[domain_type]
        for metric in METRICS:
            filename = f"{metric}.csv"
            out_path = out_dir / filename
            write_csv(out_path, problems_order, heuristics, domain_data[domain_type][metric])
            print(f"WROTE: {out_path} ({len(problems_order)} problems)")



if __name__ == "__main__":
    main()
