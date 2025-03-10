#!/usr/bin/python3
import argparse
import sys
import signal
import os
import time
sys.path.append(sys.path[0]+'/../xPL-base')
import common
import math

# ------------------------------------------------------------------------------
# constants
#
VALUES_PER_PIXEL = 4
OFFSET_RED   = 0
OFFSET_GREEN = 1
OFFSET_BLUE  = 2
OFFSET_ALPHA = 3
COMPONENT_MAX = 255

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
                                                          # LED strip IP address
parser.add_argument(
    '-A', '--address', default='192.168.1.71',
    help = 'the LED strip\'s IP address'
)
                                                          # LED strip controller
parser.add_argument(
    '-C', '--ledController', default='Shelly-2',
    help = 'the LED strip\'s IP address'
)
                                                                    # clock hand
parser.add_argument(
    '-H', '--hand', default='hour',
    help = 'the clock hand (\'hour\' or \'minute\')'
)
                                                                  # start colour
parser.add_argument(
    '-s', '--start', default=0,
    help = 'the start colour in degrees'
)
                                                                # turn direction
parser.add_argument(
    '-c', '--clockwise', action='store_true', dest='clockwise',
    help = 'turn clockwise'
)
                                                                # amplitude path
parser.add_argument(
    '-a', '--amplitude', default='hexagon',
    help = 'the amplitude path (hexagon, circle, reuleaux or triangle)'
)
                                                                  # warm colours
parser.add_argument(
    '-W', '--warmColours', action='store_true', dest='warmColours',
    help = 'emphasize warm colours'
)
                                                           # HTTP request server
parser.add_argument(
    '-r', '--request', default='*',
    help = 'name of the xpl-httpRequest service instance'
)
                                                             # xPL Ethernet port
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
LED_strip_ip_address = parser_arguments.address
LED_strip_controller = parser_arguments.ledController
hand_type = parser_arguments.hand
start_colour = int(parser_arguments.start)
turn_clockwise = parser_arguments.clockwise
amplitude_path = parser_arguments.amplitude
emphasize_warm_colors = parser_arguments.warmColours
request_service_name = parser_arguments.request
Ethernet_base_port = parser_arguments.port
instance_id = parser_arguments.id
heartbeat_interval = int(parser_arguments.timer)
startup_delay = int(parser_arguments.wait)
verbose = parser_arguments.verbose

# ==============================================================================
# Internal functions
#
# ------------------------------------------------------------------------------
# find triant of pixel coordinate
#
def pixel_triant(x, y):
    triant = 0
                                                                     # hue angle
    angle = math.atan2(y, x)
                                                                  # first triant
    if (angle >= 0) and (angle < 2/3*math.pi) :
        triant = 1
                                                                  # third triant
    elif (angle >= -2/3*math.pi) and (angle < 0) :
        triant = 3
                                                                 # second triant
    else :
        triant = 2

    return triant

# ------------------------------------------------------------------------------
# find R and G components of a pixel in the first triant
#
def R_G(x, y):
                                                                      # triangle
    red_component = 2*(x + round(y*math.tan(math.pi/6)))
    green_component = 2*round(y/math.cos(math.pi/6))
                                                                    # limitation
#    if red_component < 0 :
#        red_component = 0
#    if green_component < 0 :
#        green_component = 0
    if red_component > COMPONENT_MAX :
        red_component = COMPONENT_MAX
    if green_component > COMPONENT_MAX :
        green_component = COMPONENT_MAX

    return(red_component, green_component)

# ------------------------------------------------------------------------------
# find G and B components of a pixel in the second triant
#
def G_B(x, y):
                                                                    # rotate 60°
    angle = math.atan2(y, x)
    amplitude = math.sqrt(x*x + y*y)
    rotated_angle = angle - 2/3*math.pi
    rotated_x = round(amplitude * math.cos(rotated_angle))
    rotated_y = round(amplitude * math.sin(rotated_angle))
                                               # get component from first triant
    (green_component, blue_component) = R_G(rotated_x, rotated_y)

    return(green_component, blue_component)

# ------------------------------------------------------------------------------
# find R and B components of a pixel in the third triant
#
def R_B(x, y):
                                               # get component from first triant
    (red_component, blue_component) = R_G(x, -y)

    return(red_component, blue_component)

# ------------------------------------------------------------------------------
# find R G B components of a pixel in any triant
#
def R_G_B(x, y):
    red_component   = 0
    green_component = 0
    blue_component  = 0
                                                            # select from triant
    if pixel_triant(x, y) == 1 :
        (red_component, green_component)  = R_G(x, y)
    elif pixel_triant(x, y) == 2 :
        (green_component, blue_component) = G_B(x, y)
    else :
        (red_component, blue_component)   = R_B(x, y)

    return(red_component, green_component, blue_component)

#-------------------------------------------------------------------------------
# pick colour code for a given angle
#
def colour_code(division, division_nb) :
                                                                  # colour angle
    pick_angle = division/division_nb*2*math.pi
#    print("%d/%d %d°" % (division, division_nb, pick_angle/math.pi*180))
    if turn_clockwise :
        pick_angle = 2*math.pi - pick_angle
#    print("%d° after clockwise control" % (pick_angle/math.pi*180))
    if emphasize_warm_colors :
        pick_angle = 2*math.pi*(
            2/3*(pick_angle/(2*math.pi))**2 + 1/3*pick_angle/(2*math.pi)
        )
#    print("%d° after emphasis" % (pick_angle/math.pi*180))
    pick_angle = (pick_angle + start_colour/360*2*math.pi) % (2*math.pi)
#    print("%d° after offset" % (pick_angle/math.pi*180))
                                                              # colour amplitude
    if amplitude_path == 'triangle':
        angle_modulo = pick_angle % (2/3*math.pi) + 2/3*math.pi
        pick_amplitude = -COMPONENT_MAX/2/(2*math.cos(angle_modulo))
    elif amplitude_path == 'reuleaux':
        radius = 1.5*COMPONENT_MAX/2/math.cos(math.pi/6)
        x_center = COMPONENT_MAX/2
        y_center = 0
        angle_triant_2 = (pick_angle % (2*math.pi/3)) + 2*math.pi/3
        pick_amplitude = radius* \
            math.sin(math.pi/2-angle_triant_2/2)/math.sin(angle_triant_2)
        if abs(angle_triant_2 - math.pi) < 1E-6 :
            pick_amplitude = radius - COMPONENT_MAX/2
            pick_amplitude = COMPONENT_MAX/2*math.cos(math.pi/6)  # why ?
    elif amplitude_path == 'circle' :
        pick_amplitude = COMPONENT_MAX/2*math.cos(math.pi/6)
        if pick_angle % (2*math.pi/3) == 0:
            pick_amplitude = COMPONENT_MAX/2*math.cos(math.pi/12)  # why ?
    else :  # hexagon
        angle_modulo = pick_angle % (math.pi/6)
        pick_amplitude = COMPONENT_MAX/2*math.cos(angle_modulo)
                                                  # colour cartesian coordinates
    pick_x = round(pick_amplitude*math.cos(pick_angle))
    pick_y = round(pick_amplitude*math.sin(pick_angle))
#    print("%d %d° (%d, %d)" % \
#        (pick_amplitude, pick_angle/math.pi*180, pick_x, pick_y))
                                                        # colour RGB coordinates
    (red_component, green_component, blue_component) = R_G_B(pick_x, pick_y)

    return(red_component, green_component, blue_component)

#-------------------------------------------------------------------------------
# set LED strip colour
#
def build_LEDs_colour_message(red, green, blue) :
    message_body = {'server' : LED_strip_ip_address}
                                                                    # build path
    if LED_strip_controller == 'Shelly-1':
        message_body['path'] = 'light/0'
        message_body['red'] = "%d" % red
        message_body['green'] = "%d" % green
        message_body['blue'] = "%d" % blue
        message_body['transition'] = '0'
    else :
        message_body['path'] = 'rpc/rgbw.set'
        message_body['id'] = '0'
        message_body['rgb'] = "[%d,%d,%d]" % (red, green, blue)
        message_body['transition_duration'] = '0.5'

    return(message_body)

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
    print(INDENT + "class id              : %s" % CLASS_ID)
    print(INDENT + "instance id           : %s" % instance_id)
    print(INDENT + "LED strip IP address  : %s" % LED_strip_ip_address)
    print(INDENT + "LED strip controller  : %s" % LED_strip_controller)
    print(INDENT + "hand type             : %s" % hand_type)
    print(INDENT + "start colour angle    : %d" % start_colour)
    print(INDENT + "clockwise             : %r" % turn_clockwise)
    print(INDENT + "amplitude path        : %s" % amplitude_path)
    print(INDENT + "emphasize warm colors : %r" % emphasize_warm_colors)
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
if request_service_name != '*' :
    message_target = 'dspc-request.' + request_service_name
message_class = 'request.basic'

division_nb = 24
if hand_type == 'minute' :
    division_nb = 60

import time
division = int(time.strftime("%H"))
if hand_type == 'minute' :
    division = int(time.strftime("%M"))
(red, green, blue) = colour_code(division, division_nb)
if verbose :
    time = time.strftime("%Hh%M")
    print("time is %s" % time)
    print(INDENT + 
        "setting colour to [%3d, %3d, %3d]" % (red, green, blue)
    )
message_body = build_LEDs_colour_message(red, green, blue)
common.xpl_send_message(
    xpl_socket, common.XPL_PORT,
    message_type, message_source, message_target, message_class,
    message_body
);

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
                (hour, minute) = time.split('h')
                division = int(hour)
                if hand_type == 'minute' :
                    division = int(minute)
                (red, green, blue) = colour_code(division, division_nb)
                if verbose :
                    print("time is %s" % time)
                    print(INDENT + 
                        "setting colour to [%3d, %3d, %3d]" % (red, green, blue)
                    )
                message_body = build_LEDs_colour_message(red, green, blue)
                common.xpl_send_message(
                    xpl_socket, common.XPL_PORT,
                    message_type, message_source, message_target, message_class,
                    message_body
                );

                                                             # delete xPL socket
common.xpl_disconnect(xpl_socket, xpl_id, xpl_ip, client_port)
