#!/usr/bin/perl

use XML::Simple;

use FindBin;                            # find the script's directory
use lib "$FindBin::Bin/../xPL-base";    # add path for common lib
use common;


################################################################################
# constants
#
$vendor_id = 'dspc';            # from xplproject.org
$device_id = 'state';           # max 8 chars
$class_id = 'state';            # max 8 chars

$separator = '-' x 80;
$indent = ' ' x 2;

#-------------------------------------------------------------------------------
# global variables
#
my %configuration;
$configuration{'stateFile'} = '/home/control/Controls/xPL/central/state.xml';

my %state;
$state{last_card} = 'none';


################################################################################
# Input arguments
#
use Getopt::Std;
my %opts;
getopts('hvp:n:t:w:s:', \%opts);

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
    "${indent}-s file the XML state file spec\n".
    "\n".
    "Interfaces to the home's state information.\n".
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

$configuration{'stateFile'} = $opts{'s'} || $configuration{'stateFile'};


################################################################################
# Internal functions
#

#-------------------------------------------------------------------------------
# Parse the xPL command to get object to update
#
sub parse_command {
  my ($verbose, %body) = @_;
                                                                     # command
  my $command = $body{'command'};
  if ($command eq '') {
    if ($verbose > 0) {
      print $indent, "No command specified\n";
    }
  }
                                                                        # room
  my $room = $body{'room'};
  if ($room eq '') {
    $command = '';
    if ($verbose > 0) {
      print($indent . "No room specified\n");
    }
  }
                                                                        # kind
  my $kind = $body{'kind'};
  if ($kind eq '') {
    $command = '';
    if ($verbose > 0) {
      print($indent . "No kind specified\n");
    }
  }
                                                                      # object
  my $object = $body{'object'};
  if ($object eq '') {
    $command = '';
    if ($verbose > 0) {
      print($indent . "No object specified\n");
    }
  }
                                                                       # value
  my $value = $body{'value'};
  if ($value eq '') {
    if ( ($command eq 'update') or ($command eq 'set') ) {
      $command = '';
      if ($verbose > 0) {
        print($indent . "No value specified\n");
      }
    }
  }

  return($command, $room, $kind, $object, $value);
}


#-------------------------------------------------------------------------------
# Get a state value
#
sub get_state {
  my ($file_spec, $room, $kind, $object) = @_;
                                                        # read state from file
  my $state_ref = XMLin($configuration{stateFile});
                                                              # get state item
  $value = $state_ref->{$room}->{$kind}->{$object};

  return($value);
}


#-------------------------------------------------------------------------------
# Update the state file
#
sub update_state {
  my ($file_spec, $room, $kind, $object, $value) = @_;
                                                        # read state from file
  my $state_ref;
  if (-s $file_spec) {
    $state_ref = XMLin($file_spec);
  }
                                                            # check for change
  my $has_changed = 0;
  if ($state_ref->{$room}->{$kind}->{$object} ne $value) {
    $has_changed = 1;
  }
  if ($has_changed) {
                                                           # update state item
    $state_ref->{$room}->{$kind}->{$object} = $value;
                                                         # write state to file
    open(state_file, "> $file_spec");
    print state_file
      XMLout($state_ref,
        RootName => 'state',
        XMLDecl => '<?xml version="1.0" encoding="ISO-8859-1"?>'
      );
    close(state_file);
  }

  return($has_changed);
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
if ($verbose >  0) {
  system("clear");
  print("$separator\n");
  print("Starting xPL home state controller.\n");
  print($indent . "class id: $class_id\n");
  print($indent . "xPL id: $xpl_id\n");
  print($indent . "state file: \"$configuration{'stateFile'}\"\n");
	print("\n");
}

#-------------------------------------------------------------------------------
# Main loop
#
my $timeout = 1;
my $last_heartbeat_time = 0;

while ( (defined($xpl_socket)) && ($xpl_end == 0) ) {
                                                 # check time and send heartbeat
  $last_heartbeat_time = xpl_send_heartbeat(
    $xpl_socket, $xpl_id, $xpl_ip, $client_port,
    $heartbeat_interval, $last_heartbeat_time
  );
                                              # get xpl-UDP message with timeout
  my ($xpl_message) = xpl_get_message($xpl_socket, $timeout);
  if ($xpl_message) {
    my ($type, $source, $target, $schema, %body) = xpl_get_message_elements($xpl_message);
    if ( xpl_is_for_me($xpl_id, $target) ) {
                                                              # process commands
      if ($schema eq "$class_id.basic") {
        if ($type eq 'xpl-cmnd') {
          if ($verbose > 0) {
            print("\n");
            print("Received command from \"$source\"\n");
          }
          my ($command, $room, $kind, $object, $value) = parse_command(
            $verbose,
            %body
          );
          if ($command) {
            if ($verbose > 0) {
              print($indent . "Command is \"$command\"\n");
            }
                                                               # get state value
            if (($command eq 'ask') or ($command eq 'get')) {
              $value = get_state(
                $configuration{'stateFile'},
                $room, $kind, $object
              );
              xpl_send_message(
                $xpl_socket, $xpl_port,
                'xpl-stat', $xpl_id, $source, "$class_id.basic",
                (
                  'room' => $room,
                  'kind' => $kind,
                  'object' => $object,
                  'value' => $value
                )
              );
              if ($verbose > 0) {
                print($indent . "$object $kind in $room is \"$value\"\n");
              }
            }
                                                            # update state value
            elsif (($command eq 'update') or ($command eq 'set')) {
              if ($verbose > 0) {
                print($indent . "Updating $object $kind in $room to \"$value\"\n");
              }
              my $has_changed = update_state(
                $configuration{'stateFile'},
                $room, $kind, $object, $value
              );
                                                               # set state value
              if (($command eq 'set') and ($has_changed)) {
                if ($verbose > 0) {
                  print($indent . "Sending \"act\" message\n");
                }
#                 xpl_send_message(
#                   $xpl_socket, $xpl_port,
#                   'xpl-cmnd', $xpl_id, '*', "$class_id.basic",
#                   (
#                     'command' => 'act',
#                     'room' => $room,
#                     'kind' => $kind,
#                     'object' => $object,
#                     'value' => $value
#                   )
#                 );
              }
            }
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

xpl-homeState.pl - Interfaces to the home's state information

=head1 SYNOPSIS

xpl-homeState.pl [options]

=head1 DESCRIPTION

This xPL client receives xPL cmnd messages to update state information
or to provide state value.

The C<state.basic> command message contains the following items:

=over 8

=item B<command>

The command can be C<ask>, C<update> or C<set>.
Difference between C<update> and C<set> is that a C<set> command additionally
triggers an C<act> message for the central command interpreter.

=item B<room>

The room in which an object's state is monitored

=item B<kind>

kind can be C<lights>, C<shutters>, C<audio>, ...

=item B<object>

The object whoses state is monitored.

=item B<value>

In case the object's state has to be updated.

=back

The C<state.basic> stat message contains the following items:

=over 8

=item B<room>

The room in which an object's state is queried

=item B<kind>

kind can be C<lights>, C<shutters>, C<audio>, ...

=item B<object>

The object whoses state is queried.

=item B<state>

The requested object's state.

=back

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

=item B<-s file>

Specify the XML state file spec.

=back

=head1 TEST

Make sure you have an C<xpl-hub> running on the machine.

Make sure you have a valid state file.
Default file spec is C</home/control/Documents/Controls/state.xml>.

Start the home state interface:
C<./xpl-homeState.pl -v -n home>.

Start C<xpl-monitor.pl -v> in another terminal window.

Ask for state value:
C<xpl-send.pl -v -c state.basic command=ask room=study kind=lights object=ceiling>.

Change state value:
C<xpl-send.pl -v -c state.basic command=set room=study kind=lights object=ceiling value=off>.

Update state value:
C<xpl-send.pl -v -c state.basic command=update room=study kind=lights object=ceiling value=off>.

=head1 AUTHOR

Francois Corthay, DSPC

=head1 VERSION

2.1, 2012

=cut
