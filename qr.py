#!/usr/bin/env python2
# vim: sw=4 ts=8 softtabstop=4 tw=79 expandtab

"""
A python program that will accept a string from the x clipboard and display a qrcode on the screen.

The program can also optionally accept a string from stdin or program arguments.

This program will use the program ``qrencode`` to build the barcode and ``Tk`` to display it.
"""

import os
import argparse
import subprocess

from tempfile import TemporaryFile
from PIL import ImageFile, ImageTk

import Tkinter as tk


def build_qrcode(string):
    """
    Builds a qrcode for the given *string* into a temporary file.

    Returns a PIL image of the QR code.
    """
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
        raise RuntimeError('qrencode returned "{}"'.format(ret))

    return image.close()


root = tk.Tk()

pil_image = build_qrcode("Hello World!")
image = ImageTk.PhotoImage(pil_image)

root.geometry("{}x{}".format(*pil_image.size))

button = tk.Button(image=image, command=root.quit)
button.image = image #keep a reference
button.pack()

root.mainloop()
