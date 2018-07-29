# !/usr/bin/python
"""
Tool to extract all subtitle or audio tracks from a video into separate files.

Requires:
- mkvtoolnix (Mac OS: brew install mkvtoolnix)
- mediainfo (Mac OS: brew install mediainfo, or install from https://mediaarea.net/en/MediaInfo)
"""
import argparse
import itertools
import json
import os

try:
    import subprocess32 as subprocess
except ImportError:
    import subprocess
try:
    from typing import Dict, List, Any, AnyStr, Generator
except ImportError:
    pass

class VideoExtractor(object):

    CODEC_TO_EXT = {
        "AAC": "m4a",
        "AC3": "ac3",
        "AC-3": "ac3",
        "A_MPEG/L3": "mp3",
        "S_VOBSUB": "sub",
        "PGS": "sup",
        "S_TEXT/ASS": "sup",
        "S_TEXT": "srt",
        "AVC": "h264",
        "HEVC": "h265",
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
    def format_to_ext(cls, codec, format):
        # type: (str) -> str
        """
        Map a codec name to a file extension to save it to.

        :param format: codec name
        :return: file extension
        """
        for key in (format, codec, codec.split("/")[0]):
            if key in cls.CODEC_TO_EXT:
                return cls.CODEC_TO_EXT[key]
        print(u'Unknown track code="{0}" format="{1}"'.format(codec, format))
        return format


    @classmethod
    def mediainfo(cls, videoFile):
        # type: (str) -> Generator[Dict]
        """
        Read the available tracks from video file.

        :param videoFile: source video file
        :return: track available as dictionaries {ID, Language, Forced, Extension}
        """
        mediainfo_cmd = ["mediainfo", "--output=JSON", videoFile]
        mediainfo = json.load(subprocess.Popen(mediainfo_cmd, stdout=subprocess.PIPE, universal_newlines=True).stdout)
        for track in mediainfo["media"]["track"]:
            if "ID" in track and track["@type"] != "Menu":
                print track
                track["Extension"] = VideoExtractor.format_to_ext(track["CodecID"], track["Format"])
                track["Language"] = track.get("Language") or "en"
                track["id"] = int(track["ID"]) - 1
                if "@typeorder" in track:
                    track["ID"] = track["@typeorder"]
                elif "StreamOrder" in track:
                    track["ID"] = track["StreamOrder"]
                if track.get("Forced") == "Yes":
                    track["Language"] += "-forced"
                if "Title" not in track:
                    track["Title"] = ""
                yield track

    def get_track_name(self, track):
        # type: (dict) -> unicode
        """
        Create an appropriate name-extension for this track
        :param track: mediainfo track dictionary
        :return: id-prefixed track name
        """
        if track["Title"]:
            format = u"{ID}.{Title}.{Language}.{Extension}"
        else:
            format = u"{ID}.{Language}.{Extension}"

        return format.format(**track)

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

        tracks = [u"{id}:{name}.{track}".format(name=basename, track=self.get_track_name(track), **track)
                  for track in self.mediainfo(videoFile)
                  if self.should_save_track(track["@type"])]

        cmd = []
        if self.should_save_track("chapters"):
            cmd += ["chapters", u"{0}.chapters.xml".format(basename)]

        if tracks:
            cmd += ["tracks"] + tracks

        if cmd:
            cmd = ["mkvextract", videoFile] + cmd

            if self.dry_run:
                print u" \\\n\t".join(cmd)
            else:
                for line in subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True).stdout:
                    print line,
        else:
            print(u"{file}: no {types} tracks found.".format(file=videoFile, types="/".join(self.track_types)))


    @staticmethod
    def scan_dir(src):
        # type: (str) -> None
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
    group.add_argument("--video", dest='track_types', action='append_const', const="Video",
                       help="extract video tracks")
    group.add_argument("--audio", dest='track_types', action='append_const', const="Audio",
                       help="extract audio tracks")
    group.add_argument("--subtitles", dest='track_types', action='append_const', const="Text",
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
