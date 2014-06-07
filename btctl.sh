#!/bin/sh

#
# A simple script for interfacing with a running transmission-daemon instance.
# Designed to simplify certain tasks such as scanning dirs and removing finished
# torrents.
#

WATCHDIR_1="/share/downloads/torrents/anime"
ACTIVEDIR_1="/share/downloads/active"
COMPLETEDIR_1="/share/downloads/complete/anime"

WATCHDIR_2="/share/downloads/torrents/movies"
ACTIVEDIR_2="/share/downloads/active"
COMPLETEDIR_2="/share/downloads/complete/movies"

WATCHDIR_3="/share/downloads/torrents/television"
ACTIVEDIR_3="/share/downloads/active"
COMPLETEDIR_3="/share/downloads/complete/television"

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
    iter=1

    while [ 1 ]
    do
        watchdir="$(eval echo \${WATCHDIR_${iter}})"
        activedir="$(eval echo \${ACTIVEDIR_${iter}})"
        completedir="$(eval echo \${COMPLETEDIR_${iter}})"

        if [ -z "$watchdir" ] || [ -z "$activedir" ] || [ -z "$completedir" ]
        then
            break
        else
            log "scanning $watchdir"
    
            for torrent in "$watchdir"/*.torrent
            do
                if [ "$torrent" != "$watchdir/*.torrent" ]
                then
                    log "found torrent: $torrent"
                    output=`$REMOTE --add "$torrent" --incomplete-dir "$activedir" --download-dir "$completedir"`

                    if [ $? == 0 ]
                    then
                        /bin/rm -f "$torrent"
                    else
                        log "failed to add torrent: $output"
                    fi
                fi
            done
        fi

        iter=`expr $iter + 1`
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
