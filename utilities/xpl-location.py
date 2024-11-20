#! /usr/bin/env python3

import os
import sys
import argparse
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
    '-l', '--logDir', default=os.path.dirname(os.path.realpath(__file__)),
    help = 'the directory logs'
)
                                                                 # xPL base port
parser.add_argument(
    '-x', '--xplPort', default=50000,
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
                                                                  # message type
parser.add_argument(
    '-y', '--type', default='xpl-trig',
    help = 'xPL message type (cmnd, stat or trig)'
)
                                                                # message source
parser.add_argument(
    '-s', '--source', default="%s-%s.%s"%(
        VENDOR_ID, DEVICE_ID, common.xpl_build_automatic_instance_id()
    ),
    help = 'xPL message source (vendor_id-device_id.instance_id)'
)
                                                                # message target
parser.add_argument(
    '-d', '--destination', default='*',
    help = 'xPL message destination (vendor_id-device_id.instance_id)'
)
                                                                     # verbosity
parser.add_argument(
    '-v', '--verbose', action='store_true', dest='verbose',
    help = 'verbose console output'
)
                                                  # parse command line arguments
parser_arguments = parser.parse_args()
http_server_port = int(parser_arguments.httpPort)
log_directory = parser_arguments.logDir
xPL_base_port = int(parser_arguments.xplPort)
instance_id = parser_arguments.id
heartbeat_interval = int(parser_arguments.timer)
message_type = parser_arguments.type
message_source = parser_arguments.source
message_target = parser_arguments.destination
verbose = parser_arguments.verbose

# ==============================================================================
# Internal functions
#

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
                print(time)
                latitude  = sensor_data['values']['latitude']
                longitude = sensor_data['values']['longitude']
                altitude  = sensor_data['values']['altitude']
                speed     = sensor_data['values']['speed']

    return(time, latitude, longitude, altitude, speed)

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
    log_file_lines.append(' '.join(parameters))
                                                                    # write file
    open(log_file_spec, "w").write(
        "\n".join(log_file_lines[-LOG_FILE_LENGTH:])
    )


#-------------------------------------------------------------------------------
# String to byte array
#
def to_bytes(string) :
    return(bytes(string, "utf-8"))

#-------------------------------------------------------------------------------
# HTTP GET service
#
class MyServer(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
                                                               # analyse request
        (path, params) = self.path.split('?')
        if path[0] == '/' :
            path = path[1:]
        parameters = params.split('&')
        print(path)
        print(parameters)
                                                                      # log info
        log_GPS_info(path, parameters)
                                                                 # send response
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(to_bytes(
            "<html><head><title>GPS tracking service</title></head>"
        ))
        self.wfile.write(to_bytes("<body>"))
        self.wfile.write(to_bytes("<p>from %s:" % path))
        for parameter in parameters :
            self.wfile.write(to_bytes("<ul>%s</ul>" % parameter))
        self.wfile.write(to_bytes("</p>"))
        self.wfile.write(to_bytes("</body></html>"))

    def do_POST(self):
                                                               # analyse request
        path = self.path
        print(path)
        data_string = self.rfile.read(int(self.headers['Content-Length']))
        print(data_string)

# ------------------------------------------------------------------------------
# HTTP methods
#
class http_server(BaseHTTPRequestHandler):
                                                                           # GET
    def do_GET(self):
        client = self.client_address[0]
        path = self.path
        print(client + ' : GET ' + path)
                                                                          # POST
    def do_POST(self):
        client = self.client_address[0]
        path = self.path
        print(client + ' : POST ' + path)
        if is_sensor_logger_info(path) :
            name = device_name(path)
            data = self.rfile.read(int(self.headers['Content-Length']))
            data_dictionary = json.loads(data.decode(encoding='ascii'))
            (time, latitude, longitude, altitude, speed) = sensor_logger_info(
                data_dictionary
            )
            if verbose :
                print("received coordinate from Sensor Logger for %s" %name)
                print(INDENT + "time     : %s" % time)
                print(INDENT + "latitude : %g" % latitude)
                print(INDENT + "longitude: %g" % longitude)
                print(INDENT + "altitude : %g" % altitude)
                print(INDENT + "speed    : %g" % speed)
            log_GPS_info(name, [
                "time : %s," % time,
                "latitude : %g," % latitude,
                "longitude : %g," % longitude,
                "altitude : %g," % altitude,
                "speed : %g" % speed
            ])
        else :
            self.send_reply(code=HTTPStatus.NOT_FOUND)
                                                                           # PUT
    def do_PUT(self):
        client = self.client_address[0]
        path = self.path
        print(client + ' : PUT ' + path)
        self.send_reply()
                                                                         # PATCH
    def do_PATCH(self):
        client = self.client_address[0]
        path = self.path
        print(client + ' : PATCH ' + path)
        print('patch:/' + path)
        self.send_reply()
                                                                        # DELETE
    def do_DELETE(self):
        client = self.client_address[0]
        path = self.path
        print(client + ':  DELETE ' + path)
        print('delete:/' + path)
        self.send_reply()
                                                                 # HTML response
    def send_reply(self, info='', code=HTTPStatus.OK):
        path = self.path
        if code == HTTPStatus.OK :
            self.send_response(code)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
 #           self.wfile.write(build_HTML_reply(path, info).encode("ascii"))
        else :
            self.send_error(code, explain="Path was \"%s\"" % path)


# ==============================================================================
# Main script
#
if verbose :
    os.system('clear||cls')
    print(SEPARATOR)
    print(
        INDENT + "Started listening for GPS data on port %s" % http_server_port
    )
                                                                    # run server
server = HTTPServer(('', http_server_port), http_server)
try:
    server.serve_forever()
except KeyboardInterrupt:
    server.server_close()
