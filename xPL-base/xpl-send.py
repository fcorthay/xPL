#!/usr/bin/python3
import argparse
import sys
import re
import common

# ------------------------------------------------------------------------------
# constants
#
VENDOR_ID = 'dspc';             # from xplproject.org
DEVICE_ID = 'sender';           # max 8 chars
CLASS_ID = 'sender';            # max 8 chars

INDENT = '  '

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
                                                                  # message type
parser.add_argument(
    '-t', '--type', default='cmnd',
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
    '-c', '--m_class', default='hbeat.app',
    help = 'xPL message class (class_id.type_id)'
)
                                                          # additional arguments
parser.add_argument('args', nargs=argparse.REMAINDER)
                                                  # parse command line arguments
parser_arguments = parser.parse_args()
verbose = parser_arguments.verbose
Ethernet_base_port = parser_arguments.port
instance_id = parser_arguments.id
message_type = parser_arguments.type
message_source = parser_arguments.source
message_target = parser_arguments.destination
message_class = parser_arguments.m_class
message_body = parser_arguments.args

# ------------------------------------------------------------------------------
# main script
#
if verbose :
    print(
        "\nSending xPL message as \"%s\" to \"%s\""
        % (message_source, message_target)
    );
xpl_ip = common.xpl_find_ip()

# ..............................................................................
                                                        # check xPL message type
is_OK = False
for msg_type in ['cmnd', 'stat', 'trig'] :
    if message_type == msg_type :
        is_OK = True
        message_type = 'xpl-' + message_type
if not is_OK :
    print("%s is not a valid xPL message type." % message_type);
    sys.exit(1)
                                                      # check xPL message source
if not re.search("\A(\w|\d)+-(\w|\d)+\.(\w|\d)+\Z", message_source) :
    print("%s is not a valid xPL source indentifier." % message_source);
    sys.exit(1)
                                                      # check xPL message target
if not re.search("\A(\w|\d)+-(\w|\d)+\.(\w|\d)+\Z", message_target) :
    if message_target != '*' :
        print("%s is not a valid xPL target indentifier." % message_target);
        sys.exit(1)
                                                       # check xPL message class
if not re.search("\A(\w|\d)+\.(\w|\d)+\Z", message_class) :
    print("%s is not a valid xPL class indentifier." % message_class);
    sys.exit(1)

# ..............................................................................
                                                             # create xPL socket
(client_port, xpl_socket) = common.xpl_open_socket(
    common.XPL_PORT, Ethernet_base_port
)
if verbose :
    print(INDENT + "Started UDP socket on port %s" % client_port)
                                                   # transform body list to dict
body_dict = {}
for element in message_body :
    if '=' in element :
        (parameter, value) = element.split('=', 2)
        body_dict[parameter] = value
                                                                  # send message
if verbose :
    print(INDENT + "Sending %s" % message_body)
common.xpl_send_message(
  xpl_socket, common.XPL_PORT,
  message_type, message_source, message_target, message_class,
  body_dict
);
                                                              # close xPL socket
xpl_socket.close();
