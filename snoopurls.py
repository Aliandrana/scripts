#!/usr/bin/env python2
# vim: sw=4 ts=8 softtabstop=4 tw=79 expandtab

"""
A simple script that uses the program ngrep to scan for HTTP GET/POST
requests and prints them to stdout.

As ngrep requires privlige escalation, this script will execute ngrep with
sudo. This prevents python from being executed as root.
"""

import os
import re
import sys
import argparse
import subprocess

def parse_arguments():
    parser = argparse.ArgumentParser(
                        formatter_class=argparse.RawDescriptionHelpFormatter,
                        description='Regular expression renamer.',
                        epilog=__doc__,
    )

    parser.add_argument('-v', '--verbose', action='store_true',
                        required=False, default=False,
                        help='Be verbose.')

    parser.add_argument('-p', '--port', type=int,
                        required=False, default=80,
                        help='Use a specified port.')

    parser.add_argument('-i', '--interface', action='store',
                        required=False, default="eth0",
                        help='Interface to store variables')

    return parser.parse_args()

def regexmatchgroup(regex, s):
    """
    Returns the first group matched in the re compiled regex.
    Returns None if no string found.
    """
    m = regex.search(s)
    if m:
        return m.group(1)
    else:
        return None

def parse_line(line):
    """
    Parses the line, turning the line read from ngrep into something readable.
    """
    path = regexmatchgroup(parse_line.path_regex, line)
    host = regexmatchgroup(parse_line.host_regex, line)

    if path:
        if host is None:
            host = regexmatchgroup(parse_line.ip_regex, line)
        print("http://{0}/{1}".format(host, path))
parse_line.path_regex = re.compile(r"(?:GET|HEAD)\s+/?(.+?)\s")
parse_line.host_regex = re.compile(r"H[Oo][Ss][Tt]: (.+?)\|")
parse_line.ip_regex = re.compile(r"-> (\d+\.\d+\.\d+\.\d+):\d+ [AP]")


def main():
    call = ['sudo', 'ngrep',
            '-W', 'single',
            '-d', options.interface,
            '-P', '|',
            '-l',
            '-q',
            '^GET |^POST ',
            'tcp', 'and', 'port', str(options.port)
    ]

    p = subprocess.Popen(call,
            stdout=subprocess.PIPE,
            shell=False
    )

    while True:
        line = p.stdout.readline()
        if len(line) > 0 and line[0] == 'T':
            parse_line(line)
            sys.stdout.flush()


if __name__ == '__main__':
    global options
    options = parse_arguments()
    main()

