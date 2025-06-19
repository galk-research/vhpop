import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import os
import argparse
from pathlib import Path
from multiprocessing import Pool
import sys

histograms_folder = Path("histograms")

def create_histogram_from_csv(csv_path, output_png_path):
    """
    Reads a CSV file with 'value' and 'count' columns and generates a bar chart
    (visual histogram) from the data, saving it as a PNG image.
    """
    try:

        df = pd.read_csv(csv_path)
        plt.figure(figsize=(14, 7))
        plt.bar(df['value'], df['count'], color='skyblue', edgecolor='black')


        plt.title('Distribution of Landmark Counts', fontsize=16)
        plt.xlabel('Landmark Position', fontsize=12)
        plt.ylabel('Frequency', fontsize=12)
        

        plt.xticks(df['value'])
        plt.xticks(rotation=45)


        ax = plt.gca()
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: format(int(x), ',')))

        plt.grid(axis='y', linestyle='--', alpha=0.7)

        plt.tight_layout()

        plt.savefig(output_png_path, dpi=300)
        
        plt.close()

        print(f"Histogram successfully saved to: {output_png_path}")

    except FileNotFoundError:
        print(f"Error: The file was not found at {csv_path}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def worker(path):
    print(f"Processing {path}")
    for f in path.iterdir():
        if str(f).lower().endswith('.csv'):
            csv_filename = Path(path) / "landmarks_distribution.csv"

            if "UCPOPLM" in str(f):
                heuristic = "UCPOPLM"
            elif "UCPOP" in str(f):
                heuristic = "UCPOP"
            
            full_heuristics = (str(heuristic) + "_neutral_")
            png_filename = path.name.replace(full_heuristics, "")
            png_filename = histograms_folder/ Path(str(heuristic)) / Path(png_filename)

            create_histogram_from_csv(csv_path=csv_filename, output_png_path=png_filename)



if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('data_directory')
    p.add_argument("-j", "--jobs", type=int,
               help="Number of parallel jobs")
    args = p.parse_args()

    indir = Path(args.data_directory)
    if not indir.is_dir():
        print(f"[!] '{indir}' is not a directory", file=sys.stderr)
        sys.exit(1)

    folders = [f for f in indir.iterdir() if "neutral" in f.name]

    with Pool(processes=args.jobs) as pool:
        pool.map(worker, folders)