#!/usr/bin/python
"""Extract show metadata from old SnapStream tv recording files

This metadata is stored somewhere at the end of the video file and Beyond TV could display it.

Usage: extract-snapstream-metadata.py --src <snapstream_dir>

Sample metadata:

{
  "Actors": "", 
  "Channel": "47", 
  "Display-title": "The Hollow Men", 
  "EPGID": "EP7256900006", 
  "Genre": "Comedy", 
  "MPAA-Rating": "", 
  "Orig-Airdate": "20050414", 
  "SOURCE": "test1.avi", 
  "SOURCE_CLEAN": "test1.avi", 
  "Series-description": "", 
  "Series-title": "The Hollow Men", 
  "Show-description": "Investigating Abraham Lincoln; an expedition to the North Pole goes awry.", 
  "Show-title": "", 
  "Start": "127842318023230138", 
  "Station-Callsign": "COMEDYP", 
  "TZBias": "480", 
  "Target-DurationCNS": "18000000000", 
  "Target-Start": "127842318000000000", 
  "Unique-Channel-ID": "00000047000000010150", 
  "Year-Of-Release": ""
}

"""

import os
import stat
import struct
import re
import json
import argparse


def iter_cstring_at(buf, offset):
    """Read series of null-terminated strings from buffer, starting at given offset
    
    @param buf: input string
    @param offset: starting position
    @yield: strings read from buffer
    """
    while offset < len(buf):
        pos = buf.find("\0", offset)
        if pos < 0:
             raise StopIteration()

        s = buf[offset:pos]
        offset = pos+1
        yield s


# Series of regex-sub pairs to be applied to filenames
FILENAME_SUBS = (
    (re.compile(r'(.*) / ([^()]+) - (\d{4}-\d{2}-\d{2})', flags=re.X), r"\1/\2 (\3)"),
    (re.compile(r'(.*) / [^/]+\((.*?)\) - (\d{4}-\d{2}-\d{2})', flags=re.X), r"\1/\2 (\3)"),
    (re.compile(r'-0([.].*)$', flags=re.X), r"\1"),
    (re.compile(r'(_\s+)'), " ")
)


def cleanup_name(filename):
    """Clean up the SnapStream-style filenames
    
    from "South Park-(Christmas in Canada_)-2006-11-02-0.avi"
    to "Christmas in Canada (2006-11-02).avi"

    @param filename: source video filename
    @return: cleaned up filename
    """
    for rec, sub in FILENAME_SUBS:
        filename = rec.sub(sub, filename)
    return filename


def extract_metadata(filename, ignore_keys=("OriginalFileSize", "ShowSqueeze")):
    """Extract the metadata from the given snapstream video file.
    
    @param filename: source video filename
    @param ignore_keys: keys to ignore (leave the SS- out)
    @return: metadata dictionary, or None (if no metadata was found)
    """

    # The metadata is last in avi, and near the end in mpg
    with open(filename) as f:
        f.seek(-100000, 2)
        data = f.read()
    
    # The format of the data block looks like this, the keys and values are null-terminated:
    # MPG: <4 bytes count> <key-name> \0 [key-value] \0 <key-name> \0 ...
    # AVI: ATTR <4 bytes size> <4 bytes count> <key-name> \0 ...
    # It appears that SS-Actors is always the first key.
    FIRST_KEYWORD = "SS-Actors"

    offset = data.find(FIRST_KEYWORD)
    if offset < 0:
        return None
    
    # This is the count of key-value pairs
    count = struct.unpack_from("I", data, offset-4)[0]

    metadata = {
        "SOURCE": os.path.basename(filename),
        "SOURCE_CLEAN": cleanup_name(os.path.basename(filename))
    }
    parser = iter_cstring_at(data, offset)
    while count:
        key = parser.next().replace("SS-","")
        value = parser.next()
        if key not in ignore_keys:
            metadata[key] = value
        count -= 1

    return metadata


def scan_dir(src_path, dst_path=None, exts=(".avi", ".tp", ".mpg", ".mp4")):
    """Scan directory and extract metadata from every file

    For each src_path/dir/video.avi file, it will write dst_path/dir/video.json
    with the same timestamp as the video file, IF dst_path/dir/video.mkv exists.
    json files are not overwritten if they exist.

    If dst_path is None, the json will be output to terminal instead.
    
    @param src_path: directory where the video files live
    @param dst_path: directory where to write the json metadata, must have the same structure
    @param exts: list of video files extensions to check
    """

    for root, dirs, files in os.walk(src_path):
        for filename in files:
            basename, ext = os.path.splitext(filename)
            if ext not in ('.avi', '.tp', '.mpg', '.mp4'):
                continue
            
            src_filename = os.path.join(root, filename)
            metadata = extract_metadata(src_filename)
            if not metadata:
                print "ERROR: No metadata for %s" % src_filename
                continue

            metadata_json = json.dumps(metadata, indent=2, sort_keys=True, encoding="latin-1")
            if not dst_path:
                print metadata_json
                continue
            
            clean_filename = os.path.join(root.replace(src_path, dst_path), cleanup_name(basename))
            mkv_file = clean_filename + ".mkv"
            metadata_file = clean_filename + ".json"

            if not os.path.exists(mkv_file):
                print "MISSING FILE %s for %s" % (mkv_file, filename)
                
            elif not os.path.exists(metadata_file):
                print metadata_file
                with open(metadata_file, "w") as f:
                    f.write(metadata_json)

                # Copy timestamps
                finfo = os.stat(src_filename)
                os.utime(metadata_file, (finfo[stat.ST_ATIME], finfo[stat.ST_MTIME]))


def main():
    parser = argparse.ArgumentParser(description="Extract metadata from Beyond TV video files")
    parser.add_argument("-s", "--src", required=True,
                        help="path to snapstream directory containing video files")
    parser.add_argument("-d", "--dst", required=False,
                        help="path to target directory to write json metadata")
    args = parser.parse_args()

    scan_dir(args.src, args.dst)


if __name__ == '__main__':
    main()
