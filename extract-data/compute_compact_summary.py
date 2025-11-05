#!/usr/bin/env python3
import sys
from pathlib import Path
import argparse
import pandas as pd
import numpy as np

def compute_for_domain(df_domain, heuristics):
    """
    df_domain: DataFrame (only heuristic columns, numeric or NaN), index = problems
    heuristics: list of heuristic column names (ordered)
    Returns: (mean_pct_above_avg_series, win_rate_series) indexed by heuristics
    """
    if df_domain.shape[0] == 0:
        return (pd.Series([np.nan]*len(heuristics), index=heuristics),
                pd.Series([np.nan]*len(heuristics), index=heuristics))

    per_problem_mean = df_domain.mean(axis=1, skipna=True)

    pct_diff = pd.DataFrame(index=df_domain.index, columns=heuristics, dtype=float)
    for idx in df_domain.index:
        m = per_problem_mean.loc[idx]
        for heur in heuristics:
            v = df_domain.at[idx, heur] if heur in df_domain.columns else np.nan
            if pd.isna(v) or pd.isna(m) or m == 0:
                pct = np.nan
            else:
                pct = (v - m) / m * 100.0
            pct_diff.at[idx, heur] = pct

    mean_pct_above_avg = pct_diff.mean(axis=0, skipna=True)


    wins = pd.Series(0.0, index=heuristics, dtype=float)
    problem_count = 0
    for idx in df_domain.index:
        row = df_domain.loc[idx]
        if row.isna().all():
            continue
        problem_count += 1
        minv = row.min(skipna=True)

        winners = []
        for col in row.index:
            val = row[col]
            if pd.isna(val):
                continue
            if np.isclose(val, minv, atol=1e-12, rtol=1e-8):
                winners.append(col)
        if len(winners) == 0:
            continue
        share = 1.0 / len(winners)
        for w in winners:
            wins[w] += share

    if problem_count == 0:
        win_rate = pd.Series([np.nan]*len(heuristics), index=heuristics)
    else:
        win_rate = wins.reindex(heuristics).fillna(0.0) / problem_count

    # ensure the same index/order
    mean_pct_above_avg = mean_pct_above_avg.reindex(heuristics)
    win_rate = win_rate.reindex(heuristics)

    return mean_pct_above_avg, win_rate


def domain_of(problem_str):
    s = str(problem_str)
    return s.split("-", 1)[0]

def main(argv):
    p = argparse.ArgumentParser()
    p.add_argument("input_csv")
    p.add_argument("output_csv")
    args = p.parse_args(argv)

    in_path = Path(args.input_csv)
    out_path = Path(args.output_csv)
    if not in_path.is_file():
        print(f"Error: input file not found: {in_path}", file=sys.stderr)
        sys.exit(2)

    df = pd.read_csv(in_path)
    heuristics = [c for c in df.columns if c != "problem"]
    
    heuristics.sort()

    df = df.copy()
    df["__domain__"] = df["problem"].apply(domain_of)

    for c in heuristics:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    domains = sorted(df["__domain__"].unique())

    out_rows = []
    row_index = []

    for domain in domains:
        sub = df[df["__domain__"] == domain]
        if sub.empty:
            continue
        # build numeric-only DataFrame indexed by problem id (keep original problem strings as index)
        sub_num = sub.set_index("problem")[heuristics]
        mean_pct, win_rate = compute_for_domain(sub_num, heuristics)

        # add rows named "<domain>_mean_pct_above_avg" and "<domain>_win_rate"
        out_rows.append(mean_pct)
        row_index.append(f"{domain}_mean_pct_above_avg")
        out_rows.append(win_rate)
        row_index.append(f"{domain}_win_rate")

    if not out_rows:
        print("No domains / problems found in input. No output produced.", file=sys.stderr)
        sys.exit(0)

    out_df = pd.DataFrame(out_rows, index=row_index, columns=heuristics)
    out_df = out_df.round(2)

    out_df.to_csv(out_path, index=True)
    print(f"Wrote compact per-domain summary to: {out_path}")

if __name__ == "__main__":
    main(sys.argv[1:])
