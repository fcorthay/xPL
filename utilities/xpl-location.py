#! /usr/bin/env python3

import os
import sys
import argparse
import math
import datetime
import json
import http.server
from http.server import BaseHTTPRequestHandler, HTTPServer
from http import HTTPStatus
sys.path.append(sys.path[0]+'/../xPL-base')
import common

# ------------------------------------------------------------------------------
# constants
#
VENDOR_ID = 'dspc';             # from xplproject.org
DEVICE_ID = 'location';         # max 8 chars
CLASS_ID = 'location';          # max 8 chars

LOG_FILE_LENGTH = 60*24*3

INDENT = '  '
SEPARATOR = 80 * '-'

# ------------------------------------------------------------------------------
# command line arguments
#
parser = argparse.ArgumentParser()
                                                            # HTTP listener port
parser.add_argument(
    '-p', '--httpPort', default=8003,
    help = 'the HTTP server port'
)
                                                                 # log directory
parser.add_argument(
    '-l', '--logDir',
    default=os.sep.join([
        os.path.dirname(os.path.realpath(__file__)), 'locations'
    ]),
    help = 'the directory logs'
)
                                                           # reference longitude
parser.add_argument(
    '-x', '--longitude', default=0,
    help='the reference longitude (x-coordinate)'
)
                                                            # reference latitude
parser.add_argument(
    '-y', '--latitude', default=0,
    help='the reference latitude (y-coordinate)'
)
                                                            # reference altitude
parser.add_argument(
    '-z', '--altitude', default=0,
    help='the reference altitude (z-coordinate)'
)
                                                                     # distances
parser.add_argument(
    '-d', '--distances', default='200, 500',
    help='distances to draw [m])'
)
                                                                  # figure_width
parser.add_argument(
    '-w', '--width', default=12,
    help='plot width [in]'
)
                                                                 # xPL base port
parser.add_argument(
    '-X', '--xplPort', default=50000,
    help = 'the clients base UDP port'
)
                                                                   # instance id
parser.add_argument(
    '-N', '--id', default=common.xpl_build_automatic_instance_id(),
    help = 'the instance id (max. 16 chars)'
)
                                                               # heartbeat timer
parser.add_argument(
    '-t', '--timer', default=5,
    help = 'the heartbeat interval in minutes'
)
                                                                  # message type
parser.add_argument(
    '-T', '--type', default='xpl-trig',
    help = 'xPL message type (cmnd, stat or trig)'
)
                                                                # message source
parser.add_argument(
    '-S', '--source', default="%s-%s.%s"%(
        VENDOR_ID, DEVICE_ID, common.xpl_build_automatic_instance_id()
    ),
    help = 'xPL message source (vendor_id-device_id.instance_id)'
)
                                                                # message target
parser.add_argument(
    '-D', '--destination', default='*',
    help = 'xPL message destination (vendor_id-device_id.instance_id)'
)
                                                                     # verbosity
parser.add_argument(
    '-v', '--verbose', action='store_true', dest='verbose',
    help = 'verbose console output'
)
                                      # transform string list argument to vector
def argument_string_to_float_vector(parameter):
    vector = []
    for value in parameter.split(',') :
        vector.append(float(value))

    return(vector)
                                                  # parse command line arguments
parser_arguments = parser.parse_args()
http_server_port = int(parser_arguments.httpPort)
log_directory = parser_arguments.logDir
reference_longitude = float(parser_arguments.longitude)
reference_latitude = float(parser_arguments.latitude)
reference_altitude = float(parser_arguments.altitude)
radiuses = argument_string_to_float_vector(parser_arguments.distances)
figure_width = float(parser_arguments.width)
xPL_base_port = int(parser_arguments.xplPort)
instance_id = parser_arguments.id
heartbeat_interval = int(parser_arguments.timer)
message_type = parser_arguments.type
message_source = parser_arguments.source
message_target = parser_arguments.destination
verbose = parser_arguments.verbose

debug = False

sys.path.append(log_directory)
import buildMap

# ==============================================================================
# Internal functions
#

#-------------------------------------------------------------------------------
# send xPL trigger
#
def send_xPL_trigger(device, distance_state) :
                                                             # create xPL socket
    (client_port, xpl_socket) = common.xpl_open_socket(
        common.XPL_PORT, xPL_base_port
    )
                                                                  # send message
    message_type = 'xpl-trig'
    message_class = CLASS_ID + '.basic'
    body_dict = {'device' : device, 'distance' : distance_state}
    common.xpl_send_message(
        xpl_socket, common.XPL_PORT,
        message_type, message_source, message_target, message_class,
        body_dict
    );
                                                              # close xPL socket
    xpl_socket.close();

# ------------------------------------------------------------------------------
# get device name
#
def device_name(path) :
    name = ''
    path_elements = path.split('/')
    if len(path_elements) > 1 :
        name = path_elements[1]

    return(name)

# ------------------------------------------------------------------------------
# check if request is from Sensor Logger
#
def is_sensor_logger_info(path) :
    is_sensor_logger = False
    path_elements = path.split('/')
    if path_elements[-1] == 'sensorLogger' :
        is_sensor_logger = True

    return(is_sensor_logger)

# ------------------------------------------------------------------------------
# check if request is from GPSLogger
#
def is_gps_logger_info(path) :
    is_gps_logger = False
    path_elements = path.split('/')
    if path_elements[-1] == 'gpsLogger' :
        is_gps_logger = True

    return(is_gps_logger)

# ------------------------------------------------------------------------------
# get GPSLogger coordinates
#
def GPS_logger_info(parameters) :
    time      = 0
    latitude  = 0
    longitude = 0
    altitude  = 0
    speed     = 0
                                                               # get coordinates
    parameter_list = parameters.split('&')
    for parameter_data in parameter_list :
        (parameter, value) = parameter_data.split('=')
        if parameter == 'time' :
            (date, time) = value.split('T')
            time = date + ' ' + time[:8]
        if parameter == 'latitude' :
            latitude = float(value)
        if parameter == 'longitude' :
            longitude = float(value)
        if parameter == 'altitude' :
            altitude = float(value)
        if parameter == 'speed' :
            speed = float(value)

    return(time, latitude, longitude, altitude, speed)

# ------------------------------------------------------------------------------
# get Sensor Logger coordinates
#
def sensor_logger_info(data_dictionary) :
    time      = 0
    latitude  = 0
    longitude = 0
    altitude  = 0
    speed     = 0
                                                               # get coordinates
    for sensor_data in data_dictionary['payload'] :
        if 'name' in sensor_data :
            if sensor_data['name'] == 'location' :
                timestamp  = sensor_data['time']
                time_dt = datetime.datetime.fromtimestamp(timestamp // 1E9)
                time = time_dt.strftime('%Y-%m-%d %H:%M:%S')
                latitude  = sensor_data['values']['latitude']
                longitude = sensor_data['values']['longitude']
                altitude  = sensor_data['values']['altitude']
                speed     = sensor_data['values']['speed']

    return(time, latitude, longitude, altitude, speed)

#-------------------------------------------------------------------------------
# calculate distance from reference point
#
def device_distance(longitude, latitude) :
    EARTH_DIAMETER = 40075*1E3
    reference_diameter = EARTH_DIAMETER*math.cos(reference_latitude/360*math.pi)
    x_distance = (longitude - reference_longitude)*reference_diameter/360
    y_distance = (latitude - reference_latitude)*EARTH_DIAMETER/360
    distance = math.sqrt(x_distance**2 + y_distance**2)

    return(distance)


#-------------------------------------------------------------------------------
# check distance state
#
def check_distance_state(device, longitude, latitude) :
                                                            # calculate distance
    global device_distance_state
    distance = device_distance(longitude, latitude)
                                                                # find new state
    distance_state = 'far'
    if distance < radiuses[0] :
        distance_state = 'near'
    elif distance < radiuses[-1] :
        distance_state = 'middle'
                                                              # check if trigger
    if device in device_distance_state.keys() :
        if distance_state == 'near'                     \
            and device_distance_state[device] != 'near' \
        :
            if verbose :
                print('Sending trigger for near location')
            send_xPL_trigger(device, distance_state)
        if distance_state == 'far'                     \
            and device_distance_state[device] != 'far' \
        :
            if verbose :
                print('Sending trigger for far location')
            send_xPL_trigger(device, distance_state)
    device_distance_state[device] = distance_state

#-------------------------------------------------------------------------------
# log GPS info to file
#
def log_GPS_info(device, parameters) :
                                                               # build file spec
    log_file_spec = os.sep.join([log_directory, device + '.log'])
                                                                     # read file
    log_file_lines = []
    if os.path.isfile(log_file_spec) :
        log_file_lines = open(log_file_spec, "r").read().split("\n")
                                                                      # add info
    log_line = ''
    for (parameter, value) in parameters.items() :
        log_line = "%s, %s : %s" % (log_line, parameter, value)
    log_line = log_line[2:]
    log_file_lines.append(log_line)
                                                                    # write file
    open(log_file_spec, "w").write(
        "\n".join(log_file_lines[-LOG_FILE_LENGTH:])
    )

#-------------------------------------------------------------------------------
# create map
#
def create_map(log_file_spec) :
                                                                     # read file
    buildMap.create_plot(
        log_file_spec,
        reference_longitude, reference_latitude, reference_altitude,
        radiuses, figure_width
    )

# ------------------------------------------------------------------------------
# HTTP methods
#
class http_server(BaseHTTPRequestHandler):
                                                                           # GET
    def do_GET(self):
        client = self.client_address[0]
        path = self.path
        if debug :
            print(client + ' : GET ' + path)
        path_elements = path.split('/')
        device = path_elements[1]
                                                                      # show map
        not_found = True
        if len(path_elements) == 2 :
            log_file_spec = os.sep.join([log_directory, device + '.log'])
            if os.path.exists(log_file_spec) :
                create_map(log_file_spec)
                image_file_spec = os.sep.join([log_directory, device + '.png'])
                if os.path.exists(image_file_spec) :
                    self.send_image(image_file_spec)
                    not_found = False
        if not_found :
            self.send_reply(code=HTTPStatus.NOT_FOUND)
                                                                          # POST
    def do_POST(self):
        client = self.client_address[0]
        path = self.path
        parameters = ''
        if '?' in path :
            (path, parameters) = path.split('?')
        if debug :
            print(client + ' : POST ' + path + ' ' + parameters)
        time = ''
                                              # receive point from Sensor Logger
        if is_sensor_logger_info(path) :
            name = device_name(path)
            data = self.rfile.read(int(self.headers['Content-Length']))
            data_dictionary = json.loads(data.decode(encoding='ascii'))
            (time, latitude, longitude, altitude, speed) = sensor_logger_info(
                data_dictionary
            )
                                                  # receive point from GPSLogger
        elif is_gps_logger_info(path) :
            name = device_name(path)
            (time, latitude, longitude, altitude, speed) = GPS_logger_info(
                parameters
            )
        else :
            self.send_reply(code=HTTPStatus.NOT_FOUND)
                                                                     # add point
        if time :
            if verbose :
                print("received coordinate from GPSLogger for %s" %name)
                print(INDENT + "time     : %s" % time)
                print(INDENT + "longitude: %g" % longitude)
                print(INDENT + "latitude : %g" % latitude)
                print(INDENT + "altitude : %g" % altitude)
                print(INDENT + "speed    : %g" % speed)
            parameters = {
                'time' : time,
                'latitude' : latitude,
                'longitude' : longitude,
                'altitude' : altitude,
                'speed' : speed
            }
            log_GPS_info(name, parameters)
            check_distance_state(name, longitude, latitude)
            self.send_reply(code=HTTPStatus.OK)
                                                                           # PUT
    def do_PUT(self):
        client = self.client_address[0]
        path = self.path
        if debug :
            print(client + ' : PUT ' + path)
                                                        # update reference point
        if path == '/reference' :
            data = self.rfile.read(int(self.headers['Content-Length']))
            data_dictionary = json.loads(data.decode(encoding='ascii'))
            for item in data_dictionary :
                if item == 'longitude' :
                    global reference_longitude
                    reference_longitude = float(data_dictionary[item])
                    if verbose :
                        print(
                            INDENT +
                            "new reference longitude : %g" % reference_longitude
                        )
                if item == 'latitude' :
                    global reference_latitude
                    reference_latitude = float(data_dictionary[item])
                    if verbose :
                        print(
                            INDENT +
                            "new reference latitude : %g" % reference_latitude
                        )
                if item == 'altitude' :
                    global reference_altitude
                    reference_altitude = float(data_dictionary[item])
                    if verbose :
                        print(
                            INDENT +
                            "new reference altitude : %g" % reference_altitude
                        )
            self.send_reply(code=HTTPStatus.OK)
        else :
            self.send_reply(code=HTTPStatus.NOT_FOUND)
                                                                         # PATCH
    def do_PATCH(self):
        client = self.client_address[0]
        path = self.path
        if debug :
            print(client + ' : PATCH ' + path)
        self.send_reply()
                                                                        # DELETE
    def do_DELETE(self):
        client = self.client_address[0]
        path = self.path
        if debug :
            print(client + ':  DELETE ' + path)
        if verbose :
            print("received deletion command for %s" % path)
        path_elements = path.split('/')
        device = path_elements[1]
                                                             # clear a recording
        not_found = True
        if len(path_elements) == 2 :
            log_file_spec = os.sep.join([log_directory, device + '.log'])
            if os.path.exists(log_file_spec) :
                os.remove(log_file_spec)
                not_found = False
        if not_found :
            self.send_reply(code=HTTPStatus.NOT_FOUND)
        else :
            self.send_reply(code=HTTPStatus.OK)
                                                                 # HTML response
    def send_reply(self, HTML='', code=HTTPStatus.OK):
        if code == HTTPStatus.OK :
            self.send_response(code)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML.encode("ascii"))
        else :
            self.send_error(code, explain="Path was \"%s\"" % self.path)
                                                           # HTML page for image
    def send_image(self, image_file_spec, image_type='png'):
        image_size = os.stat(image_file_spec).st_size
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-type', "image/%s" % image_type)
        self.send_header('Content-length', image_size)
        self.end_headers()
        image_file = open(image_file_spec, 'rb')
        self.wfile.write(image_file.read())
        image_file.close()
                                                           # silent terminal log
    def log_message(self, format, *args):
        return

# ==============================================================================
# Main script
#
if verbose :
    os.system('clear||cls')
    print(SEPARATOR)
    print("Started listening for GPS data on port %s" % http_server_port)
    print(INDENT + "Logging to %s" % log_directory)
    print(INDENT + "Reference longitude : %9.6f" % reference_longitude)
    print(INDENT + "Reference latitude  : %9.6f" % reference_latitude)
    print(INDENT + "Reference altitude  : %g" % reference_altitude)
device_distance_state = {}
                                                                    # run server
server = HTTPServer(('', http_server_port), http_server)
try:
    server.serve_forever()
except KeyboardInterrupt:
    server.server_close()
