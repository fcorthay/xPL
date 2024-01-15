#!/usr/bin/perl

use FindBin;                    # find the script's directory
use lib $FindBin::Bin;          # add that directory to the library path
use xPL::common;


################################################################################
# constants
#
$vendor_id = 'dspc';             # from xplproject.org
$device_id = 'sender';           # max 8 chars
#$class_id = 'sender';            # max 8 chars

$separator = '-' x 80;
$indent = ' ' x 2;

################################################################################
# Input arguments
#
use Getopt::Std;
my %opts;
getopts('hvp:n:t:s:d:c:', \%opts);

die("\n".
    "Usage: $0 [options] [message body]\n".
    "\n".
    "Options:\n".
    "${indent}-h       display this help message\n".
    "${indent}-v       verbose\n".
    "${indent}-p port  the base UDP port\n".
    "${indent}-n id    the instance id (max. 16 chars)\n".
    "${indent}-t type  the message type identifier (cmnd, stat or trig)\n".
    "${indent}-s src   the message source (vendor_id-device_id.instance_id)\n".
    "${indent}-d dest  the message destination (vendor_id-device_id.instance_id)\n".
    "${indent}-c class the message class (class_id.type_id)\n".
    "\n".
    "Monitors xPL messages.\n".
    "\n".
    "More information with: perldoc $0\n".
    "\n".
    ""
   ) if ($opts{h});
my $verbose = $opts{v};
my $client_base_port = $opts{'p'} || 50000;

my $xpl_type = $opts{'t'} || 'cmnd';

my $instance_id = $opts{'n'} || xpl_build_automatic_instance_id;

my $xpl_source = $opts{'s'} || $vendor_id . '-' . $device_id . '.' .
          xpl_trim_instance_name($instance_id);

my $xpl_target = $opts{'d'} || '*';

my $xpl_class = $opts{'c'} || 'hbeat.app';

my %xpl_body = (sender => "\"$0\"");
if (@ARGV) {
  %xpl_body = ();
  foreach my $item (@ARGV) {
    my ($key, $value) = split(/=/, $item);
    $xpl_body{$key} = $value;
  }
}


################################################################################
# Main script
#
if ($verbose > 0) {
  print "\nSending xPL message as \"$xpl_source\" to \"$xpl_target\"\n";
}
my $xpl_ip = xpl_find_ip;

#-------------------------------------------------------------------------------
# test xPL message type
#
if ($xpl_type =~ m/(cmnd|stat|trig)/) {
  $xpl_type = "xpl-$xpl_type";
}
else {
  die "\"$xpl_type\" is not a valid xPL message type.\n";
}


#-------------------------------------------------------------------------------
# test xPL source tag
#
if ($xpl_source !~ m/\A(\w|\d)+-(\w|\d)+\.(\w|\d)+\Z/) {
  die "\"$xpl_source\" is not a valid xPL source indentifier.\n";
}


#-------------------------------------------------------------------------------
# test xPL target tag
#
if ($xpl_target !~ m/\A(\w|\d)+-(\w|\d)+\.(\w|\d)+\Z/) {
  if ($xpl_target ne '*') {
    die "\"$xpl_target\" is not a valid xPL target indentifier.\n";
  }
}


#-------------------------------------------------------------------------------
# test xPL class tag
#
if ($xpl_class !~ m/\A(\w|\d)+\.(\w|\d)+\Z/) {
  die "\"$xpl_class\" is not a valid xPL message class indentifier.\n";
}


#-------------------------------------------------------------------------------
# create xPL socket
#
my ($client_port, $xpl_socket) = xpl_open_socket($xpl_port, $client_base_port);
if ($verbose > 0) {
  print "${indent}Started UDP socket on port $client_port\n";
}


#-------------------------------------------------------------------------------
# send message
#
if ($verbose > 0) {
  print "${indent}Sending \"". join(', ', @ARGV) . "\"\n\n";
}

xpl_send_message(
  $xpl_socket, $xpl_port,
  $xpl_type, $xpl_source, $xpl_target, $xpl_class,
  %xpl_body
);


close($xpl_socket);


################################################################################
# Documentation (access it with: perldoc <scriptname>)
#
__END__

=head1 NAME

xpl-send.pl - Sends an xPL messages

=head1 SYNOPSIS

xpl-send.pl [options] message

=head1 DESCRIPTION

This xPL client sends an xPL message.

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

=item B<-t type>

Specify the message type identifier.
This must be one of: C<cmnd, stat or trig>.
If not specified, the type will be C<cmnd>.

=item B<-s src>

Specify the message source.
The source is in the form C<vendor_id-device_id.instance_id>.

=item B<-d dest>

Specify the message destination.
The destination is in the form C<vendor_id-device_id.instance_id> or is C<*>.

=item B<-c class>

Specify the message class.
The class is in the form C<class_id.type_id>.

=back

=head1 USAGE

Make sure you have an C<xpl-hub> running on the machine.

In a terminal, start a monitor:
C<xpl-monitor.pl -v>.

In another terminal, send a message:
C<xpl-send.pl -v hello=boy time=12>
and watch the output on the xPL monitor.

=head1 AUTHOR

Francois Corthay, DSPC

=head1 VERSION

2.0, 2012

=cut
