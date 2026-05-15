#!/usr/bin/python3
import argparse
import sys
import signal
import os
import time
from datetime import datetime
sys.path.append(sys.path[0]+'/../xPL-base')
import common
import queue
import sounddevice as sd
import vosk

# ------------------------------------------------------------------------------
# constants
#
VENDOR_ID = 'dspc';             # from xplproject.org
DEVICE_ID = 'speech';           # max 8 chars
CLASS_ID = 'speech';            # max 8 chars

LOG_FILE_LENGTH = 100

INDENT = '  '
SEPARATOR = 80 * '-'

# ------------------------------------------------------------------------------
# command line arguments
#
parser = argparse.ArgumentParser()
                                                                     # verbosity
parser.add_argument(
    '-v', '--verbose', action='store_true', dest='verbose',
    help = 'verbose console output'
)
                                                                 # Ethernet port
parser.add_argument(
    '-p', '--port', default=50000,
    help = 'the clients base UDP port'
)
                                                                   # instance id
parser.add_argument(
    '-n', '--id', default=common.xpl_build_automatic_instance_id(),
    help = 'the instance id (max. 16 chars)'
)
                                                                      # language
parser.add_argument(
    '-l', '--language', default='en-gb',
    help='speech language (vosk-transcriber --list-languages)'
)
                                                              # recording device
parser.add_argument(
    '-d', '--device', default=sd.query_devices('', 'input')['name'],
    help='input device (numeric ID or substring)'
)
                                                                   # sample rate
parser.add_argument(
    '-r', '--samplerate', type=int,
    help='sampling rate'
)
                                                                     # data type
parser.add_argument(
    '-t', '--datatype', default='int16',
    help='samples data type'
)
                                                                    # block size
parser.add_argument(
    '-b', '--blocksize', type=int, default=8000,
    help='block size'
)
                                                                      # log file
parser.add_argument(
    '-o', '--logfile', default='/tmp/tts.log',
    help='log file spec'
)
                                                            # list known devices
parser.add_argument(
    "-k", "--knowndevices", action="store_true",
    help="show list of audio devices and exit")
                                                  # parse command line arguments
parser_arguments = parser.parse_args()
verbose = parser_arguments.verbose
Ethernet_base_port = parser_arguments.port
instance_id = parser_arguments.id
language = parser_arguments.language
device = parser_arguments.device
sampling_rate = parser_arguments.samplerate
if sampling_rate is None :
    device_info = sd.query_devices(device, 'input')
    sampling_rate = int(device_info['default_samplerate'])
block_size = parser_arguments.blocksize
data_type = parser_arguments.datatype
log_file_spec = parser_arguments.logfile
                                                                  # list devices
if parser_arguments.knowndevices:
    print(sd.query_devices())
    exit(0)


# ==============================================================================
# Internal functions
#
#-------------------------------------------------------------------------------
# Reload an audio block
#
def callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    if status:
        print(status, file=sys.stderr)
    recording_queue.put(bytes(indata))

#-------------------------------------------------------------------------------
# Log a phrase
#
def log_phrase(text) :
                                                         # limit log file length
    if os.path.isfile(log_file_spec) :
        log_file_lines = open(log_file_spec, "r").read().split("\n")
        log_file = open(log_file_spec, "w")
        log_file.write("\n".join(log_file_lines[-LOG_FILE_LENGTH:]))
        log_file.close()
                                                                      # log text
    time_stamp = datetime.now().strftime("%Hh%M")
    log_file = open(log_file_spec, 'a')
    log_file.write("%s : %s\n" % (time_stamp, text))
    log_file.close()

# ------------------------------------------------------------------------------
# catch ctrl-C interrupt
#
end = False

def ctrl_C_handler(sig, frame):
    global end
    end = True
    print('')

signal.signal(signal.SIGINT, ctrl_C_handler)

# ==============================================================================
# main script
#
                                                             # create xPL socket
(client_port, xpl_socket) = common.xpl_open_socket(
    common.XPL_PORT, Ethernet_base_port
)
                                                    # display working parameters
if verbose :
    os.system('clear||cls')
    print(SEPARATOR)
    print("Listening to voice control"
    )
    print(INDENT + "class id    : %s" % CLASS_ID)
    print(INDENT + "instance id : %s" % instance_id)
    print(INDENT + "language    : %s" % language)
    print(INDENT + "device      : %s" % device)
    print(INDENT + "sample rate : %d Hz" % sampling_rate)
    print(INDENT + "data type   : %s" % data_type)
    print(INDENT + "block size  : %d" % block_size)
    print()
                                                                   # setup queue
recording_queue = queue.Queue()
                                                                    # setup vosk
vosk.SetLogLevel(-1) 
model = vosk.Model(lang=language)

# ..............................................................................
                                                                  # xPL settings
xPL_message_type = 'xpl-trig'
xPL_message_source = "%s-%s.%s" % (VENDOR_ID, DEVICE_ID, instance_id)
xPL_message_target = '*'
xPL_message_class = "%s.basic" % CLASS_ID
                                                                     # main loop
with sd.RawInputStream(
    samplerate=sampling_rate, blocksize=block_size, device=device,
    dtype=data_type, channels=1, callback=callback
):
    recording = vosk.KaldiRecognizer(model, sampling_rate)

    while not end :
        data = recording_queue.get()
        if recording.AcceptWaveform(data):
            result = recording.Result()
            result_dict = eval(result)
            if 'text' in result_dict :
                text = result_dict['text']
                if text :
                    print("decoded : \"%s\"" % text)
                    body_dict = {'text' : text.replace(' ', '_')}
                    common.xpl_send_message(
                        xpl_socket, common.XPL_PORT,
                        xPL_message_type, xPL_message_source,
                        xPL_message_target, xPL_message_class,
                        body_dict
                    );
                    log_phrase(text)
                                                              # close xPL socket
xpl_socket.close();
