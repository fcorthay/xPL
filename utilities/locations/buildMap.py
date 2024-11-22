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
                                                                  # figure_width
parser.add_argument(
    '-w', '--width', default=12,
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
figure_width = float(parser_arguments.width)
verbose = parser_arguments.verbose

# ==============================================================================
# Internal functions
#

#-------------------------------------------------------------------------------
# read log file into arrays
#
def read_log(log_file_spec):
    time = np.array([])
    latitudes = np.array([])
    longitudes = np.array([])
    altitudes = np.array([])
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
                longitudes = np.append(longitudes, float(value))
            elif name.lower() == 'latitude' :
                latitudes = np.append(latitudes, float(value))
            elif name.lower() == 'altitude' :
                altitudes = np.append(altitudes, float(value))

    return(time, longitudes, latitudes, altitudes)

#-------------------------------------------------------------------------------
# project values onto a map
#
def project_onto_map(
    longitudes, latitudes,
    reference_longitude, reference_latitude
):
    reference_diameter = EARTH_DIAMETER*math.cos(reference_latitude/360*math.pi)
    x_coordinates = (longitudes - reference_longitude)*reference_diameter/360
    y_coordinates = (latitudes - reference_latitude)*EARTH_DIAMETER/360

    return(x_coordinates, y_coordinates)

#-------------------------------------------------------------------------------
# plot map
#
def plot_map(x_coordinates, y_coordinates, z_coordinates,
    plot_file_spec, figure_width
):
                                                                      # plot map
    (fig, ax) = plt.subplots(figsize=(figure_width, figure_width))
    ax.plot(x_coordinates, y_coordinates)
    #ax.plot(x_coordinates, y_coordinates, 'o')
    ax.scatter(
        x_coordinates, y_coordinates,
        marker='o', c=z_coordinates, cmap=plt.cm.coolwarm
    )
    ax.axis('equal')
    ax.grid()
    plt.savefig(plot_file_spec)


#-------------------------------------------------------------------------------
# create plot file
#
def create_plot(
    log_file_spec,
    reference_longitude, reference_latitude, reference_altitude,
    figure_width,
    verbose=False
):
                                                            # read location file
    if verbose :
        print("Reading locations from \"%s\"" % log_file_spec)
    (time, longitudes, latitudes, altitudes) = read_log(log_file_spec)
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
    (x_coordinates, y_coordinates) = project_onto_map(
        longitudes, latitudes, reference_longitude, reference_latitude
    )
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
                                                  # substract reference altitude
    z_coordinates = altitudes - reference_altitude
                                                                      # plot map
    plot_file_spec = '.'.join(log_file_spec.split('.')[:-1]) + '.png'
    if verbose :
        print("Plotting the map to \"%s\"" % plot_file_spec)
    plot_map(
        x_coordinates, y_coordinates, z_coordinates,
        plot_file_spec, figure_width
    )

# ==============================================================================
# Main script
#

if __name__ == "__main__":
    create_plot(
        log_file_spec,
        reference_longitude, reference_latitude, reference_altitude,
        figure_width,
        verbose
    )
