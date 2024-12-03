#!/usr/bin/python3
import argparse
import sys
import signal
import os
import time
sys.path.append(sys.path[0]+'/../xPL-base')
import common
import requests

# ------------------------------------------------------------------------------
# constants
#
VENDOR_ID = 'dspc';             # from xplproject.org
DEVICE_ID = 'request';          # max 8 chars
CLASS_ID = 'request';           # max 8 chars

INDENT = '  '
SEPARATOR = 80 * '-'

# ------------------------------------------------------------------------------
# command line arguments
#
parser = argparse.ArgumentParser()
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
                                                                     # verbosity
parser.add_argument(
    '-v', '--verbose', action='store_true', dest='verbose',
    help = 'verbose console output'
)
                                                  # parse command line arguments
parser_arguments = parser.parse_args()
Ethernet_base_port = parser_arguments.port
instance_id = parser_arguments.id
heartbeat_interval = int(parser_arguments.timer)
startup_delay = int(parser_arguments.wait)
verbose = parser_arguments.verbose

debug = False

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
    print("Ready to send HTTP requests on demand")
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
        if schema == CLASS_ID + '.basic' :
            if xpl_type == 'xpl-cmnd' :
                if common.xpl_is_for_me(xpl_id, target) :
                                                                        # method
                    method = 'GET'
                    if 'method' in body.keys() :
                        method = body['method'].upper()
                        body.pop('method')
                                                                      # protocol
                    request_URL = 'http'
                    if 'protocol' in body.keys() :
                        request_URL = body['protocol']
                        body.pop('protocol')
                    request_URL = request_URL + '://'
                                                                        # server
                    server = 'localhost'
                    if 'server' in body.keys() :
                        server = body['server']
                        body.pop('server')
                    request_URL = request_URL + server
                                                                          # port
                    port = ''
                    if 'port' in body.keys() :
                        port = ':' + body['port']
                        body.pop('port')
                    request_URL = request_URL + port + '/'
                                                                          # path
                    path = ''
                    if 'path' in body.keys() :
                        path = body['path']
                        body.pop('path')
                    request_URL = request_URL + path
                                                                    # parameters
                    parameters = ''
                    if body :
                        for parameter, value in body.items():
                            parameters = parameters + "&%s=%s" \
                                % (parameter, value)
                        parameters = parameters.replace('&', '?', 1)
                    request_URL = request_URL + parameters
                    if verbose :
                        print("request \"%s %s\"" % (method, request_URL))
                                                                           # GET
                    if method == 'GET' :
                        try :
                            request = requests.get(request_URL)
                        except:
                            if verbose :
                                print(
                                    INDENT +
                                    "request \"%s\" rejected" % request_URL
                                )
                                                                          # POST
                    elif method == 'POST' :
                        try :
#                            request = requests.post(request_URL, data='')
                            request = requests.post(request_URL)
                        except:
                            if verbose :
                                print(
                                    INDENT +
                                    "request \"%s\" rejected" % request_URL
                                )
                                                                           # PUT
                    elif method == 'PUT' :
                        try :
                            request = requests.put(request_URL)
                        except:
                            if verbose :
                                print(
                                    INDENT +
                                    "request \"%s\" rejected" % request_URL
                                )
                                                                        # DELETE
                    elif method == 'DELETE' :
                        try :
                            request = requests.delete(request_URL)
                        except:
                            if verbose :
                                print(
                                    INDENT +
                                    "request \"%s\" rejected" % request_URL
                                )
                    if verbose :
                        try :
                            print(INDENT + requests.reason)
                        except:
                            pass
                                                             # delete xPL socket
common.xpl_disconnect(xpl_socket, xpl_id, xpl_ip, client_port)
