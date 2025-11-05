# VHPOP Log Data Extraction Scripts

This folder contains scripts used to process and extract data from VHPOP log files.

---

## `build_csvs.py`

This script processes a directory containing multiple subdirectories, each with compressed VHPOP log files (`.bz2`).  
It extracts key metrics from each log, including:

- Whether the planner **finished** successfully.  
- The **number of plans generated** (if finished).  
- The **makespan** of the final plan (if finished).

### Output
The script creates an output directory (default: `results`) containing two subfolders:
- `time-simple/`
- `strips/`

Inside each subfolder, it generates three CSV files:
- `finished.csv`
- `makespan.csv`
- `plans_generated.csv`

Each CSV file contains:
- A row for each **problem**.
- Columns representing each **plan selection heuristic** used in the runs  
  (or **flaw selection heuristics** if run with the `-f` flag).

---

## `compute_compact_summary.py`

This script takes an input CSV file and produces a summarized output CSV.  
For each **heuristic** within each **domain**, it computes the following metrics:

1. **Mean Percent Above Average**  
   (how much better or worse than average a heuristic performs on average)

2. **Win Rate**  
   (the percentage of problems where the heuristic achieved the best result)

---
