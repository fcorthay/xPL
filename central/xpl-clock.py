#!/usr/bin/python3
import argparse
import sys
import signal
import os
import time
from datetime import datetime
sys.path.append(sys.path[0]+'/../xPL-base')
import common

# ------------------------------------------------------------------------------
# constants
#
VENDOR_ID = 'dspc';             # from xplproject.org
DEVICE_ID = 'clock';            # max 8 chars
CLASS_ID = 'clock';             # max 8 chars

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
                                                  # parse command line arguments
parser_arguments = parser.parse_args()
verbose = parser_arguments.verbose
Ethernet_base_port = parser_arguments.port
instance_id = parser_arguments.id
heartbeat_interval = int(parser_arguments.timer)
startup_delay = int(parser_arguments.wait)

debug = False

# ==============================================================================
# Internal functions
#

#-------------------------------------------------------------------------------
# Check the time and send a clock update message every beginning of a minute
#
def tick(last_time) :
                                                          # get time information
    now = datetime.now()
    time = now.strftime('%Hh%M');
                                                             # check if new time
    if (time == last_time) :
        time = ''

    return(time)

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
    print("Started xPL clock on port %s" % client_port)
    print(INDENT + "class id    : %s" % CLASS_ID)
    print(INDENT + "instance id : %s" % instance_id)
    print()

# ..............................................................................
                                                                  # main loop
timeout = 1;
sleep_for_next_minute = 60 - 10*timeout;
is_first_minute = True;
last_heartbeat_time = 0;
last_message_time = 0;
last_time = ''

while not end :
                                                 # check time and send heartbeat
    last_heartbeat_time = common.xpl_send_heartbeat(
        xpl_socket, xpl_id, xpl_ip, client_port,
        heartbeat_interval, last_heartbeat_time
    )
                                                                  # get new time
    time.sleep(timeout);
    present_time = tick(last_time);
                                                        # send time tick message
    if present_time :
        if verbose :
            if debug :
                print('')
            print("Time is %s" % present_time)
        common.xpl_send_message(
            xpl_socket, common.XPL_PORT,
            'xpl_stat', xpl_id, '*', "%s.tick" % CLASS_ID,
            {
                'time' : present_time
            }
        );
        last_time = present_time
                                                           # leverage CPU effort
        if not is_first_minute :
            time.sleep(sleep_for_next_minute)
            if debug :
                print(INDENT + 'checking for next minute ', end='', flush=True)
        is_first_minute = False
                                                       # print debug information
    else :
        if debug :
            print('.', end='', flush=True)
                                                             # delete xPL socket
common.xpl_disconnect(xpl_socket, xpl_id, xpl_ip, client_port)
