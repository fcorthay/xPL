#!/usr/bin/python3
import argparse
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
verbose = parser_arguments.verbose

# ==============================================================================
# Internal functions
#

# ------------------------------------------------------------------------------
# get button action
#
def get_button_action(path) :
    button_id = ''
    button_action = ''
    path_elements = path.split('/')
    if len(path_elements) == 5 :
        if path_elements[1] == 'myStrom' :
            if path_elements[2] == 'button' :
                button_id = path_elements[3]
                button_action = path_elements[4]

    return(button_id, button_action)

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
def send_xPl_message(button_id, button_action) :
    message_body = {}
    message_body['hardware'] = 'myStrom'
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
                                                                           # GET
    def do_GET(self):
        (button_id, button_action) = get_button_action(self.path)
        if button_id :
            info = "On button <code>%s</code>, action was <code>%s</code>" \
                % (button_id, button_action)
            self.send_reply(info=info, code=HTTPStatus.OK)
            send_xPl_message(button_id, button_action)
        else :
            self.send_reply(code=HTTPStatus.BAD_REQUEST)
                                                                          # POST
    def do_POST(self):
        (button_id, button_action) = get_button_action(self.path)
        if button_id :
            self.send_reply(code=HTTPStatus.OK)
            send_xPl_message(button_id, button_action)
        else :
            self.send_reply(code=HTTPStatus.BAD_REQUEST)
                                                                           # PUT
    def do_PUT(self):
        print('put:/' + self.path)
        self.send_reply()
                                                                         # PATCH
    def do_PATCH(self):
        print('patch:/' + self.path)
        self.send_reply()
                                                                        # DELETE
    def do_DELETE(self):
        print('delete:/' + self.path)
        self.send_reply()

# ==============================================================================
# main script
#
                                                             # create xPL socket
(client_port, xpl_socket) = common.xpl_open_socket(
    common.XPL_PORT, xPL_base_port
)
                                                             # start HTML server
server = HTTPServer(('', http_server_port), http_server)
try:
    server.serve_forever()
except KeyboardInterrupt:
    server.server_close()
