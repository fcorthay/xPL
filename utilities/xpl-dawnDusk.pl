#!/usr/bin/perl

use Math::Trig;
use FindBin;                            # find the script's directory
use lib "$FindBin::Bin/../xPL-base";    # add path for common lib
use common;


################################################################################
# constants
#
$vendor_id = 'dspc';            # from xplproject.org
$device_id = 'dawnDusk';        # max 8 chars
$class_id = 'dawnDusk';         # max 8 chars
$tty_name_length = 4;

$separator = '-' x 80;
$indent = ' ' x 2;

#-------------------------------------------------------------------------------
# global variables
#
my %configuration;
$configuration{'latitude'} = 46.0037;
$configuration{'longitude'} = 7.3191;
$configuration{'twilightOffset'} = 18;
$configuration{'logFile'} = '/dev/null';

my $days_per_year = 365.24;
my $max_declination = 23.44;
my $declination_day_offset = 9;
my $declination_day_gain = 360 / $days_per_year;


################################################################################
# Input arguments
#
use Getopt::Std;
my %opts;
getopts('hvp:n:t:w:l:g:o:d:', \%opts);

die("\n".
    "Usage: $0 [serial_port_device] [serial_port_settings]\n".
    "\n".
    "Parameters:\n".
    "${indent}-h      display this help message\n".
    "${indent}-v      verbose\n".
    "${indent}-p port the base UDP port\n".
    "${indent}-n id   the instance id (max. 12 chars)\n".
    "${indent}-t mins the heartbeat interval in minutes\n".
    "${indent}-w secs the startup sleep interval\n".
    "${indent}-l deg  the local latitude in degrees\n".
    "${indent}-g deg  the local longitude (from Greenwich) in degrees\n".
    "${indent}-o deg  the twilight offset in degrees\n".
    "${indent}-d file the debug log file\n".
    "\n".
    "Signals dawn and dusk times.\n".
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

$configuration{'latitude'} = $opts{'l'} || $configuration{'latitude'};
$configuration{'longitude'} = $opts{'g'} || $configuration{'longitude'};
$configuration{'twilightOffset'} = $opts{'o'} || $configuration{'twilightOffset'};
$configuration{'logFile'} = $opts{'d'} || $configuration{'logFile'};


################################################################################
# Internal functions
#


#-------------------------------------------------------------------------------
# Calculate sun declination as a function of the day of the year
#
sub sun_declination {

  my ($max_declination, $day_gain, $day_offset, $day) = @_;
                                                            # convert to radians
  my $max_declination_radians = deg2rad($max_declination);
  my $day_gain_radians = deg2rad($day_gain);
                                                         # calculate declination
  my $declination = asin(
    sin(-$max_declination_radians)
    * cos($day_gain_radians*($day+$day_offset))
  );
                                                            # convert to degrees
  my $declination_radians = rad2deg($declination);

  return($declination_radians)
}

#-------------------------------------------------------------------------------
# Calculate times of the day related to the sun
#
sub sun_times {

  my ($latitude, $declination, $twilight_offset) = @_;
  my $hours_per_day = 24;
  my $angle_to_hour = $hours_per_day / (2*deg2rad(180));
                                                            # convert to radians
  my $latitude_radians = deg2rad($latitude);
  my $declination_radians = deg2rad($declination);
  my $twilight_offset_radians = deg2rad($twilight_offset);
                                                    # calculate sun set and rise
  my $hour_angle = acos( tan($latitude_radians) * tan($declination_radians) );
  my $sunrise = $hour_angle * $angle_to_hour;
  my $sunset = $hours_per_day - $hour_angle * $angle_to_hour;
                                                   # calculate dawn set and dusk
  my $hour_angle = acos(
    tan($latitude_radians)
    * tan($declination_radians + $twilight_offset_radians)
  );
  my $dawn = $hour_angle * $angle_to_hour;
  my $dusk = $hours_per_day - $hour_angle * $angle_to_hour;
                                                            # convert to degrees
  my $declination_radians = rad2deg($declination);

  return($sunrise, $sunset, $dawn, $dusk)
}

#-------------------------------------------------------------------------------
# Convert hours with decimal values to hours and minutes
#
sub hours_decimal_to_minutes {

  my ($hour) = @_;
                                                     # integer and decimal parts
  my $hour_int = int($hour);
  my $hour_dec = $hour - $hour_int;
                                                            # convert to minutes
  my $minutes = int($hour_dec * 100/60);
                                                             # convert to string
  my $hour = sprintf('%02d', $hour_int) . 'h' . sprintf('%02d', $minutes);

  return($hour)
}

#-------------------------------------------------------------------------------
# Log and send xPL message
#
sub send_message_with_log {
  my (
    $log_file_spec,
    $xpl_socket, $xpl_port,
	  $type, $source, $target, $class,
	  %body
  ) = @_;
                                                              # get local time
  my ($sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst) =
    localtime(time);
                                                                    # log info
  open(LOG_FILE, ">> $log_file_spec");
  printf(LOG_FILE '%02d:%02d:%02d', $hour, $min, $sec);
  foreach my $item (keys %body) {
    print(LOG_FILE ", $item = $body{$item}");
  }
  print(LOG_FILE "\n");
  close(LOG_FILE);
                                                            # send xPL message
  xpl_send_message(
    $xpl_socket, $xpl_port,
	  $type, $source, $target, $class,
	  %body
  );
}

#-------------------------------------------------------------------------------
# Send event at sun times
#
sub send_time_trigger {

  my (
    $solar_time,
    $dawn, $sunrise, $sunset, $dusk,
    $gt_dawn, $gt_sunrise, $gt_sunset, $gt_dusk,
    $log_file_spec,
    $xpl_socket, $xpl_port, $xpl_id,
    $verbose
  ) = @_;
                                                 # compare with different events
  my ($is_dawn, $is_sunrise, $is_sunset, $is_dusk) = (0, 0, 0, 0);
                                                                        # dawn
  if ($solar_time > $dawn) {
    if ($gt_dawn == 0) {$is_dawn = 1}
    $gt_dawn = 1
  } else {
    $gt_dawn = 0
  };
                                                                     # sunrise
  if ($solar_time > $sunrise) {
    if ($gt_sunrise == 0) {$is_sunrise = 1}
    $gt_sunrise = 1
  } else {
    $gt_sunrise = 0
  };
                                                                      # sunset
  if ($solar_time > $sunset) {
    if ($gt_sunset == 0) {$is_sunset = 1}
    $gt_sunset = 1
  } else {
    $gt_sunset = 0
  };
                                                                        # dusk
  if ($solar_time > $dusk) {
    if ($gt_dusk == 0) {$is_dusk = 1}
    $gt_dusk = 1
  } else {
    $gt_dusk = 0
  };
if ($is_dawn + $is_sunrise + $is_sunset + $is_dusk > 0) {
print("\nDaily event:\n");
printf("  now    : %2.3f\n", $solar_time);
printf("  dawn   : %2.3f\n", $dawn);
printf("  sunrise: %2.3f\n", $sunrise);
printf("  sunset : %2.3f\n", $sunset);
printf("  dusk   : %2.3f\n", $dusk);
}
                                                                  # send message
                                                                        # dawn
  if ($is_dawn != 0) {
    if ($verbose > 0) {
      print("\n");
      print("Sending dawn trigger message\n");
    }
    send_message_with_log(
      $log_file_spec,
      $xpl_socket, $xpl_port,
      'xpl-trig', $xpl_id, '*', "$class_id.basic",
      ('status' => 'dawn')
    );
  }
                                                                     # sunrise
  if ($is_sunrise != 0) {
    if ($verbose > 0) {
      print("\n");
      print("Sending sunrise trigger message\n");
    }
    send_message_with_log(
      $log_file_spec,
      $xpl_socket, $xpl_port,
      'xpl-trig', $xpl_id, '*', "$class_id.basic",
      ('status' => 'sunrise')
    );
  }
                                                                      # sunset
  if ($is_sunset != 0) {
    if ($verbose > 0) {
      print("\n");
      print("Sending sunset trigger message\n");
    }
    send_message_with_log(
      $log_file_spec,
      $xpl_socket, $xpl_port,
      'xpl-trig', $xpl_id, '*', "$class_id.basic",
      ('status' => 'sunset')
    );
  }
                                                                        # dusk
  if ($is_dusk != 0) {
    if ($verbose > 0) {
      print("\n");
      print("Sending dusk trigger message\n");
    }
    send_message_with_log(
      $log_file_spec,
      $xpl_socket, $xpl_port,
      'xpl-trig', $xpl_id, '*', "$class_id.basic",
      ('status' => 'dusk')
    );
  }

  return($gt_dawn, $gt_sunrise, $gt_sunset, $gt_dusk)
}

#-------------------------------------------------------------------------------
# Build sun times status response
#
sub build_times_status {

  my ($query, $declination, $solar_time, $sunrise, $sunset, $dawn, $dusk, $verbose) = @_;
  my %status = ();
                                                                 # format values
  $declination = sprintf("%.2f", $declination);
  $solar_time = sprintf('%.2f', $solar_time);
  $sunrise = hours_decimal_to_minutes($sunrise);
  $sunset = hours_decimal_to_minutes($sunset);
  $dawn = hours_decimal_to_minutes($dawn);
  $dusk = hours_decimal_to_minutes($dusk);
  if ($verbose > 0) {
    print($indent . "Declination: $declination\n");
    print($indent . "Solar time : $solar_time\n");
    print($indent . "Dawn       : $dawn\n");
    print($indent . "Sunrise    : $sunrise\n");
    print($indent . "Sunset     : $sunset\n");
    print($indent . "Dusk       : $dusk\n");
  }
                                                            # build message body
  $status{'solarTime'} = $solar_time;
  if ( ($query eq 'declination') or ($query eq 'all') ) {
    $status{'declination'} = $declination;
  }
  if ( ($query eq 'sunrise') or ($query eq 'all') ) {
    $status{'sunrise'} = $sunrise;
  }
  if ( ($query eq 'sunset') or ($query eq 'all') ) {
    $status{'sunset'} = $sunset;
  }
  if ( ($query eq 'dawn') or ($query eq 'all') ) {
    $status{'dawn'} = $dawn;
  }
  if ( ($query eq 'dusk') or ($query eq 'all') ) {
    $status{'dusk'} = $dusk;
  }

  return(%status)
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
  print("Starting dawn dusk indicator on xPL port $client_port.\n");
  print($indent, "Latitude  is $configuration{'latitude'} degrees.\n");
  print($indent, "Longitude is $configuration{'longitude'} degrees.\n");
  print("$separator\n");
}


#===============================================================================
# Main loop
#

#($sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst) = gmtime(time);
#$dusk = (24*60*$hour + 60*$min + $sec + 5) / (24*60);

my $timeout = 1;
my $last_heartbeat_time = 0;
my ($gt_dawn, $gt_sunrise, $gt_sunset, $gt_dusk) = (1, 1, 1, 1);
my $solar_time;

while ( (defined($xpl_socket)) && ($xpl_end == 0) ) {
  my ($sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst) =
    gmtime(time);
                                                 # clear log file in the morning
  if ( ($yday == 0) and ($hour == 0) and ($min < 10) ) {
    unlink($configuration{'logFile'});
  }
                                                              # find actual time
  my $solar_time = $hour + $min/60 + $configuration{'longitude'}*24/360;
  if ($solar_time >= 24) { $solar_time = $solar_time - 24; };
  if ($solar_time < 0) { $solar_time = $solar_time + 24; };
#if ($sec < 1) {printf("GMT time is %02d:%02d, longitude offset is %2.3f => solar time is %2.3f\n", $hour, $min, $configuration{'longitude'}*24/360, $solar_time);}
                                                         # calculate declination
  my $declination = sun_declination(
    $max_declination,
    $declination_day_gain,
    $declination_day_offset,
    $yday
  );
                                                         # calculate time values
#  my ($sunrise, $sunset, $dawn) = sun_times(
  my ($sunrise, $sunset, $dawn, $dusk) = sun_times(
    $configuration{'latitude'},
    $declination,
    $configuration{'twilightOffset'},
  );
                                                                # check if event
  if ($sec < 2) {
    ($gt_dawn, $gt_sunrise, $gt_sunset, $gt_dusk) = send_time_trigger(
      $solar_time,
      $dawn, $sunrise, $sunset, $dusk,
      $gt_dawn, $gt_sunrise, $gt_sunset, $gt_dusk,
      $configuration{'logFile'},
      $xpl_socket, $xpl_port, $xpl_id,
      $verbose
    );
  }
                                                 # check time and send heartbeat
  $last_heartbeat_time = xpl_send_heartbeat(
    $xpl_socket, $xpl_id, $xpl_ip, $client_port,
    $heartbeat_interval, $last_heartbeat_time
  );
#print "time: $last_heartbeat_time\n";
                                              # get xpl-UDP message with timeout
  my ($xpl_message) = xpl_get_message($xpl_socket, $timeout);
                                                           # process XPL message
  if ($xpl_message) {
    my ($type, $source, $target, $schema, %body) = xpl_get_message_elements($xpl_message);
    if ( xpl_is_for_me($xpl_id, $target) ) {
      if (lc($schema) eq lc("$class_id.basic")) {
#print "$xpl_message\n";
        if ($type eq 'xpl-cmnd') {
          my $command = $body{'command'};
          if ($verbose > 0) {
            print("\n");
            print("Received \"$command\" query from \"$source\"\n");
          }
          if ($command eq 'status') {
            my $day = $body{'day'};
                                                                # update times
            if ($day) {
              $declination = sun_declination(
                $max_declination,
                $declination_day_gain,
                $declination_day_offset,
                $day
              );
              ($sunrise, $sunset, $dawn, $dusk) = sun_times(
                $configuration{'latitude'},
                $declination,
                $configuration{'twilightOffset'},
              );
            }
                                                        # send status response
            my $query = $body{'query'} || 'all';
#print "query: $query\n";
            my %status = build_times_status(
              $query,
              $declination, $solar_time,
              $sunrise, $sunset, $dawn, $dusk,
              $verbose
            );
            send_message_with_log(
              $configuration{'logFile'},
              $xpl_socket, $xpl_port,
              'xpl-stat', $xpl_id, $source, "$class_id.response",
              %status
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

xpl-dawnDusk.pl - Gives dawn and dusk times.

=head1 SYNOPSIS

xpl-dawnDusk.pl [options]

=head1 DESCRIPTION

This xPL client calculates various times related to the sun:
dawn, sunrise, sunset, dusk.

It sends <dawnDusk.basic> trigger messages at these specific times of the day.

It also replies to a C<command=status> command message
and sends these specific times, together with the declination
associated to the day.
The status message can also specify the day to analyse
as a number between 1 and 365.

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
The id is limited to 8 characters.
If not specified, it is constructed from the host name

=item B<-t mins>

Specify the number of minutes between two heartbeat messages.

=item B<-w secs>

Specify the number of seconds before sending the first heartbeat.
This allows to start the client after the hub,
thus eliminating an prospective startup delay of one heartbeat interval.

=item B<-l deg>

Specify the local latitude.
Default is 46.0037 (Verbier, CH).

=item B<-o deg>

Specify the twilight offset.
Default is 18 (astronomic).
Other known values are 12 (nautical) and 6 (civil).

=item B<-d file>

Specify the debug log file.
Default is C</dev/null>.
Logs outgoing messages with timestamps on a daily basis.

=back

=head1 TEST

Start C<xpl-monitor.pl -vf> in a terminal window.

Start C<./xpl-dawnDusk.pl -v> in another terminal window.

In a third terminal window, launch the command:
C<xpl-send.pl -v -c dawnDusk.basic command=status query=all>.
The dawnDusk client should display the info and the monitor display
the corresponding messages.

Find the sunrise time of the first day of the year:
C<xpl-send.pl -v -c dawnDusk.basic command=status query=sunrise day=1>.
Find the sunset time of the last day of the year:
C<xpl-send.pl -v -c dawnDusk.basic command=status query=sunset day=365>

=head1 AUTHOR

Francois Corthay, DSPC

=head1 VERSION

2.0, 2013

=cut
