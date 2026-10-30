#!/usr/bin/python3
import argparse
import sys
import signal
import os
import subprocess
import time
sys.path.append(sys.path[0]+'/../xPL-base')
import common

# ------------------------------------------------------------------------------
# constants
#
VENDOR_ID = 'dspc';             # from xplproject.org
DEVICE_ID = 'volume';           # max 8 chars
CLASS_ID = 'volume';            # max 8 chars

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
                                                  # maximal value for the volume
parser.add_argument(
    '-V', '--maxVolume', default=100,
    help = 'dial positions number'
)
                                              # maximal value for dial positions
parser.add_argument(
    '-d', '--maxDial', default=15,
    help = 'maximal value for dial positions'
)
                                                             # minimal dB volume
parser.add_argument(
    '-m', '--minDB', default=50,
    help = 'minimal dB value'
)
                                                                # amplifier card
parser.add_argument(
    '-c', '--amplifierCard', default='sndrpihifiberry',
    help = 'alsa volume control item'
)
                                                                # volume control
parser.add_argument(
    '-s', '--volumeControl', default='Digital',
    help = 'alsa volume control item'
)
                                                  # parse command line arguments
parser_arguments = parser.parse_args()
verbose = parser_arguments.verbose
Ethernet_base_port = parser_arguments.port
instance_id = parser_arguments.id
heartbeat_interval = int(parser_arguments.timer)
startup_delay = int(parser_arguments.wait)
maximal_volume = int(parser_arguments.maxVolume)
maximal_dial_position = int(parser_arguments.maxDial)
min_db_value = -abs(int(parser_arguments.minDB))
alsa_card = parser_arguments.amplifierCard
alsa_volume_control = parser_arguments.volumeControl

# ==============================================================================
# Internal functions
#

# ..............................................................................
                                                                # volume control
def update_volume(volume, card, volume_control):
                                                                  # apply volume
    volume_info = subprocess.run(
        [
            'amixer',
            '-D',
            "hw:%s" % card,
            'sset',
            "%s" % volume_control,
            "%d%%" % volume
        ],
        capture_output=True, text=True
    )

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
    print("Ready to control RPi audio volume")
    print(INDENT + "class id    : %s" % CLASS_ID)
    print(INDENT + "instance id : %s" % instance_id)
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
        if common.xpl_is_for_me(xpl_id, target) :
            if xpl_type == 'xpl-cmnd' :
                if schema == CLASS_ID + '.basic' :
                                                                   # ALSA volume
                    if 'volume' in body :
                        volume = int(body['volume'])
                        print("setting volume to %d%%" % volume)
                        update_volume(volume, alsa_card, alsa_volume_control)
                                                                 # knob position
                elif schema == 'knob.basic' :
                    position = -1
                    if 'position' in body :
                        position = int(body['position'])
                    maximal_position = maximal_dial_position
                    if 'max' in body :
                        maximal_position = int(body['max'])
                    if position >= 0 :
                        volume_relative = position/maximal_position
                        volume_dB = min_db_value - volume_relative*min_db_value
                        volume_for_amixer = int(100 + volume_dB)
                        if verbose :
                            print("dial position %d" % position)
                            print(
                                INDENT + \
                                "setting volume to %d%%" % volume_for_amixer
                            )
                        update_volume(
                            volume_for_amixer, alsa_card, alsa_volume_control
                        )
                                                             # delete xPL socket
common.xpl_disconnect(xpl_socket, xpl_id, xpl_ip, client_port)
