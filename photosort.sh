#!/bin/sh

#
# this is a small utility script that will use EXIF
# data to sort photos based on the date they were
# created. the script is designed to be either run
# manually or as part of cron
#

EXIF=/usr/local/bin/exif
FIND=/usr/bin/find
MKDIR=/bin/mkdir

scan()
{
    src=$1
    root=$2

    files=`$FIND $src -iname "*.jpg" -or -iname "*.png"`

    $FIND $src -iname "*.jpg" -or -iname "*.png" | while read file
    do
        dt=`$EXIF --tag 0x132 -m "$file"`

        if [ "$?" != 0 ] || [ -z "$dt" ]
        then
            log "failed to read date from $file, defaulting to 'today'"
            parent=`date -j +%Y/%m.%B`
        else
            parent=`date -j -f "%Y:%m:%d %H:%M:%S" "$dt" +%Y/%m.%B`
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

scan $1 $2

exit 0
