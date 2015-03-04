#!/bin/sh

#
# A script that will read video files from a specified directory
# and move them to a destination directory based on their recorded
# date. This script is meant to be used either from the command line
# or as a cron job
#

self="$(basename $0)"
dotpid="/var/run/$self.pid"

scan()
{
    src=$1
    root=$2

    find $1 -iname "*.mov" -or -iname "*.avi" -or -iname "*.mp4" | while read file
    do
        #dt=`$EXIF --tag 0x132 -m "$file"`
        dt=$(mediainfo --inform="General;%Recorded_Date%" $file)

        if [ "$?" != 0 ] || [ -z "$dt" ]
        then
            log "failed to read date from $file, defaulting to 'today'"
            parent=`date -j +%Y/%m.%B`
        else
            parent=`date -j -f "%Y-%m-%dT%H:%M:%S%z" "$dt" +%Y/%m.%B`
        fi

        dest="$root/$parent"

        move "$file" "$dest"
    done
}

move()
{
    file=$1
    dest=$2

    mkdir -p "$dest"

    if [ "$?" != 0 ]
    then
        log "failed to make the destination directory '$dest'"
        return;
    fi

    # strip the leading path off the file
    filename=`echo $file | sed 's|.*/||'`

    if [ -z "$filename" ]
    then
        log "failed to strip full path from '$file'"
        return;
    fi

    counter=0
    while [ -e "$file" ] && [ $counter -lt 5 ]
    do
        if [ "$counter" == 0 ]
        then
            destfilename="$filename"
        else
            basefilename=`echo $filename | sed 's|\(.*\)\..*|\1|'`
            fileext=`echo $filename | sed 's|.*\.\(.*\)|\1|'`
            destfilename="${basefilename}_${counter}.${fileext}"

            log "failed to move the file '$file', trying again (new filename: '$destfilename')"
        fi

        if [ -e "$dest/$destfilename" ]
        then
            orighash=`sha1 -q "$file"`
            desthash=`sha1 -q "$dest/$destfilename"`

            if [ "$orighash" == "$desthash" ]
            then
                log "duplicate file '$file' detected at '$dest/$destfilename', deleting '$file'"
                rm "$file"
            fi

        else
            mv -n "$file" "$dest/$destfilename"
        fi
        counter=`expr $counter + 1`
    done

    if [ -e "$file" ]
    then
        log "failed to move the file '$file' after $counter attempts, skipping"
        return
    fi
}

log()
{
    tag="vidsort.sh"

    echo "$1"
    logger -t $tag "$1"
}

usage()
{
    echo "usage: vidsort.sh srcdir destdir"
    echo "srcdir: the source directory containing files to sort"
    echo "destdir: the destination directory to put the sorted files"
}

if [ $# != 2 ]
then
    usage
    exit 1
fi

if [ ! -d "$1" ]
then
    log "could not find srcdir: '$1'"
    exit 1
fi

if [ ! -d "$2" ]
then
    log "could not find destdir: '$2'"
    exit 1
fi

pid=$(pgrep -F $dotpid 2>/dev/null)

if [ ! -z $pid ]
then
    log "$self is already running as pid $pid, exiting"
    exit 0
fi

echo $$ > $dotpid

scan $1 $2

sleep 20

rm $dotpid
exit 0
