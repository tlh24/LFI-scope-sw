#include <math.h>
#include <iostream>
#include <cstdlib>
#include <pthread.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>

#define PNG_DEBUG 3
#include <png.h>

int x, y;

int width, height;
png_byte color_type;
png_byte bit_depth;

png_structp png_ptr;
png_infop info_ptr;
int number_of_passes;
png_bytep * row_pointers;

void abort_(const char * s, ...){
	va_list args;
	va_start(args, s);
	vfprintf(stderr, s, args);
	fprintf(stderr, "\n");
	va_end(args);
	abort();
}

void write_png_file(char* file_name)
{
	/* create file */
	FILE *fp = fopen(file_name, "wb");
	if (!fp)
				abort_("[write_png_file] File %s could not be opened for writing", file_name);
	/* initialize stuff */
	png_ptr = png_create_write_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);

	if (!png_ptr)
				abort_("[write_png_file] png_create_write_struct failed");

	info_ptr = png_create_info_struct(png_ptr);
	if (!info_ptr)
				abort_("[write_png_file] png_create_info_struct failed");

	if (setjmp(png_jmpbuf(png_ptr)))
				abort_("[write_png_file] Error during init_io");

	png_init_io(png_ptr, fp);

	/* write header */
	if (setjmp(png_jmpbuf(png_ptr)))
				abort_("[write_png_file] Error during writing header");

	png_set_IHDR(png_ptr, info_ptr, width, height,
					bit_depth, color_type, PNG_INTERLACE_NONE,
					PNG_COMPRESSION_TYPE_BASE, PNG_FILTER_TYPE_BASE);

	png_write_info(png_ptr, info_ptr);

	/* write bytes */
	if (setjmp(png_jmpbuf(png_ptr)))
				abort_("[write_png_file] Error during writing bytes");

	png_write_image(png_ptr, row_pointers);

	/* end write */
	if (setjmp(png_jmpbuf(png_ptr)))
				abort_("[write_png_file] Error during end of write");
	png_write_end(png_ptr, NULL);
	
	fclose(fp);
}

// copied from the python test code ... 
// microlens pitch = 100um; DMD pitch = 7.6um
float ulens_pitch_x = 13.165;
float ulens_pitch_y = 13.165;
float ulens_phase_x = ulens_pitch_x - 0.5; // specifies the center of the microlens.  
float ulens_phase_y = 7.5; // pixel here illuminates perpendicuarly. 
// lens is f/17, diameter 100um; this converts *normalized* sub-coordinates (+- 1.0) to radians.
// but of course this is passed through hte microscope -- magnification!
float ulens_subpixel_to_angle = 0.4;

void pixel_to_4d(float px, float py, float &ox, float &oy, float &ax, float &ay){
	/* Convert ALP pixel coordinates to integer microlens array position and angle
	(angle in radians) */
	float nx = (px - ulens_phase_x)/ulens_pitch_x;
	float ny = (py - ulens_phase_y)/ulens_pitch_y;
	ox = round(nx);
	oy = round(ny);
	// angles: note there may need to be a sign-flip here!
	float sx = nx-ox;
	float sy = ny-oy;
	ax = tan(sx*2.0*ulens_subpixel_to_angle); // so we can later directly multiply by z. 
	ay = tan(sy*2.0*ulens_subpixel_to_angle);
	float l = sqrt(sx*sx + sy*sy);
	if (l > 0.45){ // technically the lens has 100% fill factor, but I don't trust that yet..
		ox = oy = -1000.0; 
		ax = ay = 0.0; 
	}
}

// conversion LUT. 
float p4d_array[1600][2560][4]; 
//grayscale image
unsigned char gimage[1600][2560];

void illuminate_voxel(float x, float y, float z, float color){
	/* Illuminate a voxel.  x and y are microlens coordinates, 
	e.g. 0,0 is the center of the first microlens, 0.5,0.0 is halfway to the second microlens..
	z is normalized based on microlens pitch (100um)'''
	dumb algorithm: loop through all the pixels, draw the ones that intersect. */
	unsigned char col = (unsigned char)(color * 255.0); 
	for(int py = 0; py < 1600; py++){
		for(int px = 0; px < 2560; px++){
			float ox, oy, ax, ay; 
			ox = p4d_array[py][px][0]; 
			oy = p4d_array[py][px][1]; 
			ax = p4d_array[py][px][2]; 
			ay = p4d_array[py][px][3]; 
			float bx = ox + (ax*z); 
			float by = oy + (ay*z); 
			if(((bx-0.35) <= x) && ((bx+0.35) >= x)){
				if(((by-0.35) <= y) && ((by+0.35) >= y)){
					gimage[py][px] = col; 
				}
			}
		}
	}
}
void *illuminate_voxel_thread(void* t){
	float* a = (float*)t; 
	illuminate_voxel(a[0], a[1], a[2], a[3]); 
	pthread_exit(NULL); 
}
/* illuminate voxel is pretty inefficient -- we can of course invert this mapping
 * with a coarse discretization along the z-axis.  But maybe later, this is quite fast now w/threading */
int main(void){
	//fill the LUT. 
	for(int y = 0; y < 1600; y++){
		for(int x = 0; x < 2560; x++){
			float ox,oy,ax,ay; 
			float px = x; 
			float py = y; 
			pixel_to_4d(px, py, ox, oy, ax, ay); 
			p4d_array[y][x][0] = ox; 
			p4d_array[y][x][1] = oy; 
			p4d_array[y][x][2] = ax; 
			p4d_array[y][x][3] = ay; 
		}
	}
	// clear the image. 
	for(int y = 0; y < 1600; y++){
		for(int x = 0; x < 2560; x++){
			gimage[y][x] = 0;
		}
	}
	// test illuminate voxels in parallel!
	pthread_t threads[6 * 20]; 
	float thread_args[6*20][4]; 
	pthread_attr_t attr;
   void *status;
   // Initialize and set thread joinable
   pthread_attr_init(&attr);
   pthread_attr_setdetachstate(&attr, PTHREAD_CREATE_JOINABLE);
	
	// test illuminate some voxels.. 
	for(int j = 0; j < 6; j++){
		float y = (float)j * 20.0 + 10.0; 
		for(int i = 0; i < 20; i++){
			float x = (float)i * 10.0 + 7.0 + (float)j/10.0; 
			float z = (float)i - 9.5; 
			printf("%f, %f, %f\n", x, y, z);
			thread_args[j*20+i][0] = x; 
			thread_args[j*20+i][1] = y; 
			thread_args[j*20+i][2] = z; 
			thread_args[j*20+i][3] = 1.0; 
			pthread_create(&threads[j*20+i], &attr, 
								illuminate_voxel_thread, (void*)(&(thread_args[j*20+i]))); 
			//illuminate_voxel(x, y, z, 0xff); 
		}
	}
	pthread_attr_destroy(&attr);
	for(int i = 0; i < 6*20; i++) {
      int rc = pthread_join(threads[i], &status);
      if (rc) {
         printf("Error:unable to join %d\n", rc); 
         exit(-1);
      }
      printf("Main: completed thread id %d\n", i);
   }
	// write an image. 
	width = 2560; 
	height = 1600; 
	color_type = PNG_COLOR_TYPE_GRAY; 
	bit_depth = 8; 
	row_pointers = (png_bytep*) malloc(sizeof(png_bytep) * height);
	for(int j=0; j<1600; j++){
		row_pointers[j] = (png_bytep)(&(gimage[j][0])); 
	}
	write_png_file("test.png");
	free(row_pointers); 
	return 0; 
}
