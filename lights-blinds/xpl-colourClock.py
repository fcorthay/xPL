#!/usr/bin/python3
import argparse
import sys
import signal
import os
import time
sys.path.append(sys.path[0]+'/../xPL-base')
import common
import math
import colorsys

# ------------------------------------------------------------------------------
# constants
#
VENDOR_ID = 'dspc';             # from xplproject.org
DEVICE_ID = 'light';            # max 8 chars
CLASS_ID = 'light';             # max 8 chars

LOG_FILE_LENGTH = 100

INDENT = '  '
SEPARATOR = 80 * '-'

# ------------------------------------------------------------------------------
# command line arguments
#
parser = argparse.ArgumentParser()
                                                                     # LED strip
parser.add_argument(
    '-l', '--led', default='192.168.1.70',
    help = 'the LED strip\'s IP address'
)
                                                                    # clock hand
parser.add_argument(
    '-H', '--hand', default='hour',
    help = 'the clock hand (\'hour\' or \'minute\')'
)
                                                                   # start color
parser.add_argument(
    '-s', '--start', default=315,
    help = 'the start color in degrees'
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
                                                                     # verbosity
parser.add_argument(
    '-v', '--verbose', action='store_true', dest='verbose',
    help = 'verbose console output'
)
                                                  # parse command line arguments
parser_arguments = parser.parse_args()
led_strip_ip_address = parser_arguments.led
hand_type = parser_arguments.hand
start_color = int(parser_arguments.start)
Ethernet_base_port = parser_arguments.port
instance_id = parser_arguments.id
heartbeat_interval = int(parser_arguments.timer)
startup_delay = int(parser_arguments.wait)
verbose = parser_arguments.verbose

# ==============================================================================
# Internal functions
#

#-------------------------------------------------------------------------------
# Execute a command together with its arguments
#
def color_code(time) :
    hue = 1
    saturation = 1
    value = 1
                                                                  # select count
    count = time[:time.index('h')]
    max_count = 24
    if hand_type == 'minute' :
        max_count = 60
        count = time[time.index('h')+1:]
                                                                      # find hue
    hue = (start_color/360-float(count)/max_count) % 1
                                                                    # HSV to RGB
    (red, green, blue) = colorsys.hsv_to_rgb(hue, saturation, value)
    red   = round(255*red)
    green = round(255*green)
    blue  = round(255*blue)

    return(red, green, blue)

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
    print("Listening to the clock")
    print(INDENT + "class id    : %s" % CLASS_ID)
    print(INDENT + "instance id : %s" % instance_id)
    print()

# ..............................................................................
                                                                     # main loop
timeout = 1;
last_heartbeat_time = 0;
last_message_time = 0;

message_type = 'xpl-cmnd'
message_source = "%s-%s.%s"%(
    VENDOR_ID, DEVICE_ID, common.xpl_build_automatic_instance_id()
)
message_target = '*'
message_class = 'request.basic'

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
        if schema == 'clock.tick' :
            time = body['time']
            if (hand_type == 'minute') or (time.endswith('h00')) :
                (red, green, blue) = color_code(time)
                if verbose :
                    print("time is %s" % time)
                    print(INDENT + "setting color to [%d, %d, %d]" % (red, green, blue))
                    message_body = {
                        'server' : led_strip_ip_address,
                        'path'   : 'light/0',
                        'red'    : "%d" % red,
                        'green'  : "%d" % green,
                        'blue'   : "%d" % blue
                    }
                    common.xpl_send_message(
                        xpl_socket, common.XPL_PORT,
                        message_type, message_source, message_target, message_class,
                        message_body
                    );

                                                             # delete xPL socket
common.xpl_disconnect(xpl_socket, xpl_id, xpl_ip, client_port)
