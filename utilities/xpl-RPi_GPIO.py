#!/usr/bin/python3
import argparse
import sys
import signal
import os
import time
sys.path.append(sys.path[0]+'/../xPL-base')
import common
import RPi.GPIO as GPIO

# ------------------------------------------------------------------------------
# constants
#
VENDOR_ID = 'dspc';             # from xplproject.org
DEVICE_ID = 'gpio';             # max 8 chars
CLASS_ID = 'gpio';              # max 8 chars

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

# find pin and GPIO list with the CLI command "pinctrl -p"
GPIO_start = 2
GPIO_end = 27
reserved_pins = [2, 3, 7, 8]

# ==============================================================================
# Internal functions
#

# ------------------------------------------------------------------------------
# set GPIO as output
#
def set_as_output(GPIO_id):
    if GPIO_id in input_GPIOs :
        input_GPIOs.remove(GPIO_id)
    if GPIO_id not in output_GPIOs :
        output_GPIOs.append(GPIO_id)
    GPIO.setup(GPIO_id, GPIO.OUT)

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
    print("Ready to control RPi GPIO")
    print(INDENT + "class id    : %s" % CLASS_ID)
    print(INDENT + "instance id : %s" % instance_id)
    print()

# ..............................................................................
                                                                     # main loop
timeout = 1;
last_heartbeat_time = 0;
last_message_time = 0;
message_source = "%s-%s.%s" % (VENDOR_ID, DEVICE_ID, instance_id)
message_target = '*'
message_class = "%s.basic" % CLASS_ID
                                                                # pin directions
GPIO.setmode(GPIO.BCM)
input_GPIOs = []
GPIO_input_previous_values = {}
GPIO_input_toggle_values = {}
for GPIO_id in range(GPIO_start, GPIO_end+1) :
    if GPIO_id not in reserved_pins :
        input_GPIOs.append(GPIO_id)
        GPIO.setup(GPIO_id, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO_input_previous_values[GPIO_id] = GPIO.input(GPIO_id)
        GPIO_input_toggle_values[GPIO_id] = 0
output_GPIOs = []

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
                                                                       # outputs
                    output_id = 0
                    if 'led' in body :
                        output_id = int(body['led'])
                    if 'output' in body :
                        output_id = int(body['output'])
                                                                # output control
                    if 'set' in body :
                        output_state = body['set']
                        if verbose :
                            print(
                                "setting LED %d %s" %
                                (output_id, output_state)
                            )
                        set_as_output(output_id)
                        if output_state == 'on' :
                            GPIO.output(output_id, GPIO.HIGH)
                        else :
                            GPIO.output(output_id, GPIO.LOW)
                                                                  # output state
                    else :
                        GPIO_value = GPIO.input(output_id)
                        if GPIO_value == 0 :
                            GPIO_value = 'off'
                        else :
                            GPIO_value = 'on'
                        if verbose :
                            print("LED %d is %s" % (output_id, GPIO_value))
                        common.xpl_send_message(
                            xpl_socket, common.XPL_PORT,
                            'xpl-stat', message_source,
                            message_target, message_class,
                            {'led': output_id, 'value': GPIO_value}
                        );
                                                                        # inputs
    GPIO_input_values = {}
    for GPIO_id in input_GPIOs :
                                                                    # poll state
        GPIO_value = GPIO.input(GPIO_id)
        GPIO_input_values[GPIO_id] = GPIO_value
        if GPIO_id not in GPIO_input_previous_values :
            print("New input: %d" % GPIO_id)
        else :
                                                                # detect changes
            if GPIO_value != GPIO_input_previous_values[GPIO_id] :
                GPIO_input_previous_values[GPIO_id] = GPIO_value
                if verbose :
                    print(
                        "input %d has changed to %d" % (GPIO_id, GPIO_value)
                    )
                                                           # update toggle value
                toggle_value = GPIO_input_toggle_values[GPIO_id]
                if GPIO_value == 1 :
                    toggle_value = (toggle_value + 1) % 2
                    GPIO_input_toggle_values[GPIO_id] = toggle_value
                                                              # send xPL message
                common.xpl_send_message(
                    xpl_socket, common.XPL_PORT,
                    'xpl-trig', message_source,
                    message_target, message_class,
                    {
                        'switch': GPIO_id, 'value': GPIO_value,
                        'toggle': toggle_value
                    }
                )
                                                             # delete xPL socket
common.xpl_disconnect(xpl_socket, xpl_id, xpl_ip, client_port)
