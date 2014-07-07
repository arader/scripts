#!/bin/sh

#
# a cron script that replicates zfs datasets to a remote machine
#

PATH=/bin:/usr/bin:/sbin

host="$1"
self="`basename $0`"
dotpid="/var/run/$self.pid"
base_snap="shadow.base"
delta_snap="shadow.delta"
ec=0

process_dataset()
{
    local=`echo "$1" | sed 's/:.*//'`
    remote=`echo "$1" | sed 's/.*://'`

    zfs list -H "$local" >/dev/null 2>&1

    if [ $? != 0 ]
    then
        fail "could not find dataset $local"
        return
    fi

    # make sure we can actually write the data
    ssh $host zfs set readonly=off "$remote" >/dev/null 2>&1

    # get a list of all the datasets under the specified dataset
    datasets=`zfs list -H -r -o name $local`

    # iterate through each dataset and send a backup
    for dataset in $datasets
    do
        # calculate what the remote dataset's name is
        remote_dataset="$remote`echo $dataset | sed 's|^[^/]*||'`"

        # blindly try to create the base snapshot, then check the
        # return code to branch on either sending the initial data, or sending
        # an incremental stream.
        zfs snapshot $dataset@$base_snap >/dev/null 2>&1

        if [ $? == 0 ]
        then
            # the base snapshot was just created, destroy any remote data
            # and start fresh
            log "initial snapshot $datset@$base_snap created, clearing remote host's copy (if any)"

            ssh $host zfs destroy -r "$remote_dataset" > /dev/null 2>&1
            zfs destroy $dataset@$delta_snap > /dev/null 2>&1 

            send_output=`zfs send $dataset@$base_snap | ssh $host zfs recv -dvF $remote`

            if [ $? == 0 ]
            then
                log "successfully sent snapshot '$dataset@$base_snap'"
            else
                fail "failed to send snapshot '$dataset@$base_snap', output: '$send_output', destroying newly created base snapshot"

                # destroy the newly created base snapshot so that the next time
                # this script is run, the base snapshot will be re-created and
                # re-sent
                zfs destroy -r $dataset@$base_snap > /dev/null 2>&1
            fi
        else
            # the base snapshot already exists
            zfs snapshot $dataset@$delta_snap >/dev/null 2>&1

            if [ $? != 0 ]
            then
                # something went wrong with a previous iteration of this script
                # that caused the delta snap to be left around. Don't create
                # a new delta snap, just try to re send the last one
                log "failed to create $dataset@$delta_snap, attempting to re-send"
                resend=1
            fi

            send_output=`zfs send -i $base_snap $dataset@$delta_snap | ssh $host zfs recv -dvF $remote`

            if [ $? == 0 ]
            then
                log "successfully sent $dataset@$delta_snap, updating base snapshot"
                log "    destroying local snapshot $dataset@$base_snap"
                zfs destroy $dataset@$base_snap >/dev/null 2>&1
                log "    renaming local snapshot $dataset@$delta_snap to $dataset@$base_snap"
                zfs rename $dataset@$delta_snap $dataset@$base_snap >/dev/null 2>&1
                log "    destroying remote snapshot $remote_dataset@$base_snap"
                ssh $host zfs destroy $remote_dataset@$base_snap >/dev/null 2>&1
                log "    renaming remote snapshot $remote_dataset@$delta_snap to $remote_dataset@$base_snap"
                ssh $host zfs rename $remote_dataset@$delta_snap $remote_dataset@$base_snap >/dev/null 2>&1
            else
                fail "failed to send $dataset@$delta_snap, output:'$send_output'"

                if [ $resend ]
                then
                fi
            fi
        fi
    done

    ssh $host zfs set readonly=on "$remote" >/dev/null 2>&1
}

log()
{
    echo "$1"
    logger -t $self "$1"
}

fail()
{
    ec=1
    log $1
}

usage()
{
    echo "usage: $self dest_host local_dataset1:remote_dataset1 [local_dataset2:remote_dataset2] ..."
    echo " dest_host: the destination host to receive the datasets from"
    echo " local_dataset1: the local dataset to replicate"
    echo " remote_dataset1: the place to replicate local_dataset1 to"
}

if [ ! `whoami` = "root" ]
then
    echo "$self must be run as root"
    exit 1
fi

if [ $# -lt 2 ]
then
    usage
    exit 1
fi

pid=`pgrep -F $dotpid 2>/dev/null`

if [ ! -z $pid ]
then
    log "$self is already running as pid $pid, exiting"
    exit 0
fi

echo $$ > $dotpid

shift


while [ $# -gt 0 ]
do
    process_dataset "$1"
    shift
done

exit $ec
