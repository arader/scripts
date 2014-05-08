#!/bin/sh

#
# This is a simple script that can watch multiple dirs
# for .torrent files. When torrent files are found they
# will be added to a running transmission instance.
#

watch_dirs="/share/torrents/anime /share/torrents/movies /share/torrents/television"

for dir in $watch_dirs
do
    for torrent in "$dir"/*.torrent
    do
        if [ "$torrent" != "$dir/*.torrent" ]
        then
            echo "found torrent: $torrent"
            output=`/usr/local/bin/transmission-remote --add "$torrent" --download-dir "$dir"`

            if [ $? == 0 ]
            then
                /bin/rm -f "$torrent"
            else
                echo "failed to add torrent: $output"
            fi
        fi
    done
done
