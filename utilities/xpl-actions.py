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

LOG_FILE_LENGTH = 100

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
                                                             # scripts directory
parser.add_argument(
    '-d', '--directory',
    default=os.path.dirname(os.path.realpath(__file__))+os.sep+'actions',
    help = 'the directory containing the action scripts'
)
                                                             # scripts directory
parser.add_argument(
    '-l', '--logFile', default='/tmp/xpl-actions.log',
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
log_file_spec = parser_arguments.logFile

debug = False

# ==============================================================================
# Internal functions
#

#-------------------------------------------------------------------------------
# Execute a command together with its arguments
#
def execute_command(command, body) :
                                                # get arguments from xPL message
    arguments = '';
    for key in body :
        if key != 'command' :
            if len(key) == 1 :
                arguments = arguments + " -%s %s" %(key, body[key])
            else :
                arguments = arguments + " --%s %s" %(key, body[key])
                                                             # check for command
    action = os.sep.join([actions_directory, command])
    if os.path.isfile(action) :
        full_command = command + arguments
        full_action = action + arguments
        if verbose :
            print(INDENT + "Received command: \"%s\"\n" % full_command);
                                                         # limit log file length
        if os.path.isfile(log_file_spec) :
            log_file_lines = open(log_file_spec, "r").read().split("\n")
            log_file_lines.extend(['', "%s :" % full_command, '', ''])
            open(log_file_spec, "w").write(
                "\n".join(log_file_lines[-LOG_FILE_LENGTH:])
            )
                                                               # execute command
        os.system(full_action + ' >> ' + log_file_spec)

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
                                                           # process XPL message
    if (xpl_message) :
        (xpl_type, source, target, schema, body) = \
            common.xpl_get_message_elements(xpl_message)
        if schema == CLASS_ID + '.basic' :
            if xpl_type == 'xpl-cmnd' :
                if common.xpl_is_for_me(xpl_id, target) :
                    if verbose :
                        print("Received command from %s" % source)
                    command = body['command'];
                    if command :
                        execute_command(command, body)
                                                             # delete xPL socket
common.xpl_disconnect(xpl_socket, xpl_id, xpl_ip, client_port)
