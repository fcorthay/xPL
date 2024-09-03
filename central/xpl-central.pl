#!/usr/bin/perl

use Data::Dumper;
use XML::Simple;
use Time::HiRes qw(usleep);

use FindBin;                            # find the script's directory
use lib "$FindBin::Bin/../xPL-base";    # add path for common lib
use common;

################################################################################
# constants
#
$vendor_id = 'dspc';            # from xplproject.org
$device_id = 'central';         # max 8 chars
$class_id = 'central';          # max 8 chars

$separator = '-' x 80;
$indent = ' ' x 2;

#-------------------------------------------------------------------------------
# global variables
#
my %configuration;
$configuration{'actionsFileSpec'} = '/home/control/Controls/xPL/central/centralActions.xml';
$configuration{'reloadFile'} = 0;
$configuration{'logFile'} = '/tmp/xpl.log';
$configuration{'logFileLength'} = 1000;

################################################################################
# Input arguments
#
use Getopt::Std;
my %opts;
getopts('hvp:n:t:w:a:rl:', \%opts);

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
    "${indent}-a file the XML actions file spec\n".
    "${indent}-r      reload file at each message interpretation\n".
    "${indent}-l file the log file\n".
    "${indent}-z size the maximal log file line number\n".
    "\n".
    "Parses xPL messages and takes appropriate actions.\n".
    "\n".
    "More information with: perldoc $0\n".
    "\n".
    ""
   ) if ($opts{'h'});

my $verbose = $opts{'v'};
my $client_base_port = $opts{'p'} || 50000;
my $startup_sleep_time = $opts{'w'} || 0;

my $instance_id = $opts{'n'} || xpl_build_automatic_instance_id;
my $heartbeat_interval = $opts{'t'} || 5;

$configuration{'actionsFileSpec'} = $opts{'a'} || $configuration{'actionsFileSpec'};
$configuration{'reloadFile'} = $opts{'r'} || $configuration{'reloadFile'};
$configuration{'logFile'} = $opts{'l'} || $configuration{'logFile'};
$configuration{'logFileLength'} = $opts{'z'} || $configuration{'logFileLength'};

################################################################################
# Internal functions
#

#-------------------------------------------------------------------------------
# Log an xPL message
#
sub log_xpl_message {
  my ($log_file, $log_file_length, $type, $source, $target, $schema, %body) = @_;
  my $delimiter1 = '_';
  my $delimiter2 = '_';
                                                               # read log file
  my @lines;
  if (-e $log_file) {
    open (LOG_FILE, "< $log_file") or die "Can't open log file for read: $!";
      @lines = <LOG_FILE>;
    close LOG_FILE or die "Cannot close log file: $!"; 
  }
                                                              # append message
  my ($sec, $min, $hour) = localtime();
  my $message = sprintf('%02d:%02d:%02d ', $hour, $min, $sec);
  $message .= join($delimiter1, ($type, $source, $target, $schema));
  $message =~ s/\*/any/g;
  foreach my $key (keys(%body)) {
#print "  $key=$body{$key}\n";
    if ($body{$key} =~ m/\s/) {
      $body{$key} = "'$body{$key}'";
    }
    $message .= "$delimiter1$key$delimiter2$body{$key}";
  }
#print "$message\n";
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

#-------------------------------------------------------------------------------
# Compare xPL message with command list and build actions list
#
sub interpret_message {
  my ($actions_file, $type, $source, $target, $schema, %body) = @_;
                                                          # get XML actions list
  my $list_ref = $actions_file;
  if (ref($list_ref) ne 'HASH') {
    $list_ref = XMLin($actions_file);
  }
#print Dumper($list_ref);
  my $actions_ref = {};
  foreach my $key (keys(%$list_ref)) {
    my $additional_actions_ref = $$list_ref{$key};
    %$actions_ref = (%$actions_ref, %$additional_actions_ref);
  }
#print Dumper($actions_ref);
                                                              # match xPL header
  my @actions = ();
  foreach my $mask (keys(%$actions_ref)) {
#print "$mask\n";
    my $matches = 1;
    my @fields = split(/_/, $mask, 5);
    if ( ($fields[0] ne 'any') and (lc($fields[0]) ne lc($type)) ) {
      $matches = 0;
    }
#print "|$fields[0]| matches $type: $matches\n";
    if ( ($fields[1] ne 'any') and (lc($fields[1]) ne lc($source)) ) {
      $matches = 0;
    }
    if ( ($fields[2] ne 'any') and (lc($fields[2]) ne lc($target)) ) {
      $matches = 0;
    }
                                                              # match xPL schema
    if ( ($fields[3] ne 'any') and (lc($fields[3]) ne lc($schema)) ) {
      $matches = 0;
    }
#print "  $fields[0]_$fields[1]_$fields[2]_$fields[3] matches ${type}_${source}_${target}_$schema: $matches\n";
                                                                # match xPL data
#if ($fields[3] eq 'radio') { print "$fields[4]\n";}
    my %fields = split(/_/, $fields[4]);
    foreach my $name (keys(%fields)) {
      my $to_compare = $body{$name};
#      $to_compare =~ s/\//./g;
                                     # allow replacements in the xPL value field
      $to_compare =~ s/ /\.x20/g;                          # '.x20' replaces ' '
      $to_compare =~ s/\-/\.x2D/g;                         # '.x2D' replaces '-'
#print "    $name -> $fields{$name}  <-> $to_compare \n";
      if ($fields{$name} ne $to_compare) {
        $matches = 0;
      }
#print "  matches: $matches\n";
    }
                                                           # add actions to list
    if ($matches != 0) {
                                                    # replace elements from body
      my $action = $$actions_ref{$mask} . '|';
#print "  -> action: $action\n";
      while ($action =~ m/\$(.*?)[\s\|]/) {
        my $target = $1;
        my $replacement = $body{$target};
        $action =~ s/\$$target/$replacement/;
      }
      $action =~ s/\|\Z//;
                                                           # add actions to list
      push(@actions, split(/\|/, $action));
    }
  }

  return(@actions);
}

#-------------------------------------------------------------------------------
# Sleep a given amount of time between 2 commands to be executed
#
sub sleep_delay {
  my ($delay, $unit) = @_;
                                                          # interpret time units
  if ($unit eq 'ms') {
    $delay = $delay * 1E3;
  }
  elsif ($unit eq 's') {
    $delay = $delay * 1E6;
  }
  elsif ($unit eq 'sec') {
    $delay = $delay * 1E6;
  }
                                                             # sleep given delay
print "sleeping $delay\n";
  usleep($delay);
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
  print("Starting xPL central message parser.\n");
  print($indent . "class id: $class_id\n");
  print($indent . "xPL id: $xpl_id\n");
  print($indent . "actions file: \"$configuration{'actionsFileSpec'}\"\n");
	print("\n");
}

#-------------------------------------------------------------------------------
# Main loop
#
my $timeout = 1;
my $last_heartbeat_time = 0;
my $list_ref = XMLin($configuration{'actionsFileSpec'});


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
    if ($schema ne 'hbeat.app') {
      if ($verbose >  0) {
        print("Received: $type\_$source\_$target\_$schema\n");
      }
                                                                   # log message
      if ($configuration{'logFileLength'} >  0) {
        log_xpl_message(
          $configuration{'logFile'}, $configuration{'logFileLength'},
          $type, $source, $target, $schema, %body
        );
      }
                                                              # get actions list
      my $file_parameter = $list_ref;
      if ($configuration{'reloadFile'}) {
        $file_parameter = $configuration{'actionsFileSpec'};
      }
      my @actions = interpret_message($file_parameter, $type, $source, $target, $schema, %body);
      foreach my $action (@actions) {
        if ($verbose >  0) {
          print($indent . "executing: $action\n");
          print("\n");
        }
                                                   # get type, target and schema
        my @command = split(/ /, $action, 4);
                                             # replace last space with separator
#print "$command[3]\n";
        my @elements = split(/=/, "$command[3] ");
        foreach my $element (@elements) {
          $element =~ s/\s(\S*?)\Z/|$1/;
        }
        $command[3] = join('=', @elements);
        $command[3] =~ s/\|\Z//;
#print "$command[3]\n";
                                                            # build command list
        my @elements = split(/\|/, $command[3]);
        my %command = ();
        foreach my $element (@elements) {
          my ($parameter, $value) = split(/=/, $element);
#          $value =~ s/_/ /g;
          $command{$parameter} = $value;
#print "-> to send: $parameter=$command{$parameter}\n";
        }
                                                                  # sleep action
        if ($command[0] eq 'sleep') {
          sleep_delay($command[1], $command[2]);
        }
                                                                   # xPL actions
        else {
          my $type = shift(@command);
          my $target = shift(@command);
          my $schema = shift(@command);
          xpl_send_message(
            $xpl_socket, $xpl_port,
            $type, $xpl_id, $target, $schema,
            %command
          );
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

xpl-central.pl - Parses xPL messages and takes appropriate actions

=head1 SYNOPSIS

xpl-central.pl [options]

=head1 DESCRIPTION

This xPL client examines all xPL messages it receives
and matches them with XML data from a file.
If a match is found, one or more xPL messages are sent as specified in the XML.
Sleep commands can be inserted between xPL messages to send.

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

=item B<-a file>

Specify the the XML actions file spec.
This file contains a list of xPL messages to trigger to
and a list of command associated to each trigger.
Default value is: C</home/control/Documents/Controls/centralActions.xml>.

=item B<-r>

Tell the script to reload the action file information at each new message to be parsed.

=item B<-l file>

Specify the log file spec.

=item B<-z size>

Specify the log file maximal number of lines.

=back

=head1 TEST

Make sure you have an C<xpl-hub> running on the machine.

Start the central controller:
C<xpl-central.pl -v>
and watch the output.

Send a trigger command:
C<xpl-send.pl -v -t stat -c clock.tick time=17h20>.

=head1 AUTHOR

Francois Corthay, DSPC

=head1 VERSION

2.2, 2015

=cut
