# PCAN_Test.py

# Code for keyboard input from https://repolinux.wordpress.com/2012/10/09/non-blocking-read-from-stdin-in-python/

from PCANBasic import *
from time import sleep
from pprint import pprint
import sys
import select
import os
import h5py
import numpy as np

# multiprocessing
import multiprocessing
import Queue
import puck_tracker as pt
import user_interface as ui

PCAN = PCANBasic() 		# Initialize an instance of the PCANBasic class
read_list = [sys.stdin] # Files monitored for input

##############################################################################################
## Global data storage
## Maybe improve this later
##############################################################################################

timeout = 0.1 			# Timeout for keyboard input in seconds

mc_pos_cmd_x_mm = 0
mc_pos_cmd_y_mm = 0
pc_pos_status_x_mm = 0
pc_pos_status_y_mm = 0

dataToUI = 0
dataFromUI = 0
dataToPT = 0
dataFromPT = 0

##############################################################################################
## CAN protocol definition
## Refer to: https://github.com/tabdallah/capstone/blob/master/1_Planning/System_Interface_Design.xlsx
##############################################################################################

# CAN message ID's
ID_mc_cmd_pc =		0x100		# CAN message ID for Master Controller Command to PC on X and Y position
ID_pc_status_x = 	0x101 		# CAN message ID for Paddle Controller Status on X-axis
ID_pc_status_y = 	0x102		# CAN message ID for Paddle Controller Status on Y-axis

# CAN signal masks
mask_pos_cmd_x_mm_b0 = 		0x00FF		# Hex mask for pos_cmd_x_mm signal (msg byte0)
mask_pos_cmd_x_mm_b1 = 		0xFF00		# Hex mask for pos_cmd_x_mm signal (msg byte1)
mask_pos_cmd_y_mm_b2 = 		0x00FF		# Hex mask for pos_cmd_y_mm signal (msg byte2)
mask_pos_cmd_y_mm_b3 = 		0xFF00		# Hex mask for pos_cmd_y_mm signal (msg byte3)

# CAN signal value tables

##############################################################################################
## Functions/methods
##############################################################################################

##
## Init_IPC() - Need to add error detection
## Initialize multiprocessing between UI, Puck Tracker and MC
## Create queues between those processes for IPC
## start child processes
##
def Init_IPC():
	global dataToUI
	global dataFromUI
	global dataToPT
	global dataFromPT

	# create queues for bidirectional communication with other processes
	dataToUI = multiprocessing.Queue()
	dataFromUI = multiprocessing.Queue()
	dataToPT = multiprocessing.Queue()
	dataFromPT = multiprocessing.Queue()
	print "Created IPC queues"

	# create seperate processes for the UI and Puck Tracker and give them Queues for IPC
	uiProcess = multiprocessing.Process(target=ui.uiProcess, name="ui", args=(dataToUI, dataFromUI))
	print "Created UI process with a queue"
	ptProcess = multiprocessing.Process(target=pt.ptProcess, name="pt", args=(dataToPT, dataFromPT))
	print "Created Puck Tracker process with a queue"

	# start child processes
	uiProcess.start()
	print "Started UI process"
	ptProcess.start()
	print "Started Puck Tracker process"

	#dataToPT.put("Calibrate")
	#dataToPT.put("TrackPuck")
	dataToUI.put("RunUI")

## end of method


##
## Rx_IPC() -  Need to add error detection
## Receive any pending IPC Queue messages and populate global variables as necessary
##
def Rx_IPC():
	global mc_pos_cmd_x_mm
	global mc_pos_cmd_y_mm
	global dataToUI
	global dataFromUI
	global dataToPT
	global dataFromPT

	try:
		ptData = dataFromPT.get(False)
	except Queue.Empty:
		ptData = 0
	else:
		print ptData
		if ptData == "Calibration Complete":
			dataToPT.put("TrackPuck")

	try:
		uiData = dataFromUI.get(False)
		
		#string manipulation
		uiData = uiData.split(":")
		if uiData[0] == "paddle_position_mm_x":
			mc_pos_cmd_x_mm = uiData[1]
		if uiData[0] == "paddle_position_mm_y":
			mc_pos_cmd_y_mm = uiData[1]

	except Queue.Empty:
		uiData = 0
	else:
		print uiData

## end of method


##
## Init_PCAN()
## Initialize the PCAN USB Dongle & Check for Errors
## Resets Tx & Rx queues
##
def Init_PCAN(device):
	status = PCANBasic.Initialize(device, PCAN_USBBUS1, PCAN_BAUD_125K)
	PCANBasic.Reset(device, PCAN_USBBUS1)
	if status > 0:
		print "Error Initializing PCAN USB"
		print PCANBasic.GetErrorText(device, status, 0)
		exit
	else:
		print "PCAN USB Initialized"

## end of method


###
## Uninit_PCAN()
## Uninitialize the PCAN USB Dongle & check for errors
##
def Uninit_PCAN(device):
	status = PCANBasic.Uninitialize(device, PCAN_USBBUS1)
	if status > 0:
		print "Error Uninitializing PCAN USB"
		print PCANBasic.GetErrorText(device, status, 0)
		exit
	else:
		print "PCAN USB Uninitialized"
		exit	
## end of method	


##
## process_input()
## Debug mode - allow user to set parameters and stuff
##
def process_input():
	global mc_pos_cmd_x_mm
	global mc_pos_cmd_y_mm

	print "Elevator Command Input"
	mc_pos_cmd_x_mm = input("Enter Position X: ")
	mc_pos_cmd_y_mm = input("Enter Position Y: ")		
## end of method


##
## update_display()
## Show elevator status and command
##
def update_display():
	global mc_pos_cmd_x_mm
	global mc_pos_cmd_y_mm
	global pc_pos_status_x_mm
	global pc_pos_status_y_mm

	os.system('clear')
	print("Air Hockey Robot Status")
	print("---------------")
	print "Position X Status: ", pc_pos_status_x_mm
	print "Position Y Status: ", pc_pos_status_y_mm
	print "Position X Command: ", mc_pos_cmd_x_mm
	print "Position Y Command: ", mc_pos_cmd_y_mm
	print " "
	print "Press 'Enter' for debug mode"
## end of method


##
## Rx_CAN(device)
## Receive any pending CAN messages and populate global variables as necessary
##
def Rx_CAN(device):
	global pc_pos_status_x_mm
	global pc_pos_status_y_mm

	message = PCANBasic.Read(PCAN, PCAN_USBBUS1)

	# Keep reading messages until there aren't any more
	while message[1].ID > 1:
		print "Incoming messages"
		# Process PC Status X message
		if message[1].ID == ID_pc_status_x:
			pc_pos_status_x_mm_b0 = message[1].DATA[0]
			pc_pos_status_x_mm_b1 = message[1].DATA[1]
			pc_pos_status_x_mm = pc_pos_status_x_mm_b0 | (pc_pos_status_x_mm_b1 << 8)

		# Process PC Status Y message
		elif message[1].ID == ID_pc_status_y:
			pc_pos_status_y_mm_b0 = message[1].DATA[0]
			pc_pos_status_y_mm_b1 = message[1].DATA[1]
			pc_pos_status_y_mm = pc_pos_status_y_mm_b0 | (pc_pos_status_y_mm_b1 << 8)

		# Read next message
		message = PCANBasic.Read(PCAN, PCAN_USBBUS1)
## end of method


## 
## Tx_PC_Cmd(device)
## Transmit the command message to the Paddcle Controller
##
def Tx_PC_Cmd(device):
	global mc_pos_cmd_x_mm
	global mc_pos_cmd_y_mm
	message = TPCANMsg()

	message.ID = ID_mc_cmd_pc
	message.MSGTYPE = PCAN_MESSAGE_STANDARD
	message.LEN = 4
	message.DATA[0] = (mc_pos_cmd_x_mm & mask_pos_cmd_x_mm_b0)
	message.DATA[1] = ((mc_pos_cmd_x_mm & mask_pos_cmd_x_mm_b1) >> 8)
	message.DATA[2] = (mc_pos_cmd_y_mm & mask_pos_cmd_y_mm_b2)
	message.DATA[3] = ((mc_pos_cmd_y_mm & mask_pos_cmd_y_mm_b3) >> 8)

	# Send the message and check if it was successful
	status = PCANBasic.Write(device, PCAN_USBBUS1, message)
	if status > 0:
		print "Error transmitting CAN message"
		print PCANBasic.GetErrorText(device, status, 0)
		exit()

## end of method


## 
## main()
##
def main():
	# Initialize device
	Init_PCAN(PCAN)
	
	# When we control position using UI
	if str(sys.argv[0]) == "UI":
		# Initialize IPC between MC - PC - UI
		Init_IPC()

		# read messages from IPC
		while 1:
			print "arg0", str(sys.argv[0])
			Rx_CAN(PCAN)
		  	Rx_IPC()
		  	update_display()
		  	Tx_PC_Cmd(PCAN)
		  	#sleep(timeout)

	#Keyboard control of the position
	else:	
		# Infinite loop of reading CAN messages & keyboard input
		while 1:
			# Wait for keyboard input, or do other stuff
			while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
				line = sys.stdin.readline()
				if line:
					process_input()
				else: 
					print('eof')
					exit(0)
			else:
				Rx_CAN(PCAN)
		  		update_display()
		  		if (pc_pos_status_x_mm != mc_pos_cmd_x_mm) or (pc_pos_status_y_mm != mc_pos_cmd_y_mm):
		  			Tx_PC_Cmd(PCAN)
		  		sleep(timeout)
## end of method


try:
	main()
except KeyboardInterrupt:
	print " "
	Uninit_PCAN(PCAN)



## Place to store cool shit
def playground(device):
	PCAN = device
	message = PCANBasic.Read(PCAN, PCAN_USBBUS1)

	if message[1].ID > 1:	# For some reason .Read returns ID of 1 when no messages present...
		print "Received CAN Message"
		print "ID: ",format(message[1].ID, '02x')
		print "DLC: ", message[1].LEN
		print "DATA: "

		for j in range(0, message[1].LEN):
			print "Byte ", j, ": ", message[1].DATA[j]



##
## Create_HDF5()
## Create/truncate logger HDF5 file (for MATLAB) using h5py library
##
#def Create_HDF5():
#	f = h5py.File("mytestfile.hdf5", "w")
#	dset = f.create_dataset("positions", (1000,), dtype='uint16')

## end of method