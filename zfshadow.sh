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

    # blindly try to create the recursive base snapshots, then check the
    # return code to branch on either sending the initial data, or sending
    # an incremental stream.
    zfs snapshot -r "$local"@$base_snap >/dev/null 2>&1

    if [ $? == 0 ]
    then
        # the base snapshot was just created
        zfs send -R "$local"@$base_snap | ssh $host zfs recv -d "$remote"

        ssh $host zfs set readonly=on "$remote"
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

        ssh $host zfs set readonly=off "$remote"

        zfs send -R -i @$base_snap "$local"@$delta_snap | ssh $host zfs recv -d "$remote"

        if [ $? == 0 ]
        then
            log "sent delta, updating snapshots"
            zfs destroy -r "$local"@$base_snap
            zfs rename -r "$local"@$delta_snap "$local"@$base_snap
        else
            if [ $resend ]
            then
                log "failed to send "$local@$delta_snap" for a second time"
            else
                log "failed to send "$local@$delta_snap", will retry again later"
            fi
        fi

        ssh $host zfs set readonly=on "$remote"

    fi
}

log()
{
    echo $1
    logger -t $self "$1"
}

fail()
{
    ec=1
    echo $1
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
