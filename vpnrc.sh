#!/bin/sh

#
# define per-VPN services
#
# The below contains the list of services that should be
# started and stopped per VPN id. You'll need to
#  1) add an entry into the VPN ID => Service Name map
#  2) add "{service_name}_start()" and "{service_name}_stop()" functions
#
# the start function is responsible for actually starting the service.
# note that "{service_name}_stop()" is called prior to calling start
# to make sure any previous instance of the service is no longer running.
#
# start is called with the following arguments:
# $1 - the ID of the VPN
# $2 - the tunnel's local IP
# $3 - the tunnel's public IP
#

# service name map (comma delimited)
vpn_1=""
vpn_2=""
vpn_3="transmission,sabnzbd"

forward_transmission_port()
{
    USER=`cat /usr/local/etc/openvpn/pia-user`
    PASS=`cat /usr/local/etc/openvpn/pia-pass`
    CLIENTID=`cat /usr/local/etc/openvpn/pia-clientid`

    fib=$1
    ip=$2
    port=""

    log "acquiring forwarded port for $ip"

    attempt=1

    while [ -z "$port" ] && [ $attempt -lt 7 ]
    do
        response=`/usr/sbin/setfib $fib /usr/local/bin/curl --insecure -s -S --stderr - -d "user=$USER&pass=$PASS&client_id=$CLIENTID&local_ip=$ip" https://www.privateinternetaccess.com/vpninfo/port_forward_assignment`

        if [ "$?" -eq 0 ]
        then
            port=`echo $response | sed 's/[^0-9]*\([0-9]*\)[^0-9]*/\1/'`
        fi

        if [ -z "$port" ]
        then
            log "failed to acquire forwarded port (response: '$response'), sleeping before retrying (attempt: $attempt)"
            sleep 5
        fi

        attempt=`expr $attempt + 1`
    done

    if [ ! -z "$port" ]
    then
        log "acquired forwarded port $port"
        /usr/sbin/jexec piracy /usr/local/bin/transmission-remote -p $port
    else
        log "failed to acquire forwarded port"
    fi
}

# service start/stop functions
transmission_start()
{
    fib=$1
    ip=$2
    user=pirate
    pidfile=/var/run/transmission/daemon.pid
    conf_dir=/usr/local/etc/transmission/home
    watch_dir=/share/downloads/torrents
    download_dir=/share/downloads/complete
    incomplete_dir=/share/downloads/active
    bind_ip=${ip:-"127.0.0.1"}
    bind_ip6="::1"

    log "starting transmission"
    /usr/sbin/jexec -U $user piracy /usr/sbin/setfib $fib /usr/local/bin/transmission-daemon \
        -x $pidfile \
        -g $conf_dir \
        -i $bind_ip \
        -I $bind_ip6 \
        -c $watch_dir \
        --download-dir $download_dir \
        --incomplete-dir $incomplete_dir

    forward_transmission_port $fib $ip &
}

transmission_stop()
{
    pid=`pgrep -F /usr/jails/piracy/var/run/transmission/daemon.pid 2>/dev/null`

    if [ ! -z "$pid" ]
    then
        log "stopping transmission"
        kill -TERM $pid

        log "waiting on PID $pid"
        pwait $pid
    fi

    rm /usr/jails/piracy/var/run/transmission/daemon.pid 2>/dev/null
}

sabnzbd_start()
{
    fib=$1
    ip=$2
    user=pirate
    python=/usr/local/bin/python2.7
    command=/usr/local/bin/SABnzbd.py
    pidfile=/var/run/sabnzbd/sabnzbd.pid
    conf_dir=/usr/local/sabnzbd

    log "starting sabnzbd"
    /usr/sbin/jexec -U $user piracy /usr/sbin/setfib $fib $python -OO $command --daemon -f $conf_dir/sabnzbd.ini --pidfile $pidfile
}

sabnzbd_stop()
{
    pid=`pgrep -F /usr/jails/piracy/var/run/sabnzbd/sabnzbd.pid 2>/dev/null`

    if [ ! -z "$pid" ]
    then
        log "stopping sabnzbd"
        kill -TERM $pid

        log "waiting on PID $pid"
        pwait $pid
    fi

    rm /usr/jails/piracy/var/run/sabnzbd/sabnzbd.pid 2>/dev/null
}

usage ()
{
    echo "usage: vpnrc.sh vpnid [up|down]"
    echo "vpnrc.sh is meant to be run as a --route-up and --route-pre-down"
    echo "script by OpenVPN. It allows for the following:"
    echo " 1) Each VPN gets its own FIB (thus, it's own routing tables)"
    echo " 2) Each VPN gets its own set of services started (BitTorrent, etc)"
    echo ""
    echo "to use vpnrc.sh, put the following in /etc/rc.conf:"
    echo ""
    echo "openvpn_flags=\"--script-security 2 --route-noexec \\"
    echo "  --route-up \"/path/to/vpnrc.sh 1 up\" \\"
    echo "  --route-pre-down \"/path/to/vpnrc.sh 1 down"
}

onup()
{
    vpn=$1

    if [ -z "$vpn" ]
    then
        log "missing VPN id, exiting"
        return
    fi

    #
    # $ifconfig_local is the client's side of the tunnel
    # $ifconfig_remote is the server's side of the tunnel
    # $trusted_ip is the public ip of the server
    # $route_net_gateway is the original gateway of the network
    #
    
    log "vpn $vpn is coming up"
    log "  local endpoint: $ifconfig_local"
    log "  remote endpoint: $ifconfig_remote"
    log "  server ip: $trusted_ip"
    log "  original gateway: $route_net_gateway"

    if [ ! -z "$ifconfig_remote" ] &&
        [ ! -z "$trusted_ip" ] &&
        [ ! -z "$route_net_gateway" ]
    then
        # set up the routes
        /usr/sbin/setfib $vpn /sbin/route add -net default $ifconfig_remote
        /usr/sbin/setfib $vpn /sbin/route add -net $trusted_ip $route_net_gateway
    fi

    # start the vpn specific services
    services="$(eval echo \${vpn_${vpn}})"
    for service in `echo $services | tr "," "\n"`
    do
        # first call stop in case it is running, then start
        eval "${service}_stop"
        eval "${service}_start $vpn $ifconfig_local $trusted_ip"
    done
}

ondown()
{
    vpn=$1

    if [ -z "$vpn" ]
    then
        log "missing VPN id, exiting"
        return
    fi

    log "vpn $vpn is going down"
    log "  local endpoint: $ifconfig_local"
    log "  remote endpoint: $ifconfig_remote"
    log "  server ip: $trusted_ip"
    log "  original gateway: $route_net_gateway"

    # stop the services
    services="$(eval echo \${vpn_${vpn}})"
    for service in `echo $services | tr "," "\n"`
    do
        eval "${service}_stop"
    done

    if [ ! -z "$trusted_ip" ] && [ ! -z "route_net_gateway" ]
    then
        # delete the route (note that the default route is deleted automatically)
        log "deleting VPN route"
        /usr/sbin/setfib $vpn /sbin/route delete -net $trusted_ip $route_net_gateway
    fi
}

log()
{
    tag="vpnrc.sh"

    echo "$1"
    logger -t $tag "$1"
}

if [ $# -lt 2 ]
then
    usage
    exit
fi

if [ "$2" = "up" ]
then
    onup $1
elif [ "$2" = "down" ]
then
    ondown $1
else
    usage
fi

exit 0
