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

    # blindly try to create the recursive base snapshots, then check the
    # return code to branch on either sending the initial data, or sending
    # an incremental stream.
    zfs snapshot -r "$local"@$base_snap >/dev/null 2>&1

    if [ $? == 0 ]
    then
        # the base snapshot was just created, destroy any remote data
        # and start fresh
        log "initial snapshot created, clearing remote host's copy (if any)"

        remotefs="$remote`echo $local | sed 's|[^/]*||'`"

        ssh $host zfs destroy -r "$remotefs" > /dev/null 2>&1
        zfs destroy -r "$local"@$delta_snap > /dev/null 2>&1 

        snaps=`zfs list -H -r -t snapshot -o name $local | grep @$base_snap\$`

        for snap in $snaps
        do
            send_output=`zfs send $snap | ssh $host zfs recv -dvF $remote`

            if [ $? == 0 ]
            then
                log "successfully sent snapshot '$snap'"
            else
                fail "failed to send snapshot '$snap', output: '$send_output'"
                fail "destroying newly created base snapshot"

                zfs destroy -r "$local"@$base_snap > /dev/null 2>&1

                break
            fi
        done
    else
        # the base snapshot already exists
        zfs snapshot -r "$local"@$delta_snap >/dev/null 2>&1

        if [ $? != 0 ]
        then
            # something went wrong with a previous iteration of this script
            # that caused the delta snap to be left around. Don't create
            # a new delta snap, just try to re send the last one
            log "failed to create "$local@$delta_snap", attempting to re-send"
            resend=1
        fi

        snaps=`zfs list -H -r -t snapshot -o name $local | grep @$delta_snap\$`

        for snap in $snaps
        do
            send_output=`zfs send -i $base_snap $snap | ssh $host zfs recv -dvF $remote`

            if [ $? == 0 ]
            then
                log "sent delta, updating snapshots"
                old_local_base=`echo $snap | sed 's/@[^@]*$//'`@$base_snap
                old_remote_base="$remote`echo $old_local_base | sed 's|^[^/]*||'`"
                old_remote_delta="$remote`echo $snap | sed 's|^[^/]*||'`"
                log "destroying local snapshot $old_local_base"
                zfs destroy $old_local_base >/dev/null 2>&1
                log "renaming local snapshot $snap to $old_local_base"
                zfs rename $snap $old_local_base >/dev/null 2>&1
                log "destroying remote snapshot $old_remote_base"
                ssh $host zfs destroy $old_remote_base >/dev/null 2>&1
                log "renaming remote snapshot $old_remote_delta to $old_remote_base"
                ssh $host zfs rename $old_remote_delta $old_remote_base >/dev/null 2>&1
            else
                log "failed to send $snap, output:'$send_output'"
                if [ $resend ]
                then
                    log "failed to send "$local@$delta_snap" for a second time"
                else
                    log "failed to send "$local@$delta_snap", will retry again later"
                fi
            fi
        done
    fi

    ssh $host zfs set readonly=on "$remote" >/dev/null 2>&1
}

log()
{
    echo $1
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
