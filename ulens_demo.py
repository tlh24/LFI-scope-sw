from __future__ import print_function
import logging
import numpy as np
from ALP4 import *
import time
from PIL import Image
import aggdraw
import numpy
import math

import grpc
import ulens_pb2
import ulens_pb2_grpc

is_windows = False

def _find_getch():
    try:
        import termios
    except ImportError:
        # Non-POSIX. Return msvcrt's (Windows') getch.
        is_windows = True
        import msvcrt
        return msvcrt.getch

    # POSIX system. Create and return a getch that manipulates the tty.
    import sys, tty
    def _getch():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

    return _getch

getch = _find_getch()

def make_image(theta, imn):
	with grpc.insecure_channel('10.8.3.29:50043') as channel:
		stub = ulens_pb2_grpc.IlluminateStub(channel)
		
		response = stub.Clear(ulens_pb2.SimpleReq(msg="doit"))
		print("Greeter client received: " + response.msg)
		
		for j in range(6):
			y = float(j) * 20.0 + 10.0
			for i in range(19):
				x = i * 10.0 + 10.0 + j/11.7; 
				z = (i-9.0) * math.sin(theta); 
				stub.Illum(ulens_pb2.IllumReq(x=x,y=y,z=z,c=1.0))
				if i != 9: #darken the central mode
					stub.Illum(ulens_pb2.IllumReq(x=x,y=y,z=0.0,c=-0.75))
		
		response = stub.Get(ulens_pb2.SimpleReq(msg="-"))
		print("Get rx: ", response.w, " ", response.h)
		print("return size", len(response.data))
		imgData = numpy.frombuffer(response.data, dtype=numpy.dtype('S1'), count=(response.w*response.h))
		imgData = numpy.reshape(imgData, (1600, 2560)); 
		img = Image.fromarray(imgData, mode='L'); 
		img.save('ulens_grpc_' + str(imn) + '.png')
		return imgData

if is_windows: 
	bitDepth = 8 
	# Load the Vialux .dll
	DMD = ALP4(version = '4.3', libDir = 'C:/Program Files/ALP-4.3/ALP-4.3 API')
	# Initialize the device
	DMD.Initialize()
	# Allocate the onboard memory for the image sequence
	DMD.SeqAlloc(nbImg = 25, bitDepth = bitDepth)

needhalt = False
c = 'g'

while c != 'q':
	theta = 0.0
	dtheta = math.pi * 2.0 / 25.0; 
	for imn in range(25):
		pix = make_image(theta, imn)
		if imn == 0:
			imgSeq = pix.ravel()
		else: 
			imgSeq = numpy.append(imgSeq, pix.ravel())
		theta = theta + dtheta
	
	if is_windows: 
		if needhalt:
			DMD.Halt()
		# Send the image sequence as a 1D list/array/numpy array
		DMD.SeqPut(imgData = imgSeq.astype(int))
		# Set image rate to 20 Hz
		DMD.SetTiming(illuminationTime = 50000)
		
		# Run the sequence in an infinite loop
		DMD.Run()
	needhalt = True
	c = getch()

if is_windows:
	# Stop the sequence display
	DMD.Halt()
	# Free the sequence from the onboard memory
	DMD.FreeSeq()
	# De-allocate the device
	DMD.Free()
