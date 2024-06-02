#!/usr/bin/perl

use FindBin;                    # find the script's directory
use lib $FindBin::Bin;          # add that directory to the library path
use xPL::common;


################################################################################
# constants
#
$vendor_id = 'dspc';            # from xplproject.org
$device_id = 'squeeze';         # max 8 chars
$class_id = 'slimserv';         # max 8 chars

$separator = '-' x 80;
$indent = ' ' x 2;

#-------------------------------------------------------------------------------
# global variables
#
my %configuration;
$configuration{'server'} = 'hephaistos.cofnet';
$configuration{'port'} = '9090';


################################################################################
# Input arguments
#
use Getopt::Std;
my %opts;
getopts('hvn:t:w:p:s:', \%opts);

die("\n".
    "Usage: $0 [options]\n".
    "\n".
    "Options:\n".
    "${indent}-h        display this help message\n".
    "${indent}-v        verbose\n".
    "${indent}-n id     the instance id (max. 12 chars)\n".
    "${indent}-t mins   the heartbeat interval in minutes\n".
    "${indent}-w secs   the startup sleep interval\n".
    "${indent}-p port   the base UDP port\n".
    "${indent}-b bridge the IP address of the hue bridge\n".
    "\n".
    "Controls a Philips hue lighting system.\n".
    "\n".
    "More information with: perldoc $0\n".
    "\n".
    ""
   ) if ($opts{h});
my $verbose = $opts{v};
my $instance_id = $opts{'n'} || xpl_build_automatic_instance_id;
my $heartbeat_interval = $opts{'t'} || 5;
my $startup_sleep_time = $opts{'w'} || 0;
my $client_base_port = 50000;

$configuration{'server'} = $opts{'s'} || $configuration{'server'};
$configuration{'port'} = $opts{'p'} || $configuration{'port'};


################################################################################
# Internal functions
#

#-------------------------------------------------------------------------------
# Build CLI message from xPL command
#
sub build_cli_message {

  my %body = @_;
  my $message;
                                                               # decode commands
  my $command = $body{'command'};
#print "$command\n";
  my $player = $body{'player'};
  if (
    ($command eq 'play') or
    ($command eq 'stop') or
    ($command eq 'pause') or
    ($command =~ m/pause\s+[01]/) or
    ($command =~ m/power\s+[01]/)
  ) {
    $message = "$player $command";
  }
  elsif (
    ($command =~ m/volume\s+\d+/)
  ) {
    $message = "$player mixer $command";
  }
  else {
    $message = $command;
  }

  return($message)
}

#-------------------------------------------------------------------------------
# Send CLI command to server
#
sub send_cli_command
{
  my ($server, $port, $message) = @_;
                                                              # build TCP socket
  my $socket  = IO::Socket::INET -> new (
    PeerAddr => $server,
    PeerPort => $port,
    Proto    => 'tcp'
  ) or die "Could not connect to $server port $port\n";
                                                              # send CLI command
#print "sending \"$message\"\n";
  print($socket "$message\n");
   my $response = <$socket>;
   if ( ! $socket->connected() )
      { die "Server dropped socket connection\n"; }
   chomp $response;
#print "  received \"$response\"\n";
                                                                  # close socket
  close($socket) if $socket;

 return $response;
}

#-------------------------------------------------------------------------------
# get player names
#
sub get_players
{
  my ($server, $port) = @_;
  my %players;
                                                             # get player number
  my $player_count = send_cli_command($server, $port, 'player count ?');
  $player_count =~ s/.*\s+count\s+//;
                                                              # get player names
  for ($index = 0; $index < $player_count; $index++) {
    my $cli_player_name = send_cli_command($server, $port, "player name $index ?");
    $cli_player_name =~ s/.*\s+name\s+\d+\s+//;
    my $xpl_player_name = $cli_player_name;
    $xpl_player_name =~ s/%20//g;
    $xpl_player_name = substr($xpl_player_name, 0, $instance_name_length);
    $players{$xpl_player_name} = $cli_player_name;
#print "  $xpl_player_name -> \"$cli_player_name\"\n";
  }

   return %players;
}

#-------------------------------------------------------------------------------
# get player status
#
sub get_status
{
  my ($server, $port, $player) = @_;
  my %status;
                                                              # get player power
  my $power = send_cli_command($server, $port, "$player power ?");
  $power =~ s/.*\s+power\s+//;
  $status{'power'} = $power;

  if ($power > 0) {
                                                            # get playing status
    my $mode = send_cli_command($server, $port, "$player mode ?");
    $mode =~ s/.*\s+mode\s+//;
    $mode =~s/\Aplay\Z/playing/;
    $mode =~s/\Apause\Z/paused/;
    $mode =~s/\Astop\Z/stopped/;
    $status{'status'} = $mode;
                                                                    # get artist
    my $artist = send_cli_command($server, $port, "$player artist ?");
    $artist =~ s/.*\s+artist\s+//;
    $artist =~ s/%20/ /g;
    $status{'artist'} = $artist;
                                                                     # get album
    my $album = send_cli_command($server, $port, "$player album ?");
    $album =~ s/.*\s+album\s+//;
    $album =~ s/%20/ /g;
    $status{'album'} = $album;
                                                                     # get track
    my $track = send_cli_command($server, $port, "$player title ?");
    $track =~ s/.*\s+title\s+//;
    $track =~ s/%20/ /g;
    $status{'track'} = $track;
  }

   return %status;
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
  print("Controlling the squeeze server \"$configuration{'server'}\", port $configuration{'port'}.\n");
  print($indent . "device id: $device_id\n");
  print($indent . "class id: $class_id\n");
  print($indent . "instance id: $instance_id\n");
	print("\n");
}


#-------------------------------------------------------------------------------
# Main loop
#
my $timeout = 1;
my $last_heartbeat_time = 0;

my %players = get_players($configuration{'server'}, $configuration{'port'});
#foreach my $player (keys(%players)) { print "$player -> $players{$player}\n"; }

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
                                                # check for squeeze device match
    my $squeeze_device = $target;
    $squeeze_device =~ s/.*\.//;
    if ($squeeze_device ne 'controller') {
      $squeeze_device = $players{$squeeze_device};
    }
#print "-> $squeeze_device\n";
    if ($squeeze_device ne '') {
      $target =~ s/\..*/.$instance_id/;
      $body{'player'} = $squeeze_device;
    }
    if ( xpl_is_for_me($xpl_id, $target) ) {
                                                              # process commands
      if ($schema eq "$class_id.basic") {
        if ($type eq 'xpl-cmnd') {
          if ($verbose > 0) {
            print("\n");
            print("Received command from \"$source\"\n");
          }
          my $cli_message = build_cli_message(%body);
#print "-> \"$cli_message\"\n";
          if ($cli_message ne '') {
            if ($verbose == 1) {
              print("${indent}sending: \"$cli_message\" to server\n");
            }
            my $response = send_cli_command(
              $configuration{'server'},
              $configuration{'port'},
              $cli_message
            );
            if (lc($body{'mode'}) eq 'cli') {
              xpl_send_message(
                $xpl_socket, $xpl_port,
                'xpl-stat', $xpl_id, '*', "$class_id.status",
                ('player' => $body{'player'}, 'response' => $response)
              );
            }
          }
        }
      }
                                                               # process replies
      if ($schema eq "$class_id.request") {
        if ($type eq 'xpl-cmnd') {
          my $command = $body{command};
          if ($verbose == 1) {
            print "\n";
              print("Received request \"$command\" from \"$source\"\n");
          }
          if ($command eq 'status') {
            my %body = get_status(
              $configuration{'server'},
              $configuration{'port'},
              $body{'player'}
            );
            if ($verbose == 1) {
              my $status;
              foreach my $item (keys(%body)) {
                $status .= "$item -> $body{$item}\n";
              }
              print $indent, "replying: $status\n";
            }
            xpl_send_message(
              $xpl_socket, $xpl_port,
              'xpl-stat', $xpl_id, '*', "$class_id.status",
              %body
            );
          }
          elsif ($command eq 'list') {
            xpl_send_message(
              $xpl_socket, $xpl_port,
              'xpl-stat', $xpl_id, '*', "$class_id.status",
              reverse(%players)
            );
          }
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

xpl-squeeze.pl - Controls a Philips hue lighting system

=head1 SYNOPSIS

xpl-squeeze.pl [options]

=head1 DESCRIPTION

This xPL client sends commands to a SqueezeCenter
in order to control multi-room audio.

The C<slimserv.basic> commands allow to control following items:
C<play>, C<stop>, C<pause>, C<pause 0>, C<pause 1>, C<power 0>, C<power 1>,
C<volume nn>.

The C<slimserv.request> commands allow to aks for following items:
C<status>, C<list>.

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
The id is limited to 12 characters.
If not specified, it is constructed from the host name and the serial port controller name.

=item B<-t mins>

Specify the number of minutes between two heartbeat messages.

=item B<-w secs>

Specify the number of seconds before sending the first heartbeat.
This allows to start the client after the hub,
thus eliminating an prospective startup delay of one heartbeat interval.

=item B<-b str>

Specify the hue bridge's URL.

=item B<-u str>

Specify a username in the bridge's whitelist.

=back

=head1 TEST

Make sure you have an C<xpl-hub> running on the machine.

Start the hue controller:
C<xpl-hue.pl -vn hue>.

Start C<xpl-logger -v> in another terminal window.

Launch the command
C<xpl-send.pl -v -c lighting.basic device=3 command=activate level=100>.
The bulb nb 3 should turn on and C<xpl-logger> display the control message.

Launch the command
C<xpl-send.pl -v -c lighting.request device=3>.
C<xpl-logger> should display the status message.

=head1 AUTHOR

Francois Corthay, DSPC

=head1 VERSION

1.0, 2013

=cut
