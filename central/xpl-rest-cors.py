#!/usr/bin/python3
import os
import time
import argparse
import logging
from logging.handlers import RotatingFileHandler
from http import HTTPStatus
from http.server import HTTPServer, SimpleHTTPRequestHandler
import sys
sys.path.append(sys.path[0]+'/../xPL-base')
import common

# ------------------------------------------------------------------------------
# constants
#
VENDOR_ID = 'dspc';             # from xplproject.org
DEVICE_ID = 'rest';             # max 8 chars
CLASS_ID = 'rest';              # max 8 chars

INDENT = '  '
SEPARATOR = 80 * '-'

# ------------------------------------------------------------------------------
# command line arguments
#
parser = argparse.ArgumentParser()
                                                              # HTTP server port
parser.add_argument(
    '-p', '--httpPort', default=8002,
    help = 'the HTTP server port'
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
                                                                      # log file
parser.add_argument(
    '-l', '--logFile', default='/tmp/xpl-rest.log',
    help = 'log file'
)
                                                                     # verbosity
parser.add_argument(
    '-v', '--verbose', action='store_true', dest='verbose',
    help = 'verbose console output'
)
                                                  # parse command line arguments
parser_arguments = parser.parse_args()
http_server_port = int(parser_arguments.httpPort)
xPL_base_port = int(parser_arguments.xplPort)
instance_id = parser_arguments.id
heartbeat_interval = int(parser_arguments.timer)
message_type = parser_arguments.type
message_source = parser_arguments.source
message_target = parser_arguments.destination
log_file_spec = parser_arguments.logFile
verbose = parser_arguments.verbose

# ==============================================================================
# Internal functions
#

# ------------------------------------------------------------------------------
# check if home status request
#
def is_home_status_request(path) :
    is_home_status = False
    path_elements = path.split('/')
    if len(path_elements) == 5 :
        if path_elements[1] == 'home' :
            is_home_status = True

    return(is_home_status)

# ------------------------------------------------------------------------------
# check if home control request
#
def is_home_control_request(path) :
    is_home_control = False
    path_elements = path.split('/')
    if len(path_elements) == 6 :
        if path_elements[1] == 'home' :
            is_home_control = True

    return(is_home_control)

# ------------------------------------------------------------------------------
# get status request
#
def get_status_request(path) :
    path_elements = path.split('/')
    room = path_elements[2]
    kind = path_elements[3]
    obj = path_elements[4]

    return(room, kind, obj)

# ------------------------------------------------------------------------------
# get control action
#
def get_control_action(path) :
    path_elements = path.split('/')
    room = path_elements[2]
    kind = path_elements[3]
    obj = path_elements[4]
    value = path_elements[5]

    return(room, kind, obj, value)

# ------------------------------------------------------------------------------
# check if button request
#
def is_button_request(path) :
    is_button = False
    path_elements = path.split('/')
    if len(path_elements) == 5 :
        if path_elements[2] == 'button' :
            is_button = True

    return(is_button)

# ------------------------------------------------------------------------------
# send home control xPl message
#
def send_control_xPL_message(query, room, kind, obj, value='') :
                                   # send heartbeat to receive messages from hub
    last_heartbeat_time = 0;
    last_heartbeat_time = common.xpl_send_heartbeat(
        xpl_socket, xpl_id, xpl_ip, client_port,
        heartbeat_interval, last_heartbeat_time
    )
                                                          # clear message buffer
    buffer_empty = False
    while not buffer_empty:
        (message, source) = common.xpl_get_message(xpl_socket, 0.1)
        if message == '' :
            buffer_empty = True
                                                # send message to ask for status
    state_message_type = 'xpl-cmnd'
    message_body = {}
    message_body['command'] = query
    message_body['room']    = room
    message_body['kind']    = kind
    message_body['object']  = obj
    if query == 'set' :
        message_body['value']   = value
    common.xpl_send_message(
        xpl_socket, common.XPL_PORT,
        state_message_type, message_source, message_target, 'state.basic',
        message_body
    );

# ------------------------------------------------------------------------------
# get home control xPl status
#
def get_xPL_status_message() :
                                                           # read message buffer
    message = 'hello'
    while message != '' :
        (message, source) = common.xpl_get_message(xpl_socket, 1)
        if message :
            (
                xpl_type, source, target, schema, body_dict
            ) = common.xpl_get_message_elements(message)
            if (xpl_type == 'xpl-stat') and (schema == 'state.basic') :
                if 'value' in body_dict :
                    value = body_dict['value']
                else :
                    value = 'unknown'

    return(value)

# ------------------------------------------------------------------------------
# get button action
#
def get_button_action(path) :
    button_brand = ''
    button_id = ''
    button_action = ''
    path_elements = path.split('/')
    button_brand = path_elements[1]
    button_id = path_elements[3]
    button_action = path_elements[4]

    return(button_brand, button_id, button_action)

# ------------------------------------------------------------------------------
# send button xPl message
#
def send_button_xPL_message(button_brand, button_id, button_action) :
    message_body = {}
    message_body['hardware'] = button_brand
    message_body['id'] = button_id.replace(':', '').upper()
    message_body['action'] = button_action

    common.xpl_send_message(
        xpl_socket, common.XPL_PORT,
        message_type, message_source, message_target, 'button.basic',
        message_body
    );

# ------------------------------------------------------------------------------
# build HTML reply
#
def build_HTML_reply(path, info) :
    reply = "<html>\n"
    reply += INDENT + "<title>\n"
    reply += 2*INDENT + "HTML request service\n"
    reply += INDENT + "</title>\n"
    reply += INDENT + "<body>\n"
    reply += 2*INDENT + "<p>\n"
    reply += 3*INDENT + 'Request was: <code>' + path + "</code>\n"
    reply += 2*INDENT + "</p>\n"
    if info :
        reply += 2*INDENT + "<p>\n"
        reply += 3*INDENT + info + "\n"
        reply += 2*INDENT + "</p>\n"
    reply += INDENT + "</body>\n"
    reply += "</html>\n"

    return(reply)

# ------------------------------------------------------------------------------
# HTTP methods
#
class http_server(SimpleHTTPRequestHandler):
                                                                           # GET
    def do_GET(self):
        client = self.client_address[0]
        path = self.path
        logging.info(client + ' GET ' + path)
        if is_button_request(path) :
            (button_brand, button_id, button_action) = get_button_action(path)
            info = "On <code>%s</code> " % button_brand
            info += "button <code>%s</code>, " % button_id
            info += "action was <code>%s</code>" % button_action
            self.send_reply(info=info, code=HTTPStatus.OK)
            send_button_xPL_message(button_brand, button_id, button_action)
        elif is_home_status_request(path) :
            (room, kind, obj) = get_status_request(path)
            send_control_xPL_message('ask', room, kind, obj)
            value = get_xPL_status_message()
            info = "As to the %s %s, " % (room, kind)
            info += "the value of \"%s\" is \"%s\"" % (obj, value)
            self.send_reply(info=info, code=HTTPStatus.OK)
        elif is_home_control_request(path) :
            (room, kind, obj, value) = get_control_action(path)
            info = "For the %s %s, " % (room, kind)
            info += "setting \"%s\" to \"%s\"" % (obj, value)
            self.send_reply(info=info, code=HTTPStatus.OK)
            send_control_xPL_message('set', room, kind, obj, value)
        else :
            self.send_reply(code=HTTPStatus.NOT_FOUND)
                                                                          # POST
    def do_POST(self):
        client = self.client_address[0]
        path = self.path
        logging.info(client + ' POST ' + path)
        if is_button_request(path) :
            (button_brand, button_id, button_action) = get_button_action(path)
            if button_id :
                self.send_reply(code=HTTPStatus.OK)
                send_button_xPL_message(button_brand, button_id, button_action)
            else :
                self.send_reply(code=HTTPStatus.BAD_REQUEST)
        else :
            self.send_reply(code=HTTPStatus.NOT_FOUND)
                                                                           # PUT
    def do_PUT(self):
        client = self.client_address[0]
        path = self.path
        logging.info(client + ' PUT ' + path)
        if is_button_request(path) :
            (button_brand, button_id, button_action) = get_button_action(path)
            if button_id :
                self.send_reply(code=HTTPStatus.OK)
                send_button_xPL_message(button_brand, button_id, button_action)
            else :
                self.send_reply(code=HTTPStatus.BAD_REQUEST)
        elif is_home_control_request(path) :
            (room, kind, obj, value) = get_control_action(path)
            info = "For the %s %s, " % (room, kind)
            info += "setting \"%s\" to \"%s\"" % (obj, value)
            self.send_reply(info=info, code=HTTPStatus.OK)
            send_control_xPL_message('set', room, kind, obj, value)
        else :
            self.send_reply(code=HTTPStatus.NOT_FOUND)
                                                                         # PATCH
    def do_PATCH(self):
        client = self.client_address[0]
        path = self.path
        logging.info(client + ' PATCH ' + path)
        print('patch:/' + path)
        self.send_reply()
                                                                        # DELETE
    def do_DELETE(self):
        client = self.client_address[0]
        path = self.path
        logging.info(client + ' DELETE ' + path)
        print('delete:/' + path)
        self.send_reply()
                                                                 # HTML response
    def send_reply(self, info='', code=HTTPStatus.OK):
        path = self.path
        if code == HTTPStatus.OK :
            self.send_response(code)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(build_HTML_reply(path, info).encode("ascii"))
        else :
            self.send_error(code, explain="Path was \"%s\"" % path)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', '*')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        return super(http_server, self).end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

# ==============================================================================
# main script
#
                                                                 # setup logging
try:
    os.remove(log_file_spec)
except OSError:
    pass
logging.basicConfig(
    handlers = [
        RotatingFileHandler(
            log_file_spec,
            maxBytes = 100*80,
            backupCount = 1
        )
    ],
    level = logging.INFO,
    format = '%(asctime)s %(levelname)s %(message)s',
    datefmt = '%Y-%m-%d %H:%M:%S'
)
                                                             # create xPL socket
xpl_id = common.xpl_build_id(VENDOR_ID, DEVICE_ID, instance_id);
xpl_ip = common.xpl_find_ip()
(client_port, xpl_socket) = common.xpl_open_socket(
    common.XPL_PORT, xPL_base_port
)
if verbose :
    os.system('clear||cls')
    print(SEPARATOR)
    print(INDENT + "Started UDP socket on port %s" % client_port)
                                                             # start HTML server
server = HTTPServer(('', http_server_port), http_server)
logging.info('Starting xPL REST server')
try:
    server.serve_forever()
except KeyboardInterrupt:
    server.server_close()
