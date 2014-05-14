#!/bin/sh

#
# A simple script for interfacing with a running transmission-daemon instance.
# Designed to simplify certain tasks such as scanning dirs and removing finished
# torrents.
#

WATCHDIRS="/share/torrents/anime /share/torrents/movies /share/torrents/television"
REMOTE="/usr/local/bin/transmission-remote "
GREP="/usr/bin/grep"
SED="/usr/bin/sed"

usage ()
{
    log "usage: btctl.sh <command> <args>"
    log " commands:"
    log "  scan - scans the watch dirs for torrents and adds them to transmission"
    log "  sweep - checks the curren torrents and removes any marked as 'Finished'"
}

scan()
{
    for dir in $WATCHDIRS
    do
        log "scanning $dir"

        for torrent in "$dir"/*.torrent
        do
            if [ "$torrent" != "$dir/*.torrent" ]
            then
                log "found torrent: $torrent"
                output=`$REMOTE --add "$torrent" --download-dir "$dir"`
    
                if [ $? == 0 ]
                then
                    /bin/rm -f "$torrent"
                else
                    log "failed to add torrent: $output"
                fi
            fi
        done
    done
}

sweep()
{
    ids=`$REMOTE -l | $GREP -i finished | $SED 's/[ ]*\([0-9]*\).*/\1/'`

    for id in $ids
    do
        $REMOTE -t $id --remove

        if [ $? == 0 ]
        then
            log "removed finished torrent $id"
        else
            log "failed to remove torrent $id"
        fi
    done
}

log()
{
    tag="btctl.sh"

    echo "$1"
}

if [ $# -lt 1 ]
then
    usage
    exit
fi

if [ "$1" == "scan" ]
then
    scan
elif [ "$1" == "sweep" ]
then
    sweep
fi

exit 0
