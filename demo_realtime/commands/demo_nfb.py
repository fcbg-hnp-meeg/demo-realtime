import argparse

from bsl import set_log_level as bsl_set_log_level
from bsl.utils.lsl import search_lsl

from .. import nfb_fillingbar


def run():
    """Run 'demo-nfb' command."""
    bsl_set_log_level("INFO")

    parser = argparse.ArgumentParser(
        prog="demo-nfb",
        description="Start a demo of a neurofeedback system.",
    )
    parser.add_argument(
        "-s",
        "--stream_name",
        type=str,
        metavar="str",
        help="stream to connect to.",
    )
    parser.add_argument(
        "-w",
        "--winsize",
        type=float,
        metavar="float",
        help="duration of the acquisition window (seconds).",
        default=3.0,
    )
    parser.add_argument(
        "-d",
        "--duration",
        type=float,
        metavar="float",
        help="duration of the nfb loop (seconds).",
        default=30.0,
    )
    parser.add_argument(
        "--verbose", help="enable debug logs.", action="store_true"
    )
    args = parser.parse_args()

    stream_name = args.stream_name
    if stream_name is None:
        stream_name = search_lsl(ignore_markers=True, timeout=3)
    nfb_fillingbar(
        stream_name,
        args.winsize,
        args.duration,
        verbose="DEBUG" if args.verbose else "INFO",
    )
