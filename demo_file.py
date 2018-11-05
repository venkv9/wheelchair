import socket, sys, os, array, threading
from time import *
from fcntl import ioctl
from can2RNET import *


cansocket = socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW)


#Play little song
cansend(cansocket,"181C0100#2056080010560858")




