#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set fenc=utf-8 ai ts=4 sw=4 sts=4 et:

import os
import re
import sys
import argparse

def parse_arguments():
    parser = argparse.ArgumentParser(
                        formatter_class=argparse.RawDescriptionHelpFormatter,
                        description='Regular expression renamer.',
                        epilog=r"""
Will preform a regular expression test and replace to all files in the
working directory.

Examples:
       $ {0} 'Episode_(\d)_' 'Episode_0\1_'
            will append a leading 0 to the episode numbers.

       $ {0} '^(\d\d[^\d])' '0\1' 
            will append a leading zero to files with starting numbers between 10 and 99.

       $ {0} '\.htm$' '.html'
            will rename all .htm files to .html files.

       $ {0} '^000(\d+)' '\1'
            will remove leading zeros of files starting with 000.

       $ {0} '^(.+)_(\d+)-' '0\2-\1_\2-'
            will prepend a the files with ordering digits. 
""".format(os.path.basename(sys.argv[0])),
    )

    parser.add_argument('-t', '--test', action='store_true',
                        required=False, default=False,
                        help='Do not rename files.'
                       )

    parser.add_argument('-v', '--verbose', action='store_true',
                        required=False, default=False,
                        help='Be verbose.')

    parser.add_argument('-r', '--recursive', action='store_true',
                        required=False, default=False,
                        help='Recursivly transverse directories..')

    parser.add_argument('regex', action='store',
                        help='Regular expression matching')

    parser.add_argument('replace', action='store',
                        help='Replacement string')

    return parser.parse_args()



def remv(options):
    regex = re.compile(options.regex)
    files = os.listdir('.')
    files.sort()
    if len(files) > 0:
        length = max(len(f) for f in files)
        for f in files:
            if os.path.isdir(f) and options.recursive:
                # remember current directory.
                curdir = os.getcwd()
                os.chdir(f)
                remv(options)
                os.chdir(curdir)
            new = regex.sub(options.replace, f)
            if new != f:
                # file has changed.
                if options.test or options.verbose:
                    print("'{0: <{2}} -> '{1}'".format(f + "'", new, length + 1))
                if not options.test:
                    os.rename(f, new)


if __name__ == '__main__':
    options = parse_arguments()
    if options.verbose:
        print("re.rub(\"{}\", \"{}\", f)".format(options.regex, options.replace))
    remv(options)

