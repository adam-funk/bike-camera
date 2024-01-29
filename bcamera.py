#!/usr/bin/env python3

import argparse
import json
import os
import re
import subprocess
from collections import ChainMap
from datetime import datetime, timedelta

PREFIX = re.compile(r'[^-_]{,4}')
DEFAULT_CONFIG = os.path.join(os.environ['HOME'], '.config', 'bike-camera.json')
TIME_KEY = 'QuickTime:CreateDate'
DURATION_KEY = 'QuickTime:Duration'
# 'File:FileInodeChangeDate' changes when the file is copied


def get_mapping(path, config0):
    base = os.path.basename(path)
    for k, v in config0['mapping'].items():
        if base.startswith(k):
            return v
    m = PREFIX.match(os.path.basename(path))
    if m:
        fallback_name = m.group(0)
    else:
        fallback_name = ''
    return {'rename': fallback_name,
            'time_end': False}


def run_command(command0: list, config0: ChainMap):
    print('>  %s' % ' '.join(command0))
    if not config0.get('dry_run'):
        subprocess.call(command0)
    return


def exiftool(filename):
    command1 = ['exiftool', '-G', '-j', filename]
    exif_stdout = subprocess.check_output(command1, universal_newlines=True)
    exif_data = json.loads(exif_stdout)[0]
    return exif_data


def get_exif_date(filename, from_end):
    exif_data = exiftool(input_file)
    create_date = exif_data[TIME_KEY]
    timestamp = datetime.strptime(create_date, '%Y:%m:%d %H:%M:%S')
    if from_end:
        duration0 = exif_data[DURATION_KEY]
        timestamp -= timedelta(seconds=convert(duration0))
    print(f'* {create_date}  {filename}')
    print(f'* {timestamp.isoformat()}')
    return timestamp


def convert(hms):
    # https://stackoverflow.com/questions/6402812/how-to-convert-an-hmmss-time-string-to-seconds-in-python
    return sum(float(x) * 60 ** i for i, x in enumerate(reversed(hms.split(":"))))


parser = argparse.ArgumentParser(description="cut & rename bike camera file",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument('input_files', metavar='FILE', nargs='*',
                    help='input files')

parser.add_argument("-c", dest="config_file",
                    default=DEFAULT_CONFIG,
                    metavar="JSON",
                    help="JSON config file")

parser.add_argument('-s', dest='start',
                    metavar="MM:SS",
                    default='0', type=str,
                    help='start at this point')

parser.add_argument('-t', dest='length',
                    metavar="MM:SS",
                    default=None, type=str,
                    help='stop after this duration')

parser.add_argument('-e', dest='end',
                    metavar="MM:SS",
                    default=None, type=str,
                    help='stop at this point')

parser.add_argument('-p', dest='plate',
                    metavar="BR549",
                    default=None, type=str,
                    help='plate number for filename')

parser.add_argument('-S', dest='sound',
                    default=None,
                    action='store_true',
                    help='sound enabled')

parser.add_argument('-o', dest='output_directory',
                    metavar="DIRECTORY",
                    default=None, type=str,
                    help='output directory')

parser.add_argument('-n', dest='dry_run',
                    default=False, action='store_true',
                    help='dry run')

parser.add_argument('-v', dest='verbose',
                    default=False, action='store_true',
                    help='verbose')

options = parser.parse_args()

command_line_args = {k: v for k, v in vars(options).items() if v is not None}
with open(options.config_file, 'r') as f:
    base_config = json.load(f)
config = ChainMap(command_line_args, base_config)

if config.get('verbose'):
    print()
    print(config)
    print()

for input_file in config['input_files']:
    command = ['nice', '-10', 'ffmpeg',
               '-i', input_file,
               '-loglevel', '24',
               '-ss', config['start'],
               '-vcodec', 'copy']

    if config.get('length'):
        command += ['-t', config['length']]
    elif config.get('end'):
        duration = convert(config['end']) - convert(config['start'])
        command += ['-t', str(duration)]

    if config.get('sound'):
        command += ['-acodec', 'copy']
    else:
        command += ['-an']

    camera_info = get_mapping(input_file, config)
    file_start = get_exif_date(input_file, camera_info['time_end'])
    clip_start = file_start + timedelta(seconds=convert(options.start))
    print(f'* {clip_start.isoformat()}')
    basename_parts = [clip_start.strftime('%Y-%m-%d-%H%M')]

    if config.get('plate'):
        basename_parts.append(config['plate'].upper())

    basename_parts.append(camera_info['rename'])
    new_basename = '_'.join(basename_parts)

    filename0 = os.path.join(config['output_directory'], new_basename + '.mp4')

    command += [str(filename0)]
    run_command(command, config)
