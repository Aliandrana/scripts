#!/usr/bin/env python2
# vim: sw=4 ts=8 softtabstop=4 tw=79 expandtab

"""
A python program that will accept a string from the x clipboard and display a qrcode on the screen.

The program can also optionally accept a string from stdin or program arguments.

This program will use the program ``qrencode`` to build the barcode and ``Tk`` to display it.
"""

import os
import sys
import argparse
import subprocess

from tempfile import TemporaryFile
from PIL import ImageFile, ImageTk

import Tkinter as tk

def get_xclip(selection='primary'):
    """
    Returns the value of the xclipboard using the program xclip.

    The optional *selection* argument describes the X selection to use.
    """
    p = subprocess.Popen(
            ('xclip', '-o', '-selection', selection),
            stdout=subprocess.PIPE,
    )

    stdout, stderr = p.communicate()

    return stdout


def read_file(filename):
    """
    Reads a given file (with '-' being stdin) and outputs its contents.
    """
    if filename == '-':
        fp = sys.stdin
    else:
        fp = open(filename, 'rb')

    string = fp.read()

    fp.close()

    return string


def build_qrcode(string):
    """
    Builds a qrcode for the given *string* into a temporary file.

    Returns a PIL image of the QR code.
    """
    #if len(string) == 0:
    #    raise ValueError('Invalid string')

    image = ImageFile.Parser()

    p = subprocess.Popen(
            ('qrencode', '--size=4', '--output=-'),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
    )

    p.stdin.write(string)
    p.stdin.close()

    while True:
        data = p.stdout.read(1024)
        if len(data) == 0:
            break
        else:
            image.feed(data)
    p.stdout.close()

    p.wait()

    if p.returncode != 0:
        raise RuntimeError('qrencode returned "{}"'.format(p.returncode))

    return image.close()


def display_qr_from_string(string):
    """
    Displays a new Tk window displaying a QR code of the given button.

    This function exits after the window is closed or the barcode is clicked.
    """
    root = tk.Tk()
    root.title("QR barcode")

    pil_image = build_qrcode(string)
    image = ImageTk.PhotoImage(pil_image)

    button = tk.Button(root, image=image, command=root.quit)
    button.image = image #keep a reference
    button.pack()

    # This forces a tiled window manager to treat is as a floating item
    root.geometry("{}x{}".format(*pil_image.size))
    root.resizable(False, False)

    root.mainloop()


def main():
    """
    Handles program arguments, displays the QR code for the given options/data.
    """
    parser = argparse.ArgumentParser(description='Clipboard QR code displayer.')

    group = parser.add_mutually_exclusive_group(required=False)

    group.add_argument('-c', '--clipboard',
            action='store_true', default=False, 
            help='Reads from the XA_CLIPBOARD instead of XA_PRIMARY'
    )
    group.add_argument('filename', nargs='?', default=None,
            help='Read from file (- is stdin).'
    )
    
    options = parser.parse_args()

    if options.clipboard:
        string = get_xclip('clipboard')
    elif options.filename:
        string = read_file(options.filename)
    else:
        string = get_xclip()

    display_qr_from_string(string)


if __name__ == '__main__':
    main()

