#!/bin/sh

if [ -z "$1" ] || [ -z "$2" ]
then
    echo "ERROR: missing arguments, usage:"
    echo "$0 <hostname> <cpu #> [collectd socket file]"
    exit 1
fi

host="$1"
cpuid="$2"

if [ ! -z "$3" ]
then
    socket="-s $3"
else
    socket=""
fi

idle=$(collectdctl $socket getval $host/cpu-$cpuid/cpu-idle | sed 's/^value=//' | xargs printf '%.5f\n')

usage=0
for key in interrupt nice system user
do
    value=$(collectdctl $socket getval $host/cpu-$cpuid/cpu-$key | sed 's/^value=//' | xargs printf '%.5f\n')
    usage=$(echo "$usage + $value" | bc -l)
done

percent=$(echo "($usage / ($usage + $idle)) * 100" | bc -l | xargs printf '%.1f\n')
echo $percent
