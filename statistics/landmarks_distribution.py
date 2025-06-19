#!/usr/bin/env python3
import argparse
import csv
import sys
from pathlib import Path
from multiprocessing import Pool
import bz2
import re
import pandas as pd


RE_CANDIDATE = re.compile(r"^\s*#<OPEN \((.+)\) .+> LL: (\S+)")
RE_HANDLE = re.compile(r'^\s*handle #<(?P<id>[^>]+)>')
RE_VISITLINE = re.compile(r"^(\d+):.*CURRENT PLAN \(id (\d+)\) with rank \(\d+\)")
RE_CHILD = re.compile(r"^.*CHILD \(id (\d+)\) with rank \(\d+\)")


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
    in_block = False
    depths = {0: 0}
    depth = 0
    positions = {}

    for raw in f:
        line = raw.rstrip("\n")
        
        if match := RE_VISITLINE.match(line):
            id = match.group(2)
            depth = depths[int(id)]
            del depths[int(id)]
            in_block = True
            num_flaws = 0

        if in_block:
            if match := RE_CANDIDATE.search(line):
                num_flaws += 1
                ll = match.group(2)
                if ll and ll != 'X':
                    landmark = match.group(1)
                    current_positions = num_flaws + depth
                    if current_positions not in positions:
                        positions[current_positions] = {}
                    if landmark not in positions[current_positions]:
                        positions[current_positions][landmark] = 0
                    positions[current_positions][landmark] += 1
            
            elif RE_HANDLE.match(line):
                in_block = False
        
        if match := RE_CHILD.match(line):
            child_id = int(match.group(1))
            depths[child_id] = depth + 1

    records = []
    for position, landmark_counts in positions.items():
        for landmark_type, count in landmark_counts.items():
            records.append({
                'position': position,
                'landmark_type': landmark_type,
                'count': count
            })
    df = pd.DataFrame(records)
    df.sort_values(by=['position', 'landmark_type']).reset_index(drop=True)
    return df


def process_bz2(path):
    """Parse a .bz2‑compressed log and return list of row dicts"""
    with bz2.open(path, 'rt', encoding='utf-8', errors='ignore') as f:
        res = parse_trace_stream(f)
        return res

def worker(path):
    print(f"Processing {path}")
    for f in path.iterdir():
        if str(f).lower().endswith('vhpop-log.bz2'):
            positions_df = process_bz2(f)
            output_path = Path(path) / "landmarks_distribution.csv"
            positions_df.to_csv(output_path, index=False)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('data_directory')
    p.add_argument("-j", "--jobs", type=int,
               help="Number of parallel jobs")
    args = p.parse_args()

    indir = Path(args.data_directory)
    if not indir.is_dir():
        print(f"[!] '{indir}' is not a directory", file=sys.stderr)
        sys.exit(1)

    folders = [f for f in indir.iterdir()]

    with Pool(processes=args.jobs) as pool:
        pool.map(worker, folders)

if __name__ == '__main__':
    main()