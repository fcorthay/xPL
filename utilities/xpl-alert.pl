#!/usr/bin/perl

use File::Basename;
use FindBin;                            # find the script's directory
use lib "$FindBin::Bin/../xPL-base";    # add path for common lib
use common;


################################################################################
# constants
#
$vendor_id = 'dspc';            # from xplproject.org
$device_id = 'alert';           # max 8 chars
$class_id = 'alert';            # max 8 chars

$separator = '-' x 80;
$indent = ' ' x 2;

#-------------------------------------------------------------------------------
# global variables
#
my %configuration;


################################################################################
# Input arguments
#
use Getopt::Std;
my %opts;
getopts('hvp:n:t:w:d:s:c:', \%opts);

die("\n".
    "Usage: $0 [options]\n".
    "\n".
    "Options:\n".
    "${indent}-h      display this help message\n".
    "${indent}-v      verbose\n".
    "${indent}-p port the base UDP port\n".
    "${indent}-n id   the instance id (max. 16 chars)\n".
    "${indent}-t mins the heartbeat interval in minutes\n".
    "${indent}-w secs the startup sleep interval\n".
    "${indent}-d dir  the sound files directory\n".
    "${indent}-s file the sound files name\n".
    "${indent}-c cmd  the command-line sound play control\n".
    "\n".
    "Announces text messages.\n".
    "\n".
    "More information with: perldoc $0\n".
    "\n".
    ""
   ) if ($opts{h});
my $verbose = $opts{v};
my $client_base_port = $opts{'p'} || 50000;
my $instance_id = $opts{'n'} || xpl_build_automatic_instance_id;
my $heartbeat_interval = $opts{'t'} || 5;
my $startup_sleep_time = $opts{'w'} || 0;

$configuration{'soundDirectory'} = $opts{'d'} || dirname($0) . '/sounds';
$configuration{'soundFile'}      = $opts{'s'} || 'doorBell.wav';
$configuration{'playCommand'}    = $opts{'c'} || 'SDL_AUDIODRIVER="alsa" AUDIODEV="hw:3" /usr/bin/ffplay -nodisp -autoexit -loglevel quiet';


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
  print "Servicing audio alerts.\n";
  print($indent . "class id: $class_id\n");
  print($indent . "xPL client id: $xpl_id\n");
	print("\n");
}


#===============================================================================
# Main loop
#

my $timeout = 10;
my $last_heartbeat_time = 0;

while ( (defined($xpl_socket)) && ($xpl_end == 0) ) {
                                                 # check time and send heartbeat
  $last_heartbeat_time = xpl_send_heartbeat(
    $xpl_socket, $xpl_id, $xpl_ip, $client_port,
    $heartbeat_interval, $last_heartbeat_time
  );
                                              # get xpl-UDP message with timeout
  my ($xpl_message) = xpl_get_message($xpl_socket, $timeout);
                                                           # process XPL message
  if ($xpl_message) {
    my ($type, $source, $target, $schema, %body) = xpl_get_message_elements($xpl_message);
    if ( xpl_is_for_me($xpl_id, $target) ) {
      if ( $schema eq "$class_id.basic" ) {
        if ($verbose > 0) {
          print("Received \"$type\" message from \"$source\" of schema \"$schema\"\n");
          print($indent . "Message body:\n");
          foreach $item (keys(%body)) {
            print($indent x 2 . "$item -> $body{$item}\n");
          }
        }
        if (lc($body{'command'}) eq 'play') {
          my $soundDirectory = $body{'soundDirectory'} || $configuration{'soundDirectory'};
          my $soundFile = $body{'soundFile'} || $configuration{'soundFile'};
          system("$configuration{'playCommand'} $soundDirectory/$soundFile");
        }
      }
    }
  }
}

xpl_disconnect($xpl_socket, $xpl_id, $xpl_ip, $client_port);


################################################################################
# Documentation (access it with: perldoc <scriptname>)
#
__END__

=head1 NAME

xpl-alert.pl - Plays an alert sound

=head1 SYNOPSIS

xpl-alert.pl [options]

=head1 DESCRIPTION

This xPL client plays an alert sound.

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

=head1 USAGE

Make sure you have an C<xpl-hub> running on the machine.

Start the alert client:
C<xpl-alert.pl -v>.

In another terminal, send a message to the echo client:
C<xpl-send.pl -v -t cmnd -c alert.basic command=play>.

Select the sound to play:
C<xpl-send.pl -v -t cmnd -c alert.basic command=play soundFile=pop.wav>.

=head1 AUTHOR

Francois Corthay, DSPC

=head1 VERSION

2.0, 2013

=cut
