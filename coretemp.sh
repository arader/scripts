#!/bin/sh

cpu_count=$(sysctl -n hw.ncpu)

temp_sum=0
i=0
while [ $i -lt $cpu_count ]
do
    temp=$(sysctl -n dev.cpu.$i.temperature | sed 's/C$//')
    temp_sum=$(echo "$temp_sum + $temp" | bc -l)
    i=$(echo "$i + 1" | bc -l)
done

temp_avg=$(echo "$temp_sum / $cpu_count" | bc -l | sed 's/\..*//')

echo $temp_avg
