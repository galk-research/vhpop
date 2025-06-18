#!/usr/bin/env python3
import argparse
import csv
import sys
from pathlib import Path
from multiprocessing import Pool
import bz2
import re


RE_START = re.compile(r'^Selecting a flaw from')
RE_CANDIDATE = re.compile(r"#<([^>]+)> LL: (\S+) .*? ADD_WORK: (\d+)")
RE_HANDLE = re.compile(r'^\s*handle #<(?P<id>[^>]+)>')
RE_GENERATED = re.compile(r"^Plans generated:\s*(\d+)")
RE_VISITED = re.compile(r"^Plans visited:\s*(\d+)")
RE_DEAD = re.compile(r"^Dead ends encountered:\s*(\d+)")
RE_STEPS = re.compile(r"^Number of steps:\s*(\d+)")
RE_ID = re.compile(r"\(id\s+(\d+)\)")
RE_VISITLINE = re.compile(r"^(\d+):.*CURRENT PLAN")
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
        

def parse_trace_stream(f):
    """
    Parse from any text file-like object line by line.
    """
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
    in_block = False
    candidates_ll = {}
    candidates_add = {}
    open_flaws = set()
    current_plans = 0
    done = False

    for raw in f:
        line = raw.rstrip("\n")

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


        if RE_START.match(line):

            if in_block:
                in_block = False


            current_plans += 1
            in_block = True
            candidates_ll.clear()
            candidates_add.clear()
            continue

        if in_block:
            try:
                flaw_id, ll, add = parse_flaw(line)
                if GOAL_ID not in flaw_id:  # Skip the goal ID
                    candidates_ll[flaw_id] = ll
                candidates_add[flaw_id] = add
            except ValueError:

                m_handle = RE_HANDLE.match(line)
                if m_handle:
                    chosen_id = m_handle.group('id')
                    in_block = False

                    # 1. Plans Until Landmark
                    chosen_ll = candidates_ll.get(chosen_id)
                    if metrics["plans_until_landmark"] is None and chosen_ll and chosen_ll != 'X':
                        metrics["plans_until_landmark"] = current_plans

                    # 2. Flaws Reopened
                    is_landmark = chosen_ll and chosen_ll != 'X'
                    if chosen_id in open_flaws:    
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
                            if max_add > min_add:
                                metrics["add_work_rounds"] += 1
                                score = (chosen_add_val - min_add) / (max_add - min_add)
                                metrics["add_work_wins"] += score


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


def process_bz2(path):
    """Parse a .bz2‑compressed log and return list of row dicts"""
    rows = []
    with bz2.open(path, 'rt', encoding='utf-8', errors='ignore') as f:
        res = parse_trace_stream(f)
        rows.append(res)
    return rows

def worker(path):
    print(f"Processing {path}")
    results = []
    for f in path.iterdir():
        if str(f).lower().endswith('vhpop-log.bz2'):
            results.extend(process_bz2(f))
            results[-1]['problem'] = Path(path).stem
            return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument('data_directory')
    p.add_argument('output_csv')
    p.add_argument("-j", "--jobs", type=int,
               help="Number of parallel jobs")
    args = p.parse_args()

    indir = Path(args.data_directory)
    outcsv = Path(args.output_csv)
    if not indir.is_dir():
        print(f"[!] '{indir}' is not a directory", file=sys.stderr)
        sys.exit(1)

    folders = [f for f in indir.iterdir()]
    fieldnames = [
        'problem','finished','plans_generated','plans_visited',
        'dead_ends','plan_length','plans_until_landmark',
        'normalized_add_work','flaws_reopened','landmarks_reopened'
    ]

    with open(outcsv, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        with Pool(processes=args.jobs) as pool:
            for row_list in pool.imap_unordered(worker, folders, chunksize=1):
                if not row_list:
                    continue
                for row in row_list:
                    writer.writerow(row)

    print(f"Done! Summary written to {outcsv}")

if __name__ == '__main__':
    main()