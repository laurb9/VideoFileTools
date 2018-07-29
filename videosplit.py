# !/usr/bin/python
"""
Tool to extract all subtitle or audio tracks from a video into separate files.

Requires the following command-line tools to be installed:
- mkvtoolnix (Mac OS: brew install mkvtoolnix)
- mediainfo (Mac OS: brew install mediainfo, or get from App Store via https://mediaarea.net/en/MediaInfo)
- MP4Box (Mac OS: brew install mp4box)
"""
from __future__ import print_function
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
        "AAC": "aac",
        "AC3": "ac3",
        "AC-3": "ac3",
        "A_MPEG/L3": "mp3",
        "S_VOBSUB": "idx",
        "VobSub": "idx",
        "PGS": "sup",
        "S_TEXT/ASS": "sup",
        "S_TEXT": "srt",
        "tx3g": "srt",
        "AVC": "h264",
        "HEVC": "h265",
    }  # type: Dict[str, str]

    def __init__(self, track_types, dry_run=False):
        # type: (List[str], bool) -> None
        self.track_types = track_types
        self.dry_run = dry_run


    def should_save_track(self, track_type):
        # type: (unicode) -> bool
        """
        Return True if the track should be saved
        :param track_type:
        :return:
        """
        return track_type in self.track_types


    @classmethod
    def format_to_ext(cls, codec, format):
        # type: (str, str) -> str
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
        # type: (unicode) -> (unicode, List[Dict])
        """
        Read the available tracks from video file.

        :param videoFile: source video file
        :return: track available as dictionaries {ID, Language, Forced, Extension}
        """
        media_type = None
        tracks = []
        mediainfo_cmd = ["mediainfo", "--output=JSON", videoFile]
        mediainfo = json.load(subprocess.Popen(mediainfo_cmd, stdout=subprocess.PIPE, universal_newlines=True).stdout)
        for track in mediainfo["media"]["track"]:
            if track["@type"] == "General":
                media_type = track["Format"]

            if "ID" in track and track["@type"] != "Menu":
                #print track
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

                tracks.append(track)

        return media_type, tracks


    def get_track_name(self, track):
        # type: (dict) -> unicode
        """
        Create an appropriate name-extension for this track
        :param track: mediainfo track dictionary
        :return: id-prefixed track name
        """
        if track["Title"]:
            track["Title"] = track["Title"].replace("/", "-")
            format = u"{ID}.{Title}.{Language}.{Extension}"
        else:
            format = u"{ID}.{Language}.{Extension}"

        return format.format(**track)


    def split_video_file(self, videoFile, dst):
        # type: (str, AnyStr) -> None
        """
        Extract and save tracks of specified type from mkv file.

        :param videoFile: source mkv directory
        :param dst: optional directory or filename to save tracks to
        """
        targetName = os.path.splitext(videoFile)[0]
        if dst:
            if os.path.isdir(dst):
                targetName = os.path.join(dst, os.path.basename(targetName))
            else:
                targetName = dst

        targetName = targetName.decode("utf8")
        videoFile = videoFile.decode("utf8")
        media_type, tracks = self.mediainfo(videoFile)
        tracks = filter(lambda track: self.should_save_track(track["@type"]), tracks)
        if media_type == "Matroska":
            self.split_video_mkv(videoFile, targetName, tracks)
        elif media_type == "MPEG-4":
            self.split_video_mp4(videoFile, targetName, tracks)
        else:
            print("{0} not supported".format(videoFile, media_type))


    def split_video_mkv(self, videoFile, target_name, tracks):
        # type: (unicode, unicode, List[dict]) -> None
        """
        Extract and save tracks of specified type from mkv file.

        :param videoFile: source mkv directory
        :param dst: optional directory or filename to save tracks to
        :param tracks: list of selected tracks to extract
        """
        tracks = [u"{id}:{name}.{track}".format(name=target_name, track=self.get_track_name(track), **track)
                  for track in tracks]

        cmd = []
        if self.should_save_track("chapters"):
            cmd += ["chapters", u"{0}.chapters.xml".format(target_name)]

        if tracks:
            cmd += ["tracks"] + tracks

        if cmd:
            cmd = ["mkvextract", videoFile] + cmd

            if self.dry_run:
                print(u" \\\n\t".join(cmd))
            else:
                for line in subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout:
                    print(line, end="")
        else:
            print(u"{file}: no {types} tracks found.".format(file=videoFile, types="/".join(self.track_types)))


    def split_video_mp4(self, videoFile, target_name, tracks):
        # type: (unicode, unicode, List[dict]) -> None
        """
        Extract and save tracks of specified type from MP4 file.

        :param videoFile: source mkv directory
        :param dst: optional directory or filename to save tracks to
        :param tracks: list of selected tracks to extract
        """

        for track in tracks:
            track_filename = u"{name}.{track}".format(name=target_name, track=self.get_track_name(track))
            track_id = str(track["id"]+1)
            print("Track {0} {1}".format(track_id, track_filename))
            cmd = ["MP4Box", videoFile]
            if track["Extension"] == "srt":
                cmd += ["-std", "-srt", track_id]
                mp4box = subprocess.Popen(cmd, stdout=subprocess.PIPE)
                with open(track_filename, "w") as out:
                    filter(out.write, mp4box.stdout.readlines())

            else:
                #if track["Extension"] == "sub":
                #    track_filename = track_filename.replace(".sub", ".idx")
                cmd = ["MP4Box", videoFile, "-raw", "{0}:output={1}".format(track_id, track_filename)]
                for line in subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout:
                    print(line, end="")


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
                    _, ext = os.path.splitext(filename)
                    if ext in (".mkv", ".mp4", ".m4v"):
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
        splitter.split_video_file(videoFile, args.dst)


if __name__ == "__main__":
    main()
