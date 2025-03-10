#!/usr/bin/perl

use Net::Telnet;
use FindBin;                            # find the script's directory
use lib "$FindBin::Bin/../xPL-base";    # add path for common lib
use common;


################################################################################
# constants
#
$vendor_id = 'dspc';            # from xplproject.org
$device_id = 'ampDenon';        # max 8 chars
$class_id = 'media';            # max 8 chars
$tty_name_length = 4;

$separator = '-' x 80;
$indent = ' ' x 2;

#-------------------------------------------------------------------------------
# global variables
#
my %configuration;
$configuration{'ipAddress'} = '192.168.1.205';


################################################################################
# Input arguments
#
use Getopt::Std;
my %opts;
getopts('hvn:t:w:a:', \%opts);

die("\n".
    "Usage: $0 [serial_port_device] [serial_port_settings]\n".
    "\n".
    "Parameters:\n".
    "${indent}-h      display this help message\n".
    "${indent}-v      verbose\n".
    "${indent}-n id   the instance id (max. 12 chars)\n".
    "${indent}-t mins the heartbeat interval in minutes\n".
    "${indent}-w secs the startup sleep interval\n".
    "${indent}-a addr the telnet IP address\n".
    "\n".
    "Controls a Denon AVR 3808 audio-video controller via Ethernet.\n".
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

$configuration{'ipAddress'} = $opts{'a'} || $configuration{'ipAddress'};


################################################################################
# Internal functions
#

#-------------------------------------------------------------------------------
# Open telnet communication channel
#
sub open_telnet {

  my ($ip_address) = @_;
                                                           # open telnet channel
  my $telnet_comm = new Net::Telnet (
    Binmode => 1,
    Telnetmode => 0,
    Timeout => 1,
    Input_record_separator => "\r",
    Output_record_separator => "\r",
    Errmode => 'return'
  );
  $telnet_comm->open($ip_address);

  return($telnet_comm)
}

#-------------------------------------------------------------------------------
# convert master volume (1 to 100) to AVR representation (0 to 99, dB)
#
sub master_volume_to_AVR {

  my ($volume) = @_;
                                                               # calculate value
  my $AVR_volume = sprintf('%02d', $volume-1);

  return($AVR_volume)
}

#-------------------------------------------------------------------------------
# convert AVR volume (0 to 99, dB) to xPL audio (1 to 100)
#
sub master_volume_from_AVR {

  my ($AVR_volume) = @_;
                                                               # calculate value
  my $volume = $AVR_volume+1;
  if ($volume >= 100) {
   $volume = $volume/10;
  }

  return($volume)
}

#-------------------------------------------------------------------------------
# Translate a command to the corresponding crontrols for the serial port client
#
sub build_amplifier_control {

  my (%body) = @_;
  my @commands = ();
                                                            # interpret commands
  foreach $control (keys(%body)) {
    my $value = lc($body{$control});
    $value =~ s/\Atv\Z/TV\/CBL/;
    $value =~ s/\Aaux\Z/V.AUX/;
    $value =~ s/\Anet\Z/NET\/USB/;
    $value =~ s/\Ausb\Z/NET\/USB/;
    $value =~ s/pure\Z/PURE DIRECT/i;
    $value =~ s/dolby\Z/DOLBY DIGITAL/i;
    $value =~ s/dts\Z/DTS SURROUND/i;
    $value =~ s/wide\Z/WIDE SCREEN/i;
    $value =~ s/7ch\Z/7CH STEREO/i;
    $value =~ s/rock\Z/ROCK ARENA/i;
    $value =~ s/jazz\Z/JAZZ CLUB/i;
    $value =~ s/classic\Z/CLASSIC CONCERT/i;
    $value =~ s/mono\Z/MONO MOVIE/i;
#print "$control -> \"$value\"\n";
                                                                         # power
    if ($control eq 'power') {
      if ($value eq 'on') {
        push(@commands, 'PWON');
      }
      elsif ($value eq 'off') {
        push(@commands, 'PWSTANDBY');
      }
      elsif ($value eq 'ask') {
        push(@commands, 'PW?');
      }
    }
                                                                          # mute
    if ($control eq 'mute') {
      if ($value eq 'on') {
        push(@commands, 'MUON');
      }
      elsif ($value eq 'off') {
        push(@commands, 'MUOFF');
      }
      elsif ($value eq 'ask') {
        push(@commands, 'MU?');
      }
    }
                                                                        # volume
    if ($control eq 'volume') {
      if ($value =~ m/\d+/) {
        push(@commands, 'MV' . master_volume_to_AVR($value));
      }
      elsif ($value eq 'ask') {
        push(@commands, 'MV?');
      }
    }
                                                                   # audio input
    if ($control eq 'audio') {
      if ($value eq 'ask') {
        push(@commands, 'SI?');
      }
      else {
        push(@commands, 'SI' . uc($value));
      }
    }
                                                                   # video input
    if ($control eq 'video') {
      if ($value eq 'ask') {
        push(@commands, 'SV?');
      }
      else {
        push(@commands, 'SV' . uc($value));
      }
    }
                                                                      # surround
    if ($control eq 'surround') {
      if ($value eq 'ask') {
        push(@commands, 'MS?');
      }
      else {
        push(@commands, 'MS' . uc($value));
      }
    }

  }

  return(@commands)
}

#-------------------------------------------------------------------------------
# Translate a AVR message to the corresponding status
#
sub build_status {

  my (@messages) = @_;
  my %status = ();
  foreach my $message (@messages) {
#print "message: $message\n";
                                                                         # power
    if ($message eq 'PWSTANDBY') {
      $status{'power'} = 'off';
    }
    elsif ($message eq 'PWON') {
      $status{'power'} = 'on';
    }
                                                                          # mute
    elsif ($message eq 'MUOFF') {
      $status{'mute'} = 'off';
    }
    elsif ($message eq 'MUON') {
      $status{'mute'} = 'on';
    }
                                                                        # volume
    elsif ($message =~ m/\Amv\d+/i) {
      my $volume = $message;
      $volume =~ s/\Amv//i;
      if ($volume !~ m /vmax/i) {
        $status{'volume'} = master_volume_from_AVR($volume);
      }
    }
                                                                   # audio input
    elsif ($message =~ m/\Asi/i) {
      my $input = lc($message);
      $input =~ s/\Asi//;
      $input =~ s/tv\/cbl/tv-cbl/;
      $status{'audio'} = $input;
    }
                                                                   # video input
    elsif ($message =~ m/\Asv/i) {
      my $input = lc($message);
      $input =~ s/\Asv//;
      $input =~ s/source/off/;
      $status{'video'} = $input;
    }
                                                                      # surround
    elsif ($message =~ m/\Ams/i) {
      my $input = lc($message);
      $input =~ s/\Ams//;
      $input =~ s/\s/_/g;
      $status{'surround'} = $input;
    }
  }

  return(%status)
}

#-------------------------------------------------------------------------------
# Send a command list from xPL to telnet communication channel
#
sub send_telnet_commands {

  my ($telnet_comm, @commands) = @_;
                                                                  # build string
  my $command = join("\r", @commands);
                                                            # write it to telnet
#print "$command\n";
  $telnet_comm->put("$command\r");
}


################################################################################
# Catch control-C interrupt
#
$SIG{INT} = sub{ $xpl_end++ };


################################################################################
# Main script
#
sleep($startup_sleep_time);
                                             # open telnet communication channel
my $telnet_comm = open_telnet($configuration{'ipAddress'});
                                                                # xPL parameters
my $xpl_id = xpl_build_id($vendor_id, $device_id, $instance_id);
my $xpl_ip = xpl_find_ip;
                                                             # create xPL socket
my ($client_port, $xpl_socket) = xpl_open_socket($xpl_port, $client_base_port);
                                                    # display working parameters
if ($verbose == 1) {
  system("clear");
  print("$separator\n");
  print("Controlling Denon AVR at $configuration{'ipAddress'}\n");
  print($indent, "instance id : $instance_id\n");
  print($indent, "IP address  : $configuration{'ipAddress'}\n");
  print("$separator\n");
}


#===============================================================================
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
#print "$xpl_message\n";
    my ($type, $source, $target, $schema, %body) = xpl_get_message_elements(
      $xpl_message
    );
    if ( xpl_is_for_me($xpl_id, $target) ) {
      if (lc($schema) eq lc("$class_id.basic")) {
        if ($type eq 'xpl-cmnd') {
                                                   # build command messages list
          my $command;
          foreach my $key (keys %body) {
            $command .= "$key: $body{$key}, ";
          }
          $command =~ s/,\s+\Z//;
          if ($verbose > 0) {
            print("\n");
            print("Received \"$command\" from \"$source\"\n");
          }
                                      # re-open telnet communication at power on
          if ($command eq 'power: on') {
            print($indent . "restarting Telnet connection\n");
            $telnet_comm->close;
#            sleep(1);
            $telnet_comm = open_telnet($configuration{'ipAddress'});
          }
          my @message = build_amplifier_control(%body);
                                                         # send command messages
          if ($verbose == 1) {
            print($indent . "sending \"@message\"\n");
          }
          send_telnet_commands($telnet_comm, @message);
        }
      }
    }
  }
  else {
                                                     # check if status available
    my $status = $telnet_comm->get(Timeout => 0.1);
    $status =~ s/\r\Z//;
    $status =~ s/\r/|/g;
    if (length($status) > 0) {
#print "-> $status\n";
      if ($verbose == 1) {
        print("${indent}Received \"$status\" from AV controller\n");
      }
      my @messages = split(/\|/, $status);
      my %status = build_status(@messages);
      if (keys %status) { 
        xpl_send_message(
          $xpl_socket, $xpl_port,
          'xpl-trig', $xpl_id, '*', "$class_id.response",
          %status
        );
      }
    }
  }
}

xpl_disconnect($xpl_socket, $xpl_id, $xpl_ip, $client_port);
                                            # close telnet communication channel
$telnet_comm->close;


################################################################################
# Documentation (access it with: perldoc <scriptname>)
#
__END__

=head1 NAME

xpl-avController-DenonAVR-telnet.pl - Controls a Denon AVR 3808 audio-video controller
via Ethernet

=head1 SYNOPSIS

xpl-avController-DenonAVR.pl [options]

=head1 DESCRIPTION

This xPL client sends Telnet commands to a Denon AV5103 audio/video controller.

The C<media.basic> commands allow to control following items:

=over 8

=item B<power=state>

Can have C<state=on>, C<state=off> or C<state=ask>.

=item B<mute= state>

Can have C<state=on>, C<state=off> or C<state=ask>.

=item B<volume=value>

Should have C<value=dd>: decimal value between 0 and 100 or C<value=ask>.

=item B<surround=mode>

Can have : C<surround=direct>, C<surround=pure>, C<surround=stereo>,
C<surround=standard>, C<surround=dolby>, C<surround=dts>, C<surround=wide>
C<surround=7ch>, C<surround=rock>, C<surround=jazz>, C<surround=classic>,
C<surround=mono>, C<surround=matrix>, C<surround=virtual> or C<surround=ask>.

=item B<audio=source>

Can have : C<audio=phono>, C<audio=cd>, C<audio=tuner>, C<audio=dvd>,
C<audio=hdp>, C<audio=tv>, C<audio=sat>, C<audio=vcr>, C<audio=dvr>,
C<audio=aux>, C<audio=net>, C<audio=usb> or C<audio=ask>.

=item B<video=source>

Can have : C<video=dvd>, C<video=hdp>, C<video=tv>, C<video=sat>, C<video=vcr>,
C<video=dvr>, C<video=aux> or C<video=ask>.

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

=item B<-s str>

Specify the C<xPL-serial_port> target's id.

=item B<-t mins>

Specify the number of minutes between two heartbeat messages.

=item B<-w secs>

Specify the number of seconds before sending the first heartbeat.
This allows to start the client after the hub,
thus eliminating an prospective startup delay of one heartbeat interval.

=item B<-a addr>

IP address of the audio-video controller.

=back

=head1 TEST

Connect the amplifier to the PC's first serial port C</dev/ttyS0>.

Make sure you have an C<xpl-hub> running on the machine.

Start the amplifier controller:
C<xpl-avController-DenonAVR-telnet.pl -v -n loungeAmp -s loungeAmp>.

Start C<xpl-monitor.pl -v> in another terminal window.

Mute the amplifier:
C<xpl-send.pl -v -d dspc-ampDenon.loungeAmp -c media.basic mute=on>.
Unmute it:
C<xpl-send.pl -v -d dspc-ampDenon.loungeAmp -c media.basic mute=off>.
Check mute status:
C<xpl-send.pl -v -d dspc-ampDenon.loungeAmp -c media.basic mute=ask>

Change audio source:
C<xpl-send.pl -v -d dspc-ampDenon.loungeAmp -c media.basic audio=dvr>,
or:
C<xpl-send.pl -v -d dspc-ampDenon.loungeAmp -c media.basic audio=tv>

The amplifier should reflect the changes and the logger log.

=head1 AUTHOR

Francois Corthay, DSPC

=head1 VERSION

2.0, 2012

=cut
