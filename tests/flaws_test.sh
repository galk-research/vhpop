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
h='-h ADDR/OL'
# f='-f {n,s}LR/{l}MW_add -l 12000 -f {n,s}LR/{u}MW_add/{l}MW_add -l 100000 -f {n,s,l}LR -l 240000 -f {n,s,u}LR/{l}LR -l unlimited'
f='-f {n,s}LIFO/{o}LIFO'
f_lf='-f {n,s}LIFO/{m}LIFO/{o}LIFO'
f_ll='-f {n,s}LIFO/{x}LIFO/{o}LIFO'

landmark_extraction_path=$1

tmp1=$(mktemp)
tmp2=$(mktemp)
tmp3=$(mktemp)
tmp4=$(mktemp)

trap 'rm -f "$tmp1" "$tmp2" "$tmp3" "$tmp4"' EXIT

problems=()

plans_generated_1=()
plans_generated_2=()
plans_generated_3=()

plans_visited_1=()
plans_visited_2=()
plans_visited_3=()

dead_ends_1=()
dead_ends_2=()
dead_ends_3=()

plan_length_1=()
plan_length_2=()
plan_length_3=()

for pair in "${file_pairs[@]}"; do
    set -- $pair
    domain=$1
    problem=$2

    problems+=("$problem")

    total_tests=$(( total_tests + 1 ))
    
    python3 $landmark_extraction_path --alias seq-sat-lama-2011 examples/$domain examples/$problem > $tmp1

    echo "Running $problem"

    lf_cmd="./vhpop -g -v1 --landmark-file=$tmp1 $h $f_lf examples/$domain examples/$problem"
    ll_cmd="./vhpop -g -v1 --landmark-file=$tmp1 $h $f_ll examples/$domain examples/$problem"
    no_landmarks_cmd="./vhpop -g -v1 --landmark-file=$tmp1 $h $f examples/$domain examples/$problem"


    timeout 5s $lf_cmd > "$tmp2" 2>&1
    status1=$?
    timeout 5s $ll_cmd > "$tmp3" 2>&1
    status2=$?
    timeout 5s $no_landmarks_cmd > "$tmp4" 2>&1
    status3=$?

    cat $tmp1 > output1.txt
    cat $tmp2 > output2.txt
    cat $tmp3 > output3.txt
    cat $tmp4 > output4.txt

    plans1=$(extract_plans_generated "$tmp2")
    plans2=$(extract_plans_generated "$tmp3")
    plans3=$(extract_plans_generated "$tmp4")

    visited1=$(extract_plans_visited "$tmp2")
    visited2=$(extract_plans_visited "$tmp3")
    visited3=$(extract_plans_visited "$tmp4")

    dead1=$(extract_dead_ends "$tmp2")
    dead2=$(extract_dead_ends "$tmp3")
    dead3=$(extract_dead_ends "$tmp4")

    length1=$(extract_plan_length "$tmp2")
    length2=$(extract_plan_length "$tmp3")
    length3=$(extract_plan_length "$tmp4")

    # If a command timed out, mark the stats as 'x'
    [ $status1 -eq 124 ] && { plans1='x'; visited1='x'; dead1='x'; length1='x'; }
    [ $status2 -eq 124 ] && { plans2='x'; visited2='x'; dead2='x'; length2='x'; }
    [ $status3 -eq 124 ] && { plans3='x'; visited3='x'; dead3='x'; length3='x'; }

    # Append this benchmark's values into arrays
    plans_generated_1+=("$plans1")
    plans_generated_2+=("$plans2")
    plans_generated_3+=("$plans3")

    plans_visited_1+=("$visited1")
    plans_visited_2+=("$visited2")
    plans_visited_3+=("$visited3")

    dead_ends_1+=("$dead1")
    dead_ends_2+=("$dead2")
    dead_ends_3+=("$dead3")

    plan_length_1+=("$length1")
    plan_length_2+=("$length2")
    plan_length_3+=("$length3")

done

print_table() {
    local title="$1"
    shift
    local arr1=("${!1}")
    shift
    local arr2=("${!1}")
    shift
    local arr3=("${!1}")

    echo ""
    echo "                      $title                         "
    echo "|       Problem       | LMs First | LMs Last  |  Neutral  |"
    echo "|---------------------|-----------|-----------|-----------|"
    for i in "${!problems[@]}"; do
        printf "| %-19s | %-9s | %-9s | %-9s |\n" \
            "${problems[$i]}" "${arr1[$i]}" "${arr2[$i]}" "${arr3[$i]}"
    done
}

# Print the four tables
print_table "Plans Generated" plans_generated_1[@] plans_generated_2[@] plans_generated_3[@]
print_table "Plans Visited"   plans_visited_1[@]   plans_visited_2[@]   plans_visited_3[@]
print_table "Dead Ends"       dead_ends_1[@]       dead_ends_2[@]       dead_ends_3[@]
print_table "Plan Length"     plan_length_1[@]     plan_length_2[@]     plan_length_3[@]