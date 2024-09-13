import socket
import sys
import re
import time

# ------------------------------------------------------------------------------
# constants
#
XPL_PORT = 3865
INSTANCE_NAME_LENGTH = 16; # instance names have max. 16 chars

ETHERNET_BUFFER_SIZE = 1024


# ==============================================================================
# Exported functions: utilities
#

# ------------------------------------------------------------------------------
# find machine IP address
#
def xpl_find_ip(host_name='localhost') :

    xpl_ip = socket.gethostbyname(host_name)

    return xpl_ip;

# ------------------------------------------------------------------------------
# trim instance name to valid characters and max length
#
def xpl_trim_instance_name(instance_name) :
                                                    # replace invalid characters
    trimmed_instance_name = re.sub(r'\W+', '', instance_name)
                                                            # trim to max length
    trimmed_instance_name = trimmed_instance_name[:INSTANCE_NAME_LENGTH]

    return(trimmed_instance_name);

# ------------------------------------------------------------------------------
# build automatic instance name
#
def xpl_build_automatic_instance_id() :
                                                                # find host name
    host_name = socket.gethostname()
                                                          # limit to max. length
    automatic_instance_id = xpl_trim_instance_name(host_name)

    return(automatic_instance_id)

#-------------------------------------------------------------------------------
# build xPL id
#
def xpl_build_id (vendor_id, device_id, instance_id) :

  xpl_id =                              \
    vendor_id + '-' +                   \
    device_id + '.' +                   \
    xpl_trim_instance_name(instance_id)

  return xpl_id;

#-------------------------------------------------------------------------------
# Open a broadcast UDP socket to the xPL hub
#
def xpl_open_socket(xpl_port, client_base_port) :
                                                       # start on base port port
    client_port = client_base_port;
    xpl_socket = 0;
                                                     # find and open a free port
    found = False
    while (not found) and (client_port < client_base_port+1000) :
        try :
            xpl_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            xpl_socket.bind(('', client_port))
            xpl_socket.setblocking(0)
            found = True
        except :
            client_port = client_port + 1
                                               # end script if no available port
    if not found :
        print('Could not create xpl socket');
        sys.exit(1)

    return(client_port, xpl_socket);

#-------------------------------------------------------------------------------
# Send UDP message to xPL broadcast port
#
def xpl_send_broadcast (xpl_socket, xpl_port, message) :
                                                      # enable broadcasting mode
    xpl_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                                                        # send broadcast message
    xpl_socket.sendto(message.encode(), ('localhost', xpl_port))

#-------------------------------------------------------------------------------
# Send xPL message to broadcast address
#
def xpl_send_message (
    xpl_socket, xpl_port,
    xpl_type, xpl_source, xpl_target, xpl_class,
    body
) :
                                                             # build xPL message
    message = xpl_type + "\n"
    message += "{\n";
    message += "hop=1\n";
    message += "source=%s\n" % xpl_source;
    message += "target=%s\n" % xpl_target;
    message += "}\n";
    message += xpl_class + "\n";
    message += "{\n";
    for parameter in body.keys() :
        message += "%s=%s\n" % (parameter, body[parameter]);
    message += "}\n";
#    print(message)
                                                              # send xPL message
    xpl_send_broadcast(xpl_socket, xpl_port, message)

#-------------------------------------------------------------------------------
# Get xPL message constituting elements
#
def xpl_get_message_elements(message) :
                                                               # trim line feeds
    message = message.replace("\r", "\n")
    message = re.sub(r"\n+", "\n", message)
  # $message =~ s/\n+/\n/g;
                                                           # split into elements
    (xpl_type, schema, body_string) = message.split('{', 3)
    xpl_type = xpl_type.replace("\n", '').lower()
    (source, schema) = schema.split('}', 2)
    schema = schema.replace("\n", '').lower()
                                                                # process header
    source = source.lower()
    target = source
    source = source.split('source=', 1)[1]
    source = source.split("\n", 1)[0]
    target = target.split('target=', 1)[1]
    target = target.split("\n", 1)[0]
                                                                  # process body
    body_string = body_string.split('}', 1)[0]
    body_list = body_string.split("\n")
    body_dict = {}
    for element in body_list :
        if '=' in element :
            (parameter, value) = element.split('=', 2)
            body_dict[parameter] = value
                                                               # return elements
    return(xpl_type, source, target, schema, body_dict)

#-------------------------------------------------------------------------------
# Check if xPL message is for the client
#
def xpl_is_only_for_me(xpl_id, target) :
                                                            # check target field
    matches = False
    if target.lower() == xpl_id.lower() :
        matches = True

    return(matches)

def xpl_is_for_me(xpl_id, target) :
                                                            # check target field
    matches = False
    if (target.lower() == xpl_id.lower()) or (target == '*') :
        matches = True

    return(matches)

# ==============================================================================
# Exported functions for main programs
#

#-------------------------------------------------------------------------------
# Get new xPl message with timeout
#
def xpl_get_message(xpl_socket, timeout) :
                                                    # read message from UDP port
    xpl_socket.settimeout(timeout)
    try:
        (message, source_address) = xpl_socket.recvfrom(ETHERNET_BUFFER_SIZE)
        message = message.decode()
    except socket.timeout:
        message = ''
        source_address = ''
                                                                # return message
    return(message, source_address)

#-------------------------------------------------------------------------------
# Check for elapsed time and send heartbeat
#
def xpl_send_heartbeat(
    xpl_socket, xpl_id, xpl_ip, client_port,
    heartbeat_interval, last_heartbeat_time
) :
                                                            # check elapsed time
    elapsed_time = round((time.time() - last_heartbeat_time) / 60);
#    print(elapsed_time)
                                                        # send heartbeat message
    if (elapsed_time >= heartbeat_interval) :
        xpl_send_message(
            xpl_socket, XPL_PORT,
            'xpl-stat', xpl_id, '*', 'hbeat.app',
            {
                'interval'  : heartbeat_interval,
                'remote-ip' : xpl_ip,
                'port'      : client_port
            }
        )
        last_heartbeat_time = time.time();
                                                    # return last heartbeat time
    return(last_heartbeat_time)

#-------------------------------------------------------------------------------
# Send disconnect (heartbeat) message
#
def xpl_disconnect(xpl_socket, xpl_id, xpl_ip, client_port) :
                                             # send disconnext heartbeat message
    xpl_send_message(
        xpl_socket, XPL_PORT,
        'xpl-stat', xpl_id, '*', 'hbeat.end',
        {
            'remote-ip' : xpl_ip,
            'port'      : client_port
        }
    );
                                                                  # close socket
    xpl_socket.close()
