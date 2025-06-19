import pandas as pd
import csv
import argparse
from pathlib import Path
from multiprocessing import Pool
import sys
import numpy as np

histograms_folder = Path("histograms")
max_bins = None


def calculate_entropy(csv_path):
    """
    Reads a CSV, generates a histogram, and colors landmarks by frequency
    to ensure the most common landmarks have the most distinct colors.
    """
    df = pd.read_csv(csv_path)

    positions_counts = df.groupby('position')['count'].sum()

    total_landmarks = positions_counts.sum()
    entropy = -sum(count / total_landmarks * np.log2(count / total_landmarks) for count in positions_counts)

    return entropy 

def worker(path):
    print(f"Processing {path}")
    for f in path.iterdir():
        if str(f).lower().endswith('.csv'):
            csv_filename = Path(path) / "landmarks_distribution.csv"
            
            return {'problem': path.stem, 'entropy': calculate_entropy(csv_path=csv_filename)}



if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('data_directory')
    p.add_argument('output_csv')
    p.add_argument("-j", "--jobs", type=int,
               help="Number of parallel jobs")
    args = p.parse_args()

    outcsv = Path(args.output_csv)

    indir = Path(args.data_directory)
    if not indir.is_dir():
        print(f"[!] '{indir}' is not a directory", file=sys.stderr)
        sys.exit(1)

    folders = [f for f in indir.iterdir() if "neutral" in f.name]
    fieldnames = ['problem','entropy']

    with open(outcsv, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        with Pool(processes=args.jobs) as pool:
            for row in pool.imap_unordered(worker, folders, chunksize=1):
                if not row:
                    continue
                writer.writerow(row)