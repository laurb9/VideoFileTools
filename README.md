# VideoFileTools
Video file manipulation scripts

## videosplit.py

Batch extract all tracks of a given type from Matroska containers.
Uses mkvtoolnix (Mac OS: `brew install mkvtoolnix`) which does the heavy lifting
work of parsing and extracting the tracks.

The tracks are tagged by language when exported.

## Example

- Extract all subtitles and place them alongside the mkv files
```commandline
python videosplit.py --subtitles ~/Movies/*.mkv

ls ~/Movies/
Sintel.mkv
Sintel.3.eng.idx
Sintel.3.eng.sub
Sintel.4.eng.srt
```

- Extract all subtitles but save them elsewhere
```commandline
python videosplit.py --subtitles video1.mkv video2.mkv video3.mkv --dst /tmp

ls /tmp
Sintel.3.eng.idx
Sintel.3.eng.sub
Sintel.4.eng.srt
```

- Extract all audio streams, subtitles and chapters from all the mkv files under ~/Movies
including subdirectories
```commandline
python videosplit.py --subtitles --chapters --audio ~/Movies

ls ~/Movies
Sintel.mkv
Sintel.2.eng.m4a
Sintel.3.eng.idx
Sintel.3.eng.sub
Sintel.4.eng.srt
Sintel.chapters.txt
```

### Usage

```commandline
python videosplit.py --help

usage: videosplit.py [-h] [-d DST] [-n] [--video] [--audio] [--subtitles]
                     [--chapters]
                     files) [file(s ...]

Tool to extract all subtitle or audio tracks from a video into separate files.
Requires: mkvtoolnix (Mac OS: brew install mkvtoolnix)

positional arguments:
  file(s)            mkv file(s)

optional arguments:
  -h, --help         show this help message and exit
  -d DST, --dst DST  save the tracks in other directory (default same as
                     video)
  -n, --dry-run      do not write any files

Extracted tracks types:
  --video            extract video tracks
  --audio            extract audio tracks
  --subtitles        extract subtitles tracks
  --chapters         extract chapters
```


