#!/bin/bash

file_pairs=(
    "gripper-domain.pddl gripper-2.pddl"
    "gripper-domain.pddl gripper-4.pddl"
    "gripper-domain.pddl gripper-6.pddl"
    "gripper-domain.pddl gripper-8.pddl"
    "gripper-domain.pddl gripper-10.pddl"
    "hanoi-domain.pddl hanoi-3.pddl"
    "hanoi-3-domain.pddl hanoi-n-3.pddl"
    "grid-domain.pddl simple-grid2.pddl"
    "grid-domain.pddl simple-grid3.pddl"
    "logistics-domain.pddl logistics-a.pddl"
    "logistics-domain.pddl logistics-b.pddl"
    "logistics-domain.pddl logistics-c.pddl"
    "logistics-domain.pddl logistics-d.pddl"
    "rocket-domain.pddl rocket-ext-a.pddl"
    "rocket-domain.pddl rocket-ext-b.pddl"
    "simple-blocks-domain.pddl bw-large-a.pddl"
    "simple-blocks-domain.pddl bw-large-b.pddl"
    "simple-blocks-domain.pddl bw-large-d.pddl"
    "monkey-domain.pddl monkey-test1.pddl"
    "bulldozer-domain.pddl get-back-jack.pddl"
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



extract_plans_generated() {
    grep -m 1 "^Plans generated: [0-9]\+" "$1" | awk '{print $3}'
}

extract_plans_visited() {
    grep -m 1 "^Plans visited: [0-9]\+" "$1" | awk '{print $3}'
}

extract_dead_ends() {
    grep -m 1 "^Dead ends encountered: [0-9]\+" "$1" | awk '{print $4}'
}

extract_plan_length() {
    grep -m 1 "^Makespan: [0-9]\+" "$1" | awk '{print $2}'
}

# h='-h ADDR/ADDR_WORK/BUC/LIFO'
h='-h ADDR/UCPOPLM'
# f='-f {n,s}LR/{l}MW_add -l 12000 -f {n,s}LR/{u}MW_add/{l}MW_add -l 100000 -f {n,s,l}LR -l 240000 -f {n,s,u}LR/{l}LR -l unlimited'
f='-f {n,s}LIFO/{o}LIFO'
f_lf='-f {n,s}LIFO/{m}LIFO/{o}LIFO'
f_ll='-f {n,s}LIFO/{x}LIFO/{o}LIFO'

declare -A flags=(
    [default]="$f -h UCPOP -y"
    [neutral]="$f"
    [lf-I-G]="-x0 $f_lf"
    [lf-I+G]="-x1 $f_lf"
    [lf+I-G]="-x2 $f_lf"
    [lf+I+G]="-x3 $f_lf"
    [ll-I-G]="-x0 $f_ll"
    [ll-I+G]="-x1 $f_ll"
    [ll+I-G]="-x2 $f_ll"
    [ll+I+G]="-x3 $f_ll"
)

flags_order=("default" "neutral" "lf-I-G" "lf-I+G" "lf+I-G" "lf+I+G" "ll-I-G" "ll-I+G" "ll+I-G" "ll+I+G")

landmark_extraction_path=$1

declare -A results_plans_generated
declare -A results_plans_visited
declare -A results_dead_ends
declare -A results_plan_length

problems=()

tmp1=$(mktemp)
tmp2=$(mktemp)
trap 'rm -f "$tmp1" "$tmp2"' EXIT

for pair in "${file_pairs[@]}"; do
    set -- $pair
    domain=$1
    problem=$2

    problems+=("$problem")
    echo "Running benchmark for problem '$problem' in domain '$domain'..."

    python3 $landmark_extraction_path --alias seq-sat-lama-2011 examples/$domain examples/$problem > $tmp1

    for version in "${flags_order[@]}"; do
      flag=${flags[$version]}
      cmd="./vhpop -g -v1 $h $flag -m $tmp1 examples/$domain examples/$problem"
      
      timeout 5s $cmd > "$tmp2" 2>&1
      status=$?

      cat $tmp2 > output_"$version".txt 2>&1
      
      if [ $status -eq 124 ]; then
          pgen=""
          pvis=""
          dead=""
          plen=""
      else
          pgen=$(extract_plans_generated "$tmp2")
          pvis=$(extract_plans_visited "$tmp2")
          dead=$(extract_dead_ends "$tmp2")
          plen=$(extract_plan_length "$tmp2")
      fi
      
      key="${problem}|${version}"
      results_plans_generated["$key"]="$pgen"
      results_plans_visited["$key"]="$pvis"
      results_dead_ends["$key"]="$dead"
      results_plan_length["$key"]="$plen"
      
    done
done


print_table() {
    local title="$1"
    local -n res_array=$2
    echo ""
    echo "                      $title                         "

    printf "| %-19s " "Problem"
    for heuristic in "${flags_order[@]}"; do
        printf "| %-9s " "$heuristic"
    done
    echo "|"

    printf "|---------------------"
    for heuristic in "${flags_order[@]}"; do
      printf "|-----------"
    done
    echo "|"

    for problem in "${problems[@]}"; do
        printf "| %-19s " "$problem"
        for heuristic in "${flags_order[@]}"; do
            key="${problem}|${heuristic}"
            value="${res_array[$key]}"
            printf "| %-9s " "$value"
        done
        echo "|"
    done
}


print_table "Plans Generated" results_plans_generated
print_table "Plans Visited"   results_plans_visited
print_table "Dead Ends"       results_dead_ends
print_table "Plan Length"     results_plan_length

write_csv "results/flaws2/plans_generated.csv" "Plans Generated" results_plans_generated
write_csv "results/flaws2/plans_visited.csv" "Plans Visited" results_plans_visited
write_csv "results/flaws2/dead_ends.csv" "Dead Ends" results_dead_ends
write_csv "results/flaws2/plan_length.csv" "Plan Length" results_plan_length
