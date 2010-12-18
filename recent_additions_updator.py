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


