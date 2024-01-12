#!/usr/bin/perl

use IO::Socket;
use IO::Interface::Simple;
use FindBin;                    # find the script's directory
use lib $FindBin::Bin;          # add that directory to the library path
use xPL::common;


my $separator = '-' x 80;
my $indent = ' ' x 2;


################################################################################
# Input arguments
#
use Getopt::Std;
my %opts;
getopts('hvt:w:l:', \%opts);

die("\n".
    "Usage: $0 [options]\n".
    "\n".
    "Options:\n".
    "${indent}-h      display this help message\n".
    "${indent}-v      verbose\n".
    "${indent}-t ms   the UDP input timeout\n".
    "${indent}-w secs the startup sleep interval\n".
    "${indent}-l file the log file\n".
    "\n".
    "Implements a xPL hub.\n".
    "\n".
    ""
   ) if ($opts{h});
my $verbose = $opts{v};
my $timeout = $opts{'t'} || 1;
my $startup_sleep_time = $opts{'w'} || 0;
my $log_file = $opts{'l'} || '/dev/null';


################################################################################
# Local functions
#

#-------------------------------------------------------------------------------
# Get the list of the local IP addresses
#
sub get_local_IPs {
  my @addresses;
  my @interfaces = IO::Interface::Simple->interfaces;
#print "$interface\n";
  for my $interface (@interfaces) {
#print $interface->address . "\n";
    push(@addresses, $interface->address);
  }
  return @addresses;
}

#-------------------------------------------------------------------------------
# Check if an IP address belongs to the local addresses list
#
sub message_is_local {
	my ($ip_address, @local_addresses) = @_;

  my $is_local = 0;
  foreach my $ip (@local_addresses) {
    if ($ip eq $ip_address) {
      $is_local = 1;
    }
  }

  return $is_local;
}

#-------------------------------------------------------------------------------
# Broadcast an xPL message to a local client on the port he is listening to
#
sub broadcast_message {
	my ($port, $message) = @_;
                                                                   # open socket
  my $ipaddr   = inet_aton('127.0.0.1');
  my $portaddr = sockaddr_in($port, $ipaddr);
  my $sockUDP = IO::Socket::INET->new(
    PeerPort => $port,
    Proto    => 'udp'
  );
  if (!defined($sockUDP)) {
    print "Error sending xPL message to port $port.\n";
    return;
  }  
                                                                  # send message
  $sockUDP->autoflush(1);
  $sockUDP->sockopt(SO_BROADCAST, 1);
  $sockUDP->send($message, 0, $portaddr);  
#print "$message\n";
                                                                  # close socket
  close $sockUDP;
}

#-------------------------------------------------------------------------------
# Log client info
#
sub log_client_list {
  my ($log_file_spec, %clients) = @_;

  open(LOG_FILE, "> $log_file_spec");
  print(LOG_FILE "Ports and associated xPL clients:\n");
  foreach my $client (sort keys %clients) {
    print(LOG_FILE "${indent}$client: $clients{$client}\n");
  }
  close(LOG_FILE);
}


################################################################################
# Main script
#
sleep($startup_sleep_time);
                                                               # welcome message
if ($verbose > 0) {
  system("clear");
  print("$separator\n");
  print("Starting xPL hub\n");
  print("${indent}log file: $log_file\n");
  print("\n");
}
                                                          # start xPL UDP socket
my $xpl_socket = IO::Socket::INET->new(
  Proto     => 'udp',
  LocalPort => $xpl_port,
);	
die(
  "The hub could not bind to port 3865." &
  "Make sure you are not already running an xPL hub.\n"
) unless $xpl_socket;
                                                    # Get all local IP addresses
my @local_addresses = get_local_IPs;

#===============================================================================
# Main loop
#
my %clients = ();
my %timeouts = ();

while (defined($xpl_socket)) {
                                             # get message and source IP address
  my ($xPL_message, $source_address) = xpl_get_message($xpl_socket, $timeout);
  my ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) = localtime();
  my $time_string = sprintf('%02d:%02d:%02d', $hour, $min, $sec);
  if ($xPL_message) {
#print "$source_address : $xPL_message\n";
                                             # check for local heartbeat message
    if (message_is_local($source_address, @local_addresses)) {
#print "$xPL_message\n";
      my ($type, $source, $target, $schema, %body) = xpl_get_message_elements(
        $xPL_message
      );
      my $port = $body{port};
                                                    # process heartbeat messages
      if ( ($type eq 'xpl-stat') and ($schema =~ m/\Ahbeat.app/) ) {
                                                                 # restart timer
        $timeouts{$port} = $body{interval} * 1/$timeout * 60 * 1.25;
                                                            # add client to list
        if (!defined($clients{$port})) {
          $clients{$port} = $source;
          if ($verbose > 0) {
            print(
              "$time_string, Added \"$clients{$port}\", port $port, " .
              "to client list\n"
            );
          }
          log_client_list($log_file, %clients);
        }
        else {
          if ($verbose > 0) {
            print(
              "$time_string, Updated \"$clients{$port}\", port $port, " .
              "in client list\n"
            );
          }
        }
      }
                                                       # remove client from list
      if ( ($type eq 'xpl-stat') and ($schema =~ m/\Ahbeat.end/) ) {
        if (defined($clients{$port})) {
          if ($verbose > 0) {
            print(
              "$time_string, Removed \"$clients{$port}\", port $port, " .
              "from client list\n"
            );
          }
          delete $clients{$port};                
          delete $timeouts{$port};                
          log_client_list($log_file, %clients);
        }
      }
    }
                                         # broadcast xPL messages to client list
    foreach my $client (keys %clients) {
#print "$xPL_message\n";
      broadcast_message($client, $xPL_message);
    }
  }
                                                              # decrement timers
  else {
#print "$time_string -> $timeouts{50001}\n";
    foreach my $client (keys %clients) {
      $timeouts{$client} = $timeouts{$client} - 1;
                                                      # remove client on timeout
      if ($timeouts{$client} <= 0) {
        if ($verbose > 0) {
          print(
            "$time_string, Removed \"$clients{$port}\", port $port, " .
            "from client list\n"
          );
        }
        delete $clients{$client};                
        delete $timeouts{$client};                
        log_client_list($log_file, %clients);
      }
#print $indent . "$client: $timeouts{$client}\n";
    }
  }
}

close($xpl_socket);

1;
