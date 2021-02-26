"""Utilities for yapapi example scripts."""
import argparse
import os
import platform
import sys


is_a_tty = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
has_ansi_support = os.environ.get("TERM") == "ANSI"
is_windows = platform.system() == "Windows"

ANSI_RED = "\033[31;1m"
ANSI_GREEN = "\033[32;1m"
ANSI_YELLOW = "\033[33;1m"
ANSI_BLUE = "\033[34;1m"
ANSI_MAGENTA = "\033[35;1m"
ANSI_CYAN = "\033[36;1m"
ANSI_WHITE = "\033[37;1m"
ANSI_DEFAULT = "\033[0m"

if has_ansi_support or (is_a_tty and not is_windows):
    TEXT_COLOR_RED = ANSI_RED
    TEXT_COLOR_GREEN = ANSI_GREEN
    TEXT_COLOR_YELLOW = ANSI_YELLOW
    TEXT_COLOR_BLUE = ANSI_BLUE
    TEXT_COLOR_MAGENTA = ANSI_MAGENTA
    TEXT_COLOR_CYAN = ANSI_CYAN
    TEXT_COLOR_WHITE = ANSI_WHITE
    TEXT_COLOR_DEFAULT = ANSI_DEFAULT
else:
    TEXT_COLOR_RED = TEXT_COLOR_GREEN = TEXT_COLOR_YELLOW = TEXT_COLOR_BLUE = \
    TEXT_COLOR_MAGENTA = TEXT_COLOR_CYAN = TEXT_COLOR_WHITE = TEXT_COLOR_DEFAULT = ""


def build_parser(description: str):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--driver", help="Payment driver name, for example `zksync`")
    parser.add_argument("--network", help="Network name, for example `rinkeby`")
    parser.add_argument(
        "--subnet-tag", default="community.4", help="Subnet name; default: %(default)s"
    )
    parser.add_argument(
        "--log-file", default=None, help="Log file for YAPAPI; default: %(default)s"
    )
    return parser
