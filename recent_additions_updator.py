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

import binascii
import hashlib
import time
import os
import re

INT_PARAMETERS = ['minsize', 'shaclip']

class Datafile:
    """ Storage class for the datafile."""
  
    # ::TODO improve config loading::
 
    @staticmethod
    def New(datafilename, sources, target, minsize, shaclip):
        """ Creates a new datafile with the given configuration.
            
            Raises an Exception if the datafile already exists.
        """
        if os.path.exists(datafilename):
            raise Exception("Datafile %s already exists." % datafilename)

        fp = open(datafilename, 'w')
        # copy config to datafile
        for d in sources:
            fp.write("scan = %s\n" % os.path.abspath(d))
        fp.write("target = %s\n" %target)
        fp.write("shaclip = %d\n" % shaclip)
        fp.write("minsize = %d\n" % minsize)
        fp.close()

        # too much effort to recreate the variables, just reload the file
        d = Datafile()
        d.__load(datafilename)
        return d


    @staticmethod
    def Load(datafilename):
        """ Loads the datafile into memory."""
        d = Datafile()
        d.__load(datafilename)
        return d

    def __load(self, datafilename):
        # Load the datafile into memory.
        self.datafilename = datafilename
        self.config = { 'scan': [] }
        self.filenames = set()
        self.size_and_shasums = set()

        fp = open(datafilename, 'r')
        line = fp.readline()
        while line:
            m = re.match("(.+?) *= *(.+)", line)
            if m:
                # config parameter
                key = m.group(1)
                value = m.group(2)

                if key == 'scan':
                    self.config['scan'].append(value)
                else:
                    if key in INT_PARAMETERS:
                        value = int(value)
                    self.config[key] = value
            else:
                # file record 
                s = line.find(' ')
                ss = line.find(' ', s+1)
                if s < 0 and ss < 0:
                    raise Exception("Error: %s" % line)
                partial_shasum = binascii.unhexlify(line[:s])
                size = int(line[s+1:ss])
                file = line[ss+1:] 
                self.filenames.add(file)
                self.size_and_shasums.add((size, partial_shasum)) 
            line = fp.readline()
        fp.close()
        self.datafilefp = open(datafilename, 'a')


    def check_filename_exists(self, filename):
        """ Returns true if the filename exists in the
            datafile.
        """
        return self.filenames in filenames


    def hash_is_unique(self, size, partial_shasum):
        """ Returns true if the given size and partial shasum does not
            exist in the datafile.
        """
        return (size, partial_shasum.digest()) not in self.size_and_shasums


    def append_filehash(self, filename, size, partial_shasum):
        """ Appends the filename, file size and partial shasum of
            a file into the datafile.
        """
        # add to maps
        self.filenames.add(filename)
        self.size_and_shasums.add((size, partial_shasum.digest()))
        # append to datafile
        self.datafilefp.write("%s %d %s\n" % (
                partial_shasum.hexdigest(), size, filename))

    
    def __del__(self):
        # Cleanup the datafilefp
        self.datafilefp.close()

            

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


def create_initial_directory(datafilename, sources, target, minsize, shaclip):
    """ Scans the source directories and creates the datafile, while populating
        the target 'recent additions' directory.

        sources, target, minsize and shaclip are the settings of the 'recent
        additions' directory, and will be saved into the datafile.

        Raises Exception if the target directory or the datafile already exists.
    """
    datafile = Datafile.New(datafilename, sources, target, minsize, shaclip)
    if os.path.exists(target):
        raise Exception("Directory %s already exists." % target)

    # create recent updates directory 
    os.mkdir(target)
    os.mkdir(os.path.join(target, 'month'))
    os.mkdir(os.path.join(target, 'week'))
    os.mkdir(os.path.join(target, 'day'))
    # scan sources
    for d in sources:
        for f in locate(d):
            f = os.path.abspath(f)
            shasum = partial_shasum(f, datafile.config['shaclip'])
            size = os.path.getsize(f)
            mtime = time.localtime(os.path.getmtime(f))
            
            # filename is unique, only need to check size and partial shasum
            if datafile.hash_is_unique(size, shasum):
                if size > datafile.config['minsize']:
                    create_links(f, target, 'month/%Y-%m', mtime)
                    create_links(f, target, 'week/%Y-%U', mtime)
                    create_links(f, target, 'day/%Y-%m-%d', mtime) 
                datafile.append_filehash(f, size, shasum)
  
create_initial_directory('datafile.txt', ['Video'], 'recent', 1024*512, 1024*1024*10)

#d = Datafile.Load('datafile.txt')

