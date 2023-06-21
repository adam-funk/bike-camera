# bike-camera
Command-line tool for cutting down bike camera recordings

## TODO
- config file with sensible defaults
  - including mapping to front/rear
- option for output elapsed time or input cut-off time
- automatic time zone correction including summer time
- replace shell exiftool with Python library?

## Requirements
- `libimage-exiftool-perl` for the `/usr/bin/exiftool` command
- `ffmpeg` for the `/usr/bin/ffmpeg` command