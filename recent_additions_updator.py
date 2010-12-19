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
<partial shasum> <size> <file>

where parameters can be:
 * scan    - the directory to scan (this paramter can be used multiple times).
 * target  - the location of the 'recent additions' directory
 * shaclip - the number of megabytes (in the beginning of the file)
                the shasum is created from.
 * minsize - the minimum size of a file that end up in the recent additions
                directory.
"""

import hashlib
import time
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



def create_links(filename, target, format, t=None):
    if t is None:
        t = time.localtime()
        print "HI"
    dir = time.strftime(format, t)
    dir = os.path.join(target, dir)
    # create directory (if necessary)    
    if os.path.isdir(dir) is False:
        os.mkdir(dir)
    link = os.path.basename(filename)
    link = os.path.join(dir, link)
    # make link
    if os.path.exists(link):
        print "MATCH: %s %s" % (filename, link)
    else:
        os.symlink(filename, link)


def create_initial_directory(sources, datafile, target,
        minsize=1024*256, shaclip=1024*1024*10):
    """ Scans the source directories and creates the datafile, while populating
        the target 'recent additions' directory.

        sources, target, minsize and shaclip are the settings of the 'recent
        additions' directory, and will be saved into the datafile.

        Raises OSError if the target or datafile cannot be created, or if the
            sources cannot be scanned.
        Raises Error if the target directory or the datafile already exists.
    """
    if os.path.exists(target):
        raise Exception("Directory %s already exists." % target)
    if os.path.exists(datafile):
        raise Exception("Datafile %s already exists." % target)

    fp = open(datafile, 'w')
    # copy settings to datafile
    for d in sources:
        fp.write("scan = %s\n" % os.path.abspath(d))
    fp.write("target = %s\n" %target)
    fp.write("shaclip = %d\n" % shaclip)
    fp.write("minsize = %d\n" % minsize)

    # create recent updates directory 
    os.mkdir(target)
    os.mkdir(os.path.join(target, 'month'))
    os.mkdir(os.path.join(target, 'week'))
    os.mkdir(os.path.join(target, 'day'))
    # scan sources
    for d in sources:
        for f in locate(d):
            f = os.path.abspath(f)
            hash = partial_shasum(f, shaclip)
            size = os.path.getsize(f)
            mtime = time.localtime(os.path.getmtime(f))

            if size > minsize:
                create_links(f, target, 'month/%Y-%m', mtime)
                create_links(f, target, 'week/%Y-%U', mtime)
                create_links(f, target, 'day/%Y-%m-%d', mtime)

            fp.write("%s %d %s\n" % (hash.hexdigest(), size, f))
    fp.close()

create_initial_directory(['Video'], 'datafile.txt', 'recent')
