import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import os
import argparse
from pathlib import Path
from multiprocessing import Pool
import sys
import seaborn as sns

histograms_folder = Path("histograms")
max_bins = None


def create_histogram_from_csv(csv_path, output_png_path):
    """
    Reads a CSV, generates a histogram, and colors landmarks by frequency
    to ensure the most common landmarks have the most distinct colors.
    """
    try:
        df_reloaded = pd.read_csv(csv_path)

        landmark_counts = df_reloaded.groupby('landmark_type')['count'].sum().sort_values(ascending=False)

        sorted_landmarks = landmark_counts.index.tolist()
        num_landmarks = len(sorted_landmarks)
        high_contrast_palette = sns.color_palette("husl", n_colors=num_landmarks)

        custom_palette = dict(zip(sorted_landmarks, high_contrast_palette))

        num_unique_positions = df_reloaded['position'].nunique()

        if max_bins:
            number_of_bins = min(num_unique_positions, 10000)
        else:
            number_of_bins = num_unique_positions

        plt.figure(figsize=(12, 7))

        sns.histplot(
            data=df_reloaded,
            x='position',
            hue='landmark_type',
            weights='count',
            multiple='stack',
            bins=number_of_bins,
            edgecolor='white',
            legend=False,
            hue_order=sorted_landmarks,
            palette=custom_palette
        )

        plt.title('Distribution of Landmark positions', fontsize=16)
        plt.xlabel('Landmark Position', fontsize=12)
        plt.ylabel('Frequency', fontsize=12)
        
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
    p.add_argument("-b", type=int, default=None,
               help="Maximum number of bins")
    p.add_argument("-j", "--jobs", type=int,
               help="Number of parallel jobs")
    args = p.parse_args()

    max_bins = args.b

    indir = Path(args.data_directory)
    if not indir.is_dir():
        print(f"[!] '{indir}' is not a directory", file=sys.stderr)
        sys.exit(1)

    folders = [f for f in indir.iterdir() if "neutral" in f.name]

    with Pool(processes=args.jobs) as pool:
        pool.map(worker, folders)