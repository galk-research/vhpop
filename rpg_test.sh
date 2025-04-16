#!/bin/bash

file_pairs=(
    "ferry-domain.pddl test-ferry.pddl"
    "flat-tire-domain.pddl fix1.pddl"
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

declare -A heuristics=(
  [ADD]="-h ADD"
  [MAX]="-h MAX"
  [FF]="-h FF"
  [FF_COST]="-h FF_COST"
  [FFR]="-h FFR"
  [FFR_COST]="-h FFR_COST"
)

heuristics_order=("ADD" "MAX" "FF" "FF_COST" "FFR" "FFR_COST")


f='-f {n,s}LR/{l}MW_add -l 12000 -f {n,s}LR/{u}MW_add/{l}MW_add -l 100000 -f {n,s,l}LR -l 240000 -f {n,s,u}LR/{l}LR -l unlimited'
f=''

landmark_extraction_path=$1

declare -A results_plans_generated
declare -A results_plans_visited
declare -A results_dead_ends
declare -A results_plan_length

problems=()

for pair in "${file_pairs[@]}"; do
    set -- $pair
    domain=$1
    problem=$2

    problems+=("$problem")
    echo "Running benchmark for problem '$problem' in domain '$domain'..."

    for heuristic in "${heuristics_order[@]}"; do
      flag=${heuristics[$heuristic]}
      cmd="./vhpop -g -v1 $flag $f examples/$domain examples/$problem"
      
      tmp=$(mktemp)
      timeout 10s $cmd > "$tmp" 2>&1
      status=$?
      
      if [ $status -eq 124 ]; then
          pgen="x"
          pvis="x"
          dead="x"
          plen="x"
      else
          pgen=$(extract_plans_generated "$tmp")
          pvis=$(extract_plans_visited "$tmp")
          dead=$(extract_dead_ends "$tmp")
          plen=$(extract_plan_length "$tmp")
      fi
      
      key="${problem}|${heuristic}"
      results_plans_generated["$key"]="$pgen"
      results_plans_visited["$key"]="$pvis"
      results_dead_ends["$key"]="$dead"
      results_plan_length["$key"]="$plen"
      
      rm -f "$tmp"
    done
done


print_table() {
    local title="$1"
    local -n res_array=$2
    echo ""
    echo "                      $title                         "

    printf "| %-19s " "Problem"
    for heuristic in "${heuristics_order[@]}"; do
        printf "| %-9s " "$heuristic"
    done
    echo "|"

    printf "|---------------------"
    for heuristic in "${heuristics_order[@]}"; do
      printf "|-----------"
    done
    echo "|"

    for problem in "${problems[@]}"; do
        printf "| %-19s " "$problem"
        for heuristic in "${heuristics_order[@]}"; do
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
