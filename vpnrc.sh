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

# uncomment the below to enable "debug" mode. when enabled you can run
# the script and it will only start/stop your services
#DEBUG="YES"

# service name map (comma delimited)
vpn_1="transmission"
#vpn_2="example1,example2"

# service start/stop functions
transmission_start()
{
    pidfile=/var/run/transmission/daemon.pid
    conf_dir=/usr/local/etc/transmission/home
    watch_dir=/tank/torrents
    download_dir=/tank/torrents
    incomplete_dir=/tank/torrents/active
    bind_ip=${2:-"127.0.0.1"}

    log "starting transmission"
    /usr/sbin/setfib $1 /usr/local/bin/transmission-daemon \
        -x $pidfile \
        -g $conf_dir \
        -i $bind_ip \
        -c $watch_dir \
        --download-dir $download_dir \
        --incomplete-dir $incomplete_dir
}

transmission_stop()
{
    pid=`pgrep -F /var/run/transmission/daemon.pid 2>/dev/null`

    if [ ! -z "$pid" ]
    then
        log "stopping transmission"
        kill -TERM $pid

        log "waiting on PID $pid"
        pwait $pid
    fi

    rm /var/run/transmission/daemon.pid 2>/dev/null
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
    log "vpn $vpn is coming up"

    if [ -z "$DEBUG" ]
    then
        if [ -z "$vpn" ] ||
            [ -z "$ifconfig_local" ] ||
            [ -z "$ifconfig_remote" ] ||
            [ -z "$trusted_ip" ] ||
            [ -z "$route_net_gateway" ]
        then
            log "missing VPN parameters, exiting"
            return
        fi
    
        #
        # $ifconfig_local is the client's side of the tunnel
        # $ifconfig_remote is the server's side of the tunnel
        # $trusted_ip is the public ip of the server
        # $route_net_gateway is the original gateway of the network
        #
        
        log "  local endpoint: $ifconfig_local"
        log "  remote endpoint: $ifconfig_remote"
        log "  server ip: $trusted_ip"
        log "  original gateway: $route_net_gateway"
    
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
    log "vpn $vpn is going down"

    if [ -z "$DEBUG" ]
    then
        if [ -z "$vpn" ] ||
            [ -z "$ifconfig_local" ] ||
            [ -z "$ifconfig_remote" ] ||
            [ -z "$trusted_ip" ] ||
            [ -z "$route_net_gateway" ]
        then
            log "missing VPN parameters, exiting"
            return
        fi
    
        log "  local endpoint: $ifconfig_local"
        log "  remote endpoint: $ifconfig_remote"
        log "  server ip: $trusted_ip"
        log "  original gateway: $route_net_gateway"
    fi

    # stop the services
    services="$(eval echo \${vpn_${vpn}})"
    for service in `echo $services | tr "," "\n"`
    do
        eval "${service}_stop"
    done

    if [ -z "$DEBUG" ]
    then
        # delete the route (note that the default route is deleted automatically)
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
