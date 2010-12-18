#!/usr/bin/env python2
# vim: sw=4 ts=8 softtabstop=4 tw=79 expandtab

"""
A python program that creates and maintains a recent additions directory. It
is expected to be run as a cron script regularly.

As files can be created with timestamps (preventing the recent files from being
detected by using ctime or mtime), and files can be renamed this program will
maintain a list of all the files and their shasums in the scan directories. 

In order to improve the speed only a partial shasum will be preformed. To
minimize the chance of collisions, the program will also check against the
files size.

The format of the datafile is as thus;

<parameter> = <value>
<file> <size> <partial shasum>

where parameters can be:
 * scan - the directory to scan (this paramter can be used multiple times).
 * target - the location of the 'recent additions' directory
 * shaclip - the number of megabytes (in the beginning of the file)
             the shasum is created from. 
 * days - the number of days before a file is not recent anymore.
 * links - use soft or hard links (default is soft, but hard links may be
           required for samba/nfs shares.

"""

import hashlib
import os

def partial_shasum(filename, clip):
    """ Preforms a partial shasum for a given filename, clipping the file at
        clip bytes.
    """
    # ::TESTED 20101218 21:42 ::
    s = hashlib.sha1()
    fp = open(filename, 'rb')

    while True:
        # end of clipping boundary
        if fp.tell() < clip - 4096:
            b = fp.read(clip - fp.tell())
            s.update(b)
            break
        b = fp.read(4096)
        s.update(b)
        # EOF
        if len(b) < 4096:
            break; 

    fp.close()
    return s


def locate(root):
    """ Generator that recursivly lists all of the files in a given directory. """
    # ::TESTED 20101218 2208 ::
    for path, dirs, basenames in os.walk(root):
        for basename in basenames:
            yield os.path.join(path, basename)


def create_sizehashes(source_dirs):
    """ Returns a dict for each file in the source directories.

        The dict will have the filename as the key, and a tuple
        (size, partial shasum)
    """
    sizehashes = dict()
    for d in source_dirs:
        for f in locate(d):
            hash = partial_shasum(f, 1024*1024*10)
            size = os.path.getsize(f)
            
            value = (size, hash.digest())
            sizehashes[f] = value

