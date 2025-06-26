import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import matplotlib.cm as cm
import os


def plot_success_vs_entropy(entropy_file, success_file, finished_file):
    """
    Loads data from three CSVs and generates a separate plot of 
    success vs. entropy for each problem domain.

    - Filters out problems where no planner finished successfully.
    - Each plot is saved to a unique file named after its domain.
    - Finished tasks are plotted with filled markers; unfinished tasks are hollow.
    - Planners named 'neutral' are plotted as triangles.
    - Planners named 'fl' are plotted as squares.
    - Other planners are plotted as circles.
    """
    try:
        print(f"Loading data from:\n1. {entropy_file}\n2. {success_file}\n3. {finished_file}")
        df_entropy = pd.read_csv(entropy_file, index_col='problem')
        df_success = pd.read_csv(success_file, index_col='problem')
        df_finished = pd.read_csv(finished_file, index_col='problem')

    except FileNotFoundError as e:
        print(f"Error loading files: {e}")
        print("Please ensure all three CSV files are in the correct directory and named correctly.")
        return

    initial_problem_count = len(df_finished)
    print(f"\nLoaded data for {initial_problem_count} problems.")
    
    problems_to_keep_mask = df_finished.sum(axis=1) > 0
    
    df_entropy = df_entropy[problems_to_keep_mask]
    df_success = df_success[problems_to_keep_mask]
    df_finished = df_finished[problems_to_keep_mask]
    
    final_problem_count = len(df_finished)
    problems_removed = initial_problem_count - final_problem_count
    
    print(f"Filtering out problems where no planners finished. {problems_removed} problem(s) removed.")
    print(f"{final_problem_count} problems remain for plotting.\n")
    
    if final_problem_count == 0:
        print("No problems with at least one finished plan. Aborting plot generation.")
        return


    entropy_long = df_entropy.reset_index().melt(id_vars='problem', var_name='planner', value_name='entropy')
    success_long = df_success.reset_index().melt(id_vars='problem', var_name='planner', value_name='success')
    finished_long = df_finished.reset_index().melt(id_vars='problem', var_name='planner', value_name='finished')

    df = pd.merge(entropy_long, success_long, on=['problem', 'planner'])
    df = pd.merge(df, finished_long, on=['problem', 'planner'])


    df['domain'] = df['problem'].str.split('_').str[0]
    output_dir = 'stats/domain_plots'
    os.makedirs(output_dir, exist_ok=True)


    domains = sorted(df['domain'].unique())
    
    print(f"Found {len(domains)} domains. Generating a plot for each...")

    for domain in domains:
        plt.style.use('seaborn-v0_8-whitegrid')
        fig, ax = plt.subplots(figsize=(12, 8))

        domain_data = df[df['domain'] == domain]
        
        is_finished = domain_data['finished'] == 1
        is_neutral = domain_data['planner'] == 'neutral'
        is_fl = domain_data['planner'] == 'fl'
        is_other = ~is_neutral & ~is_fl

        data_subset = domain_data[is_finished & is_other]
        ax.scatter(data_subset['entropy'], data_subset['success'], 
                   marker='o', color='#007ACC', alpha=0.7, s=60)

        data_subset = domain_data[~is_finished & is_other]
        ax.scatter(data_subset['entropy'], data_subset['success'], 
                   marker='o', facecolors='none', edgecolors='#007ACC', alpha=0.7, s=60)
                   
        data_subset = domain_data[is_finished & is_neutral]
        ax.scatter(data_subset['entropy'], data_subset['success'], 
                   marker='^', color='#E84A5F', alpha=0.7, s=70)

        data_subset = domain_data[~is_finished & is_neutral]
        ax.scatter(data_subset['entropy'], data_subset['success'], 
                   marker='^', facecolors='none', edgecolors='#E84A5F', alpha=0.7, s=70)

        data_subset = domain_data[is_finished & is_fl]
        ax.scatter(data_subset['entropy'], data_subset['success'], 
                   marker='s', color='#28A745', alpha=0.7, s=60) # Green color

        data_subset = domain_data[~is_finished & is_fl]
        ax.scatter(data_subset['entropy'], data_subset['success'], 
                   marker='s', facecolors='none', edgecolors='#28A745', alpha=0.7, s=60)



        ax.set_title(f'Success vs. Entropy for Domain: {domain.capitalize()}', fontsize=18, fontweight='bold')
        ax.set_xlabel('Entropy', fontsize=14)
        ax.set_ylabel('Success', fontsize=14)
        ax.grid(True)


        legend_elements = [
            mlines.Line2D([], [], color='#007ACC', marker='o', linestyle='None', markersize=8, label='Finished (Other)'),
            mlines.Line2D([], [], color='#E84A5F', marker='^', linestyle='None', markersize=9, label='Finished (Neutral)'),
            mlines.Line2D([], [], color='#28A745', marker='s', linestyle='None', markersize=8, label='Finished (fl)'), # <-- NEW
            
            mlines.Line2D([], [], markerfacecolor='none', markeredgecolor='#007ACC', marker='o', linestyle='None', markersize=8, label='Unfinished (Other)'),
            mlines.Line2D([], [], markerfacecolor='none', markeredgecolor='#E84A5F', marker='^', linestyle='None', markersize=9, label='Unfinished (Neutral)'),
            mlines.Line2D([], [], markerfacecolor='none', markeredgecolor='#28A745', marker='s', linestyle='None', markersize=8, label='Unfinished (fl)') # <-- NEW
        ]
        ax.legend(handles=legend_elements, title="Status (Planner)", loc='best')

        plt.tight_layout()
        
        output_filename = os.path.join(output_dir, f'success_vs_entropy_{domain}.png')
        plt.savefig(output_filename, dpi=300)
        
        plt.close(fig)
        
        print(f"  - Saved plot for '{domain}' to '{output_filename}'")

    print(f"\nSuccessfully generated and saved {len(domains)} plots in the '{output_dir}' directory.")




if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('entropy_csv')
    p.add_argument('success_csv')
    p.add_argument('finished_csv')
    args = p.parse_args()

    entropy_csv = args.entropy_csv
    success_csv = args.success_csv
    finished_csv = args.finished_csv

    plot_success_vs_entropy(entropy_csv, success_csv, finished_csv)
