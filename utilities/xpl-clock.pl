#!/usr/bin/perl

use FindBin;                            # find the script's directory
use lib "$FindBin::Bin/../xPL-base";    # add path for common lib
use common;


################################################################################
# constants
#
$vendor_id = 'dspc';            # from xplproject.org
$device_id = 'clock';           # max 8 chars
$class_id = 'clock';            # max 8 chars

$separator = '-' x 80;
$indent = ' ' x 2;

#-------------------------------------------------------------------------------
# global variables
#
my $last_time = '';


################################################################################
# Input arguments
#
use Getopt::Std;
my %opts;
getopts('hvp:n:t:w:', \%opts);

die("\n".
    "Usage: $0\n".
    "\n".
    "Parameters:\n".
    "${indent}-h      display this help message\n".
    "${indent}-v      verbose\n".
    "${indent}-p port the base UDP port\n".
    "${indent}-n id   the instance id (max. 16 chars)\n".
    "${indent}-t mins the heartbeat interval in minutes\n".
    "${indent}-w secs the startup sleep interval\n".
    "\n".
    "Sends a clock update message every minute.\n".
    "\n".
    "More information with: perldoc $0\n".
    "\n".
    ""
   ) if ($opts{h});
my $verbose = $opts{v};
my $client_base_port = $opts{'p'} || 50000;
my $startup_sleep_time = $opts{'w'} || 0;

my $instance_id = $opts{'n'} || xpl_build_automatic_instance_id;
my $heartbeat_interval = $opts{'t'} || 5;

my $debug = 0;
if ($debug) { STDOUT->autoflush(1) } # print immediately, even without CR


################################################################################
# Internal functions
#

#-------------------------------------------------------------------------------
# Check the time and send a clock update message every beginning of a minute
#
sub tick {

  my ($last_time) = @_;
                                                          # get time information
  my ($minute, $hour) = (localtime(time))[1, 2];
  my $time = sprintf('%02dh%02d', $hour, $minute);
                                                             # check if new time
  if ($time eq $last_time) {
    $time = '';
  }

  return($time)
}


################################################################################
# Catch control-C interrupt
#
$SIG{INT} = sub{ $xpl_end++ };


################################################################################
# Main script
#
sleep($startup_sleep_time);
                                                                # xPL parameters
my $xpl_id = xpl_build_id($vendor_id, $device_id, $instance_id);
my $xpl_ip = xpl_find_ip;
                                                             # create xPL socket
my ($client_port, $xpl_socket) = xpl_open_socket($xpl_port, $client_base_port);
                                                    # display working parameters
if ($verbose == 1) {
  system("clear");
  print("$separator\n");
  print("Starting xPL clock on port $client_port.\n");
  print($indent . "class id: $class_id\n");
  print($indent . "instance id: $instance_id\n");
	print("\n");
}

#===============================================================================
# Main loop
#
my $timeout = 1;
my $sleep_for_next_minute = 60 - 10*$timeout;
my $is_first_minute = 1;
my $last_heartbeat_time = 0;
my $last_time = '';

while ( (defined($xpl_socket)) && ($xpl_end == 0) ) {
                                                 # check time and send heartbeat
  $last_heartbeat_time = xpl_send_heartbeat(
    $xpl_socket, $xpl_id, $xpl_ip, $client_port,
    $heartbeat_interval, $last_heartbeat_time
  );
                                                                  # get new time
  sleep($timeout);
  my $time = tick($last_time);
                                                        # send time tick message
  if ($time) {
    if ($verbose > 0) {
      if ($debug) {
        print("\n")
      }
      print "Time is $time\n";
    }
    xpl_send_message(
      $xpl_socket, $xpl_port,
      'xpl-stat', $xpl_id, '*', "$class_id.tick",
      (
        'time'  => $time
      )
    );
    $last_time = $time;
                                                           # leverage CPU effort
    if (not $is_first_minute) {
      sleep($sleep_for_next_minute);
      if ($debug) {
        print("  checking for next minute ")
      }
    }
    $is_first_minute = 0;
  }
                                                       # print debug information
  else {
    if ($debug) {
      print('.');
    }
  }
}

xpl_disconnect($xpl_socket, $xpl_id, $xpl_ip, $client_port);


################################################################################
# Documentation (access it with: perldoc <scriptname>)
#
__END__

=head1 NAME

xpl-clock.pl - Sends a clock update message every minute

=head1 SYNOPSIS

xpl-clock.pl [options]

=head1 DESCRIPTION

This xPL client sends a C<clock.tick> message status every minute.

The message body looks like: C<time=09h41>.

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

=back

=head1 TEST

Make sure you have an C<xpl-hub> running on the machine.

Start C<xpl-clock.pl -v> in a terminal window.

Start C</Users/control/Documents/Controls/xpl-monitor.pl -vf>
in another terminal window.

Wake a machine: C</Users/control/Documents/Controls/xpl-send.pl -v -c wake.basic mac=e8:06:88:cf:1d:10>

=head1 AUTHOR

Francois Corthay, DSPC

=head1 VERSION

2.0, 2012

=cut
