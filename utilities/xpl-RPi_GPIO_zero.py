#!/usr/bin/python3
import argparse
import sys
import signal
import os
import time
sys.path.append(sys.path[0]+'/../xPL-base')
import common
import gpiozero

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
                                                                # output pin ids
parser.add_argument(
    '-o', '--outputs', default='',
    help = 'the GPIO pins driven as outputs'
)
                                                  # parse command line arguments
parser_arguments = parser.parse_args()
verbose = parser_arguments.verbose
Ethernet_base_port = parser_arguments.port
instance_id = parser_arguments.id
heartbeat_interval = int(parser_arguments.timer)
startup_delay = int(parser_arguments.wait)
input_output_pins = range(2, 28)
output_pins = []
for pin in parser_arguments.outputs.split(',') :
    output_pins.append(int(pin))
input_pins = []
for index in input_output_pins :
    if index not in output_pins :
        input_pins.append(index)

# find pin list with the CLI command "pinout"

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
    print("Ready to control RPi GPIO")
    print(INDENT + "class id    : %s" % CLASS_ID)
    print(INDENT + "instance id : %s" % instance_id)
    print()
                                                        # build buttons and LEDs
gp_inputs = []
gp_outputs = []
for index in input_pins :
    gp_inputs.append(gpiozero.Button(index))
for index in output_pins :
    gp_outputs.append(gpiozero.LED(index))

# ..............................................................................
                                                                     # main loop
timeout = 1;
last_heartbeat_time = 0;
last_message_time = 0;
message_source = "%s-%s.%s" % (VENDOR_ID, DEVICE_ID, instance_id)
message_target = '*'
message_class = "%s.basic" % CLASS_ID

gp_input_values = []
for index in range(len(gp_inputs)) :
    gp_input_values.append(gp_inputs[index].value)
gp_input_previous_values = gp_input_values.copy()
gp_intput_toggles = []
for index in range(len(gp_inputs)) :
    gp_intput_toggles.append(0)

while not end :
                                                 # check time and send heartbeat
    last_heartbeat_time = common.xpl_send_heartbeat(
        xpl_socket, xpl_id, xpl_ip, client_port,
        heartbeat_interval, last_heartbeat_time
    )
                                              # get xpl-UDP message with timeout
    (xpl_message, source_address) = common.xpl_get_message(xpl_socket, timeout);
    # for index in range(len(gp_outputs)) :
        # print("%d -> %d" % (index, gp_outputs[index].pin.number))
        # gp_outputs[index].toggle()
                                                           # process XPL message
    if (xpl_message) :
        (xpl_type, source, target, schema, body) = \
            common.xpl_get_message_elements(xpl_message)
        if schema == CLASS_ID + '.basic' :
            if xpl_type == 'xpl-cmnd' :
                if common.xpl_is_for_me(xpl_id, target) :
                                                                          # LEDs
                    if 'led' in body :
                        LED_id = int(body['led'])
                        if LED_id not in output_pins :
                            if verbose :
                                print(
                                    "Pin %d not in the output pin list"
                                    % LED_id
                                )
                        else :
                            output_id = output_pins.index(LED_id)
                                                                   # LED control
                            if 'set' in body :
                                set_command = body['set']
                                if verbose :
                                    print(
                                        "setting LED %d %s" %
                                        (LED_id, set_command)
                                    )
                                if set_command == 'on' :
                                    gp_outputs[output_id].on()
                                else :
                                    gp_outputs[output_id].off()
                                                                    # LED status
                            else :
                                LED_value = gp_outputs[output_id].value
                                if LED_value == 1 :
                                    LED_value = 'on'
                                else :
                                    LED_value = 'off'
                                if verbose :
                                    print("LED %d is %s" % (LED_id, LED_value))
                                common.xpl_send_message(
                                    xpl_socket, common.XPL_PORT,
                                    'xpl-stat', message_source,
                                    message_target, message_class,
                                    {'led': LED_id, 'value': LED_value}
                                );
                                                                       # buttons
    for index in range(len(gp_inputs)) :
        switch_value = (gp_inputs[index].value)
        gp_input_values[index] = switch_value
        if switch_value != gp_input_previous_values[index] :
            switch_index = input_pins[index]
            toggle_value = gp_intput_toggles[index]
            if switch_value == 1 :
                toggle_value = (toggle_value + 1) % 2
            gp_intput_toggles[index] = toggle_value
            if verbose :
                print(
                    "input %d has changed to %d" % (switch_index, switch_value)
                )
            common.xpl_send_message(
                xpl_socket, common.XPL_PORT,
                'xpl-trig', message_source,
                message_target, message_class,
                {
                    'switch': switch_index, 'value': switch_value,
                    'toggle': toggle_value
                }
            )
    gp_input_previous_values = gp_input_values.copy()
                                                             # delete xPL socket
common.xpl_disconnect(xpl_socket, xpl_id, xpl_ip, client_port)
