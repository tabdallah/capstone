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
logging.basicConfig(filename='example.log', level=logging.DEBUG)
logging.debug('Test')
import h5py
import numpy as np
import datetime
import time
import json
import cv2

# add file path for puck tracker and user interface modules
sys.path.insert(0, '../../../3_Puck_Tracker/1_Software/1_Source/')
sys.path.insert(0, '../../../6_User_Interface/1_Software/1_Source/')

# path to settings file
settings_path = "../../../6_User_Interface/1_Software/4_Json/"

# libraries for IPC with UI and PC
import multiprocessing
import puck_tracker as pt
import user_interface as ui

# Initialize an instance of the PCANBasic class
PCAN = PCANBasic() 		

##############################################################################################
## Global data storage
## Maybe improve this later
##############################################################################################

log_fileName = "debug.log"		# File name for debug logging

timeout = 0.005 			# Timeout for keyboard input in seconds

operation_mode = 0		# Indicates whether MC decisions(0) or UI (1) control the Paddle 

# enums
pt_state_cmd_enum = 0
pt_state_enum = 0
pt_error_enum = 0
pt_rx_enum = 0
pt_tx_enum = 0
ui_state_cmd_enum = 0
ui_state_enum = 0
ui_error_enum = 0
ui_rx_enum = 0
ui_tx_enum = 0
ui_diagnostic_request_enum = 0
ui_game_state = 0
ui_screen = 0
ui_goal_enum = 0

settings = 0

# PC positions
mc_pos_cmd_x_mm = 0
mc_pos_cmd_y_mm = 0
mc_pos_cmd_sent_x_mm = 0
mc_pos_cmd_sent_y_mm = 0
pc_pos_status_x_mm = 0
pc_pos_status_y_mm = 0
filter_pos_value_mm = 5		# Threshold filter value for the UI position control

# IPC 
ui_rx = 0
ui_tx = 0
pt_rx = 0
pt_tx = 0
ui_process = 0
pt_process = 0
ui_visualization_tx = 0
pt_visualization_rx = 0

# hdf5
hdf5_fileName = "PC_positions.hdf5"		# File name for hdf5 with PC positions
hdf5_dset_size = 1000 			# dataset total number of elements for hdf5
hdf5_dset_max_size = 30000 		# dataset max number of elements  after resize when we reset the counter for hdf5
hdf5_dset_stop_resize = False	# flag that indicates whether to continue dataset resize or not
hdf5_dset_count = 0				# count to track current element in hdf5 PC_data dataset
hdf5_file_handle = 0			# handle to hdf5 file

# object dimensions & distances
table_width_mm = 774.7
table_length_mm = 1692.3
puck_radius_mm = 31.75
paddle_radius_mm = 40
goal_center_mm_x = 387.35
goal_left_post_mm_x = 257.35
goal_right_post_mm_x = 517.35

# general
pt_state = 0
pt_error = 0
ui_state = 0
ui_error = 0
ui_diagnostic_request = 0
game_mode = 0

# puck prediction
puck_position_mm_x = 0
puck_position_mm_y = 0
puck_velocity_mmps_x = 0
puck_velocity_mmps_y = 0
last_puck_position_mm_x = 0
last_puck_position_mm_y = 0
last_puck_velocity_mmps_y = 0
last_puck_prediction_averaged_mm_x = goal_center_mm_x
min_puck_velocity_mmps_y = -250
puck_prediction_averaged_window_size = 4
puck_prediction_averaged_array = np.zeros(puck_prediction_averaged_window_size)
puck_prediction_averaged_index = 0
paddle_offense_position_mm_y = 300
paddle_defense_position_mm_y = 0

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
## Enumeration functions
##############################################################################################

##
## enum(list)
## Creates an enumeration for a list of elements
##
def enum(list):
	enums = dict(zip(list, range(len(list))))
	return type('Enum', (), enums)

##
## get_enums()
## Retrieve all enums from settings file
##
def get_enums():
	global pt_state_cmd_enum
	global pt_state_enum
	global pt_error_enum
	global pt_rx_enum
	global pt_tx_enum

	global ui_state_cmd_enum
	global ui_state_enum
	global ui_error_enum
	global ui_rx_enum
	global ui_tx_enum
	global ui_diagnostic_request_enum
	global ui_game_state_enum
	global ui_screen_enum
	global ui_goal_enum

	global settings

	# get settings from file
	with open((settings_path + 'settings.json'), 'r') as fp:
		settings = json.load(fp)
		fp.close()

	pt_state_cmd_enum = enum(settings['puck_tracker']['enumerations']['pt_state_cmd'])
	pt_state_enum = enum(settings['puck_tracker']['enumerations']['pt_state'])
	pt_error_enum = enum(settings['puck_tracker']['enumerations']['pt_error'])   
	pt_rx_enum = enum(settings['puck_tracker']['enumerations']['pt_rx'])
	pt_tx_enum = enum(settings['puck_tracker']['enumerations']['pt_tx'])

	ui_state_cmd_enum = enum(settings['user_interface']['enumerations']['ui_state_cmd'])
	ui_state_enum = enum(settings['user_interface']['enumerations']['ui_state'])
	ui_error_enum = enum(settings['user_interface']['enumerations']['ui_error'])   
	ui_rx_enum = enum(settings['user_interface']['enumerations']['ui_rx'])
	ui_tx_enum = enum(settings['user_interface']['enumerations']['ui_tx'])
	ui_diagnostic_request_enum = enum(settings['user_interface']['enumerations']['ui_diagnostic_request'])
	ui_game_state_enum = enum(settings['user_interface']['enumerations']['ui_game_state'])
	ui_screen_enum = enum(settings['user_interface']['enumerations']['ui_screen'])
	ui_goal_enum = enum(settings['user_interface']['enumerations']['ui_goal'])

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
## Show master controller status and command
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
		logging.error("Error Initializing PCAN USB")
		logging.error(PCANBasic.GetErrorText(device, status, 0))
	else:
		logging.debug("PCAN USB Initialized")

## end of method


###
## Uninit_PCAN()
## Uninitialize the PCAN USB Dongle & check for errors
##
def Uninit_PCAN(device):
	status = PCANBasic.Uninitialize(device, PCAN_USBBUS1)
	if status > 0:
		logging.error("Error Uninitializing PCAN USB")
		logging.error(PCANBasic.GetErrorText(device, status, 0))
	else:
		logging.debug("PCAN USB Uninitialized")

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

	# store received positions with a puck_position_mm_xtimestamp
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
## Create arrays between those processes for IPC
## start child processes
##
def Init_IPC():
	global ui_rx
	global ui_tx
	global ui_rx_enum
	global ui_tx_enum
	global ui_state_cmd_enum
	global ui_process
	global pt_rx
	global pt_tx
	global pt_rx_enum
	global pt_tx_enum
	global pt_state_cmd_enum
	global pt_process
	global ui_visualization_tx
	global pt_visualization_rx

	# create arrays for bidirectional communication with other processes
	ui_rx = multiprocessing.Array('f', len(settings['user_interface']['enumerations']['ui_rx']))
	ui_tx = multiprocessing.Array('f', len(settings['user_interface']['enumerations']['ui_tx']))
	pt_rx = multiprocessing.Array('f', len(settings['puck_tracker']['enumerations']['pt_rx']))
	pt_tx = multiprocessing.Array('f', len(settings['puck_tracker']['enumerations']['pt_tx']))
	pt_visualization_rx, pt_visualization_tx = multiprocessing.Pipe()
	ui_visualization_rx, ui_visualization_tx = multiprocessing.Pipe()
	logging.debug("Created IPC Arrays & Pipe")

	# create seperate processes for the User Interface and Puck Tracker and give them Arrays & Pipe for IPC
	ui_process = multiprocessing.Process(target=ui.ui_process, name="ui", args=(ui_rx, ui_tx, ui_visualization_rx))
	logging.debug("Created User Interface process with Arrays and a Pipe")
	pt_process = multiprocessing.Process(target=pt.pt_process, name="pt", args=(pt_rx, pt_tx, pt_visualization_tx))
	logging.debug("Created Puck Tracker process with Arrays and a Pipe")

	# start child processes
	ui_process.start()
	logging.debug("Started User Interface process")
	pt_process.start()
	logging.debug("Started Puck Tracker process")

	ui_rx[ui_rx_enum.state_cmd] = ui_state_cmd_enum.run
	pt_rx[pt_rx_enum.state_cmd] = pt_state_cmd_enum.track

## end of method

##
## Uninit_IPC() - Need to add error detection
## Uninitialize multiprocessing between UI, Puck Tracker and MC
##
def Uninit_IPC():
	global ui_process
	global pt_process

	# terminate seperate processes User Interface and Puck Tracker 
	ui_process.terminate()
	logging.debug("Terminated User Interface process")
	pt_process.terminate()
	logging.debug("Terminated Puck Tracker process")

## end of method

##
## Rx_IPC() -  Need to add error detection
## Receive any pending IPC Queue messages and populate global variables as necessary
##
def Rx_IPC():
	global puck_position_mm_x
	global puck_position_mm_y
	global puck_velocity_mmps_x 
	global puck_velocity_mmps_y
	global pt_state
	global pt_error
	global ui_state
	global ui_error
	global ui_diagnostic_request
	global ui_game_state
	global ui_screen

	# get data from puck tracker
	pt_state = int(pt_tx[pt_tx_enum.state])
	pt_error = int(pt_tx[pt_tx_enum.error])
	puck_position_mm_x = pt_tx[pt_tx_enum.puck_position_x]
	puck_position_mm_y = pt_tx[pt_tx_enum.puck_position_y]
	puck_velocity_mmps_x = pt_tx[pt_tx_enum.puck_velocity_x]
	puck_velocity_mmps_y = pt_tx[pt_tx_enum.puck_velocity_y]

	# get data from user interface
	ui_state = int(ui_tx[ui_tx_enum.state])
	ui_error = int(ui_tx[ui_tx_enum.error])
	ui_diagnostic_request = int(ui_tx[ui_tx_enum.diagnostic_request])
	ui_game_state = int(ui_tx[ui_tx_enum.game_state])
	ui_screen = int(ui_tx[ui_tx_enum.screen])

	# clear one time messages
	ui_tx[ui_tx_enum.diagnostic_request] = ui_diagnostic_request_enum.idle
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
## get_paddle_position()
## Calculates linear trajectory of the puck based on XY positions and Y velocity
## Outputs XY position for the paddle
##
def get_paddle_position():
	global last_puck_position_mm_x
	global last_puck_position_mm_y
	global last_puck_velocity_mmps_y
	global last_puck_prediction_averaged_mm_x
	global puck_prediction_averaged_array
	global puck_prediction_averaged_index
	global mc_pos_cmd_x_mm
	global mc_pos_cmd_y_mm
	
	mm_per_pixel_y = 2.95335951134
	mm_per_pixel_x = 1.7139380531

	# get frame for visualization
	if pt_visualization_rx.poll():
		frame_received = True
		while(pt_visualization_rx.poll()):
			frame = pt_visualization_rx.recv()
	else:
		frame_received = False

	# set the target paddle position based on game mode
	if game_mode == 1: # 1 means offense right now, TODO: Enum this
		paddle_target_position_mm_y = paddle_offense_position_mm_y
	else:
		paddle_target_position_mm_y = paddle_defense_position_mm_y

	# default paddle position
	paddle_position_mm_x = last_puck_prediction_averaged_mm_x
	paddle_position_mm_y = 0

	# predicting the x axis position of the puck	
	puck_prediction_mm_x = 0
	
	# check if the puck is moving towards the robot, if yes: DEFEND!
	if puck_velocity_mmps_y < min_puck_velocity_mmps_y:
		# using the equation of a line y = mx + b, find predicted x position when y = 0
		vector_mm_x = puck_position_mm_x - last_puck_position_mm_x
		vector_mm_y = puck_position_mm_y - last_puck_position_mm_y
		
		if vector_mm_x == 0:
			# avoid divide by zero
			slope = 999999
		else:
			slope = vector_mm_y/vector_mm_x
		
		# b = y - mx
		intercept_mm_y = puck_position_mm_y - (slope * puck_position_mm_x)
		
		# x = (y - b)/m
		puck_prediction_mm_x = ((paddle_target_position_mm_y + paddle_radius_mm) - intercept_mm_y) / slope

		# predict bounces and get a real x prediction
		bounce_count = 0
		while True:
			if (table_width_mm - puck_radius_mm) >= puck_prediction_mm_x >= puck_radius_mm:
				if frame_received:
					if bounce_count == 0:
						cv2.line(frame, (int(puck_position_mm_y/mm_per_pixel_y), int(puck_position_mm_x/mm_per_pixel_x)), (int((paddle_target_position_mm_y + paddle_radius_mm)/mm_per_pixel_y), int(puck_prediction_mm_x/mm_per_pixel_x)), (255,0,0), 3)
					else:
						cv2.line(frame, (int(last_bounce_mm_y/mm_per_pixel_y), int(last_bounce_mm_x/mm_per_pixel_x)), (int((paddle_target_position_mm_y + paddle_radius_mm)/mm_per_pixel_y), int(puck_prediction_mm_x/mm_per_pixel_x)), (255,0,0), 3)
				break

			elif puck_prediction_mm_x < puck_radius_mm:
				bounce_mm_y = (slope * puck_radius_mm) + intercept_mm_y
				bounce_mm_x = puck_radius_mm
				slope = -slope
				intercept_mm_y = bounce_mm_y - (slope * puck_radius_mm)
				puck_prediction_mm_x = ((paddle_target_position_mm_y + paddle_radius_mm) - intercept_mm_y) / slope
				if frame_received:
					if bounce_count == 0:
						cv2.line(frame, (int(puck_position_mm_y/mm_per_pixel_y), int(puck_position_mm_x/mm_per_pixel_x)), (int(bounce_mm_y/mm_per_pixel_y), int(bounce_mm_x/mm_per_pixel_x)), (255,0,0), 3)
					else:
						cv2.line(frame, (int(last_bounce_mm_y/mm_per_pixel_y), int(last_bounce_mm_x/mm_per_pixel_x)), (int((bounce_mm_y)/mm_per_pixel_y), int(bounce_mm_x/mm_per_pixel_x)), (255,0,0), 3)

			elif puck_prediction_mm_x > (table_width_mm - puck_radius_mm):
				bounce_mm_y = (slope * (table_width_mm - puck_radius_mm)) + intercept_mm_y
				bounce_mm_x = (table_width_mm - puck_radius_mm)
				slope = -slope
				intercept_mm_y = bounce_mm_y - (slope * (table_width_mm - puck_radius_mm))
				puck_prediction_mm_x = ((paddle_target_position_mm_y + paddle_radius_mm) - intercept_mm_y) / slope
				if frame_received:
					if bounce_count == 0:
						cv2.line(frame, (int(puck_position_mm_y/mm_per_pixel_y), int(puck_position_mm_x/mm_per_pixel_x)), (int(bounce_mm_y/mm_per_pixel_y), int(bounce_mm_x/mm_per_pixel_x)), (255,0,0), 3)
					else:
						cv2.line(frame, (int(last_bounce_mm_y/mm_per_pixel_y), int(last_bounce_mm_x/mm_per_pixel_x)), (int((bounce_mm_y)/mm_per_pixel_y), int(bounce_mm_x/mm_per_pixel_x)), (255,0,0), 3)
						
			last_bounce_mm_y = bounce_mm_y
			last_bounce_mm_x = bounce_mm_x
			bounce_count += 1

		# draw a circle around the raw desired paddle position
		if frame_received:
			cv2.circle(frame, (int((paddle_target_position_mm_y + paddle_radius_mm)/mm_per_pixel_y), int(puck_prediction_mm_x/mm_per_pixel_x)), 10, (0, 0, 255), 2)

		# now that we have a predicted x position, take an average to improve accuracy  
		puck_prediction_averaged_array[puck_prediction_averaged_index] = puck_prediction_mm_x
		number_non_zero_values = np.count_nonzero(puck_prediction_averaged_array)
		if number_non_zero_values != 0:
			puck_prediction_averaged_mm_x = (np.sum(puck_prediction_averaged_array)) / number_non_zero_values
		else:
			puck_prediction_averaged_mm_x = 0
		
		# manage index for array
		puck_prediction_averaged_index += 1
		if puck_prediction_averaged_index >= puck_prediction_averaged_window_size:
			puck_prediction_averaged_index = 0

		# draw a circle around the averaged desired paddle position
		if frame_received:
			cv2.circle(frame, (int((paddle_target_position_mm_y + paddle_radius_mm)/mm_per_pixel_y), int(puck_prediction_averaged_mm_x/mm_per_pixel_x)), 10, (0, 255, 255), 2)

		if game_mode == 0: # only goal post correct if defense
			# Goal post correction
			if puck_prediction_averaged_mm_x < goal_left_post_mm_x:
				puck_prediction_averaged_mm_x = goal_left_post_mm_x
			# puck pos after right goalpost then set to the right goalpost_pos+tolerance
			elif puck_prediction_averaged_mm_x > goal_right_post_mm_x:
				puck_prediction_averaged_mm_x = goal_right_post_mm_x

		# set paddle position
		paddle_position_mm_x = puck_prediction_averaged_mm_x
		paddle_position_mm_y = paddle_target_position_mm_y

	if (puck_velocity_mmps_y > min_puck_velocity_mmps_y) and (last_puck_velocity_mmps_y < min_puck_velocity_mmps_y):
		puck_prediction_averaged_array.fill(0)
		puck_prediction_averaged_index = 0
		paddle_position_mm_x = goal_center_mm_x
		paddle_position_mm_y = 0

	# send frame
	if frame_received:
		frame = cv2.resize(frame, dsize=(800,600), interpolation=cv2.INTER_LINEAR)
		ui_visualization_tx.send(frame)

	last_puck_velocity_mmps_y = puck_velocity_mmps_y
	last_puck_position_mm_x = puck_position_mm_x
	last_puck_position_mm_y = puck_position_mm_y
	last_puck_prediction_averaged_mm_x = paddle_position_mm_x

	logging.debug("Paddle defense position is: %i,0", paddle_position_mm_x)

	mc_pos_cmd_x_mm = int(paddle_position_mm_x)
	mc_pos_cmd_y_mm = int(paddle_position_mm_y)

## end of method

def make_decisions():
	
	get_paddle_position()

	# TODO get real data for these vars
	mc_state = 0
	mc_error = 0
	pc_state = 0
	pc_error = 0

	# pass state data to the UI
	ui_rx[ui_rx_enum.pt_state] = pt_state
	ui_rx[ui_rx_enum.pt_error] = pt_error
	ui_rx[ui_rx_enum.mc_state] = mc_state
	ui_rx[ui_rx_enum.mc_error] = mc_error
	ui_rx[ui_rx_enum.pc_state] = pc_state
	ui_rx[ui_rx_enum.pc_error] = pc_error

	# check which UI screen we are on, this dictates a large part of what state we'll be in
	if ui_screen == ui_screen_enum.visual:
		if ui_game_state == ui_game_state_enum.playing:
			Tx_PC_Cmd(PCAN)
		elif ui_game_state == ui_game_state_enum.stopped:
			pass
	elif ui_screen == ui_screen_enum.diagnostic:
		if ui_diagnostic_request == ui_diagnostic_request_enum.calibrate_pt:
			pt_rx[pt_rx_enum.state_cmd] = pt_state_cmd_enum.calibrate

	# go through steps of shutting down if UI requests
	if ui_state == ui_state_enum.quit:
		pt_rx[pt_rx_enum.state_cmd] = pt_state_cmd_enum.quit

	if pt_state == pt_state_enum.quit:
		ui_rx[ui_rx_enum.state_cmd] = ui_state_cmd_enum.quit
	elif pt_state == pt_state_enum.calibrated:
		pt_rx[pt_rx_enum.state_cmd] = pt_state_cmd_enum.track

	if (ui_state == ui_state_enum.quit and
		pt_state == pt_state_enum.quit):
		Close_HDF5()
		Uninit_PCAN(PCAN)
		quit(0)

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
	logging.basicConfig(filename=log_fileName, filemode='w', level=logging.DEBUG, format='%(asctime)s in %(funcName)s(): %(levelname)s *** %(message)s')

	# Create enums
	get_enums()

	# Initialize PCAN device
	Init_PCAN(PCAN)

	# Create HDF5 file for logging PC position data
	Create_HDF5()

	# Initialize IPC between MC - PC - UI
	Init_IPC()

	# Master Controller State Machine
	while True:
		Rx_IPC()
		Rx_CAN(PCAN)
		#add_pos_rcvd_HDF5(str(datetime.datetime.now()))
		make_decisions()
		#Tx_PC_Cmd(PCAN)
		#add_pos_sent_HDF5(str(datetime.datetime.now()))
		#update_dset_HDF5()
		sleep(timeout)

## end of method

try:
	main()
except KeyboardInterrupt:
	pass
	#Close_HDF5()
	#Uninit_PCAN(PCAN)
	#Uninit_IPC()

##############################################################################################
## Garbage
##############################################################################################
def playground(device):

	if (pc_pos_status_x_mm != mc_pos_cmd_x_mm) or (pc_pos_status_y_mm != mc_pos_cmd_y_mm):
		Tx_PC_Cmd(PCAN)