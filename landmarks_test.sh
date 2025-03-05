#!/bin/bash

# Define an array of file name pairs (each pair is space-separated)
file_pairs=(
    "examples/gripper-domain.pddl examples/gripper-4.pddl"
    "examples/gripper-domain.pddl examples/gripper-6.pddl"
    "examples/gripper-domain.pddl examples/gripper-8.pddl"
    "examples/gripper-domain.pddl examples/gripper-10.pddl"
    "examples/hanoi-domain.pddl examples/hanoi-3.pddl"
    "examples/hanoi-3-domain.pddl examples/hanoi-n-3.pddl"
    "examples/grid-domain.pddl examples/simple-grid2.pddl"
    "examples/grid-domain.pddl examples/simple-grid3.pddl"
    "examples/logistics-domain.pddl examples/logistics-a.pddl"
    "examples/logistics-domain.pddl examples/logistics-b.pddl"
    "examples/logistics-domain.pddl examples/logistics-c.pddl"
    "examples/logistics-domain.pddl examples/logistics-d.pddl"
    "examples/rocket-domain.pddl examples/rocket-ext-a.pddl"
    "examples/rocket-domain.pddl examples/rocket-ext-b.pddl"
    "examples/simple-blocks-domain.pddl examples/bw-large-a.pddl"
    "examples/simple-blocks-domain.pddl examples/bw-large-b.pddl"
    "examples/simple-blocks-domain.pddl examples/bw-large-d.pddl"
)

# Function to extract plans count from output
extract_plans() {
    grep -m 1 "^Plans generated: [0-9]\+" "$1" | awk '{print $3}'
}

h='-h ADDR/ADDR_WORK/BUC/LIFO'
f='-f {n,s}LR/{l}MW_add -l 12000 -f {n,s}LR/{u}MW_add/{l}MW_add -l 100000 -f {n,s,l}LR -l 240000 -f {n,s,u}LR/{l}LR -l unlimited'


tmp1=$(mktemp)
# Temporary files for output capture
tmp2=$(mktemp)
tmp3=$(mktemp)

# Overall counters
total_tests=0
win_count=0       # cases where landmarks version generated fewer plans
loss_count=0      # cases where landmarks version generated more plans
tie_count=0       # cases where both versions are equal
total_win_diff=0  # cumulative difference for wins
total_loss_diff=0 # cumulative difference for losses

# Loop through each pair and run the programs
for pair in "${file_pairs[@]}"; do
    set -- $pair  # Split the pair into two variables
    domain=$1
    problem=$2

    total_tests=$(( total_tests + 1 ))
    echo "running $domain $problem"
    
    python3 ../MODDED_FD/fast-downward.py --alias seq-sat-lama-2011 $domain $problem > $tmp1


    landmarks_cmd="./vhpop -g -v1 -m $tmp1 $h $f $domain $problem"
    no_landmarks_cmd="./vhpop -g -v1 $h $f $domain $problem"


    # Run both versions and capture output
    $landmarks_cmd > "$tmp2" 2>&1
    $no_landmarks_cmd > "$tmp3" 2>&1


    # Extract numbers from both versions
    plans_with_landmarks=$(extract_plans "$tmp2")
    plans_without_landmarks=$(extract_plans "$tmp3")

    # Validate extracted numbers
    if ! [[ "$plans_with_landmarks" =~ ^[0-9]+$ ]]; then
        echo "Error: Could not extract valid plans number from version 1"
        exit 1
    fi

    if ! [[ "$plans_without_landmarks" =~ ^[0-9]+$ ]]; then
        echo "Error: Could not extract valid plans number from version 2"
        exit 1
    fi

    # Compare results
    echo "Plans generated with landmarks: $plans_with_landmarks"
    echo "Plans generated without landmarks: $plans_without_landmarks"

    if [ "$plans_with_landmarks" -eq "$plans_without_landmarks" ]; then
        echo "Both versions generated the same number of plans"
        tie_count=$(( tie_count + 1 ))
    elif [ "$plans_with_landmarks" -lt "$plans_without_landmarks" ]; then
        diff=$(( plans_without_landmarks - plans_with_landmarks ))
        echo -e "\e[32mVhpop with landmarks had to generate less plans (difference: $diff)\e[0m"
        win_count=$(( win_count + 1 ))
        total_win_diff=$(( total_win_diff + diff ))
    else
        diff=$(( plans_with_landmarks - plans_without_landmarks ))
        echo -e "\e[31mVhpop with landmarks had to generate more plans (difference: $diff)\e[0m"
        loss_count=$(( loss_count + 1 ))
        total_loss_diff=$(( total_loss_diff + diff ))   
    fi
    echo -------------------------------------
done

# Overall comparison summary
echo "========== Overall Comparison =========="
echo "Total test cases: $total_tests"
echo "Wins (landmarks generated fewer plans): $win_count"
echo "Losses (landmarks generated more plans): $loss_count"
echo "Ties: $tie_count"
if [ $win_count -gt 0 ]; then
    avg_win_diff=$(( total_win_diff / win_count ))
    echo "Average improvement in wins: $avg_win_diff fewer plans generated"
fi
if [ $loss_count -gt 0 ]; then
    avg_loss_diff=$(( total_loss_diff / loss_count ))
    echo "Average penalty in losses: $avg_loss_diff more plans generated"
fi
echo "========================================"

# Clean up temporary files
rm "$tmp1" "$tmp2" "$tmp3"