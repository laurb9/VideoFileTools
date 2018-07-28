# !/usr/bin/python
"""
Tool to extract all subtitle or audio tracks from a video into separate files.

Requires: mkvtoolnix (Mac OS: brew install mkvtoolnix)
"""
import argparse
import itertools
import os
import re
try:
    import subprocess32 as subprocess
except ImportError:
    import subprocess
try:
    from typing import Dict, List, Any, AnyStr, Generator
except ImportError:
    pass

class VideoExtractor(object):
    # Sample formats:
    # Track 3: subtitles, codec ID: S_VOBSUB, mkvmerge/mkvextract track ID: 2, language: spa
    # Track 4: subtitles, codec ID: S_TEXT/ASS, mkvmerge/mkvextract track ID: 3
    MKVINFO_TRACK_FORMAT = re.compile(r"Track \d+: (?P<type>\w+), "
                                      r"codec ID: \w_(?P<codec>\S+).*?, \S+ "
                                      r"track ID: (?P<id>\d+)(, language: (?P<lang>\w+))?")

    CODEC_TO_EXT = {
        "AAC": "m4a",
        "AC3": "ac3",
        "MP3": "mp3",
        "VOBSUB": "sub",
        "TEXT": "srt",
        "HDMV": "sup",
        "MPEG4": "mp4",
        "MPEGH": "mp4",
    }  # type: Dict[str, str]

    def __init__(self, track_types, dry_run=False):
        # type: (List[str], bool) -> None
        self.track_types = track_types
        self.dry_run = dry_run


    def should_save_track(self, track_type):
        # type: (str) -> bool
        """
        Return True if the track should be saved
        :param track_type:
        :return:
        """
        return track_type in self.track_types


    @classmethod
    def codec_to_ext(cls, codec):
        # type: (str) -> str
        """
        Map a codec name to a file extension to save it to.

        :param codec: codec name
        :return: file extension
        """
        codec = codec.split("/")[0]
        return cls.CODEC_TO_EXT[codec]


    @classmethod
    def mkv_tracks(cls, videoFile):
        # type: (str) -> Generator[Dict]
        """
        Read the available tracks from mkv file.

        :param videoFile: source mkv file
        :return: track available as dictionaries {id, ext, lang, codec}
        """
        mkvinfo = subprocess.Popen(["mkvinfo", "--summary", videoFile], stdout=subprocess.PIPE, close_fds=True)
        for line in mkvinfo.stdout:
            if not line.startswith("Track"):
                continue

            match = cls.MKVINFO_TRACK_FORMAT.search(line)
            if match:
                track = match.groupdict()
                track["ext"] = VideoExtractor.codec_to_ext(track["codec"])
                track["lang"] = track["lang"] or "eng"
                yield track
            else:
                print("%s: Do not recognize: %s" % (videoFile, line))


    def split_mkv(self, videoFile, dst):
        # type: (str, AnyStr) -> None
        """
        Extract and save tracks of specified type from mkv file.

        :param videoFile: source mkv directory
        :param dst: optional directory or filename to save tracks to
        :param track_types: tracks types to save
        :param dry_run: if True, no tracks are extracted and the commands are printed instead.
        """
        basename = os.path.splitext(videoFile)[0]
        if dst:
            if os.path.isdir(dst):
                basename = os.path.join(dst, os.path.basename(basename))
            else:
                basename = dst

        tracks = ["{id}:{name}.{id}.{lang}.{ext}".format(name=basename, **track)
                  for track in self.mkv_tracks(videoFile)
                  if self.should_save_track(track["type"])]

        cmd = ["mkvextract", videoFile]

        if self.should_save_track("chapters"):
            cmd += ["chapters", "--simple", "{0}.chapters.txt".format(basename)]

        if tracks:
            cmd += ["tracks"] + tracks
        else:
            print("{file}: no {types} tracks found.".format(file=videoFile, types="/".join(self.track_types)))

        if self.dry_run:
            print " \\\n\t".join(cmd)
        else:
            for line in subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=1, close_fds=True).stdout:
                print line,

    @staticmethod
    def scan_dir(src):
        # type: (str, AnyStr, List[str], bool) -> None
        """
        Scan directory for mkv files

        :param src: source mkv directory
        :param dst: optional directory to save tracks to
        :param track_types: tracks types to save
        :param dry_run: if True, no tracks are extracted and the commands are printed instead.
        """
        if os.path.isdir(src):
            for root, dirs, files in os.walk(src):
                for filename in files:
                    if filename.endswith(".mkv"):
                        yield os.path.join(root, filename)
        else:
            yield src


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-d", "--dst", required=False,
                        help="save the tracks in other directory (default same as video)")
    parser.add_argument("-n", "--dry-run", required=False, default=False, action="store_true",
                        help="do not write any files")
    group = parser.add_argument_group("Extracted tracks types")
    group.add_argument("--video", dest='track_types', action='append_const', const="video",
                       help="extract video tracks")
    group.add_argument("--audio", dest='track_types', action='append_const', const="audio",
                       help="extract audio tracks")
    group.add_argument("--subtitles", dest='track_types', action='append_const', const="subtitles",
                       help="extract subtitles tracks")
    group.add_argument("--chapters", dest='track_types', action='append_const', const="chapters",
                       help="extract chapters")
    parser.add_argument("files", metavar="file(s)", type=str, nargs="+", help="mkv file(s)")
    args = parser.parse_args()

    splitter = VideoExtractor(args.track_types, dry_run=args.dry_run)
    for videoFile in itertools.chain(*(splitter.scan_dir(f) for f in args.files)):
        print("Parsing {0}".format(videoFile))
        splitter.split_mkv(videoFile, args.dst)


if __name__ == "__main__":
    main()
