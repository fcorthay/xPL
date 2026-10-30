#!/usr/bin/python3
import argparse
import sys
import signal
import os
import time
sys.path.append(sys.path[0]+'/../xPL-base')
import common
import serial

# ------------------------------------------------------------------------------
# constants
#
VENDOR_ID = 'dspc';             # from xplproject.org
DEVICE_ID = 'knob';             # max 8 chars
CLASS_ID = 'knob';            # max 8 chars

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
                                                                 # TTY interface
parser.add_argument(
    '-y', '--tty', default='/dev/ttyACM1',
    help = 'the serial port receiving commands'
)
                                              # maximal value for dial positions
parser.add_argument(
    '-m', '--maxDial', default=15,
    help = 'maximal value for dial positions'
)
                                                       # target for xPL messages
parser.add_argument(
    '-d', '--destination', default="dspc-volume.%s" % os.uname()[1],
    help = 'the serial port receiving commands'
)
                                                  # parse command line arguments
parser_arguments = parser.parse_args()
verbose = parser_arguments.verbose
Ethernet_base_port = parser_arguments.port
instance_id = parser_arguments.id
heartbeat_interval = int(parser_arguments.timer)
startup_delay = int(parser_arguments.wait)
serial_port = parser_arguments.tty
maximal_dial_position = int(parser_arguments.maxDial)
message_target = parser_arguments.destination

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
    print("Ready to read volume knob")
    print(INDENT + "class id    : %s" % CLASS_ID)
    print(INDENT + "instance id : %s" % instance_id)
    print(INDENT + "serial port : %s" % serial_port)
    print(INDENT + "target      : %s" % message_target)
    print()

# ..............................................................................
                                                                     # main loop
timeout = 1;
message_source = "%s-%s.%s" % (VENDOR_ID, DEVICE_ID, instance_id)
message_class = '%s.basic' % CLASS_ID
knob_serial = serial.Serial(serial_port, timeout=0.001)

while not end :
    tty_message = knob_serial.readline().decode().rstrip()
    if tty_message :
        (command, value) = tty_message.lower().split(' ')
        print("%s %s" % (command, value))
        common.xpl_send_message(
            xpl_socket, common.XPL_PORT,
            'xpl-trig', message_source,
            message_target, message_class,
            {
                command : value,
                'max'   : str(maximal_dial_position)
            }
        )
                                                             # delete xPL socket
common.xpl_disconnect(xpl_socket, xpl_id, xpl_ip, client_port)
