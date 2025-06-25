import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import os
import argparse
from pathlib import Path
from multiprocessing import Pool
import sys
import seaborn as sns
import numpy as np
import warnings
import re
from functools import partial


warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)

histograms_folder = Path("histograms")
max_bins = None
landmark_plots = False



def create_histograms_from_csv(csv_path, output_png_path, domain_colors):
    """
    Reads a CSV, generates a combined histogram, and a separate plot for each
    landmark type.

    Improvements:
    - Renders landmarks with a single position as a bar plot instead of skipping.
    - Enforces consistent X and Y axis limits across all individual plots for
      direct visual comparison.

    The combined histogram is saved to `output_png_path`.
    Individual plots are saved in a new subdirectory.
    """
    try:
        df_reloaded = pd.read_csv(csv_path)

        if df_reloaded.empty:
            print("Error: The CSV file is empty.")
            return

        global_min_pos = df_reloaded['position'].min()
        global_max_pos = df_reloaded['position'].max()

        landmark_counts = df_reloaded.groupby('landmark_type')['count'].sum().sort_values(ascending=False)
        sorted_landmarks = landmark_counts.index.tolist()
        custom_palette = domain_colors

    except FileNotFoundError:
        print(f"Error: The input CSV file was not found at {csv_path}")
        return
    except Exception as e:
        print(f"An error occurred during data loading: {e}")
        return

    global_max_y = 0
    for landmark in sorted_landmarks:
        df_single = df_reloaded[df_reloaded['landmark_type'] == landmark]
        
        if df_single.empty:
            continue

        if df_single['position'].nunique() <= 1:
            max_height = df_single['count'].sum()
        else:
            num_unique_positions = df_single['position'].nunique()
            number_of_bins = min(num_unique_positions, 10000) if max_bins else num_unique_positions
            
            heights, _ = np.histogram(
                df_single['position'],
                bins=number_of_bins,
                weights=df_single['count']
            )
            max_height = heights.max() if len(heights) > 0 else 0
        
        if max_height > global_max_y:
            global_max_y = max_height

    try:
        print("Generating the combined histogram...")

        output_path_obj = Path(output_png_path)
        plots_dir = output_path_obj.parent / f"{output_path_obj.stem}"
        plots_dir.mkdir(parents=True, exist_ok=True)
        
        plt.figure(figsize=(12, 7))
        sns.histplot(
            data=df_reloaded, x='position', hue='landmark_type', weights='count',
            multiple='stack', bins=min(df_reloaded['position'].nunique(), 10000),
            edgecolor='white', legend=False, hue_order=sorted_landmarks, palette=custom_palette
        )
        plt.title('Combined Distribution of All Landmark Positions', fontsize=16)
        plt.xlabel('Landmark Position', fontsize=12)
        plt.ylabel('Frequency', fontsize=12)
        plt.xticks(rotation=45)
        plt.xlim(global_min_pos, global_max_pos)
        ax = plt.gca()
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: format(int(x), ',')))
        
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.savefig(plots_dir / "_combined_plot.png", dpi=300)
        plt.close()
        print(f"Combined histogram successfully created")
    except Exception as e:
        print(f"An unexpected error occurred while creating the combined plot: {e}")



    if landmark_plots:
        print("Generating individual plots...")
        
        for landmark in sorted_landmarks:
            try:
                df_single = df_reloaded[df_reloaded['landmark_type'] == landmark].copy()

                if df_single.empty:
                    print(f"--> Skipping '{landmark}': No data.")
                    continue

                plt.figure(figsize=(12, 7))
                
                if df_single['position'].nunique() <= 1:
                    position = df_single['position'].iloc[0]
                    total_count = df_single['count'].sum()
                    plt.bar(
                        x=position,
                        height=total_count,
                        width=10,
                        color=custom_palette[landmark]
                    )
                else:
                    num_unique_positions = df_single['position'].nunique()
                    number_of_bins = min(num_unique_positions, 10000) if max_bins else num_unique_positions
                    sns.histplot(
                        data=df_single, x='position', weights='count',
                        bins=number_of_bins, color=custom_palette[landmark], edgecolor='white'
                    )

                plt.title(f'Distribution for Landmark: {landmark}', fontsize=16)
                plt.xlabel('Landmark Position', fontsize=12)
                plt.ylabel('Frequency', fontsize=12)
                plt.xticks(rotation=45)
                
                plt.xlim(global_min_pos, global_max_pos)

                ax = plt.gca()
                ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: format(int(x), ',')))

                plt.grid(axis='y', linestyle='--', alpha=0.7)
                plt.tight_layout()
                
                individual_output_path = Path(plots_dir) / f"{landmark.replace('/', '_')}.png"
                plt.savefig(individual_output_path, dpi=300)
                plt.close()

            except Exception as e:
                print(f"Could not create plot for '{landmark}'. Error: {e}")

        print("All individual plots successfully created.")


def worker(path, domain_palettes):
    print(f"\nProcessing {path}")
    domain_name = path.name.split('_')[0]
    domain_colors = domain_palettes.get(domain_name)    
    
    csv_filename = path / "landmarks_distribution.csv"
    if not csv_filename.exists():
        print(f"  - Skipping {path.name}: landmarks_distribution.csv not found.")
        return


    plan_selection = "UCPOPLM" if "UCPOPLM" in path.name else "UCPOP" if "UCPOP" in path.name else "unknown_plan"
    flaw_selection_map = {"lLIFO": "lLIFO", "fLIFO": "fLIFO", "ff": "ff", "fl": "fl", "lf": "lf", "ll": "ll", "neutral": "neutral"}
    flaw_selection = next((val for key, val in flaw_selection_map.items() if key in path.name), "unknown_flaw")
    full_heuristics = str(plan_selection) + str(flaw_selection)
    png_filename_stem = path.name.replace(full_heuristics, "")
    png_path = histograms_folder / flaw_selection / plan_selection / png_filename_stem

    create_histograms_from_csv(csv_path=csv_filename, output_png_path=png_path, domain_colors=domain_colors)



if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('data_directory')
    p.add_argument("-b", type=int, default=None,
               help="Maximum number of bins")
    p.add_argument("-l", action='store_true', help='Plot histogram for each landmark separately')
    p.add_argument("-j", "--jobs", type=int,
               help="Number of parallel jobs")
    args = p.parse_args()

    max_bins = args.b

    if args.l:
        landmark_plots = True

    indir = Path(args.data_directory)
    if not indir.is_dir():
        print(f"[!] '{indir}' is not a directory", file=sys.stderr)
        sys.exit(1)

    all_folders = [f for f in indir.iterdir() if f.is_dir()]
    histograms_folder = Path("histograms")


    print("--- Pre-processing: Grouping folders by domain ---")
    domain_folders = {}
    for folder in all_folders:
        domain_name = folder.name.split('_')[0]
        domain_folders.setdefault(domain_name, []).append(folder)
    print(f"Found {len(domain_folders)} domains: {', '.join(domain_folders.keys())}\n")


    print("--- Pre-processing: Generating color palettes for each domain ---")
    domain_palettes = {}
    for domain, folders_in_domain in domain_folders.items():
        print(f"  - Processing domain: '{domain}'...")
        

        all_landmarks_for_domain = set()


        for folder in folders_in_domain:
            csv_path = folder / "landmarks_distribution.csv"
            if csv_path.exists():
                try:

                    df = pd.read_csv(csv_path)

                    if 'landmark_type' in df.columns:
                        all_landmarks_for_domain.update(df['landmark_type'].unique())
                except Exception as e:
                    print(f"    - WARNING: Could not read or process {csv_path}. Skipping this file. Error: {e}")


        if not all_landmarks_for_domain:
            print(f"    - WARNING: No landmarks found for domain '{domain}'. This domain will be skipped.")
            continue


        landmark_types = sorted(list(all_landmarks_for_domain))
        palette = sns.color_palette("husl", n_colors=len(landmark_types))
        
        domain_palettes[domain] = dict(zip(landmark_types, palette))
        print(f"    - Created palette with {len(landmark_types)} total unique colors for '{domain}'.")
    

    partial_worker = partial(
        worker, 
        domain_palettes=domain_palettes
    )


    print(f"\n--- Starting processing with {args.jobs} job(s) ---")
    with Pool(processes=args.jobs) as pool:
        pool.map(partial_worker, all_folders)
    
    print("\n--- All tasks complete! ---")