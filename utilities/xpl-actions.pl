#!/usr/bin/perl

use File::Basename;
use FindBin;                            # find the script's directory
use lib "$FindBin::Bin/../xPL-base";    # add path for common lib
use common;


################################################################################
# constants
#
$vendor_id = 'dspc';            # from xplproject.org
$device_id = 'actions';         # max 8 chars
$class_id = 'actions';          # max 8 chars

$separator = '-' x 80;
$separator2 = '=' x 80;
$indent = ' ' x 2;

#-------------------------------------------------------------------------------
# global variables
#
my %configuration;
$configuration{'baseDirectory'} = dirname($0) . '/actions';


################################################################################
# Input arguments
#
use Getopt::Std;
my %opts;
getopts('hvp:n:t:w:d:', \%opts);

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
    "${indent}-d dir  the directory containing the action scripts\n".
    "\n".
    "Launches scripts based on xPL messages.\n".
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

$configuration{'baseDirectory'} = $opts{'d'} || $configuration{'baseDirectory'};


################################################################################
# Internal functions
#

#-------------------------------------------------------------------------------
# Execute a command together with its arguments
#
sub execute_command {

  my ($base_directory, $verbose, %body) = @_;
                                                  # get command from xPL message
  my $action = $body{'command'};
                                                # get arguments from xPL message
  my $arguments = '';
  foreach $name (keys(%body)) {
    if ($body{$name} =~ m/\s/) {
      $body{$name} = "'$body{$name}'";
    }
    if ($name ne 'command') {
      if (length($name) == 1) {
        $arguments .= "-$name $body{$name} "
      } else {
        $arguments .= "--$name $body{$name} "
      }
    }
  }
  $arguments =~ s/\s\Z//;
                                                             # check for command
  if ($verbose > 0) {
    print $indent, "Received command: \"$action $arguments\"\n";
  }
  my $command_exists = 0;
  $action = "$base_directory/$action";
  if (-e $action) {
    $action = "$action $arguments";
    $command_exists = 1;
    system("$action >/dev/null 2>&1 &");
  }
                                                                  # display info
  if ($verbose > 0) {
    if ($command_exists == 0) {
      print $indent x 2, "command not found\n";
    }
    else {
      print $indent x 2, "executed $action\n";
    }
    print "\n";
  }
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
if ($verbose > 0) {
  system("clear");
  print("$separator\n");
  print "Ready to launch commands based on xPL messages.\n";
  print($indent . "class id: $class_id\n");
  print($indent . "xPL id: $xpl_id\n");
  print($indent . "actions directory: \"$configuration{'baseDirectory'}\"\n");
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
                                                           # process XPL message
  if ($xpl_message) {
    my ($type, $source, $target, $schema, %body) = xpl_get_message_elements(
      $xpl_message
    );
    if ($schema eq "$class_id.basic") {
      if ( xpl_is_for_me($xpl_id, $target) ) {
        if ($type eq 'xpl-cmnd') {
                                                               # process command
          if ($verbose > 0) {
            print("\n");
            print("Received command from \"$source\"\n");
          }
          my $command = $body{'command'};
          if ($command) {
            if ($verbose > 0) {
              print($indent . "Command is \"$command\"\n");
            }
                                                               # execute command
            execute_command($configuration{'baseDirectory'}, $verbose, %body);
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

xpl-actions.pl - Launches scripts based on xPL messages

=head1 SYNOPSIS

xpl-actions.pl [options]

=head1 DESCRIPTION

This xPL client receives xPL messages to launch commands
found in a specific directory.

The C<action.basic> command messages contain following items:

=over 8

=item B<command>

The name of the command to be launched.

=item param=value

parameter/values pairs.

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

=item B<-d str>

Specify the directory in which the commands are found.

=back

=head1 TEST

Make sure you have the corresponding scripts in the actions directory.

Start the actions launcher:
C<xpl-actions.pl -v -n computer_name>.

You should see messages to the C<xpl-actions.pl>
each time a telegram is sent.

Launch a simple command:
C<xpl-send.pl -v -c actions.basic command=play.bash>.
Launch a command with a short parameter:
C<xpl-send.pl -v -c actions.basic command=play.bash f=pop.wav>.
Launch a command with full parameters:
C<xpl-send.pl -v -c actions.basic command=openJalousie.bash room=study shutter=window pulses=5>.

=head1 AUTHOR

Francois Corthay, DSPC

=head1 VERSION

2.0, 2012

=cut
