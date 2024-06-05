#!/usr/bin/perl

use FindBin;                            # find the script's directory
use lib "$FindBin::Bin/../xPL-base";    # add path for common lib
use common;


################################################################################
# constants
#
$vendor_id = 'dspc';            # from xplproject.org
$device_id = 'screen';          # max 8 chars
$class_id = 'screen';           # max 8 chars

$separator = '-' x 80;
$indent = ' ' x 2;

#-------------------------------------------------------------------------------
# global variables
#
my %configuration;
$configuration{'server'} = '192.168.1.100';
$configuration{'key'} = 1234;


################################################################################
# Input arguments
#
use Getopt::Std;
my %opts;
getopts('hvp:n:t:w:s:k:', \%opts);

die("\n".
    "Usage: $0 [options]\n".
    "\n".
    "Options:\n".
    "${indent}-h        display this help message\n".
    "${indent}-v        verbose\n".
    "${indent}-p port   the base UDP port\n".
    "${indent}-n id     the instance id (max. 12 chars)\n".
    "${indent}-t mins   the heartbeat interval in minutes\n".
    "${indent}-w secs   the startup sleep interval\n".
    "${indent}-s server the screen's server name\n".
    "${indent}-k PSK    the screen's server Pre-Shared Key\n".
    "\n".
    "Controls a Sony Bravia screen.\n".
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

$configuration{'server'} = $opts{'s'} || $configuration{'server'};
$configuration{'key'} = $opts{'k'} || $configuration{'key'};


################################################################################
# Internal functions
#

#-------------------------------------------------------------------------------
# Translate a command to the corresponding crontrols for the serial port client
#
sub build_screen_control {

  my (%body) = @_;
  my $method = '';
  my $parameter = '';
  my $service = '';
  my @commands = ();
                                                            # interpret commands
  foreach $control (keys(%body)) {
    my $value = lc($body{$control});
#print "$control -> \"$value\"\n";
                                                                         # power
    if ($control eq 'power') {
      $service = 'system';
      $method = 'setPowerStatus';
      if ($value eq 'off') {
        $parameter = '{"status": false}';
      } else {
        $parameter = '{"status": true}';
      }
    }
                                                                  # input source
    elsif ($control eq 'input') {
      $service = 'avContent';
      $method = 'setPlayContent';
      if ($value =~ /hdmi\d/) {
        my $port = chop($value);
        $parameter = "{uri: \"extInput:hdmi?port=$port\"}";
      }
      elsif ($value =~ /component\d/) {
        $parameter = '{uri: "extInput:component?port=1"}';
      }
      elsif ($value =~ /video\d/) {
        $parameter = '{uri: "extInput:composite?port=1"}';
      }
      elsif ($value eq 'cast') {
        $parameter = '{uri: "extInput:widi?port=1"}';
      }
    }
    push(@commands, {
      'method' => $method, 'parameter' => $parameter, 'service' => $service
    });
  }

  return(@commands)
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
  print("Controlling a Sony Bravia screen.\n");
  print($indent . "class id: $class_id\n");
  print($indent . "instance id: $instance_id\n");
	print("\n");
}


#-------------------------------------------------------------------------------
# Main loop
#
my $timeout = 1;
my $last_heartbeat_time = 0;
my $procedure_call_id = 1;

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
    my (
      $type, $source, $target, $schema, %body
    ) = xpl_get_message_elements($xpl_message);
    if ($schema eq "$class_id.basic") {
      if ($type eq 'xpl-cmnd') {
        if ( xpl_is_for_me($xpl_id, $target) ) {
                                                              # process commands
          my $command = $body{'command'};
          if ($verbose > 0) {
            print("\n");
            print("Received command from \"$source\"\n");
          }
          my @commands = build_screen_control(%body);
          if (@commands ne ()) {
            foreach $command (@commands) {
              if ($verbose == 1) {
                print(
                  $indent,
                  "sending $command->{'method'}($command->{'parameter'})\n"
                );
              }
              my $system_command = 'curl -s';
              $system_command .= ' -H "Content-Type: application/json"';
              $system_command .= " -H \"X-Auth-PSK: $configuration{'key'}\"";
              $system_command .= ' -d \'{"version": "1.0"';
              $system_command .= ", \"id\": $procedure_call_id";
              $system_command .= ", \"method\": \"$command->{'method'}\"";
              $system_command .= ", \"params\": [$command->{'parameter'}]";
              $system_command .= '}\'';
              $system_command .= " http://$configuration{'server'}";
              $system_command .= "/sony/$command->{'service'}";
# print("$system_command\n");
              my $response = `$system_command`;
              if ($verbose == 1) {
                print($indent x 2, "-> $response\n");
              }
              $procedure_call_id = ($procedure_call_id + 1) % 100;
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

xpl-screen-bravia.pl - Controls a Sony Bravia screen

=head1 SYNOPSIS

xpl-screen-bravia.pl [options]

=head1 DESCRIPTION

This xPL client sends commands to an C<xPL-serial_port>
in order to control a Sony Bravia screen.

The C<screen.basic> commands allow to control following items:

=over 8

=item B<power>

Can be C<on> or C<toggle>.

=item B<input>

Can be C<hdmi*>, C<component*>, C<video*> or C<tv>.

=back

=head1 OPTIONS

=over 8

=item B<-h>

Display a help message.

=item B<-v>

Be verbose.

=item B<-n id>

Specify the instance id (name).
The id is limited to 12 characters.
If not specified, it is constructed from the host name and the serial port controller name.

=item B<-c script>

Specify the C<bravia_console> script name with its path.

=item B<-t mins>

Specify the number of minutes between two heartbeat messages.

=item B<-w secs>

Specify the number of seconds before sending the first heartbeat.
This allows to start the client after the hub,
thus eliminating an prospective startup delay of one heartbeat interval.

=back

=head1 TEST

Make sure you have an C<xpl-hub> running on the machine.

Start the screen controller:
C<xpl-screen-bravia.pl -v -n loungeScreen>.

Start C<xpl-logger -v> in another terminal window.

Power the screen off with the remote control and launch the command
C<xpl-send.pl -d dspc-screen.loungeScreen -c screen.basic power=on>.
The screen should power on.

=head1 AUTHOR

Francois Corthay, DSPC

=head1 VERSION

2.0, 2018

=cut
