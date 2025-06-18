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
    in_block = False
    candidates_ll = {}
    sum_plans_until_landmark = 0
    plans_until_landmark = 0
    landmarks_count = 0

    for raw in f:
        line = raw.rstrip("\n")
        
        if RE_START.match(line):
            if in_block:
                in_block = False
            plans_until_landmark += 1
            in_block = True
            candidates_ll.clear()
            continue

        if in_block:
            try:
                flaw_id, ll, add = parse_flaw(line)
                if GOAL_ID not in flaw_id:
                    candidates_ll[flaw_id] = ll
            except ValueError:

                m_handle = RE_HANDLE.match(line)
                if m_handle:
                    chosen_id = m_handle.group('id')
                    in_block = False


                    chosen_ll = candidates_ll.get(chosen_id)
                    if chosen_ll and chosen_ll != 'X':
                        sum_plans_until_landmark += plans_until_landmark
                        landmarks_count += 1
                        plans_until_landmark = 0
                    

    return {
        "plans_between_landmarks": sum_plans_until_landmark / landmarks_count if landmarks_count > 0 else "N/A"
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
    p.add_argument('input_csv',     help="the existing CSV with a 'problem' column")
    p.add_argument('output_csv',    help="where to write the merged CSV")
    p.add_argument("-j", "--jobs",  type=int, help="parallel jobs")
    args = p.parse_args()

    indir   = Path(args.data_directory)
    in_csv  = Path(args.input_csv)
    out_csv = Path(args.output_csv)
    if not indir.is_dir():
        print(f"[!] '{indir}' is not a directory", file=sys.stderr)
        sys.exit(1)
    if not in_csv.is_file():
        print(f"[!] '{in_csv}' is not a file", file=sys.stderr)
        sys.exit(1)


    with in_csv.open(newline='') as f:
        reader   = csv.DictReader(f)
        rows     = list(reader)
        if not reader.fieldnames:
            print(f"[!] '{in_csv}' has no header row", file=sys.stderr)
            sys.exit(1)
        fieldnames = reader.fieldnames[:]


    new_col = 'plans_between_landmarks'
    if new_col in fieldnames:
        print(f"[!] Column '{new_col}' already exists in {in_csv}", file=sys.stderr)
        sys.exit(1)
    fieldnames = list(reader.fieldnames)
    fieldnames.append(new_col)


    folders = [d for d in indir.iterdir() if d.is_dir()]
    with Pool(processes=args.jobs) as pool:

        results = pool.imap_unordered(worker, folders, chunksize=1)


        mapping = {}
        for row_list in results:
            if not row_list:
                continue
            for r in row_list:
                mapping[r['problem']] = r['plans_between_landmarks']


    with out_csv.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            key = row.get('problem')

            row[new_col] = mapping.get(key, '')
            writer.writerow(row)

    print(f"Done! Merged CSV written to {out_csv}")

if __name__ == '__main__':
    main()
