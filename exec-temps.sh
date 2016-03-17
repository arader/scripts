#!/bin/sh

# A collectd 'exec' script used to get temperature info
# from a number of sources

HOSTNAME="${COLLECTD_HOSTNAME:-$(hostname -f)}"
INTERVAL="${COLLECTD_INTERVAL:-10}"

NCPUS=$(sysctl -n hw.ncpu)
CPUS=$(jot $NCPUS 0)

while sleep "$INTERVAL"
do
    time="$(date +%s)"

    for cpu in $CPUS
    do
        temp=$(sysctl -n dev.cpu.$cpu.temperature | sed 's/.$//')
        echo "PUTVAL $HOSTNAME/exec-temps/cpu-$cpu interval=$INTERVAL $time:$temp"
    done
done
