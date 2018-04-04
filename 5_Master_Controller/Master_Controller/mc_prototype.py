# PCAN_Test.py

# Code for keyboard input from https://repolinux.wordpress.com/2012/10/09/non-blocking-read-from-stdin-in-python/

from PCANBasic import *
from time import sleep
from pprint import pprint
import sys
import math
import select
import os
import logging
import h5py
import numpy as np
import datetime

if __debug__:
	# libraries for IPC with UI and PC
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
fileName_hdf5 = "PC_positions.hdf5"		# File name for hdf5 with PC positions
fileName_log = "debug.log"				# File name for debug logging

dset_size_hdf5 = 1000 	# dataset total number of elements for hdf5
timeout = 0.1 			# Timeout for keyboard input in seconds

mc_pos_cmd_x_mm = 0
mc_pos_cmd_y_mm = 0
mc_pos_cmd_sent_x_mm = 0
mc_pos_cmd_sent_y_mm = 0
pc_pos_status_x_mm = 0
pc_pos_status_y_mm = 0
filter_pos_value_mm = 5		# Threshold filter value for the UI position control

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
if __debug__:
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
		logging.debug("Created IPC queues")

		# create seperate processes for the UI and Puck Tracker and give them Queues for IPC
		uiProcess = multiprocessing.Process(target=ui.uiProcess, name="ui", args=(dataToUI, dataFromUI))
		logging.debug("Created UI process with a queue")
		ptProcess = multiprocessing.Process(target=pt.ptProcess, name="pt", args=(dataToPT, dataFromPT))
		logging.debug("Created Puck Tracker process with a queue")

		# start child processes
		uiProcess.start()
		logging.debug("Started UI process")
		ptProcess.start()
		logging.debug("Started Puck Tracker process")

		#dataToPT.put("Calibrate")
		#dataToPT.put("TrackPuck")
		dataToUI.put("RunUI")

## end of method


##
## Rx_IPC() -  Need to add error detection
## Receive any pending IPC Queue messages and populate global variables as necessary
##
if __debug__:
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
			logging.debug("ptData: %s", ptData)
			if ptData == "Calibration Complete":
				dataToPT.put("TrackPuck")

		try:
			uiData = dataFromUI.get(False)
			logging.debug(str(uiData))
			
			#string manipulation
			uiData = uiData.split(":")
			if uiData[0] == "paddle_position_mm_x":
				mc_pos_cmd_x_mm = uiData[1]
			elif uiData[0] == "paddle_position_mm_y":
				mc_pos_cmd_y_mm = uiData[1]

		except Queue.Empty:
			uiData = 0
		else:
			logging.debug(str(uiData))

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
		logging.error("Error Initializing PCAN USB")
		print PCANBasic.GetErrorText(device, status, 0)
		logging.error(PCANBasic.GetErrorText(device, status, 0))
		exit
	else:
		print "PCAN USB Initialized"
		logging.debug("PCAN USB Initialized")

## end of method


###
## Uninit_PCAN()
## Uninitialize the PCAN USB Dongle & check for errors
##
def Uninit_PCAN(device):
	status = PCANBasic.Uninitialize(device, PCAN_USBBUS1)
	if status > 0:
		print "Error Uninitializing PCAN USB"
		logging.error("Error Uninitializing PCAN USB")
		print PCANBasic.GetErrorText(device, status, 0)
		logging.error(PCANBasic.GetErrorText(device, status, 0))
		exit
	else:
		print "PCAN USB Uninitialized"
		logging.debug("PCAN USB Uninitialized")
		exit

## end of method

##
## Create_HDF5()
## Create/truncate logger HDF5 file (for MATLAB) using h5py library
## Example code used - http://download.nexusformat.org/sphinx/examples/h5py/index.html
##
def Create_HDF5():
	global fileName_hdf5
	global dset_size_hdf5

	# create file
	f = h5py.File(fileName_hdf5, "w")
	#dset = f.create_dataset("positions", (1000,), dtype='uint16')
	logging.debug("Created %s for logging", fileName_hdf5)

	# point to the default data to be plotted
	f.attrs['default'] = 'PC_data'
	# give the HDF5 root some more attributes
	f.attrs['file_name'] = fileName_hdf5
	f.attrs['file_time'] = str(datetime.datetime.now())
	f.attrs['creator'] = 'mc_prototype.py'
	f.attrs['project'] = 'Air Hockey Robot'
	#f.attrs[u'HDF5_Version']     = six.u(h5py.version.hdf5_version)
	#f.attrs[u'h5py_version']     = six.u(h5py.version.version)
	logging.debug("Added hdf5 attributes")

	# create the group for X-Y positions to and from PC
	h_data = f.create_group('PC_data')
	logging.debug("Created hdf5 PC_data group")

	# dataset for sent ahd received X-Y command positions to PC
	h_pos_sent_x = h_data.create_dataset("pos_sent_x", (dset_size_hdf5, ), dtype='uint16')
	h_pos_sent_x.attrs["units"] = "mm"
	h_pos_sent_y = h_data.create_dataset("pos_sent_y", (dset_size_hdf5, ), dtype='uint16')
	h_pos_sent_y.attrs["units"] = "mm"

	h_pos_rcvd_x = h_data.create_dataset("pos_rcvd_x", (dset_size_hdf5, ), dtype='uint16')
	h_pos_rcvd_x.attrs["units"] = "mm"
	h_pos_rcvd_y = h_data.create_dataset("pos_rcvd_y", (dset_size_hdf5, ), dtype='uint16')
	h_pos_rcvd_y.attrs["units"] = "mm"
	logging.debug("Created hdf5 datasets for PC sent and received X-Y positions")

	# timestamps for sent and received X-Y command positions to PC
	# no h5py support of time datatype, so will use string
	h_time_sent = h_data.create_dataset("time_sent", (dset_size_hdf5, ), dtype='S30')
	h_time_sent.attrs["units"] = "time"

	h_time_rcvd = h_data.create_dataset("time_rcvd", (dset_size_hdf5, ), dtype='S30')
	h_time_rcvd.attrs["units"] = "time"
	logging.debug("Created hdf5 datasets for PC sent and received X-Y times")

	# make sure to close the file
	f.close()
	logging.debug("Closed hdf5 file")

## end of method


##
## filter_Tx_PC_Cmd()
## filter new pos value if the distance from last sent pos
## is below set threshold
##	
def filter_Tx_PC_Cmd():
	global mc_pos_cmd_x_mm
	global mc_pos_cmd_y_mm
	global mc_pos_cmd_sent_x_mm
	global mc_pos_cmd_sent_y_mm

	pos_diff_x_mm = mc_pos_cmd_x_mm - mc_pos_cmd_sent_x_mm
	pos_diff_y_mm = mc_pos_cmd_y_mm - mc_pos_cmd_sent_y_mm
	pos_diff_mm = math.sqrt(pos_diff_x_mm**2 + pos_diff_y_mm**2)
	
	if pos_diff_mm < filter_pos_value_mm:
		logging.debug("New pos(%i,%i) is filtered coz it's %imm(within %imm) away from last sent PC pos(%i,%i)", mc_pos_cmd_x_mm,
						mc_pos_cmd_y_mm, pos_diff_mm, filter_pos_value_mm, mc_pos_cmd_sent_x_mm, mc_pos_cmd_sent_y_mm)
		mc_pos_cmd_x_mm = mc_pos_cmd_sent_x_mm
		mc_pos_cmd_y_mm = mc_pos_cmd_sent_y_mm
## end of method


##
## process_input()
## Debug mode - allow user to set parameters and stuff
##
def process_input():
	global mc_pos_cmd_x_mm
	global mc_pos_cmd_y_mm

	print "Air Hockey Command Input"
	mc_pos_cmd_x_mm = input("Enter Position X: ")
	logging.debug("New entered pos X: %s", mc_pos_cmd_x_mm)
	mc_pos_cmd_y_mm = input("Enter Position Y: ")	
	logging.debug("New entered pos Y: %s", mc_pos_cmd_y_mm)	
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
	print "Press 'Enter' for debug mode (keyboard mode only)"
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
		# Process PC Status X message
		if message[1].ID == ID_pc_status_x:
			pc_pos_status_x_mm_b0 = message[1].DATA[0]
			pc_pos_status_x_mm_b1 = message[1].DATA[1]
			pc_pos_status_x_mm = pc_pos_status_x_mm_b0 | (pc_pos_status_x_mm_b1 << 8)
			logging.debug("Incoming message from PC, Status X: %s", pc_pos_status_x_mm)

		# Process PC Status Y message
		elif message[1].ID == ID_pc_status_y:
			pc_pos_status_y_mm_b0 = message[1].DATA[0]
			pc_pos_status_y_mm_b1 = message[1].DATA[1]
			pc_pos_status_y_mm = pc_pos_status_y_mm_b0 | (pc_pos_status_y_mm_b1 << 8)
			logging.debug("Incoming message from PC, Status Y: %s", pc_pos_status_y_mm)

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
	global mc_pos_cmd_sent_x_mm
	global mc_pos_cmd_sent_y_mm

	message = TPCANMsg()

	message.ID = ID_mc_cmd_pc
	message.MSGTYPE = PCAN_MESSAGE_STANDARD
	message.LEN = 4
	message.DATA[0] = (mc_pos_cmd_x_mm & mask_pos_cmd_x_mm_b0)
	message.DATA[1] = ((mc_pos_cmd_x_mm & mask_pos_cmd_x_mm_b1) >> 8)
	message.DATA[2] = (mc_pos_cmd_y_mm & mask_pos_cmd_y_mm_b2)
	message.DATA[3] = ((mc_pos_cmd_y_mm & mask_pos_cmd_y_mm_b3) >> 8)

	# Save last sent position command
	mc_pos_cmd_sent_x_mm = mc_pos_cmd_x_mm
	mc_pos_cmd_sent_y_mm = mc_pos_cmd_y_mm

	logging.debug("Transmitting message to PC: %s", message)

	# Send the message and check if it was successful
	status = PCANBasic.Write(device, PCAN_USBBUS1, message)
	if status > 0:
		print "Error transmitting CAN message"
		logging.error("Error transmitting CAN message")
		print PCANBasic.GetErrorText(device, status, 0)
		logging.error(PCANBasic.GetErrorText(device, status, 0))
		exit()

## end of method


## 
## main()
##
def main():
	global fileName_log

	# Create and set format of the logging file
	logging.basicConfig(filename=fileName_log, filemode='w', level=logging.DEBUG,
	 					format='%(asctime)s in %(funcName)s(): %(levelname)s *** %(message)s')

	# Initialize device
	Init_PCAN(PCAN)

	# Create HDF5 file for logging PC position data
	Create_HDF5()

	# UI control of the position
	if __debug__:
		logging.debug("Mode: UI control of the position")
		
		# Initialize IPC between MC - PC - UI
		Init_IPC()

		# read messages from IPC
		while 1:
			Rx_CAN(PCAN)
		  	Rx_IPC()
		  	filter_Tx_PC_Cmd()
		  	Tx_PC_Cmd(PCAN)
		  	update_display()
		  	sleep(timeout)

	# Keyboard control of the position
	#"""
	logging.debug("Mode: Keyboard control of the position")

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
			#Rx_CAN(PCAN)
	  		update_display()
	  		filter_Tx_PC_Cmd()
	  		#Tx_PC_Cmd(PCAN)
	  		sleep(timeout)

	#"""

## end of method

try:
	main()
except KeyboardInterrupt:
	print " "
	Uninit_PCAN(PCAN)



## Place to store cool shit
def playground(device):

	if (pc_pos_status_x_mm != mc_pos_cmd_x_mm) or (pc_pos_status_y_mm != mc_pos_cmd_y_mm):
		Tx_PC_Cmd(PCAN)