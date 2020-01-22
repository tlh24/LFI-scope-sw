from __future__ import print_function
import logging
import numpy as np
from ALP4 import *
import time
from PIL import Image
import numpy
import math
import readchar
import platform

import grpc
import ulens_pb2
import ulens_pb2_grpc

is_windows = platform.system() == 'Windows'

def make_image(theta, imn):
	with grpc.insecure_channel('10.8.3.29:50043') as channel:
		stub = ulens_pb2_grpc.IlluminateStub(channel)
		
		response = stub.Clear(ulens_pb2.SimpleReq(msg="doit"))
		print("Greeter client received: " + response.msg)
		
		req = ulens_pb2.IllumReq()
		for j in range(6):
			y = float(j) * 20.0 + 10.0
			for i in range(19):
				x = i * 10.0 + 10.0; 
				z = (i-9.0) * math.sin(theta); 
				cmd = req.cmds.add()
				cmd.x = x
				cmd.y = y
				cmd.z = z
				cmd.c = 1.0
				if i != 9: #darken the central mode
					cmd = req.cmds.add()
					cmd.x = x
					cmd.y = y
					cmd.z = z
					cmd.c = -0.75
					
		stub.Illum(req)
		
		response = stub.Get(ulens_pb2.SimpleReq(msg="-"))
		print("Get rx no ", imn, ": ", response.w, " ", response.h)
		print("return size", len(response.data))
		imgData = numpy.frombuffer(response.data, dtype=numpy.dtype('S1'), count=(response.w*response.h))
		imgData = numpy.reshape(imgData, (1600, 2560)); 
		if not is_windows:
			# can't see it, so save a png. 
			img = Image.fromarray(imgData, mode='L'); 
			img.save('ulens_grpc_' + str(imn) + '.png')
		return imgData

n_images = 25

if is_windows: 
	bitDepth = 8 
	# Load the Vialux .dll
	DMD = ALP4(version = '4.3', libDir = 'C:/Program Files/ALP-4.3/ALP-4.3 API')
	# Initialize the device
	DMD.Initialize()
	# Allocate the onboard memory for the image sequence
	DMD.SeqAlloc(nbImg = n_images, bitDepth = bitDepth)

needhalt = False
c = 'g'

while c != b'q' and c != 'q':
	theta = 0.0
	dtheta = math.pi * 2.0 / 25.0; 
	for imn in range(n_images):
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
		q = np.frombuffer(imgSeq, dtype=np.uint8)
		DMD.SeqPut(imgData = q.astype(int))
		# Set image rate to 20 Hz
		DMD.SetTiming(illuminationTime = 50000)
		
		# Run the sequence in an infinite loop
		DMD.Run()
	needhalt = True
	c = readchar.readchar()
	print(c)


if is_windows:
	# Stop the sequence display
	DMD.Halt()
	# Free the sequence from the onboard memory
	DMD.FreeSeq()
	# De-allocate the device
	DMD.Free()
