#!/usr/bin/env python3

import argparse
import json
import os
import pathlib
import re
import subprocess
from collections import ChainMap
from datetime import datetime, timedelta

PREFIX = re.compile(r'[^-_]{,4}')


def get_suffix(path, config0):
    base = os.path.basename(path)
    for k, v in config0['mapping'].items():
        if base.startswith(k):
            return v
    # fall back to prefix
    m = PREFIX.match(os.path.basename(path))
    if m:
        return '-' + m.group(0)
    return ''


def run_command(command0: list, config0: ChainMap):
    print('>  %s' % ' '.join(command0))
    if not config0.get('dry_run'):
        subprocess.call(command0)
    return


def exiftool(filename, config0: ChainMap):
    command1 = ['exiftool', '-G', '-j', filename]
    exif_stdout = subprocess.check_output(command1, universal_newlines=True)
    exif_data = json.loads(exif_stdout)[0]
    return exif_data


def get_exif_date(filename, config0: ChainMap):
    exif_data = exiftool(input_file, config0)
    create_date = exif_data['QuickTime:CreateDate']
    # "QuickTime:CreateDate": "2016:01:28 16:30:48",
    # works for Garmin VIRB and Cycliq
    start_time = datetime.strptime(create_date, '%Y:%m:%d %H:%M:%S')
    print(f'* {create_date}  {start_time.isoformat()}  {filename}')
    return start_time


def convert(hms):
    # https://stackoverflow.com/questions/6402812/how-to-convert-an-hmmss-time-string-to-seconds-in-python
    # TODO would float(x) break ffmpeg options?
    return sum(int(x) * 60 ** i for i, x in enumerate(reversed(hms.split(":"))))


parser = argparse.ArgumentParser(description="cut & rename bike camera file",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument('input_files', metavar='FILE', nargs='*',
                    help='input files')

parser.add_argument("-c", dest="config_file",
                    required=True,
                    metavar="JSON",
                    help="JSON config file")

parser.add_argument('-s', dest='start',
                    metavar="MM:SS",
                    default='0', type=str,
                    help='start this far into video')

parser.add_argument('-t', dest='length',
                    metavar="MM:SS",
                    default=None, type=str,
                    help='stop after this duration (optional)')

parser.add_argument('-e', dest='end',
                    metavar="MM:SS",
                    default=None, type=str,
                    help='stop at this time(optional)')

parser.add_argument('-p', dest='plate',
                    metavar="BR549",
                    default=None, type=str,
                    help='plate number for filename')

parser.add_argument('-o', dest='output_directory',
                    metavar="DIRECTORY",
                    default='.', type=str,
                    help='output directory')

parser.add_argument('-n', dest='dry_run',
                    default=False, action='store_true',
                    help='dry run')

parser.add_argument('-v', dest='verbose',
                    default=False, action='store_true',
                    help='verbose')

parser.add_argument('-S', dest='sound',
                    default=None,
                    action='store_true',
                    help='sound enabled')

parser.add_argument('-z', dest='timezone',
                    type=str, metavar='Europe/London',
                    default=None,
                    help='timezone')

options = parser.parse_args()

command_line_args = {k: v for k, v in vars(options).items() if v is not None}
with open(options.config_file, 'r') as f:
    base_config = json.load(f)
config = ChainMap(command_line_args, base_config)

if config.get('verbose'):
    print(config)

for input_file in config['input_files']:
    command = ['nice', '-10', 'ffmpeg', '-i', input_file,
               '-loglevel', '24', '-ss', config['start']]

    if config.get('length'):
        command += ['-t', config['length']]
    elif config.get('end'):
        duration = convert(config['end']) - convert(config['start'])
        command += ['-t', duration]

    file_start = get_exif_date(input_file, config)
    clip_start = file_start + timedelta(seconds=convert(options.start))
    basename_parts = [clip_start.strftime('%Y-%m-%d-%H%M')]

    if config.get('plate'):
        basename_parts.append(config.get['plate'].upper())
    basename_parts.append(get_suffix(input_file, config))
    new_basename = '_'.join(basename_parts)

    filename0 = pathlib.Path(options.output_directory, new_basename + '.mp4')
    filename1 = pathlib.Path(options.output_directory, new_basename + '.wmv')

    command += ['-vcodec', 'copy']

    if config.get('sound'):
        command += ['-acodec', 'copy']
    else:
        command += ['-an']

    command += [str(filename0)]

    # Experimentally, this seems good & produces files close to the same
    # size.
    # ffmpeg -i INPUT.MP4 -qscale 6 -vcodec msmpeg4 -acodec wmav2  OUTPUT.WMV

    run_command(command, config)
