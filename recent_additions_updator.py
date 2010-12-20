#!/usr/bin/env python2
# vim: sw=4 ts=8 softtabstop=4 tw=79 expandtab

"""
A python program that creates and maintains a recent additions directory. It
is expected to be run as a cron script regularly.

As files can be created with timestamps (preventing the recent files from being
detected by using ctime or mtime), and files can be renamed this program will
maintain a list of all the files and their partial shasums in the scan
directories.

In order to improve the speed, only a partial shasum will be preformed. To
minimize the chance of collisions, the program will also check against the
files size.

The format of the datafile is as thus;

    <parameter> = <value>
    <hash> <time> <file>
    COLLISION <linkname> <r>
    LINK <hash> <linkname>

where hash is:
    <partial shasum> <size>

where parameters can be:
 * scan    - the directory to scan (this paramter can be used multiple times).
 * target  - the location of the 'recent additions' directory
 * shaclip - the number of megabytes (in the beginning of the file)
                the shasum is created from.
 * minsize - the minimum size of a file that end up in the recent additions
                directory.
"""

# :: TODO add main() ::
# :: TODO 3 startup modes. file time = now, file time = mtime, daemonize::
# :: TODO Remove dead links::
# :: TODO refactor code so there is a new_file and modified_file methods::
# :: TODO refactor so checking+linking methods are in their own class (simplifying common variables)::
# :: TODO add inotify support, checking file modified and file added, file removed::

import binascii
import hashlib
import string
import time
import os
import re

INT_PARAMETERS = ['minsize', 'shaclip']
MULTI_PARAMETERS = ['scan']

class Hash:
    """ A hash contains both the size and a partial shasum of a file."""
    shaclip = 0

    @staticmethod
    def set_shaclip(clip):
        """ Sets the number of bytes read from a file before it is clipped."""
        Hash.shaclip = clip

    @staticmethod
    def FromFile(filename):
        """ Constructs a new hash from a filename."""
        h = Hash()
        h._file(filename)
        return h

    @staticmethod
    def FromString(str):
        """ Constructs a new hash file from a string.

            The format of the string is as this <partial shasum> <size>
        """
        h = Hash()
        h._read_string(str)
        return h

    def _file(self, filename):
        shasum = partial_shasum(filename, Hash.shaclip)
        self.size = os.path.getsize(filename)
        self.partial_shasum_hex = shasum.hexdigest()
        self.partial_shasum = shasum.digest()

    def _read_string(self, str):
        m = re.match("([0-9A-F]+ +[0-9]+) +([0-9]+)", str)
        self.partial_shasum_hex = m.group(1) 
        self.partial_shasum = binascii.unhexlify(m.group(1))
        self.size = int(m.group(2)) 

    def __str__(self):
        """ Converts a hash object to a string.
            
            FORMAT: <partial shasum> <size>
        """
        return "%s %d" % (self.partial_shasum_hex, self.size)

    def __eq__(self, other):
        return (self.partial_shasum, self.size) == (other.partial_shasum, other.size)

    def __cmp__(self, other):
        if self.partial_shasum == other.partial_shasum:
            return self.size - other.size
        else:
            return self.partial_shasum.__cmp__(other.partial_shasum)

    def __hash__(self):
        return hash((self.partial_shasum, self.size))



class Datafile:
    """ Storage class for the datafile."""
  
    # ::TODO improve config access ::
 
    # ::TODO Remove::
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
        self.config = dict()
        for m in MULTI_PARAMETERS:
            self.config[m] = set()
        self.collisions = dict()
        self.filenames = set()
        self.hash_links = dict() # mapping of hashes to a tupple of (date, set of links).

        fp = open(datafilename, 'r')
        for line in fp:
            m = re.match("(.+?) *= *(.+)", line)
            if m:
                # config parameter
                # format is: <key> = <value>
                key = m.group(1)
                value = m.group(2).strip()

                if key in MULTI_PARAMETERS:
                    self.config[key].add(value)
                elif key in INT_PARAMETERS:
                    self.config[key] = int(value)
                else:
                    self.config[key] = value
            elif line.startswith("COLLISION"):
                # Collision match record.
                # format is: COLLISION <linkname> <r>
                m = re.match("COLLISION +(.+) +([0-9]+)", line)
                linkname = m.group(1)
                r = int(m.group(2))
                self.collisions[linkname] = r
            elif line.startswith("LINK"):
                # Link record.
                # format is: LINK <hash> <link>
                m = re.match("LINK +([0-9A-F]+ ([0-9]+) +(.+)", line)
                h = Hash.FromString(m.group(1))
                link = m.group(2)
                self.hash_links[h].append(link)
            else:
                # file record 
                # format is: <hash> <time> <filename>
                m = re.match("([0-9A-F]+ [0-9]+) +([0-9]+) +(.+)", line)
                h = Hash.FromString(m.group(1))
                t = int(m.group(2))
                file = m.group(3) 
                self.filenames.add(file)
                self.hash_links[h] = (t, set())
        fp.close()
        self.datafilefp = open(datafilename, 'a')


    def filename_is_unique(self, filename):
        """ Returns true if the filename does not exist in the
            datafile.
        """
        return filename not in self.filenames


    def hash_exists(self, h):
        """ Returns true if the given hash shasum exist in the datafile.
        """
        return h in self.hash_links


    def append_filehash(self, filename, h, t):
        """ Appends the filename, hash and time of a file into the datafile.
        """
        # add to maps
        self.filenames.add(filename)
        intt = int(time.mktime(t))
        # reset links (as the links either do not exist or have been deleted)
        self.hash_links[h] = (intt, set())
        # append to datafile
        self.datafilefp.write("%s %d %s\n" % (h, intt, filename))


    def add_link(self, hash, linkname):
        """ Adds the linkname (with a hash) to the datafile."""
        t, links = self.hash_links[hash]
        links.add(linkname)
        self.datafilefp.write("LINK %s %s\n" % (hash, linkname))


    def get_links(self, hash):
        """ Returns a set of links for a given hash."""
        t, links = self.hash_links[hash]
        return links


    def get_time(self, hash):
        """ Returns the time a given hash was added to the datafile."""
        t, links = self.hash_links[hash]
        return time.localtime(t)
        

    def get_linkname_collision(self, linkname):
        """ Returns the r value of a linkname collision.

            If the linkname has no collisions, then 0 is returned.
        """
        if linkname in self.collisions:
            return self.collisions[linkname]
        else:
            return 0


    def set_linkname_collision(self, linkname, r):
        """ Sets the r value of a given linkname collision in the datafile."""
        self.datafilefp.write("COLLISION %s %d\n" %(linkname, r))
        self.collisions[linkname] = r

    
    def __del__(self):
        # Close the datafile
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


def concat_parent_directories(filename, r, c=' - '):
    """ Concatinates r parent directories of the given filename into the
        basename of filename.

        ie, filename="/export/Video/TV-Show/Episode 01.avi" n=2 c=" - " 
        returns "TV-Show - Episode 01.avi"
    """
    l = []
    # add extra one for basename.
    for i in xrange(r+1):
        head, tail = os.path.split(filename)
        filename = head
        l.append(tail)
    l.reverse()
    return string.join(l, c)

    
def create_link(datafile, filename, format, t):
    """ Creates the link to the filename in a directory with the given format
        for the given time t, in the target directory.

        Returns the name of the link made.

        If the directory does not exist it will be created.
    """
    if t is None:
        t = time.localtime()
    dir = time.strftime(format, t)
    dir = os.path.join(datafile.config['target'], dir)
    # create directory (if necessary)    
    if os.path.isdir(dir) is False:
        # ::TODO first week of year, last week of last year::
        os.mkdir(dir)

    basename = os.path.basename(filename)
    link = os.path.join(dir, basename)

    # get collision r value for the link
    r = datafile.get_linkname_collision(link)
    basename = concat_parent_directories(filename, r)
    link = os.path.join(dir, basename)

    # check if there is a collision with the link
    if os.path.exists(link):
        # restore the name of the previous link
        ofilename = os.readlink(link)
        olinkname = link
        linkname = link
        # diverse until there is no collision
        while olinkname == linkname:
            # there is a collision - prepend the previous directory to the links.
            r += 1
            obasename = concat_parent_directories(ofilename, r)
            olinkname = os.path.join(dir, obasename)

            basename = concat_parent_directories(filename, r)
            linkname = os.path.join(dir, basename)
        # save r value
        datafile.set_linkname_collision(link, r)
        # rename old link
        os.rename(link, olinkname)
        link = linkname
    # make link
    os.symlink(filename, link)
    return link


def check_file(datafile, filename, t=None):
    """ Checks if the given file is unique and if so then create the links to
        the filename in the 'recent additions' month, day and week
        directories.

        t is a time struct containing the time in which the file was created.
        If None (or ommitted) then the current localtime will be used.
    """
    if t is None:
        t = time.localtime()
    # This helps prevent dead links
    filename = os.path.abspath(filename)
    
    if datafile.filename_is_unique(filename):
        # The file may be new, check its hash 
        h = Hash.FromFile(filename)
        if datafile.hash_exists(h):
            # The file has been moved or renamed.
            # Remove the old links.
            links = datafile.get_links(h)
            for link in datafile.get_links(h):
                if os.path.exists(link):
                    os.remove(link)
                # get the time of the origional link, otherwise
                # it may end up as today
                t = datafile.get_time(h)
        datafile.append_filehash(filename, h, t)
        if h.size > datafile.config['minsize']:
            # ::CHECK if the format can be moved to the config directory::
            for format in ['month/%Y-%m', 'week/%Y-%U', 'day/%Y-%m-%d']:
                linkname = create_link(datafile, filename, format, t)
                datafile.add_link(h, linkname) 


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
             mtime = time.localtime(os.path.getmtime(f))
             check_file(datafile, f, mtime)

Hash.set_shaclip(1024*1024*10)
create_initial_directory('datafile.txt', ['Video'], 'recent', 1024*512, 1024*1024*10)

#d = Datafile.Load('datafile.txt')

