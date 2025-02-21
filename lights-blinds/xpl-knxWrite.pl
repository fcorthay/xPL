#!/usr/bin/perl

use FindBin;                            # find the script's directory
use lib "$FindBin::Bin/../xPL-base";    # add path for common lib
use common;


################################################################################
# constants
#
$vendor_id = 'dspc';            # from xplproject.org
$device_id = 'knx';             # max 8 chars
$class_id = 'knx';              # max 8 chars

$separator = '-' x 80;
$indent = ' ' x 2;

#-------------------------------------------------------------------------------
# global variables
#
my %configuration;
$configuration{'writeCommand'} = '/usr/bin/knxtool groupswrite';
$configuration{'server'} = 'ip:localhost';
$configuration{'logFile'} = '/tmp/knxWrite.log';
$configuration{'logFileLength'} = 100;


################################################################################
# Input arguments
#
use Getopt::Std;
my %opts;
getopts('hvp:n:s:t:w:s:c:', \%opts);

die("\n".
    "Usage: $0 [options]\n".
    "\n".
    "Options:\n".
    "${indent}-h      display this help message\n".
    "${indent}-v      verbose\n".
    "${indent}-p port the base UDP port\n".
    "${indent}-n id   the instance id (max. 12 chars)\n".
    "${indent}-t mins the heartbeat interval in minutes\n".
    "${indent}-w secs the startup sleep interval\n".
    "${indent}-s url  the server URL\n".
    "${indent}-c cmd  the knxd groupswrite command\n".
    "${indent}-l file the log file\n".
    "${indent}-z size the maximal log file line number\n".
    "\n".
    "Writes KNX commands upon receipt of xPL messages.\n".
    "\n".
    "More information with: perldoc $0\n".
    "\n".
    ""
   ) if ($opts{h});
$verbose = $opts{'v'};
my $client_base_port = $opts{'p'} || 50000;
my $instance_id = $opts{'n'} || xpl_build_automatic_instance_id;
my $heartbeat_interval = $opts{'t'} || 5;
my $startup_sleep_time = $opts{'w'} || 0;

$configuration{'server'} = $opts{'s'} || $configuration{'server'};
$configuration{'writeCommand'} = $opts{'c'} || $configuration{'writeCommand'};
$configuration{'logFile'} = $opts{'l'} || $configuration{'logFile'};
$configuration{'logFileLength'} = $opts{'z'} || $configuration{'logFileLength'};


################################################################################
# Internal functions
#

#-------------------------------------------------------------------------------
# Translate an xPL command body to the corresponding knxd write command
#
sub build_knxd_command {
  my ($configuration_ref, %body) = @_;
  my $message_OK = 1;
                                                               # group address
  my $group_address = $body{'group'};
  if ($group_address eq '') {
    $message_OK = 0;
  }
                                                                        # data
  my $data = $body{'data'};
  if ($data eq '') {
    $message_OK = 0;
  }
  $data =~ s/0x//g;
                                                          # build command string
  my $command = "$$configuration_ref{'writeCommand'} $$configuration_ref{'server'}";
  $command .= " $group_address $data > /dev/null";
  if ($message_OK == 0) {
    $command = '';
  }
#print "message: $command\n";

  return($command)
}

#-------------------------------------------------------------------------------
# Log a groupswrite message
#
sub log_knxd_command {

  my ($message, $log_file, $log_file_length) = @_;
                                                               # read log file
  my @lines;
  if (-e $log_file) {
    open (LOG_FILE, "< $log_file") or die "Can't open log file for read: $!";
      @lines = <LOG_FILE>;
    close LOG_FILE or die "Cannot close log file: $!"; 
  }
                                                              # append message
  push(@lines, $message);
                                                               # trim log file
  my $line_nb = scalar @lines;
  if ($line_nb > $log_file_length) {
    splice(@lines, 0, $log_file_length-$line_nb+2);
  }
                                                              # write log file
  open (LOG_FILE, "> $log_file") or die "Can't open log file for write: $!";
  print LOG_FILE  (join('', @lines), "\n");
  close LOG_FILE or die "Cannot close log file: $!"; 
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
  print "Controlling the knxd daemon \"$configuration{'server'}\".\n";
  print($indent . "class id: $class_id\n");
  print($indent . "xPL client id: $xpl_id\n");
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
    if ( xpl_is_for_me($xpl_id, $target) ) {
                                                              # process commands
      if ($schema eq "$class_id.basic") {
        if ($type eq 'xpl-cmnd') {
                                                               # log xPL message
          my ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) =
            localtime(time);
          my $timestamp = sprintf(
            "%02d.%02d.%04d %02d:%02d:%02d",
            $mday, $mon+1, $year+1900, $hour, $min, $sec
          );
          log_knxd_command(
            "$timestamp : $body{'group'} > $body{'data'}",
            $configuration{'logFile'}, $configuration{'logFileLength'}
          );
          if ($verbose > 0) {
            print("Received command from \"$source\"\n");
          }
          my $command = build_knxd_command(\%configuration, %body);
          if ($command) {
            if ($verbose == 1) {
              print($indent . "sending \"$command\"\n");
            }
                                                              # log bash command
            log_knxd_command(
              "$indent$command",
              $configuration{'logFile'}, $configuration{'logFileLength'}
            );
            system("$command");
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

xpl-knxWrite.pl - Interfaces an EIB/KNX IP router for EIB control

=head1 SYNOPSIS

xpl-knxWrite.pl [options]

=head1 DESCRIPTION

This xPL client translates xPL messages in order to send KNX telegrams
via C<groupswrite>.

The C<knx.basic> command and trigger messages contain following items:

=over 8

=item B<source>

Telegram source address, only for trigger messages.

=item B<group>

Group address.

=item B<data>

The data (or value) associated to the group address.

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

=item B<-s url>

Specify the C<knxd> URL.

=item B<-c cmd>

Specify the executable C<groupswrite>.

=back

=head1 TEST

Make sure you have an C<xpl-hub> and C<knxd> running on the machine.

Start the the xPL KNX writer:
C<SCRIPTS_BASE_DIR=/home/control/Documents/Controls>
C<$SCRIPTS_BASE_DIR/xpl-knxWrite.pl -v -n home>.

Turn light C<1/1/1> on:
C<SCRIPTS_BASE_DIR=/home/control/Documents/Controls>
C<$SCRIPTS_BASE_DIR/xpl-send.pl -v -t cmnd -d dspc-knx.home -c knx.basic group='1/1/1' data=0x01>.

Turn light C<1/1/1> of:
C<$SCRIPTS_BASE_DIR/xpl-send.pl -v -t cmnd -d dspc-knx.home -c knx.basic group='1/1/1' data=0x00>.

=head1 AUTHOR

Francois Corthay, DSPC

=head1 VERSION

1.0, 2014

=cut
