#!/usr/bin/python3
import argparse
import sys
import signal
import os
import time
sys.path.append(sys.path[0]+'/../xPL-base')
import common
import json
import requests

# ------------------------------------------------------------------------------
# constants
#
VENDOR_ID = 'dspc';             # from xplproject.org
DEVICE_ID = 'snapcast';         # max 8 chars
CLASS_ID = 'snapcast';          # max 8 chars

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
                                                              # Snap server name
parser.add_argument(
    '-s', '--server', default='localhost',
    help = 'the snapcast server name'
)
                                                              # Snap server port
parser.add_argument(
    '-j', '--jsonPort', default=1780,
    help = 'the snapcast JSON-RPC server port'
)
                                                  # parse command line arguments
parser_arguments = parser.parse_args()
verbose = parser_arguments.verbose
Ethernet_base_port = parser_arguments.port
instance_id = parser_arguments.id
heartbeat_interval = int(parser_arguments.timer)
startup_delay = int(parser_arguments.wait)
snap_server_name = parser_arguments.server
snap_server_port = int(parser_arguments.jsonPort)

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
                                                              # get clients list
if verbose :
    os.system('clear||cls')
    print(SEPARATOR)
    print("Getting Snapcat client list from %s:%s" %
        (snap_server_name, snap_server_port))
service_url = "http://%s:%d/jsonrpc" % (snap_server_name, snap_server_port)
request_id = 0
request = {
    'jsonrpc': '2.0',
    'id' : "%d" % request_id,
    'method' : 'Server.GetStatus'
}
response = requests.post(service_url, data=json.dumps(request)).json()
request_id = request_id + 1
client_ids = {}
display_length = 0
groups_info = response['result']['server']['groups']
for group_info in groups_info :
    for client_info in group_info['clients'] :
        client_name = client_info['host']['name']
        client_id = client_info['id']
        client_ids[client_name] = client_id
        name_length = len(client_name)
        if name_length > display_length:
            display_length = name_length
if verbose :
    client_ids = dict(sorted(client_ids.items()))
    column_format = "%%-%ds : %%s" % display_length
    print(column_format)
    for client_name in client_ids :
        print(INDENT + column_format % (client_name, client_ids[client_name]))
                                                    # display working parameters
if verbose :
    print("Ready to control Snapcat audio")
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
                    client_name = body['client'];
                    if verbose :
                        print("Received command from %s for %s" %
                            (source, client_name)
                        )
                    client_list = []
                    if client_name == '*' :
                        for name in client_ids :
                            client_list.append(client_ids[name])
                    elif client_name in client_ids :
                        client_list.append(client_ids[client_name])
                    command = body['command'];
                    level = -1
                    if 'level' in body.keys() :
                        level = int(body['level']);
                    for client_id in client_list :
                        request['id'] = request_id
                        request['params'] = {'id' : client_id}
                        send_request = False
                        if (command == 'volume') and (level >= 0) :
                            request['method'] = 'Client.SetVolume'
                            request['params']['volume'] = {
                                'muted' : False, 'percent' : level
                            }
                            send_request = True
                        if command == 'mute' :
                            request['method'] = 'Client.SetVolume'
                            request['params']['volume'] = {'muted' : True}
                            send_request = True
                        if send_request :
                            response = requests.post(
                                service_url, data=json.dumps(request)
                            ).json()
                            request_id = request_id + 1
                            if verbose :
                                print(
                                    INDENT +
                                    "muted : %s" % (
                                        response['result']['volume']['muted']
                                    )
                                )
                                print(
                                    INDENT +
                                    "level : %s%%" % (
                                        response['result']['volume']['percent']
                                    )
                                )


                                                             # delete xPL socket
common.xpl_disconnect(xpl_socket, xpl_id, xpl_ip, client_port)
