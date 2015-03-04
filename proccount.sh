#!/bin/sh

if [ -z "$1" ]
then
    echo "ERROR: missing arguments, usage:"
    echo "$0 <hostname> [collectd socket file]"
    exit 1
fi

host="$1"

if [ ! -z "$2" ]
then
    socket="-s $2"
else
    socket=""
fi

total=0
for key in blocked idle running sleeping stopped wait zombies
do
    value=$(collectdctl $socket getval $host/processes/ps_state-$key | sed 's/^value=//' | xargs printf '%.0f\n')
    total=$(echo "$total + $value" | bc -l)
done

echo $total
