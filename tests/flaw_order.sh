#!/bin/bash

# Usage: ./run_benchmarks.sh <path-to-landmark-extractor>

landmark_extraction_path=$1

# List your problem-set folders here (paths relative to where you run this script)
folders=(
)

write_csv() {
    local filename="$1"
    local title="$2"
    local -n data=$3

    {
        IFS=','
        echo "Problem,${flags_order[*]}"
        unset IFS
        for problem in "${problems[@]}"; do
            line="$problem"
            for heuristic in "${flags_order[@]}"; do
                key="${problem}|${heuristic}"
                value="${data[$key]}"
                line="$line,$value"
            done
            echo "$line"
        done
    } > "$filename"
}

append_csv_row() {
    local filename="$1"
    local problem="$2"
    local plan="$3"
    local -n data=$4

    local line="$problem"
    for f in "${flaw_order[@]}"; do
        key="${f}|${plan}"
        value="${data[$key]}"
        line="$line,$value"
    done

    echo "$line" >> "$filename"
}

extract_plans_generated() { grep -m1 "^Plans generated: [0-9]\+" "$1" | awk '{print $3}'; }
extract_plans_visited()  { grep -m1 "^Plans visited: [0-9]\+" "$1" | awk '{print $3}'; }
extract_dead_ends()      { grep -m1 "^Dead ends encountered: [0-9]\+" "$1" | awk '{print $4}'; }
extract_plan_length()    { grep -m1 "^Makespan: [0-9]\+" "$1" | awk '{print $2}'; }

# Heuristic and flaw-ordering flags
h='-h UCPOP'
f='{n,s}LIFO/{o}LIFO'
f_f='{n,s}LIFO/{m}LIFO/{o}LIFO'
f_l='{n,s}LIFO/{x}LIFO/{o}LIFO'
f_ff='{n,s}LIFO/{m}LMO/{o}LIFO'
f_fl='{n,s}LIFO/{m}RLMO/{o}LIFO'
f_lf='{n,s}LIFO/{x}LIFO/{o}LMO'
f_ll='{n,s}LIFO/{x}LIFO/{o}RLMO'

declare -A flaw_flags=(
    [neutral]="$f"
    [fLIFO]="$f_f"
    [lLIFO]="$f_l"
    [ff]="$f_ff"
    [fl]="$f_fl"
    [lf]="$f_lf"
    [ll]="$f_ll"
)
# flaw_order=(neutral fLIFO lLIFO ff fl lf ll)
flaw_order=(neutral fLIFO lLIFO ff fl lf ll)

declare -A plan_flags=(
    [UCPOP]="UCPOP"
    [UCPOPLM]="UCPOPLM"
)
plan_order=(UCPOP UCPOPLM)

# Prepare results directories & data structures
declare -A results_plans_generated results_plans_visited results_dead_ends results_plan_length
problems=()

tmp1=$(mktemp)
trap 'rm -f "$tmp1"' EXIT

for plan in "${plan_order[@]}"; do
    rm -rf "results/flaw_orders/$plan"
    mkdir -p "results/flaw_orders/$plan"
    # initialize CSVs with headers
    write_csv "results/flaw_orders/$plan/plans_generated.csv" "Plans Generated" results_plans_generated
    write_csv "results/flaw_orders/$plan/plans_visited.csv"  "Plans Visited"   results_plans_visited
    write_csv "results/flaw_orders/$plan/dead_ends.csv"      "Dead Ends"       results_dead_ends
    write_csv "results/flaw_orders/$plan/plan_length.csv"    "Plan Length"     results_plan_length
done


for folder in "${folders[@]}"; do
    domain="$folder/domain.pddl"
    folder_name=$(basename "$folder")
    mkdir -p "results/$folder_name"
    for probpath in "$folder"/*.pddl; do
        [[ "$probpath" == "$domain" ]] && continue
        problem=$(basename "$probpath")
        baseproblem="${problem%.pddl}"
        outname="${folder_name}-${baseproblem}"
        problems+=("$problem")

        echo "Benchmarking problem '$problem' in domain '$domain'…"

        python3 "$landmark_extraction_path" --alias seq-sat-lama-2011 "$domain" "$probpath" > "$tmp1" 2>&1


        for plan in "${plan_order[@]}"; do
            p_flag=${plan_flags[$plan]}

            for flaw in "${flaw_order[@]}"; do
                f_flag=${flaw_flags[$flaw]}

                filename="results/$flaw/$plan/$outname"

                cmd=(./vhpop -g -v5 -f "$f_flag" -h "$p_flag" -y -m "$tmp1" "$domain" "$probpath")
                # ( ulimit -t 300; "${cmd[@]}" > "results/$folder_name/$problem/${plan}_${flaw}" 2>&1 )
                ( ulimit -t 300; "${cmd[@]}" > "results/$flaw/$plan/$outname" 2>&1 )
                if [ -f "$filename" ]; then
                    zip -9 "${filename}.zip" "$filename" && rm "$filename"
                else
                    echo "Error: file '$filename' was not created."
                fi
                # status=$?

                # if [ $status -eq 152 ]; then
                #     pgen=pvis=dead=plen="x"
                # else
                #     pgen=$(extract_plans_generated "$tmp2")
                #     pvis=$(extract_plans_visited  "$tmp2")
                #     dead=$(extract_dead_ends      "$tmp2")
                #     plen=$(extract_plan_length    "$tmp2")
                # fi

                # key="${flaw}|${plan}"
                # results_plans_generated["$key"]=$pgen
                # results_plans_visited["$key"]=$pvis
                # results_dead_ends["$key"]=$dead
                # results_plan_length["$key"]=$plen
            done


            # append_csv_row "results/flaw_orders/$plan/plans_generated.csv" "$problem" "$plan" results_plans_generated
            # append_csv_row "results/flaw_orders/$plan/plans_visited.csv"  "$problem" "$plan" results_plans_visited
            # append_csv_row "results/flaw_orders/$plan/dead_ends.csv"      "$problem" "$plan" results_dead_ends
            # append_csv_row "results/flaw_orders/$plan/plan_length.csv"    "$problem" "$plan" results_plan_length
        done
    done
done


print_table() {
    local title="$1"; local -n res=$2
    printf "\n===== %s =====\n" "$title"
    printf "| %-20s " "Problem"
    for h in "${flags_order[@]}"; do printf "| %-8s " "$h"; done
    echo "|"
    printf "|%s|\n" "$(printf ' %.0s-' {1..(22 + 11*${#flags_order[@]})})"
    for prob in "${problems[@]}"; do
        printf "| %-20s " "$prob"
        for h in "${flags_order[@]}"; do
            printf "| %-8s " "${res[$prob|$h]}"
        done
        echo "|"
    done
}

# print_table "Plans Generated" results_plans_generated
# print_table "Plans Visited"  results_plans_visited
# print_table "Dead Ends"      results_dead_ends
# print_table "Plan Length"    results_plan_length
