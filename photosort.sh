#!/bin/sh

#
# this is a small utility script that will use EXIF
# data to sort photos based on the date they were
# created. the script is designed to be either run
# manually or as part of cron
#

# Make sure PATH includes the path to 'exif'
PATH=/bin:/usr/bin:/sbin:/usr/local/bin

depends="find mkdir mv rm date sha1 exif realpath basename dirname xargs"

self="$(basename $0)"
dotpid="/var/run/$self.pid"

scan()
{
    src=$1
    root=$2

    find $src -iname "*.jpg" -or -iname "*.png" | while read file
    do
        parent=$(exif --no-fixup --tag 0x132 -m "$file" 2>/dev/null | xargs -I {} date -j -f "%Y:%m:%d %H:%M:%S" "{}" "+%Y/%m.%B")

        if [ -z "$parent" ]
        then
            log "failed to read EXIF date from $file, falling back to modified time"
            parent=$(stat -f %m "$file" 2>/dev/null | xargs -I {} date -j -f "%s" "{}" "+%Y/%m.%B")
        fi

        if [ -z "$parent" ]
        then
            log "failed to read modified time of $file, defaulting to 'today'"
            parent=$(date -j +%Y/%m.%B)
        fi

        dest="$root/$parent"

        move "$file" "$dest"
    done
}

move()
{
    file=$1
    dest=$2

    realfile=$(realpath "$file" | xargs -I {} dirname "{}")
    realdest=$(realpath "$dest" 2>/dev/null)

    if [ "$realfile" == "$realdest" ]
    then
        log "file source '$file' is same as destination, skipping"
        return;
    fi

    mkdir -p "$dest"

    if [ "$?" != 0 ]
    then
        log "failed to make the destination directory '$dest'"
        return;
    fi

    # strip the leading path off the file
    filename=$(basename "$file")

    if [ -z "$filename" ]
    then
        log "failed to strip full path from '$file'"
        return;
    fi

    counter=0
    skip=0
    while [ -e "$file" ] && [ $counter -lt 5 ] && [ $skip == 0 ]
    do
        if [ "$counter" == 0 ]
        then
            destfilename="$filename"
        else
            basefilename=$(echo $filename | sed 's|\(.*\)\..*|\1|')
            fileext=$(echo $filename | sed 's|.*\.\(.*\)|\1|')
            destfilename="${basefilename}_${counter}.${fileext}"

            log "failed to move the file '$file', trying again (new filename: '$destfilename')"
        fi

        if [ -e "$dest/$destfilename" ]
        then
            orighash=$(sha1 -q "$file")

            if [ "$?" != 0 ]
            then
                skip=1
                continue
            fi

            desthash=$(sha1 -q "$dest/$destfilename")

            if [ "$?" != 0 ]
            then
                skip=1
                continue
            fi

            if [ "$orighash" == "$desthash" ]
            then
                log "duplicate file '$file' detected at '$dest/$destfilename', deleting '$file' ('$orighash' == '$desthash')"
                rm "$file"
            fi

        else
            mv -n "$file" "$dest/$destfilename"
        fi
        counter=$(expr $counter + 1)
    done

    if [ -e "$file" ]
    then
        if [ $skip == 1 ]
        then
            log "file '$file' exists at '$dest/$destfilename', but could not calculate hash, skipping"
        else
            log "failed to move the file '$file' after $counter attempts, skipping"
        fi
    fi
}

verify_env()
{
    # this function will verify that we have the necessary
    # utilities to run correctly

    for dep in $depends
    do
        $(which $dep > /dev/null 2>&1)

        if [ $? != 0 ]
        then
            log "missing required dependency '$dep'"
            return 2
        fi
    done

    return 0
}

log()
{
    tag="photosort.sh"

    echo "$1"
    logger -t $tag "$1"
}

usage()
{
    echo "usage: photosort.sh srcdir destdir"
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

verify_env

if [ "$?" == 0 ]
then
    scan $1 $2
    ec=0
else
    ec=1
fi

rm $dotpid > /dev/null 2>&1
exit $ec
