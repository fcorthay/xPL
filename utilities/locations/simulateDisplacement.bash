#! /usr/bin/env bash

# ------------------------------------------------------------------------------
# constants
#
LOCATION_SERVER='192.168.1.5'
LOCATION_PORT='8003'
DEVICE='FP3'
LOCATOR_APP='gpsLogger'
REFERENCE_LONGITUDE='7.3606'
REFERENCE_LATITUDE='46.2331'
REFERENCE_ALTITUDE='500'
START_TIME=`date +%s`
TIME_STEP=60

EARTH_DIAMETER=40075 # km
REFERENCE_DIAMETER=`echo "$EARTH_DIAMETER*c($REFERENCE_LATITUDE/360*3.1416)" | bc -l`
DISTANCE_SHORT="0.2"
DISTANCE_LONG="0.5"
LATITUDE_SHORT=`echo "$DISTANCE_SHORT/$EARTH_DIAMETER*360" | bc -l`
LATITUDE_LONG=`echo "$DISTANCE_LONG/$EARTH_DIAMETER*360" | bc -l`
LONGITUDE_SHORT=`echo "$DISTANCE_SHORT/$REFERENCE_DIAMETER*360" | bc -l`

INDENT='  '
#SEPARATOR = 80 * '-'


# ------------------------------------------------------------------------------
# functions
#
sendLocation () {
  time=`printf '%(%FT%T%z)T\n' $((START_TIME + TIME_STEP))`
  locationData="longitude=$longitude&latitude=$latitude&altitude=$altitude"
  locationData="$locationData&time=$time&speed=0.0"
  curl --request POST \
  "http://$LOCATION_SERVER:$LOCATION_PORT/$DEVICE/$LOCATOR_APP?$locationData"
}

# ==============================================================================
# Main script
#
                                                           # clear location data
curl --request DELETE "http://$LOCATION_SERVER:$LOCATION_PORT/$DEVICE"
                                                          # send reference point
echo 'Reference point'
longitude=$REFERENCE_LONGITUDE
latitude=$REFERENCE_LATITUDE
altitude=$REFERENCE_ALTITUDE
sendLocation
                                                     # movement to near location
#sleep 1
echo 'near distance'
latitude=`echo "$REFERENCE_LATITUDE+0.5*$LATITUDE_SHORT" | bc -l`
sendLocation
                                                   # movement to middle location
echo 'middle distance'
latitude=`echo "$REFERENCE_LATITUDE+0.5*($LATITUDE_SHORT+$LATITUDE_LONG)" | bc -l`
sendLocation
                                                      # movement to far location
echo 'far distance'
latitude=`echo "$REFERENCE_LATITUDE+1.5*$LATITUDE_LONG" | bc -l`
sendLocation
                                                           # horizontal movement
echo 'horizontal movement'
longitude=`echo "$REFERENCE_LONGITUDE+0.5*$LONGITUDE_SHORT" | bc -l`
sendLocation
                                                   # movement to middle location
echo 'middle distance'
latitude=`echo "$REFERENCE_LATITUDE+0.5*($LATITUDE_SHORT+$LATITUDE_LONG)" | bc -l`
sendLocation
                                                     # movement to near location
echo 'near distance'
latitude=`echo "$REFERENCE_LATITUDE+0.5*$LATITUDE_SHORT" | bc -l`
sendLocation
