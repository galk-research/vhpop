import pandas as pd
import sys
import argparse


def calculate_success_scores(input_csv_path, output_csv_path):
    """
    Reads a CSV of heuristic performance, calculates a success score for each,
    and saves the results to a new CSV.

    The success score for a cell is calculated row-wise as:
    score = (max_in_row - cell_value) / (max_in_row - min_in_row)
    """
    try:
        df = pd.read_csv(input_csv_path, index_col='problem')
        print(f"Successfully loaded data from '{input_csv_path}'.")

        max_per_row = df.max(axis=1)
        min_per_row = df.min(axis=1)

        denominator = max_per_row - min_per_row
        numerator = df.rsub(max_per_row, axis='index')
        
        scores_df = numerator.div(denominator, axis='index')

        scores_df.fillna(1.0, inplace=True)
        
        scores_df.to_csv(output_csv_path)
        print(f"Success! Score data saved to '{output_csv_path}'.")

    except FileNotFoundError:
        print(f"Error: The file '{input_csv_path}' was not found.", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)



if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('input_file')
    p.add_argument('output_file')
    args = p.parse_args()
    
    input_file = args.input_file
    output_file = args.output_file

    calculate_success_scores(input_file, output_file)