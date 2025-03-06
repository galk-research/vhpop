#!/bin/bash

h='-h ADDR/ADDR_WORK/BUC/LIFO'
f='-f {n,s}LR/{l}MW_add -l 12000 -f {n,s}LR/{u}MW_add/{l}MW_add -l 100000 -f {n,s,l}LR -l 240000 -f {n,s,u}LR/{l}LR -l unlimited'

landmark=$1
domain=$2
problem=$3

./vhpop -g -v1 -m $landmark $h $f $domain $problem
