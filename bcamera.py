#!/usr/bin/env python3

import argparse, pathlib, subprocess, time, json, calendar, re, os
from   sys  import stdout

PREFIX = re.compile(r'[^-_]{,4}')


def get_suffix(path):
    m = PREFIX.match(os.path.basename(path))
    if m:
        return '-' + m.group(0)
    return ''


def run_command(command, options):
    print('>  %s' % ' '.join(command))
    if (not options.dry_run):
        subprocess.call(command)
    return


def exiftool(filename, options):
    command = ['exiftool', '-G', '-j', filename]
    exifstdout = subprocess.check_output(command, universal_newlines=True)
    exifdata = json.loads(exifstdout)[0]
    return exifdata


def exifdate(filename, options):
    exifdata = exiftool(input_file, options)
    create_date = exifdata['QuickTime:CreateDate']
    # "QuickTime:CreateDate": "2016:01:28 16:30:48",
    # works for Garmin VIRB
    # should also work for Cycliq
    start_time = calendar.timegm(time.strptime(create_date, '%Y:%m:%d %H:%M:%S'))
    print('*  %-15s   %10i   %s' % (create_date, start_time, filename))
    return start_time


def convert(hms):
    # https://stackoverflow.com/questions/6402812/how-to-convert-an-hmmss-time-string-to-seconds-in-python
    return sum(int(x) * 60 ** i for i,x in enumerate(reversed(hms.split(":"))))


parser = argparse.ArgumentParser(description="cut & rename VIRB file",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument('input_files', metavar='FILE', nargs='*',
		    help='input files')

parser.add_argument('-s', dest='start',
                    metavar="MM:SS",
                    default="0:00", type=str,
                    help='start this far into video')

parser.add_argument('-t', dest='length',
                    metavar="MM:SS",
                    default=None, type=str,
                    help='stop after this duration (optional)')

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

parser.add_argument('-e', dest='summer', 
                    default=False, action='store_true',
                    help='estival: correct for summer time')

parser.add_argument('-S', dest='silent', 
                    default=False, action='store_true',
                    help='silent (no audio)')

parser.add_argument('-W', dest='wmv', 
                    default=False, action='store_true',
                    help='generate WMV')

parser.add_argument('-q', dest='quality', 
                    metavar="N",
                    default=4, type=int,
                    help='video quality (lower is better!)')

options = parser.parse_args()

for input_file in options.input_files:
    command0 = ['nice', '-10', 'ffmpeg', '-ss', options.start, '-i', input_file,
                '-loglevel', '24']
    command1 = ['nice', '-10', 'ffmpeg', '-ss', options.start, '-i', input_file,
                '-loglevel', '24']

    if options.length:
        command0 += ['-t', options.length]
        command1 += ['-t', options.length]

    ctime = exifdate(input_file, options)
    #ctime = pathlib.Path(input_file).stat().st_ctime
    ntime = ctime + convert(options.start) # epoch time
    if options.summer:
        ntime = ntime - 3600 # subtract 1h in summer
    start = time.localtime(ntime)
    # Like gmtime() but converts to local time.
    # TODO -- auto TZ

    basename_parts = [time.strftime('%Y-%m-%d-%H%M', start)]
    if options.plate:
        basename_parts.append(options.plate.upper())
    basename_parts.append(get_suffix(input_file))
    new_basename = '_'.join(basename_parts)

    filename0 = pathlib.Path(options.output_directory, new_basename + '.mp4')
    filename1 = pathlib.Path(options.output_directory, new_basename + '.wmv')

    command0 += ['-vcodec', 'copy']
    command1 += ['-q:v', str(options.quality), '-q:a', '4', '-vcodec', 'msmpeg4']

    if options.silent:
        command0 += ['-an']
        command1 += ['-an']
    else:
        command0 += ['-acodec', 'copy']
        command1 += ['-acodec', 'wmav2']

    command0 += [str(filename0)]
    command1 += [str(filename1)]
    

    # Experimentally, this seems good & produces files close to the same
    # size.
    # ffmpeg -i INPUT.MP4 -qscale 6 -vcodec msmpeg4 -acodec wmav2  OUTPUT.WMV

    run_command(command0, options)

    if options.wmv:
        run_command(command1, options)

