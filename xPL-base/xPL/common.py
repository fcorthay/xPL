import socket
import sys
import re

# ------------------------------------------------------------------------------
# constants
#
XPL_PORT = 3865
INSTANCE_NAME_LENGTH = 16; # instance names have max. 16 chars

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
# build automatic instance name
#
def xpl_build_automatic_instance_id() :
                                                                # find host name
    host_name = socket.gethostname()
                                                          # limit to max. length
    automatic_instance_id = host_name[:INSTANCE_NAME_LENGTH]

    return(automatic_instance_id)

# ------------------------------------------------------------------------------
# trim instance name to valid characters and max length
#
def xpl_trim_instance_name(instance_name) :
                                                    # replace invalid characters
    trimmed_instance_name = re.sub(r'\W+', '', instance_name)
                                                            # trim to max length
    trimmed_instance_name = trimmed_instance_name[:INSTANCE_NAME_LENGTH]

    return(trimmed_instance_name);


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
            found = True
        except :
            client_port = client_port + 1
                                               # end script if no available port
    if not found :
        print('Could not create xpl socket');
        sys.exit(1)

    return (client_port, xpl_socket);

#-------------------------------------------------------------------------------
# Send UDP message to broadcast address
#
def xpl_send_braodcast (xpl_socket, xpl_port, message) :
#    print(message)
                                                      # enable broadcasting mode
    xpl_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                                                        # send broadcast message
    xpl_socket.sendto(message.encode(), ('<broadcast>', xpl_port))

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
    for parameter in body :
        message += parameter + "\n";
    message += "}\n";
#    print(message)
                                                              # send xPL message
    xpl_send_braodcast(xpl_socket, xpl_port, message)
