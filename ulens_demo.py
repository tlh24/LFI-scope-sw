import numpy as np
from ALP4 import *
import time
from PIL import Image
import aggdraw
import numpy
import math

def _find_getch():
    try:
        import termios
    except ImportError:
        # Non-POSIX. Return msvcrt's (Windows') getch.
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

# microlens pitch = 100um; DMD pitch = 7.6um
ulens_pitch_x = 13.165
ulens_pitch_y = 13.165
ulens_phase_x = ulens_pitch_x - 0.5 # specifies the center of the microlens.  
ulens_phase_y = 7.5 # pixel here illuminates perpendicuarly. 
# lens is f/17, diameter 100um; this converts *normalized* sub-coordinates (+- 1.0) to radians.
# but of course this is passed through hte microscope -- magnification!
ulens_subpixel_to_angle = 0.4

def pixel_to_4d(px,py):
	''' Convert ALP pixel coordinates to integer microlens array position and angle
	(angle in radians) '''
	nx = (float(px) - ulens_phase_x)/ulens_pitch_x
	ny = (float(py) - ulens_phase_y)/ulens_pitch_y
	ox = float(round(nx))
	oy = float(round(ny))
	# angles: note there may need to be a sign-flip here!
	sx = nx-ox
	sy = ny-oy
	ax = math.tan(sx*2.0*ulens_subpixel_to_angle) # so we can later directly multiply by z. 
	ay = math.tan(sy*2.0*ulens_subpixel_to_angle)
	l = math.sqrt(sx*sx + sy*sy)
	if (l > 0.45): # technically the lens has 100% fill factor, but I don't trust that yet..
		return (-100.0, -100.0, 0.0, 0.0)
	else:
		return(ox, oy, ax, ay)

# let's make a LUT to convert pix location to 4d. 
# speed things up a bit. 
p4d_array = []
for py in range(1600):
	for px in range(2560):
		p4d_array.append(pixel_to_4d(px,py))

def pixel_to_4d_cache(px,py):
	return p4d_array[py*2560+px]

def illuminate_voxel(x,y,z, draw_context, pen):
	'''Illuminate a voxel.  x and y are microlens coordinates, 
	e.g. 0,0 is the center of the first microlens, 0.5,0.0 is halfway to the second microlens..
	z is normalized based on microlens pitch (100um)'''
	# dumb algorithm: loop through all the pixels, draw the ones that intersect. 
	for py in range(1600):
		for px in range(2560):
			(ox,oy,ax,ay) = p4d_array[py*2560+px] #pixel_to_4d_cache(px,py)
			# approximation: each DMD pixel results in a rectangular solid beam, angled.
			bx = ox + (ax*z)
			by = oy + (ay*z)
			if ((bx-0.35) <= x) and ((bx+0.35) >= x):
				if ((by-0.35) <= y) and ((by+0.35) >= y):
					# intersect!  draw it.  
					draw_context.line((px, py, px, py+1), pen)

# need to test the voxel illumination, file output
def test_illumination():
	img = Image.new("L", (2560,1600), color='black') 
	d = aggdraw.Draw(img)
	pen = aggdraw.Pen("white", 1.7)
	for j in range(0,6):
		y = j*20.0+10.0
		for i in range(0,20):
			x = i*10.0+7.0 + j/10.0
			z = i-9.5
			print(x,y,z)
			illuminate_voxel(x,y,z,d,pen)
	brush = aggdraw.Brush("white")
	d.ellipse((1,1,30,30),pen,brush)
	d.flush()
	img.save('ulens_voxeltest.png')

test_illumination()

# Load the Vialux .dll
DMD = ALP4(version = '4.3', libDir = 'C:/Program Files/ALP-4.3/ALP-4.3 API')
# Initialize the device
DMD.Initialize()

c = 'g'
bitDepth = 8 
# Allocate the onboard memory for the image sequence
DMD.SeqAlloc(nbImg = 1, bitDepth = bitDepth)
needhalt = False
while c != 'q':
	print("ulens_pitch_x:"+str(ulens_pitch_x)+" ulens_pitch_y:"+str(ulens_pitch_y))
	print("ulens_phase_x:"+str(ulens_phase_x)+" ulens_phase_y:"+str(ulens_phase_y))
	'''
	for nx in range(1):
		for ny in range(1):
			img = Image.new("L", (2560,1600), color='black') 
			d = aggdraw.Draw(img)
			pen = aggdraw.Pen("white", 1.8)
			theta = (nx * 5 + ny)/25.0 * 2 * 3.1415926; 
			phasey = math.cos(theta)*0.4 + ulens_phase_y
			phasex = math.sin(theta)*0.4 + ulens_phase_x
			for y in numpy.arange(phasey, 1600, ulens_pitch_y):
				for x in numpy.arange(phasex, 2560, ulens_pitch_x):
					d.line((x, y, x, y+1), pen)
			#also draw a square in the upper left corner. 
			brush = aggdraw.Brush("black")
			d.ellipse((1,1,20,20),pen,brush)
			d.flush()
			pix = numpy.array(img)
			if ny == 0 and nx == 0:
				imgSeq = pix.ravel()
			else:
				if ny == 1 and nx == 0:
					img.save('ulens_seq_1.png')
				imgSeq = numpy.append(imgSeq, pix.ravel())
				'''
	img = Image.new("L", (2560,1600), color='black')
	d = aggdraw.Draw(img)
	pen = aggdraw.Pen("white", 1.7)
	for j in range(0,6):
		y = j*20.0+10.0
		for i in range(0,10):
			x = i*20.0+7.0
			z = 2.0*j-5.0
			print(x,y,z)
			illuminate_voxel(x,y,z,d,pen)
	brush = aggdraw.Brush("white")
	d.ellipse((1,1,30,30),pen,brush)
	d.flush()
	img.save('ulens_seq_1.png')
	pix = numpy.array(img)
	#if True:
	imgSeq = pix.ravel()
	#else:
	#	imgSeq = numpy.append(imgSeq, pix.ravel())

	if needhalt:
		DMD.Halt()
	# Send the image sequence as a 1D list/array/numpy array
	DMD.SeqPut(imgData = imgSeq.astype(int))
	# Set image rate to 30 Hz
	DMD.SetTiming(illuminationTime = 50000)

	# Run the sequence in an infinite loop
	DMD.Run()
	needhalt = True

	print("x:stepx+0.01 s:stepx-0.01; c:stepy+0.01; d:stepy-0.01")
	print("a:phasex+1 z:phasex-1; f:phasey+1; v:phasey-1")
	c = getch()
	if c == 'x':
		ulens_pitch_x = ulens_pitch_x + 0.01
	if c == 's':
		ulens_pitch_x = ulens_pitch_x - 0.01
	if c == 'c':
		ulens_pitch_y = ulens_pitch_y + 0.01
	if c == 'd':
		ulens_pitch_y = ulens_pitch_y - 0.01
	if c == 'a':
		ulens_phase_x = ulens_phase_x + 1
	if c == 'z':
		ulens_phase_x = ulens_phase_x - 1
	if c == 'f':
		ulens_phase_y = ulens_phase_y + 1
	if c == 'v':
		ulens_phase_y = ulens_phase_y - 1

# Stop the sequence display
DMD.Halt()
# Free the sequence from the onboard memory
DMD.FreeSeq()
# De-allocate the device
DMD.Free()
