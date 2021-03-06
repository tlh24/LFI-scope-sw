
OBJS = ulens.pb.o ulens.grpc.pb.o main.o
CFLAGS = -std=c++11 `pkg-config --cflags protobuf grpc` -Wall -O3
LD_FLAGS = -L/usr/local/lib `pkg-config --libs protobuf grpc++` -lpng -lpthread

all: ulens

%.o: %.cc
	g++ -c -o $@ $(CFLAGS) $(GTKFLAGS) $<

ulens: $(OBJS)
	g++ $(OBJS) $(LD_FLAGS) -o $@
	
ulens.pb.cc:
	protoc ulens.proto --cpp_out=.
	protoc ulens.proto --plugin=protoc-gen-grpc=`which grpc_cpp_plugin` --grpc_out=.
	python3 -m grpc_tools.protoc --python_out=. --grpc_python_out=. \
	--proto_path=. ulens.proto
	
clean:
	rm -rf $(OBJS) ulens *.pb.cc *.pb.h *_pb2.py *pb2_grpc.py

deps:
	sudo apt-get install libprotobuf-dev protobuf-compiler libgrpc-dev  \
	protobuf-compiler-grpc pkg-config python3 python3-grpc-tools \
	libgrpc++-dev libpng-dev python3-scipy python3-grpcio python3-grpc-tools
