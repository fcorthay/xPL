#!/usr/bin/python3
import argparse
import sys
import signal
import os
import time
sys.path.append(sys.path[0]+'/../xPL-base')
import common
import smbus

# ------------------------------------------------------------------------------
# constants
#
VENDOR_ID = 'dspc';             # from xplproject.org
DEVICE_ID = 'i2c';              # max 8 chars
CLASS_ID = 'i2c';               # max 8 chars

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

i2c_bus = smbus.SMBus(1)

# ==============================================================================
# Internal functions
#

# ------------------------------------------------------------------------------
# transform string to integer, possibly hex
#
def to_integer(string_value):
    integer_value = 0
    if string_value.isnumeric():
        integer_value = int(string_value)
    elif string_value.upper().startswith('0X') :
        integer_value = int(string_value, 0)
    elif string_value.upper().endswith('H') :
        integer_value = int(string_value[:-1], 16)
    return integer_value

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
    print("Ready to control RPi I2C")
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
                                                                    # parameters
                    read = True
                    chip_address = 0
                    register_address = 0
                    register_data = 0
                    if 'command' in body :
                        if body['command'].lower() == 'set' :
                            read = False
                        if body['command'].lower() == 'write' :
                            read = False
                    if 'chip' in body :
                        chip_address = to_integer(body['chip'])
                    if 'register' in body :
                        register_address = to_integer(body['register'])
                    if 'data' in body :
                        register_data = to_integer(body['data'])
                                                                      # read I2C
                    if read :
                        if verbose :
                            print(
                                "reading data from chip %02Xh, register %02Xh" %
                                (chip_address, register_address)
                            )
                        register_data = i2c_bus.read_byte_data(
                            chip_address, register_address
                        )
                        if verbose :
                            print(INDENT + "%02Xh" % register_data)
                        common.xpl_send_message(
                            xpl_socket, common.XPL_PORT,
                            'xpl-stat', message_source,
                            message_target, message_class,
                            {
                                'chip'    : chip_address,
                                'register': register_address,
                                'data'    : register_data
                            }
                        );
                                                                     # write I2C
                    else :
                        if verbose :
                            print(
                                "writing %02Xh to chip %02Xh, register %02Xh" %
                                (register_data, chip_address, register_address)
                            )
                        i2c_bus.write_byte_data(
                            chip_address, register_address, register_data
                        )
                                                            # end I2C bus access
i2c_bus.close()
                                                             # delete xPL socket
common.xpl_disconnect(xpl_socket, xpl_id, xpl_ip, client_port)
