#!/usr/bin/python3
import argparse
import sys
import netifaces
import socket
import signal
import os
import time
from datetime import datetime
from xPL import common

# ------------------------------------------------------------------------------
# constants
#
INDENT = '  '
SEPARATOR = 80 * '-'

# ------------------------------------------------------------------------------
# command line arguments
#
parser = argparse.ArgumentParser()
                                                                     # verbosity
parser.add_argument(
    '-v', '--verbose', action='store_true', dest='verbose',
    help = 'verbose console output'
)
                                                              # Ethernet timeout
parser.add_argument(
    '-t', '--timeout', default=1000,
    help = 'the UDP input timeout in milliseconds'
)
                                                                 # startup delay
parser.add_argument(
    '-w', '--wait', default=0,
    help = 'the startup sleep interval in seconds'
)
                                                                      # log file
parser.add_argument(
    '-l', '--log', default='/dev/null',
    help = 'the log file'
)
                                                  # parse command line arguments
parser_arguments = parser.parse_args()
verbose = parser_arguments.verbose
Ethernet_timeout = int(parser_arguments.timeout)/1000
startup_delay = int(parser_arguments.wait)
log_file_spec = parser_arguments.log

debug = False

# ==============================================================================
# functions
#
#-------------------------------------------------------------------------------
# get the list of the local IP addresses
#
def get_local_IPs() :
    ip_addresses = []
                                                                # IPv4 addresses
    for interface in netifaces.interfaces() :
        for link in netifaces.ifaddresses(interface)[netifaces.AF_INET] :
            ip_addresses.append(link['addr'])
                                                                # IPv6 addresses
    for interface in netifaces.interfaces() :
        for link in netifaces.ifaddresses(interface)[netifaces.AF_INET6] :
            ip_addresses.append(link['addr'])

    return ip_addresses;

#-------------------------------------------------------------------------------
# Check if an IP address belongs to the local addresses list
#
def message_is_local(ip_address, local_addresses) :

    is_local = False;
    for ip in local_addresses :
        if ip == ip_address :
            is_local = True

    return is_local;

#-------------------------------------------------------------------------------
# Broadcast an xPL message to a local client on the port he is listening to
#
def broadcast_message (port, message) :
                                                                   # open socket
    xpl_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    xpl_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                                                                  # send message
    try :
        xpl_socket.sendto(message.encode(), ('<broadcast>', port))
    except :
        print('Error sending xPL message to port %d.' % port)
                                                                  # close socket
    xpl_socket.close()

#-------------------------------------------------------------------------------
# Log client info
#
def log_client_list(log_file_spec, clients) :

    log_file = open(log_file_spec, 'w')
    log_file.write("Ports and associated xPL clients:\n")
    for port in clients.keys() :
        log_file.write(INDENT + "%d: %s\n" % (port, clients[port]))
    log_file.close();

# ------------------------------------------------------------------------------
# catch ctrl-C interrupt
#
end = False

def ctrl_C_handler(sig, frame):
    global end
    end = True
    print('')

signal.signal(signal.SIGINT, ctrl_C_handler)

# ==============================================================================
# main script
#
if verbose :
    os.system('clear||cls')
    print(SEPARATOR)
    print('Starting xPL hub');
    print(INDENT + 'log file : ' + log_file_spec);
    print('');
                                                                 # startup delay
time.sleep(startup_delay)
                                                 # start xPL UDP listener socket
xpl_socket = socket.socket(
    socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
)
# xpl_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
xpl_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
xpl_socket.bind(('', common.XPL_PORT))
                                                    # Get all local IP addresses
local_addresses = get_local_IPs()
if debug :
    print(local_addresses)

# ..............................................................................
                                                                     # main loop
clients = {}
timeouts = {}

while not end :
                                             # get message and source IP address
    (message, source_address) = common.xpl_get_message(
        xpl_socket, Ethernet_timeout
    )
    time_string = datetime.now().strftime("%H:%M:%S")
    if debug :
        print(time_string)
    if message :
        (source_address, source_port) = source_address
        if debug :
            print("received from: %s" % source_address)
            print(message)
                                             # check for local heartbeat message
        if (message_is_local(source_address, local_addresses)) :
            (xpl_type, source, target, schema, body) = \
                common.xpl_get_message_elements(message)
            if debug :
                print('type   : ' + xpl_type)
                print('source : ' + source)
                print('target : ' + target)
                print('schema : ' + schema)
                print('body   :')
                for parameter in body.keys() :
                    print(INDENT + parameter + '=' + body[parameter])
                                                    # process heartbeat messages
            if (xpl_type == 'xpl-stat') and (schema == 'hbeat.app') :
                                                                 # restart timer
                timer_interval = 5
                if 'interval' in body.keys() :
                    timer_interval = int(body['interval'])
                timeouts[source_port] = \
                    timer_interval * 1/Ethernet_timeout * 60 * 1.25;
                                                            # add client to list
                if source_port in clients.keys() :
                    if verbose :
                        print(
                            "Updated %s, port %d in client list"
                            % (clients[source_port], source_port)
                        )
                else :
                    clients[source_port] = source
                    if verbose :
                        print(
                            "Added %s, port %d in client list"
                            % (source, source_port)
                        )
                    log_client_list(log_file_spec, clients)
                                                       # remove client from list
            if (xpl_type == 'xpl-stat') and (schema == 'hbeat.end') :
                if source_port in clients.keys() :
                    del clients[source_port]
                    del timeouts[source_port]
                    log_client_list(log_file_spec, clients)
                    if verbose :
                        print(
                            "Removed %s, port %d from client list"
                            % (source, source_port)
                        )
                                         # broadcast xPL messages to client list
        for port in clients.keys() :
            broadcast_message(port, message)
                                                              # decrement timers
    else :
        to_delete = []
        for port in clients.keys() :
            if debug :
                print("%d : %d" % (port, timeouts[port]))
            timeouts[port] = timeouts[port] - 1
            if timeouts[port] <= 0 :
                to_delete.append(port)
                                                      # remove client on timeout
        for port in to_delete :
            if verbose :
                print(
                    "Removed %s, port %d, from client list"
                    % (clients[port], port)
                )
            del clients[port]
            del timeouts[port]
            log_client_list(log_file_spec, clients)

xpl_socket.close()
