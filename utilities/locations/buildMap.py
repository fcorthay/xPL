#! /usr/bin/env python3

import os
import argparse
import math
import numpy as np
import matplotlib.pyplot as plt

# ------------------------------------------------------------------------------
# constants
#
EARTH_DIAMETER = 40075 # km

FIGURE_SIZE = 12

INDENT = '  '
SEPARATOR = 80 * '-'

# ------------------------------------------------------------------------------
# command line arguments
#
parser = argparse.ArgumentParser()
                                                                      # log file
parser.add_argument(
    '-f', '--logFile',
    default=os.sep.join([
        os.path.dirname(os.path.realpath(__file__)), 'test.log'
    ]),
    help='the GPS log file'
)
                                                           # reference longitude
parser.add_argument(
    '-x', '--longitude', default=0,
    help='the reference longitude (x-coordinate)'
)
                                                            # reference latitude
parser.add_argument(
    '-y', '--latitude', default=0,
    help='the reference latitude (y-coordinate)'
)
                                                            # reference altitude
parser.add_argument(
    '-z', '--altitude', default=0,
    help='the reference altitude (z-coordinate)'
)
                                                                     # verbosity
parser.add_argument(
    '-v', '--verbose', action='store_true', dest='verbose',
    help = 'verbose console output'
)
                                                  # parse command line arguments
parser_arguments = parser.parse_args()
log_file_spec = parser_arguments.logFile
reference_longitude = float(parser_arguments.longitude)
reference_latitude = float(parser_arguments.latitude)
reference_altitude = float(parser_arguments.altitude)
verbose = parser_arguments.verbose

plot_file_spec = '.'.join(log_file_spec.split('.')[:-1]) + '.png'

# ==============================================================================
# Internal functions
#

#-------------------------------------------------------------------------------
# read log file into arrays
#
def read_log():
    time = np.array([])
    latitude = np.array([])
    longitude = np.array([])
    altitude = np.array([])
    log_file = open(log_file_spec, 'r')
    for line in log_file :
        line = line.rstrip("\r\n")
#        print(line)
        parameters = line.split(',')
        for parameter in parameters :
            (name, value) = parameter.split(':', 1)
            name = name.strip()
            if name.lower() == 'time' :
                time = np.append(time, value)
            elif name.lower() == 'longitude' :
                longitude = np.append(longitude, float(value))
            elif name.lower() == 'latitude' :
                latitude = np.append(latitude, float(value))
            elif name.lower() == 'altitude' :
                altitude = np.append(altitude,
                    float(value) - reference_altitude
                )

    return(time, longitude, latitude, altitude)

#-------------------------------------------------------------------------------
# project values onto a map
#
def project_onto_map(longitudes, latitudes):
    reference_diameter = EARTH_DIAMETER*math.cos(reference_latitude/360*math.pi)
    x_coordinates = (longitudes - reference_longitude)*reference_diameter/360
    y_coordinates = (latitudes - reference_latitude)*EARTH_DIAMETER/360

    return(x_coordinates, y_coordinates)


# ==============================================================================
# Main script
#
                                                            # read location file
if verbose :
    print("Reading locations from \"%s\"" % log_file_spec)
(time, longitudes, latitudes, altitudes) = read_log()
if verbose:
    print(
        INDENT + "longitudes : %6.3f° - %6.3f°"
        % (min(longitudes), max(longitudes))
    )
    print(
        INDENT + "latitudes  : %6.3f° - %6.3f°"
        % (min(latitudes), max(latitudes))
    )
                                                              # project onto map
if verbose :
    print(
        'Projecting in the region of %g, %g'
        % (reference_longitude, reference_longitude)
    )
(x_coordinates, y_coordinates) = project_onto_map(longitudes, latitudes)
if verbose:
    print(
        INDENT + "x-coordinates : %8.3f km to %8.3f km (%.3f km)" % (
            min(x_coordinates), max(x_coordinates),
            max(x_coordinates) - min(x_coordinates)
        )
    )
    print(
        INDENT + "y-coordinates : %8.3f km to %8.3f km (%.3f km)" % (
            min(y_coordinates), max(y_coordinates),
            max(y_coordinates) - min(y_coordinates)
        )
    )
                                                                      # plot map
if verbose :
    print("Plotting the map to \"%s\"" % plot_file_spec)
(fig, ax) = plt.subplots(figsize=(FIGURE_SIZE, FIGURE_SIZE))
ax.plot(x_coordinates, y_coordinates)
ax.plot(x_coordinates, y_coordinates, 'o')
ax.axis('equal')
ax.grid()
plt.savefig(plot_file_spec)
