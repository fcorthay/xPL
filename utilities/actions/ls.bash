#!/bin/bash

#-------------------------------------------------------------------------------
# Constants
#
DEFAULT_DIRECTORY='/boot'
LS_COMMAND='/usr/bin/ls'

#-------------------------------------------------------------------------------
# Command line arguments
#
directory=$DEFAULT_DIRECTORY
while [ "$1" != '' ] ; do
  case $1 in
    -d | --directory   ) shift ; directory=$1 ;;
  esac
  shift
done

#===============================================================================
# Play sound
#

$LS_COMMAND $directory
