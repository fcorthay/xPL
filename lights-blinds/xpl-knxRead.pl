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
$configuration{'server'} = 'ip:localhost';
$configuration{'logFile'} = '/tmp/knx.log';
$configuration{'logFileLength'} = 100;


################################################################################
# Input arguments
#
use Getopt::Std;
my %opts;
getopts('hvp:n:s:t:w:s:l:z:', \%opts);

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
    "${indent}-s str  the server URL\n".
    "${indent}-l file the log file\n".
    "${indent}-z size the maximal log file line number\n".
    "\n".
    "Forwards EIB/KNX IP messages to xPL.\n".
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
$configuration{'logFile'} = $opts{'l'} || $configuration{'logFile'};
$configuration{'logFileLength'} = $opts{'z'} || $configuration{'logFileLength'};


################################################################################
# Internal functions
#

#-------------------------------------------------------------------------------
# Parse a groupsocketlisten message and build the xPL message body
#
sub parse_knxd_status {

  my ($message) = @_;
  my %body;
                                                             # analyse message
#print "message: <$message>\n";
  $message =~ s/.*write from\s*//i;
  $message =~ s/\s*to\s*/ /i;
  $message =~ s/\s*:\s*/ /i;
#print "message: <$message>\n";
  my ($source_address, $group_address, $data) = split(/\s+/, $message, 3);
                                          # write adresses with leading zeroes
  my @source_address = split(/\./, $source_address, 3);
  $source_address = sprintf('%02d.%02d.%03d', @source_address);
  $group_address =~ s/\//./g;
  my @group_address = split(/\./, $group_address, 3);
  $group_address = sprintf('%02d.%02d.%03d', @group_address);
                                                  # write data with leading 0x
  $data = "0x$data";
                                                              # build xPL body
  if ($source_address ne '0.0.0') {
    %body = (
      'source' => $source_address,
      'group'  => $group_address,
      'data'   => $data
    );
  }

  return(%body)
}

#-------------------------------------------------------------------------------
# Log a groupsocketlisten message
#
sub log_knxd_message {

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
  print "Reading EIB/KNX messages from \"$configuration{'server'}\".\n";
  print($indent . "class id: $class_id\n");
  print($indent . "xPL client id: $xpl_id\n");
	print("\n");
}

#-------------------------------------------------------------------------------
# Main loop
#
my $timeout = 1;
my $last_heartbeat_time = 0;

while ($xpl_end == 0) {
                                                                   # get message
  chomp( my $message =  <STDIN>);
  if ($verbose == 1) {
    print "Received: $message\n";
  }
                                                                   # log message
  log_knxd_message(
    $message,
    $configuration{'logFile'}, $configuration{'logFileLength'}
  );
                                                                 # parse message
  my %body = parse_knxd_status($message);
  if ($verbose == 1) {
    print "${indent}sending: $body{'source'} $body{'group'} $body{'data'}\n";
  }
                                                              # send xPL message
  if ($body{'source'} ne '00.00.000') {
    xpl_send_message(
      $xpl_socket, $xpl_port,
      'xpl-trig', $xpl_id, '*', "$class_id.basic",
      %body
    );
  }
}

close($xpl_socket);


################################################################################
# Documentation (access it with: perldoc <scriptname>)
#
__END__

=head1 NAME

xpl-knxRead.pl.pl - Interfaces an EIB/KNX IP router for EIB control

=head1 SYNOPSIS

knxtool groupsocketlisten ip:localhost | XPL_BASE_DIR/lights-blinds/xpl-knxRead.pl [options]

=head1 DESCRIPTION

This xPL client translates xPL messages from the C<groupsocketlisten>
output in order to send KNX telegrams.

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

=item B<-s str>

Specify the C<groupsocketlisten> server URL.

=item B<-l file>

Specify the log file spec.

=item B<-z size>

Specify the log file maximal number of lines.

=back

=head1 TEST

Make sure you have an C<xpl-hub> and C<knxd> running on the machine.

Start an xPL monitor:
C<SCRIPTS_BASE_DIR=/home/control/Documents/Controls>
C<$SCRIPTS_BASE_DIR/xpl-monitor.pl -vf>.

Start the xPL KNX reader:
C<SCRIPTS_BASE_DIR=/home/control/Documents/Controls>
C<knxtool groupsocketlisten ip:localhost | $SCRIPTS_BASE_DIR/xpl-knxRead.pl -v -n home>.

Push on a KNX button and see the results in both windows.

=head1 AUTHOR

Francois Corthay, DSPC

=head1 VERSION

1.0, 2014

=cut
