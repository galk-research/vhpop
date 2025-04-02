#!/bin/bash

# Define an array of file name pairs (each pair is space-separated)
file_pairs=(
    "examples/gripper-domain.pddl examples/gripper-2.pddl"
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
    "examples/monkey-domain.pddl examples/monkey-test1.pddl"
    "examples/bulldozer-domain.pddl examples/get-back-jack.pddl"
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
f=''

landmark_extraction_path=$1

tmp1=$(mktemp)
tmp2=$(mktemp)
tmp3=$(mktemp)

trap 'rm -f "$tmp1" "$tmp2" "$tmp3"' EXIT

total_tests=0

win_count_plans_generated=0 
loss_count_plans_generated=0
tie_count_plans_generated=0       
total_win_diff_plans_generated=0  
total_loss_diff_plans_generated=0 

win_count_plans_visited=0 
loss_count_plans_visited=0
tie_count_plans_visited=0       
total_win_diff_plans_visited=0  
total_loss_diff_plans_visited=0 

win_count_dead_ends=0 
loss_count_dead_ends=0
tie_count_dead_ends=0       
total_win_diff_dead_ends=0  
total_loss_diff_dead_ends=0 

win_count_length=0 
loss_count_length=0
tie_count_length=0       
total_win_diff_length=0  
total_loss_diff_length=0 

timeout_count=0

# Loop through each pair and run the programs
for pair in "${file_pairs[@]}"; do
    set -- $pair  # Split the pair into two variables
    domain=$1
    problem=$2

    total_tests=$(( total_tests + 1 ))
    echo "running $domain $problem"
    
    python3 $landmark_extraction_path --alias seq-sat-lama-2011 $domain $problem > $tmp1


    landmarks_cmd="./vhpop -g -v1 --landmark-file=$tmp1 $h $f $domain $problem"
    no_landmarks_cmd="./vhpop -g -v1 $h $f $domain $problem"


    # Run both commands in parallel and get their PIDs
    $landmarks_cmd > "$tmp2" 2>&1 & pid1=$!
    $no_landmarks_cmd > "$tmp3" 2>&1 & pid2=$!

    # Wait for at most 5 seconds
    sleep 10

    skip=false

    # Check if either process is still running and kill if necessary
    if ps -p $pid1 > /dev/null; then
        echo "landmarks_cmd did not finish within timeout" >> "$tmp2"
        kill $pid1
        skip=true
    fi

    if ps -p $pid2 > /dev/null; then
        echo "no_landmarks_cmd did not finish within timeout" >> "$tmp3"
        kill $pid2
        skip=true
    fi

    if $skip; then
        echo "Skipping this test case due to timeout"
        timeout_count=$(( timeout_count + 1 ))
        continue
    fi


    plans_generated_with_landmarks=$(extract_plans_generated "$tmp2")
    plans_generated_without_landmarks=$(extract_plans_generated "$tmp3")

    plans_visited_with_landmarks=$(extract_plans_visited "$tmp2")
    plans_visited_without_landmarks=$(extract_plans_visited "$tmp3")

    dead_ends_with_landmarks=$(extract_dead_ends "$tmp2")
    dead_ends_without_landmarks=$(extract_dead_ends "$tmp3")

    plan_length_with_landmarks=$(extract_plan_length "$tmp2")
    plan_length_without_landmarks=$(extract_plan_length "$tmp3")

    # Validate extracted numbers
    if ! [[ "$plans_generated_with_landmarks" =~ ^[0-9]+$ ]]; then
        echo "Error: Could not extract valid plans number from version 1"
        exit 1
    fi

    if ! [[ "$plans_generated_without_landmarks" =~ ^[0-9]+$ ]]; then
        echo "Error: Could not extract valid plans number from version 2"
        exit 1
    fi

    echo "Plans generated with landmarks: $plans_generated_with_landmarks"
    echo "Plans generated without landmarks: $plans_generated_without_landmarks"

    if [ "$plans_generated_with_landmarks" -eq "$plans_generated_without_landmarks" ]; then
        echo "Both versions generated the same number of plans"
        tie_count_plans_generated=$(( tie_count_plans_generated + 1 ))
    elif [ "$plans_generated_with_landmarks" -lt "$plans_generated_without_landmarks" ]; then
        diff=$(( plans_generated_without_landmarks - plans_generated_with_landmarks ))
        echo -e "\e[32mVhpop with landmarks had to generate less plans (difference: $diff)\e[0m"
        win_count_plans_generated=$(( win_count_plans_generated + 1 ))
        total_win_diff_plans_generated=$(( total_win_diff_plans_generated + diff ))
    else
        diff=$(( plans_generated_with_landmarks - plans_generated_without_landmarks ))
        echo -e "\e[31mVhpop with landmarks had to generate more plans (difference: $diff)\e[0m"
        loss_count_plans_generated=$(( loss_count_plans_generated + 1 ))
        total_loss_diff_plans_generated=$(( total_loss_diff_plans_generated + diff ))   
    fi

    echo "Plans visited with landmarks: $plans_visited_with_landmarks"
    echo "Plans visited without landmarks: $plans_visited_without_landmarks"

    if [ "$plans_visited_with_landmarks" -eq "$plans_visited_without_landmarks" ]; then
        echo "Both versions visited the same number of plans"
        tie_count_plans_visited=$(( tie_count_plans_visited + 1 ))
    elif [ "$plans_visited_with_landmarks" -lt "$plans_visited_without_landmarks" ]; then
        diff=$(( plans_visited_without_landmarks - plans_visited_with_landmarks ))
        echo -e "\e[32mVhpop with landmarks had to visit less plans (difference: $diff)\e[0m"
        win_count_plans_visited=$(( win_count_plans_visited + 1 ))
        total_win_diff_plans_visited=$(( total_win_diff_plans_visited + diff ))
    else
        diff=$(( plans_visited_with_landmarks - plans_visited_without_landmarks ))
        echo -e "\e[31mVhpop with landmarks had to visit more plans (difference: $diff)\e[0m"
        loss_count_plans_visited=$(( loss_count_plans_visited + 1 ))
        total_loss_diff_plans_visited=$(( total_loss_diff_plans_visited + diff ))   
    fi

    echo "Dead ends encountered with landmarks: $dead_ends_with_landmarks"
    echo "Dead ends encountered without landmarks: $dead_ends_without_landmarks"

    if [ "$dead_ends_with_landmarks" -eq "$dead_ends_without_landmarks" ]; then
        echo "Both versions generated the same number of dead_ends"
        tie_count_dead_ends=$(( tie_count_dead_ends + 1 ))
    elif [ "$dead_ends_with_landmarks" -lt "$dead_ends_without_landmarks" ]; then
        diff=$(( dead_ends_without_landmarks - dead_ends_with_landmarks ))
        echo -e "\e[32mVhpop with landmarks encountered less dead_ends (difference: $diff)\e[0m"
        win_count_dead_ends=$(( win_count_dead_ends + 1 ))
        total_win_diff_dead_ends=$(( total_win_diff_dead_ends + diff ))
    else
        diff=$(( dead_ends_with_landmarks - dead_ends_without_landmarks ))
        echo -e "\e[31mVhpop with landmarks encountered more dead_ends (difference: $diff)\e[0m"
        loss_count_dead_ends=$(( loss_count_dead_ends + 1 ))
        total_loss_diff_dead_ends=$(( total_loss_diff_dead_ends + diff ))   
    fi

    echo "Plan length with landmarks: $plan_length_with_landmarks"
    echo "Plan length without landmarks: $plan_length_without_landmarks"

    if [ "$plan_length_with_landmarks" -eq "$plan_length_without_landmarks" ]; then
        echo "Both versions found a plan of the same length"
        tie_count_length=$(( tie_count_length + 1 ))
    elif [ "$plan_length_with_landmarks" -lt "$plan_length_without_landmarks" ]; then
        diff=$(( plan_length_without_landmarks - plan_length_with_landmarks ))
        echo -e "\e[32mVhpop with landmarks found a shorter plan (difference: $diff)\e[0m"
        win_count_length=$(( win_count_length + 1 ))
        total_win_diff_length=$(( total_win_diff_length + diff ))
    else
        diff=$(( plan_length_with_landmarks - plan_length_without_landmarks ))
        echo -e "\e[31mVhpop with landmarks found a longer plan (difference: $diff)\e[0m"
        loss_count_length=$(( loss_count_length + 1 ))
        total_loss_diff_length=$(( total_loss_diff_length + diff ))   
    fi
    echo -------------------------------------
done

echo "========== Overall Comparison =========="
echo "Total test cases: $total_tests"
echo "Timeouts: $timeout_count"
echo ""
echo "-- Plans Generated --"
echo "Wins (fewer plans generated with landmarks): $win_count_plans_generated"
echo "Losses (more plans generated with landmarks): $loss_count_plans_generated"
echo "Ties: $tie_count_plans_generated"
if [ $win_count_plans_generated -gt 0 ]; then
    avg_win_diff_plans_generated=$(( total_win_diff_plans_generated / win_count_plans_generated ))
    echo "Average improvement (wins): $avg_win_diff_plans_generated fewer plans generated"
fi
if [ $loss_count_plans_generated -gt 0 ]; then
    avg_loss_diff_plans_generated=$(( total_loss_diff_plans_generated / loss_count_plans_generated ))
    echo "Average penalty (losses): $avg_loss_diff_plans_generated more plans generated"
fi

echo ""
echo "-- Plans Visited --"
echo "Wins (fewer plans visited with landmarks): $win_count_plans_visited"
echo "Losses (more plans visited with landmarks): $loss_count_plans_visited"
echo "Ties: $tie_count_plans_visited"
if [ $win_count_plans_visited -gt 0 ]; then
    avg_win_diff_plans_visited=$(( total_win_diff_plans_visited / win_count_plans_visited ))
    echo "Average improvement (wins): $avg_win_diff_plans_visited fewer plans visited"
fi
if [ $loss_count_plans_visited -gt 0 ]; then
    avg_loss_diff_plans_visited=$(( total_loss_diff_plans_visited / loss_count_plans_visited ))
    echo "Average penalty (losses): $avg_loss_diff_plans_visited more plans visited"
fi

echo ""
echo "-- Dead Ends Encountered --"
echo "Wins (fewer dead ends encountered with landmarks): $win_count_dead_ends"
echo "Losses (more dead ends encountered with landmarks): $loss_count_dead_ends"
echo "Ties: $tie_count_dead_ends"
if [ $win_count_dead_ends -gt 0 ]; then
    avg_win_diff_dead_ends=$(( total_win_diff_dead_ends / win_count_dead_ends ))
    echo "Average improvement (wins): $avg_win_diff_dead_ends fewer dead ends"
fi
if [ $loss_count_dead_ends -gt 0 ]; then
    avg_loss_diff_dead_ends=$(( total_loss_diff_dead_ends / loss_count_dead_ends ))
    echo "Average penalty (losses): $avg_loss_diff_dead_ends more dead ends"
fi

echo ""
echo "-- Plan Length --"
echo "Wins (shorter plans with landmarks): $win_count_length"
echo "Losses (longer plans with landmarks): $loss_count_length"
echo "Ties: $tie_count_length"
if [ $win_count_length -gt 0 ]; then
    avg_win_diff_length=$(awk "BEGIN {printf \"%.2f\", $total_win_diff_length/$win_count_length}")
    echo "Average improvement (wins): $avg_win_diff_length shorter plan length"
fi
if [ $loss_count_length -gt 0 ]; then
    avg_loss_diff_length=$(awk "BEGIN {printf \"%.2f\", $total_loss_diff_length/$loss_count_length}")
    echo "Average penalty (losses): $avg_loss_diff_length longer plan length"
fi
echo "========================================"
