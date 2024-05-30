#!/usr/bin/python3
import argparse
import sys
import signal
import os
import time
sys.path.append(sys.path[0]+'/../xPL-base')
import common

# ------------------------------------------------------------------------------
# constants
#
VENDOR_ID = 'dspc';             # from xplproject.org
DEVICE_ID = 'actions';          # max 8 chars
CLASS_ID = 'actions';           # max 8 chars

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
                                                                 # startup delay
parser.add_argument(
    '-w', '--wait', default=0,
    help = 'the startup sleep interval in seconds'
)
                                                                 # startup delay
parser.add_argument(
    '-d', '--directory',
    default=os.path.dirname(os.path.realpath(__file__))+os.sep+'actions',
    help = 'the directory containing the action scripts'
)
                                                  # parse command line arguments
parser_arguments = parser.parse_args()
verbose = parser_arguments.verbose
Ethernet_base_port = parser_arguments.port
instance_id = parser_arguments.id
heartbeat_interval = int(parser_arguments.timer)
startup_delay = int(parser_arguments.wait)
actions_directory = parser_arguments.directory

debug = False

# ==============================================================================
# Internal functions
#

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
                                                                 # startup delay
time.sleep(startup_delay);
                                                                # xPL parameters
xpl_id = common.xpl_build_id(VENDOR_ID, DEVICE_ID, instance_id);
xpl_ip = common.xpl_find_ip()
                                                             # create xPL socket
(client_port, xpl_socket) = common.xpl_open_socket(
    common.XPL_PORT, Ethernet_base_port
)
                                                    # display working parameters
if verbose :
    os.system('clear||cls')
    print(SEPARATOR)
    print("Ready to launch commands based on xPL messages")
    print(INDENT + "class id    : %s" % CLASS_ID)
    print(INDENT + "instance id : %s" % instance_id)
    print(INDENT + "actions directory: \"%s\"\n" % actions_directory);
    print()

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
                                                           # display XPL message
    if (xpl_message) :
        print(SEPARATOR)
        print(xpl_message.rstrip("\n"))
                                                             # delete xPL socket
common.xpl_disconnect(xpl_socket, xpl_id, xpl_ip, client_port)
