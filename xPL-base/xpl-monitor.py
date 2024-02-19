#!/usr/bin/python3
import argparse
import sys
import signal
import os
import time
import common

# ------------------------------------------------------------------------------
# constants
#
VENDOR_ID = 'dspc';             # from xplproject.org
DEVICE_ID = 'monitor';          # max 8 chars
CLASS_ID = 'monitor';           # max 8 chars

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
                                                                 # Ethernet port
parser.add_argument(
    '-p', '--port', default=50000,
    help = 'the clients base UDP port'
)
                                                                   # instance id
parser.add_argument(
    '-n', '--id', default=common.xpl_build_automatic_instance_id(),
    help = 'the instance id (max. 16 chars)'
)
                                                               # heartbeat timer
parser.add_argument(
    '-t', '--timer', default=5,
    help = 'the heartbeat interval in minutes'
)
                                                              # heartbeat filter
parser.add_argument(
    '-f', '--filter', action='store_true', dest='filter',
    help = 'filter \"hbeat.app\" messages'
)
                                                                 # display delay
parser.add_argument(
    '-d', '--delay', action='store_true', dest='delay',
    help = 'display delay between messages'
)
                                                  # parse command line arguments
parser_arguments = parser.parse_args()
verbose = parser_arguments.verbose
Ethernet_base_port = parser_arguments.port
instance_id = parser_arguments.id
heartbeat_interval = int(parser_arguments.timer)
filter_heartbeats = parser_arguments.filter
display_delay = parser_arguments.delay

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
    print("\nStarting xPL monitor");
xpl_id = common.xpl_build_id(VENDOR_ID, DEVICE_ID, instance_id);
xpl_ip = common.xpl_find_ip()
                                                             # create xPL socket
(client_port, xpl_socket) = common.xpl_open_socket(
    common.XPL_PORT, Ethernet_base_port
)
if verbose :
    os.system('clear||cls')
    print(SEPARATOR)
    print(INDENT + "Started UDP socket on port %s" % client_port)

# ..............................................................................
                                                                     # main loop
timeout = 1;
last_heartbeat_time = 0;
last_message_time = 0;

while not end :
                                                 # check time and send heartbeat
    last_heartbeat_time = common.xpl_send_heartbeat(
        xpl_socket, xpl_id, xpl_ip, client_port,
        heartbeat_interval, last_heartbeat_time
    )
                                              # get xpl-UDP message with timeout
    (xpl_message, source_address) = common.xpl_get_message(xpl_socket, timeout);
                                                      # filter XPL hbeat message
    if filter_heartbeats :
        if xpl_message.find("}\nhbeat.app\n{") >= 0 :
            xpl_message = ''
                                                           # display XPL message
    if (xpl_message) :
        print(SEPARATOR)
        if display_delay :
            now = time.time()
            delta = "%.3f" % (now - last_message_time)
            last_message_time = now
            print("Delta: %s second(s)" % delta)
        print(xpl_message.rstrip("\n"))
                                                             # delete xPL socket
common.xpl_disconnect(xpl_socket, xpl_id, xpl_ip, client_port)
