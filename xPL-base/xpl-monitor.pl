#!/usr/bin/perl

use FindBin;                    # find the script's directory
use lib $FindBin::Bin;          # add that directory to the library path
use xPL::common;
use Time::HiRes qw(time);

################################################################################
# constants
#
$xpl_port = 3865;
$vendor_id = 'dspc';             # from xplproject.org
$device_id = 'monitor';          # max 8 chars
#$class_id = 'monitor';           # max 8 chars
$instance_name_length = 16;      # max 16 chars

$separator = '-' x 80;
$indent = ' ' x 2;

$end = 0;

################################################################################
# Input arguments
#
use Getopt::Std;
my %opts;
getopts('hvfp:n:t:d', \%opts);

die("\n".
    "Usage: $0 [options]\n".
    "\n".
    "Options:\n".
    "${indent}-h      display this help message\n".
    "${indent}-v      verbose\n".
    "${indent}-p port the base UDP port\n".
    "${indent}-n id   the instance id (max. 16 chars)\n".
    "${indent}-t mins the heartbeat interval in minutes\n".
    "${indent}-f      filter hbeat.app messages\n".
    "${indent}-d      display delay between messages\n".
    "\n".
    "Monitors xPL messages.\n".
    "\n".
    "More information with: perldoc $0\n".
    "\n".
    ""
   ) if ($opts{h});
my $verbose = $opts{'v'};
my $client_base_port = $opts{'p'} || 50000;
my $instance_id = $opts{'n'} || xpl_build_automatic_instance_id;
my $heartbeat_interval = $opts{'t'} || 5;

my $filter_heartbeats = $opts{'f'};
my $display_delay = $opts{'d'};


################################################################################
# Internal functions
#

#-------------------------------------------------------------------------------
# Trim instance name to valid characters and max length
#
sub trim_instance_name {
	my ($instance_name) = @_;
                                                    # replace invalid characters
	$instance_name =~ s/(-|\.|!|;)//g;
                                                            # trim to max length
	if (length($instance_name) > $instance_name_length) {
		$instance_name = substr($instance_name, 0, $instance_name_length);
	}

	return $instance_name;
}


#-------------------------------------------------------------------------------
# Open an UDP socket to the xPL hub
#
sub open_xpl_socket {
	my ($xpl_port, $client_base_port) = @_;
                                                      # start on base port port
  my $client_port = $client_base_port;
  my $xpl_socket;
                                                             # open a free port
  while (!$xpl_socket && $client_port < $client_base_port+1000) {
    $xpl_socket = IO::Socket::INET->new(
      Broadcast => 1,
      PeerPort => $xpl_port,
      LocalPort => $client_port,
      Proto     => 'udp'
    );

    if (!$xpl_socket) {
      $client_port = $client_port + 1;
    }
  }
  die "Could not create socket: $!\n" unless $xpl_socket;

  return ($client_port, $xpl_socket);
}


################################################################################
# Catch control-C interrupt
#
$SIG{INT} = sub{ $end++ };


################################################################################
# Main script
#
if ($verbose > 0) {
  print "$separator\n";
  print "Starting xPL monitor\n";
}

my $xpl_id = xpl_build_id($vendor_id, $device_id, $instance_id);
my $xpl_ip = xpl_find_ip;

#-------------------------------------------------------------------------------
# create xPL socket
#
my ($client_port, $xpl_socket) = open_xpl_socket($xpl_port, $client_base_port);
if ($verbose > 0) {
  system("clear");
  print "$separator\n";
  print "${indent}Started UDP socket on port $client_port\n";
}


#===============================================================================
# Main loop
#
my $timeout = 1;
my $last_heartbeat_time = 0;
my $last_message_time = 0;

while ( (defined($xpl_socket)) && ($end == 0) ) {
                                                 # check time and send heartbeat
  $last_heartbeat_time = xpl_send_heartbeat(
    $xpl_socket, $xpl_id, $xpl_ip, $client_port,
    $heartbeat_interval, $last_heartbeat_time
  );
                                              # get xpl-UDP message with timeout
  my ($xpl_message) = xpl_get_message($xpl_socket, $timeout);
                                                      # filter XPL hbeat message
  if ($filter_heartbeats != 0) {
    if ($xpl_message =~ m/\}\nhbeat.app\n\{/) {
      $xpl_message = '';
    }
  }
                                                           # display XPL message
  if ($xpl_message) {
    print "$separator\n";
    if ($display_delay) {
      my $now = time();
      my $delta = sprintf('%.3f', $now - $last_message_time);
      $last_message_time = $now;
      print "Delta: $delta second(s)\n";
    }
    print "$xpl_message\n";
  }
}

xpl_disconnect($xpl_socket, $xpl_id, $xpl_ip, $client_port);


################################################################################
# Documentation (access it with: perldoc <scriptname>)
#
__END__

=head1 NAME

xpl-monitor.pl - Displays all xPL messages

=head1 SYNOPSIS

xpl-monitor.pl [options]

=head1 DESCRIPTION

This xPL client prints all xPL messages it receives.

=head1 OPTIONS

=over 8

=item B<-h>

Display a help message.

=item B<-v>

Be verbose.

=item B<-p port>

Specify the base port from which the client searches for a free port.
If not specified, the client will take a default value.

=item B<-n id>

Specify the instance id (name).
The id is limited to 16 characters.
If not specified, it is constructed from the host name.

=item B<-t mins>

Specify the number of minutes between two heartbeat messages.

=item B<-w secs>

Specify the number of seconds before sending the first heartbeat.
This allows to start the client after the hub,
thus eliminating an prospective startup delay of one heartbeat interval.

=item B<-f>

Filters C<hbeat.app> messages.

=item B<-d>

Displays delay between messages.

=back

=head1 USAGE

Make sure you have an C<xpl-hub> running on the machine.

Start the monitor:
C<xpl-monitor.pl -v>
and watch the output.

=head1 AUTHOR

Francois Corthay, DSPC

=head1 VERSION

2.1, 2014

=cut
