#!/usr/bin/python3
import os
import argparse
import logging
from logging.handlers import RotatingFileHandler
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
import sys
sys.path.append(sys.path[0]+'/../xPL-base')
import common

# ------------------------------------------------------------------------------
# constants
#
VENDOR_ID = 'dspc';             # from xplproject.org
DEVICE_ID = 'button';           # max 8 chars
CLASS_ID = 'button';            # max 8 chars

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
                                                                  # message type
parser.add_argument(
    '-t', '--type', default='xpl-trig',
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
                                                                 # message class
parser.add_argument(
    '-c', '--m_class', default=CLASS_ID+'.basic',
    help = 'xPL message class (class_id.type_id)'
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
message_type = parser_arguments.type
message_source = parser_arguments.source
message_target = parser_arguments.destination
message_class = parser_arguments.m_class
log_file_spec = parser_arguments.logFile
verbose = parser_arguments.verbose

# ==============================================================================
# Internal functions
#

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
# send xPl message
#
def send_xPl_message(button_brand, button_id, button_action) :
    message_body = {}
    message_body['hardware'] = button_brand
    message_body['id'] = button_id.replace(':', '').upper()
    message_body['action'] = button_action

    common.xpl_send_message(
        xpl_socket, common.XPL_PORT,
        message_type, message_source, message_target, message_class,
        message_body
    );

# ------------------------------------------------------------------------------
# HTTP methods
#
class http_server(BaseHTTPRequestHandler):
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
            send_xPl_message(button_brand, button_id, button_action)
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
                send_xPl_message(button_brand, button_id, button_action)
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
                send_xPl_message(button_brand, button_id, button_action)
            else :
                self.send_reply(code=HTTPStatus.BAD_REQUEST)
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
(client_port, xpl_socket) = common.xpl_open_socket(
    common.XPL_PORT, xPL_base_port
)
                                                             # start HTML server
server = HTTPServer(('', http_server_port), http_server)
logging.info('Starting xPL REST server')
try:
    server.serve_forever()
except KeyboardInterrupt:
    server.server_close()
