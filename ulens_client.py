from __future__ import print_function
import logging
import numpy
from PIL import Image

import grpc

import ulens_pb2
import ulens_pb2_grpc


def run():
	with grpc.insecure_channel('10.8.3.29:50043') as channel:
		stub = ulens_pb2_grpc.IlluminateStub(channel)
		
		response = stub.Clear(ulens_pb2.SimpleReq(msg="doit"))
		print("Greeter client received: " + response.msg)
		for j in range(6):
			y = float(j) * 20.0 + 10.0
			for i in range(20):
				x = i * 10.0 + 7.0 + j/10.0; 
				z = i - 9.5; 
				stub.Illum(ulens_pb2.IllumReq(x=x,y=y,z=z,c=1.0))
		
		response = stub.Get(ulens_pb2.SimpleReq(msg="-"))
		print("Get rx: ", response.w, " ", response.h)
		print("return size", len(response.data))
		imgData = numpy.frombuffer(response.data, dtype=numpy.dtype('S1'), count=(response.w*response.h))
		imgData = numpy.reshape(imgData, (1600, 2560)); 
		img = Image.fromarray(imgData, mode='L'); 
		img.save('ulens_grpc.png')

if __name__ == '__main__':
    logging.basicConfig()
    run()
