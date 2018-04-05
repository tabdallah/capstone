# mc_prototype.py
# Capstone Master Controller module
# By Stanislav Rashevskyi, David Eelman, Thomas Abdallah

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

##############################################################################################
## Global data storage
## Maybe improve this later
##############################################################################################

log_fileName = "debug.log"		# File name for debug logging

timeout = 0.5 			# Timeout for keyboard input in seconds

operationMode = 0		# Indicates whether MC decisions(0) or UI (1) control the Paddle 

# PC positions
mc_pos_cmd_x_mm = 0
mc_pos_cmd_y_mm = 0
mc_pos_cmd_sent_x_mm = 0
mc_pos_cmd_sent_y_mm = 0
pc_pos_status_x_mm = 0
pc_pos_status_y_mm = 0
filter_pos_value_mm = 5		# Threshold filter value for the UI position control

# IPC 
dataToUI = 0
dataFromUI = 0
dataToPT = 0
dataFromPT = 0
uiProcess = 0
ptProcess = 0

# hdf5
hdf5_fileName = "PC_positions.hdf5"		# File name for hdf5 with PC positions
hdf5_dset_size = 1000 			# dataset total number of elements for hdf5
hdf5_dset_max_size = 30000 		# dataset max number of elements  after resize when we reset the counter for hdf5
hdf5_dset_stop_resize = False	# flag that indicates whether to continue dataset resize or not
hdf5_dset_count = 0				# count to track current element in hdf5 PC_data dataset
hdf5_file_handle = 0			# handle to hdf5 file

# puck prediction
puckPositionMmX = 0
puckPositionMmY = 0
puckVelocityMmPerSx = 0
puckVelocityMmPerSY = 0
lastPuckPositionMmX = 0
lastPuckPositionMmY = 0
lastPuckVelocityMmPerSY = 0
minPuckVelocityMmPerSY = -180
puckPredictionAveragedWindowSize = 5
puckPredictionAveragedArray = np.zeros(puckPredictionAveragedWindowSize)
puckPredictionAveragedIndex = 0

# Goal dimensions
goalLeftPostMmX = 254		# beginning of the left "goalpost" on X-axis (Y=0)
goalRightPostMmX = 511		# beginning of the right "goalpost" on X-axis (Y=0)
goalPostToleranceMmX = 5	# indicate how many mm right or left we need to move to fully protect goal area on X-axis (Y=0)

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

##############################################################################################
## Command line output functions
##############################################################################################

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


##############################################################################################
## CAN functions
##############################################################################################

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


##############################################################################################
## HDF5 functions
##############################################################################################


##
## Create_HDF5()
## Create/truncate logger HDF5 file (for MATLAB) using h5py library
## Example code used - http://download.nexusformat.org/sphinx/examples/h5py/index.html
##
def Create_HDF5():
	global hdf5_fileName
	global hdf5_dset_size
	global hdf5_file_handle

	# create file
	hdf5_file_handle = h5py.File(hdf5_fileName, "w")
	#dset = f.create_dataset("positions", (1000,), dtype='uint16')
	logging.debug("Created %s for logging", hdf5_fileName)

	# point to the default data to be plotted
	hdf5_file_handle.attrs['default'] = 'PC_data'
	# give the HDF5 root some more attributes
	hdf5_file_handle.attrs['file_name'] = hdf5_fileName
	hdf5_file_handle.attrs['file_time'] = str(datetime.datetime.now())
	hdf5_file_handle.attrs['creator'] = 'mc_prototype.py'
	hdf5_file_handle.attrs['project'] = 'Air Hockey Robot'
	#f.attrs[u'HDF5_Version']     = six.u(h5py.version.hdf5_version)
	#f.attrs[u'h5py_version']     = six.u(h5py.version.version)
	logging.debug("Added hdf5 attributes")

	# create the group for X-Y positions to and from PC
	h_data = hdf5_file_handle.create_group('PC_data')
	logging.debug("Created hdf5 PC_data group")

	# dataset for sent ahd received X-Y command positions to PC
	h_pos_sent_x = h_data.create_dataset("pos_sent_x", (hdf5_dset_size, ), maxshape=(None, ), dtype='uint16')
	h_pos_sent_x.attrs["units"] = "mm"
	h_pos_sent_y = h_data.create_dataset("pos_sent_y", (hdf5_dset_size, ), maxshape=(None, ), dtype='uint16')
	h_pos_sent_y.attrs["units"] = "mm"

	h_pos_rcvd_x = h_data.create_dataset("pos_rcvd_x", (hdf5_dset_size, ), maxshape=(None, ), dtype='uint16')
	h_pos_rcvd_x.attrs["units"] = "mm"
	h_pos_rcvd_y = h_data.create_dataset("pos_rcvd_y", (hdf5_dset_size, ), maxshape=(None, ), dtype='uint16')
	h_pos_rcvd_y.attrs["units"] = "mm"
	logging.debug("Created hdf5 datasets for PC sent and received X-Y positions")

	# timestamps for sent and received X-Y command positions to PC
	# no h5py support of time datatype, so will use string
	h_time_sent = h_data.create_dataset("time_sent", (hdf5_dset_size, ), maxshape=(None, ), dtype='S30')
	h_time_sent.attrs["units"] = "time"

	h_time_rcvd = h_data.create_dataset("time_rcvd", (hdf5_dset_size, ), maxshape=(None, ), dtype='S30')
	h_time_rcvd.attrs["units"] = "time"
	logging.debug("Created hdf5 datasets for PC sent and received X-Y times")

## end of method

##
## Close_HDF5()
## Close HDF5 file (for MATLAB) using h5py library
##
def Close_HDF5():
	global hdf5_file_handle
	# make sure to close the file
	hdf5_file_handle.close()
	logging.debug("Closed hdf5 file")

## end of method

##
## add_pos_sent_HDF5()
## Add new sent X-Y position and its' timestamp to HDF5 PC_data group
## ARGUMENTS: time_rcvd - timestamp of MC sent X-Y position to PC in a string format
##
def add_pos_sent_HDF5(time_rcvd):
	global hdf5_file_handle
	global hdf5_dset_count
	global mc_pos_cmd_sent_x_mm
	global mc_pos_cmd_sent_x_mm

	i = hdf5_dset_count

	# store received positions with a timestamp
	hdf5_file_handle['/PC_data/pos_sent_x'][i] = mc_pos_cmd_sent_x_mm
	hdf5_file_handle['/PC_data/pos_sent_y'][i] = mc_pos_cmd_sent_y_mm
	hdf5_file_handle['/PC_data/time_sent'][i] = time_rcvd
	logging.debug("Stored sent XY position no. %i", i)

## end of method

##
## add_pos_rcvd_HDF5()
## Add new received X-Y position and its' timestamp to HDF5 PC_data group
## ARGUMENTS: time_rcvd - timestamp of PC received X-Y position in a string format 
##
def add_pos_rcvd_HDF5(time_rcvd):
	global hdf5_file_handle
	global hdf5_dset_count
	global pc_pos_status_x_mm
	global pc_pos_status_y_mm

	i = hdf5_dset_count

	# store received positions with a timestamp
	hdf5_file_handle['/PC_data/pos_rcvd_x'][i] = pc_pos_status_x_mm
	hdf5_file_handle['/PC_data/pos_rcvd_y'][i] = pc_pos_status_y_mm
	hdf5_file_handle['/PC_data/time_rcvd'][i] = time_rcvd
	logging.debug("Stored received XY position no. %i", i)

## end of method

##
## update_dset_HDF5()
## Update counter
## Resize PC_data datasets if hdf5_dset_size is reached: Increase the size by hdf5_dset_size rows
## When reached max size of allowed elements in file stop resizing and reset counter to 0
## FAQ used - http://docs.h5py.org/en/latest/faq.html#appending-data-to-a-dataset 
##
def update_dset_HDF5():
	global hdf5_dset_size
	global hdf5_file_handle
	global hdf5_dset_count
	global hdf5_dset_stop_resize

	# increase counter
	hdf5_dset_count += 1

	# every hdf5_dset_size resize until reached hdf5_dset_max_size
	if (hdf5_dset_count % hdf5_dset_size) == 0:
		if hdf5_dset_count < hdf5_dset_max_size:
			if hdf5_dset_stop_resize is False:
				# resizing all PC_data datasets
				hdf5_file_handle['/PC_data/pos_rcvd_x'].resize((hdf5_dset_count+hdf5_dset_size, ))
				hdf5_file_handle['/PC_data/pos_rcvd_y'].resize((hdf5_dset_count+hdf5_dset_size, ))
				hdf5_file_handle['/PC_data/time_rcvd'].resize((hdf5_dset_count+hdf5_dset_size, ))
				hdf5_file_handle['/PC_data/pos_sent_x'].resize((hdf5_dset_count+hdf5_dset_size, ))
				hdf5_file_handle['/PC_data/pos_sent_y'].resize((hdf5_dset_count+hdf5_dset_size, ))
				hdf5_file_handle['/PC_data/time_sent'].resize((hdf5_dset_count+hdf5_dset_size, ))
				logging.debug("Resized all hdf5 PC_data datasets to %i", hdf5_dset_count+hdf5_dset_size)
		else:
			hdf5_dset_count = 0
			hdf5_dset_stop_resize = True

## end of method


##############################################################################################
## IPC functions
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
		global uiProcess
		global ptProcess

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
## Uninit_IPC() - Need to add error detection
## Uninitialize multiprocessing between UI, Puck Tracker and MC
##
if __debug__:
	def Uninit_IPC():
		global dataToUI
		global dataFromUI
		global dataToPT
		global dataFromPT
		global uiProcess
		global ptProcess

		# close queues for bidirectional communication with other processes
		dataToUI.close()
		dataFromUI.close()
		dataToPT.close()
		dataFromPT.close()
		logging.debug("Closed IPC queues")

		time.sleep(0.5)

		# terminate seperate processes for the UI and Puck Tracker 
		uiProcess.terminate()
		logging.debug("Terminated UI process")
		ptProcess.terminate()
		logging.debug("Terminated Puck Tracker process")

## end of method

##
## Rx_IPC() -  Need to add error detection
## Receive any pending IPC Queue messages and populate global variables as necessary
##
if __debug__:
	def Rx_IPC():
		global operationMode
		global dataToUI
		global dataFromUI
		global dataToPT
		global dataFromPT

		global mc_pos_cmd_x_mm
		global mc_pos_cmd_y_mm

		global puckPositionMmX
		global puckPositionMmY
		global puckVelocityMmPerSX 
		global puckVelocityMmPerSY

		# get data from Puck tracker
		try:
			ptData = dataFromPT.get(False)
			logging.debug(str(ptData))

			# set flag that indicates we are in MC-decisions mode
			operationMode = 0
			logging.debug("We are in MC-decision control mode")
			
			#string manipulation
			ptData = ptData.split(":")
			if ptData[0] == "puck_position_mm_x":
				puckPositionMmX = int(ptData[1])
			elif ptData[0] == "puck_position_mm_y":
				puckPositionMmY = int(ptData[1])
			elif ptData[0] == "puck_velocity_mmps_x":
				puckVelocityMmPerSX = int(ptData[1])
			elif ptData[0] == "puck_velocity_mmps_y":
				puckVelocityMmPerSY = int(ptData[1])

		except Queue.Empty:
			ptData = 0
		else:
			logging.debug("ptData: %s", ptData)
			if ptData == "Calibration Complete":
				dataToPT.put("TrackPuck")

		# get data from UI
		try:
			uiData = dataFromUI.get(False)
			logging.debug(str(uiData))

			# set flag that indicates we are in UI mode
			operationMode = 1 
			logging.debug("We are in UI manual control mode")

			#string manipulation
			uiData = uiData.split(":")
			if uiData[0] == "paddle_position_mm_x":
				mc_pos_cmd_x_mm = int(uiData[1])
			elif uiData[0] == "paddle_position_mm_y":
				mc_pos_cmd_y_mm = int(uiData[1])

		except Queue.Empty:
			uiData = 0
		else:
			logging.debug(str(uiData))

## end of method

##############################################################################################
## Decision Making/Logic functions
##############################################################################################

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
## get_paddle_defense_position(device)
## Calculates linear trajectory of the puck based on XY positions and Y velocity
## Outputs XY (y=0) position for the paddle to defend goal from an oncoming puck
##
def get_paddle_defense_position():
	global puckPositionMmX
	global puckPositionMmY
	global puckVelocityMmPerSX 
	global puckVelocityMmPerSY
	global lastPuckPositionMmX
	global lastPuckPositionMmY
	global lastPuckVelocityMmPerSY
	global puckPredictionAveragedArray
	global puckPredictionAveragedWindowSize
	global puckPredictionAveragedIndex
	global minPuckVelocityMmPerSY

	global goalRightPostMmX
	global goalLeftPostMmX
	global goalPostToleranceMmX

	global 	mc_pos_cmd_x_mm
	global mc_pos_cmd_y_mm
	
	puckPredictionMmX = 0
	puckPredictionAveragedMmX = 0
	
	# check if the puck is moving towards the robot
	if puckVelocityMmPerSY < minPuckVelocityMmPerSY:
		# using the equation of a line y = mx + b, find predicted x position when y = 0
		vectorY = int(puckPositionMmY - lastPuckPositionMmY)
		vectorX = int(puckPositionMmX - lastPuckPositionMmX)
		
		if vectorX == 0:
			# avoid divide by zero
			slope = 999999
		else:
			slope = vectorY/vectorX
		
		# b = y - mx
		yIntercept = puckPositionMmY - (slope * puckPositionMmX)
		
		if slope != 0:
			puckPredictionMmX = -yIntercept / slope
		else:
			puckPredictionMmX = 0
			
		# now that we have a predicted x position, take an average to improve accuracy  
		puckPredictionAveragedArray[puckPredictionAveragedIndex] = puckPredictionMmX
		numNonZeroValues = np.count_nonzero(puckPredictionAveragedArray)
		
		if numNonZeroValues != 0:
			puckPredictionAveragedMmX = (np.sum(puckPredictionAveragedArray)) / numNonZeroValues
		else:
			puckPredictionAveragedMmX = 0
		
		# manage index for array
		puckPredictionAveragedIndex += 1
		if puckPredictionAveragedIndex < puckPredictionAveragedWindowSize:
			pass
		else:
			puckPredictionAveragedIndex = 0
			
	if puckVelocityMmPerSY > minPuckVelocityMmPerSY and lastPuckVelocityMmPerSY < minPuckVelocityMmPerSY:
		puckPredictionAveragedArray.fill(0)
		puckPredictionAveragedIndex = 0

	lastPuckVelocityMmPerSY = puckVelocityMmPerSY
	lastPuckPositionMmX = puckPositionMmX
	lastPuckPositionMmY = puckPositionMmY

	logging.debug("Puck final trajectory position (before goalpost correction) is: %i,0", puckPredictionAveragedMmX)
	
	# Goal post correction
	# puck pos before left goalpost then set to the left goalpost_pos-tolerance
	if puckPredictionAveragedMmX < goalLeftPostMmX:
		puckPredictionAveragedMmX = goalLeftPostMmX - goalPostToleranceMmX
	# puck pos after right goalpost then set to the right goalpost_pos+tolerance
	elif puckPredictionAveragedMmX > goalRightPostMmX:
		puckPredictionAveragedMmX = goalRightPostMmX + goalPostToleranceMmX	

	logging.debug("Paddle defense position is: %i,0", puckPredictionAveragedMmX)

	mc_pos_cmd_x_mm = puckPredictionAveragedMmX
	mc_pos_cmd_y_mm = 0

## end of method

##############################################################################################
## MAIN() function
##############################################################################################

## 
## main()
##
def main():
	global log_fileName

	# Create and set format of the logging file
	# If you want to disable the logger then set "level=logging.ERROR"
	logging.basicConfig(filename=log_fileName, filemode='w', level=logging.DEBUG,
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
			Rx_IPC()
			# get defense pos for paddle if in MC-decisions mode
			if operationMode == 0:
				get_paddle_defense_position()
			# UI manual control mode (enable jitter filter)
			elif operationMode == 1:
				filter_Tx_PC_Cmd()
			Tx_PC_Cmd(PCAN)
			add_pos_sent_HDF5(str(datetime.datetime.now()))
			update_display()
			Rx_CAN(PCAN)
			add_pos_rcvd_HDF5(str(datetime.datetime.now()))
			update_dset_HDF5()
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
			filter_Tx_PC_Cmd()
			#Tx_PC_Cmd(PCAN)
			add_pos_sent_HDF5(str(datetime.datetime.now()))
			update_display()
			#Rx_CAN(PCAN)
			add_pos_rcvd_HDF5(str(datetime.datetime.now()))
			update_dset_HDF5()
			sleep(timeout)

	#"""

## end of method

try:
	main()
except KeyboardInterrupt:
	print " "
	Close_HDF5()
	Uninit_PCAN(PCAN)
	Uninit_IPC()


##############################################################################################
## Garbage
##############################################################################################
def playground(device):

	if (pc_pos_status_x_mm != mc_pos_cmd_x_mm) or (pc_pos_status_y_mm != mc_pos_cmd_y_mm):
		Tx_PC_Cmd(PCAN)