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
import h5py
import numpy as np
import datetime
import time
import json
import cv2
import Queue

### DO NOT CHANGE logging setup! now Kivy logger works with default python logger
# Create and set format of the logging file
import logging
logging.basicConfig(filename='debug.log', filemode='w', format='%(asctime)s: %(levelname)s *** %(message)s')

#os.environ["KIVY_NO_FILELOG"] = "1"
os.environ["KIVY_NO_CONSOLELOG"] = "1"

# To disable the logger change 'log_level' from 'debug' to 'error'
from kivy.config import Config 
Config.set('kivy', 'log_level', 'info')
Config.write()

# Replace default logger with Kivy logger
from kivy.logger import logging
### END logging setup

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
##############################################################################################

# master controller loop delay
timeout = 0.005

# object dimensions & distances
table_width_mm_x = 774.7
table_length_mm_y = 1692.3
puck_radius_mm = 31.75
paddle_radius_mm = 48
goal_center_mm_x = 387.35
goal_left_post_mm_x = 257.35
goal_right_post_mm_x = 517.35

# CAN Communication (MC-PC and PC-MC) 
# PC positions
mc_pos_cmd_mm_x = goal_center_mm_x
mc_pos_cmd_mm_y = 0
mc_pos_cmd_sent_mm_x = goal_center_mm_x
mc_pos_cmd_sent_mm_y = 0
pc_pos_status_mm_x = 0
pc_pos_status_mm_y = 0
filter_pos_value_mm = 5		# Threshold filter value for the UI position control

# Motor Speed
mc_motor_speed_cmd_x = 2
mc_motor_speed_cmd_y = 2
pc_motor_speed_x = 2	
pc_motor_speed_y = 2

# State	
pc_state_cmd = 0 # command pc to go to such state
pc_state = 0
pc_error = 0

# Other
pc_goal_scored = 0
mc_cmd_pc_debug = 0		# for debug purposes in mc_cmd_pc msg 
pc_status_debug = 0		# for debug purposes in pc_status msg 

# hdf5
hdf5_fileName = "PC_positions.hdf5"		# File name for hdf5 with PC positions
hdf5_dset_size = 1000 			# dataset total number of elements for hdf5
hdf5_dset_max_size = 30000 		# dataset max number of elements  after resize when we reset the counter for hdf5
hdf5_dset_stop_resize = False	# flag that indicates whether to continue dataset resize or not
hdf5_dset_count = 0				# count to track current element in hdf5 PC_data dataset
hdf5_file_handle = 0			# handle to hdf5 file

# general
pt_state = 0
pt_error = 0
ui_state = 0
ui_error = 0
mc_state = 0
mc_error = 0
ui_diagnostic_request = 0

# puck prediction
puck_position_mm_x = 0
puck_position_mm_y = 0
puck_velocity_mmps_x = 0
puck_velocity_mmps_y = 0
last_puck_position_mm_x = 0
last_puck_position_mm_y = 0
paddle_position_averaged_window_size = 3
paddle_position_averaged_array = np.zeros(paddle_position_averaged_window_size)
paddle_position_averaged_index = 0
paddle_offense_position_mm_y = 500
paddle_defense_position_mm_y = 0
paddle_position_mm_x = 0
attack_line_mm_y = 400
defense_line_mm_y = 0
min_puck_velocity_mmps_y = -400
puck_velocity_stopped_low_mmps_y = -400
puck_velocity_stopped_high_mmps_y = 400
offense_sm_state = 0
last_offense_sm_state = 0
defense_sm_state = 0
last_defense_sm_state = 0


##############################################################################################
## CAN protocol definition
## Refer to: https://github.com/tabdallah/capstone/blob/master/1_Planning/System_Interface_Design.xlsx
##############################################################################################

# CAN message ID's
ID_mc_cmd_pc =		0x100		# CAN message ID for Master Controller Command to PC on X and Y position
ID_pc_status = 		0x101 		# CAN message ID for Paddle Controller Status

# CAN signal masks for Tx
mask_pos_cmd_mm_x_b0 		=	0x00FF		# Hex mask for pos_cmd_mm_x signal (msg byte0)
mask_pos_cmd_mm_x_b1 		=	0xFF00		# Hex mask for pos_cmd_mm_x signal (msg byte1)
mask_pos_cmd_mm_y_b2 		=	0x00FF		# Hex mask for pos_cmd_mm_y signal (msg byte2)
mask_pos_cmd_mm_y_b3		=	0xFF00		# Hex mask for pos_cmd_mm_y signal (msg byte3)
mask_motor_speed_cmd_x_b4 	=	0x0003		# Hex mask for motor_speed_cmd_x signal (msg byte4) 	
mask_motor_speed_cmd_y_b4 	=	0x000C		# Hex mask for motor_speed_cmd_y signal (msg byte4)

# CAN signal masks for Rx
mask_motor_speed_x_b4 		=	0x0003		# Hex mask for motor_speed_x signal (msg byte4) 	
mask_motor_speed_y_b4 		=	0x000C		# Hex mask for motor_speed_y signal (msg byte4)
mask_goal_scored_b4			=	0x00F0		# Hex mask for goal_scored signal (msg byte5)

##############################################################################################
## Enumeration functions
##############################################################################################

##
## enum(list)
## Creates an enumeration for a list of elements
##
def enum(list_of_enums):
    enums = dict(zip(list_of_enums, range(len(list_of_enums))))
    reverse = dict((value, key) for key, value in enums.iteritems())
    enums['reverse_mapping'] = reverse
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
	global ui_goal_scored_enum
	global ui_game_speed_enum
	global ui_game_mode_enum
	global ui_paddle_pos_enum

	global pc_motor_speed_y_enum 
	global pc_motor_speed_x_enum 
	global pc_state_enum
	global pc_state_cmd_enum
	global pc_error_enum

	global mc_state_enum
	global mc_error_enum
	global mc_control_state_machine_enum

	global settings

	# get settings from file 	TODO - error check
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
	ui_goal_scored_enum = enum(settings['user_interface']['enumerations']['ui_goal_scored'])
	ui_game_speed_enum = enum(settings['user_interface']['enumerations']['ui_game_speed'])
	ui_game_mode_enum = enum(settings['user_interface']['enumerations']['ui_game_mode'])

	mc_control_state_machine_enum = enum(settings['master_controller']['enumerations']['mc_control_state_machine'])
	mc_state_enum = enum(settings['master_controller']['enumerations']['mc_state'])
	mc_error_enum = enum(settings['master_controller']['enumerations']['mc_error'])	

	pc_state_enum = enum(settings['paddle_controller']['enumerations']['pc_state'])
	pc_state_cmd_enum = enum(settings['paddle_controller']['enumerations']['pc_state_cmd'])
	pc_error_enum = enum(settings['paddle_controller']['enumerations']['pc_error'])
	pc_motor_speed_x_enum = enum(settings['paddle_controller']['enumerations']['pc_motor_speed_x'])
	pc_motor_speed_y_enum = enum(settings['paddle_controller']['enumerations']['pc_motor_speed_y'])

##############################################################################################
## Retrieve Settings from JSON
##############################################################################################

##
## get_settings()
## Retrieve settings for all modules from JSON file
##
def get_settings():
	global mm_per_pixel_x
	global mm_per_pixel_y
	global settings

	# get settings from file 	TODO - error check
	with open((settings_path + 'settings.json'), 'r') as fp:
		settings = json.load(fp)
		fp.close()

	mm_per_pixel_x = settings['puck_tracker']['scaling_factors']['mm_per_pixel_y']
	mm_per_pixel_y = settings['puck_tracker']['scaling_factors']['mm_per_pixel_x']

##############################################################################################
## CAN functions
##############################################################################################

##
## init_PCAN()
## Initialize the PCAN USB Dongle & Check for Errors
## Resets Tx & Rx queues
##
def init_PCAN(device):
	global mc_state
	global mc_error
	
	status = PCANBasic.Initialize(device, PCAN_USBBUS1, PCAN_BAUD_125K)
	PCANBasic.Reset(device, PCAN_USBBUS1) #TODO - why is this necessary?
	
	if status > 0:
		logging.error("Error Initializing PCAN USB")
		logging.error(PCANBasic.GetErrorText(device, status, 0))
		mc_state = mc_state_enum.error
		mc_error = mc_error_enum.pcan
	else:
		logging.info("PCAN USB Initialized")

## end of function

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
		logging.info("PCAN USB Uninitialized")

## end of function

##
## rx_CAN(device)
## Receive any pending CAN messages and populate global variables as necessary
##
def rx_CAN(device):
	global pc_pos_status_mm_x
	global pc_pos_status_mm_y
	global pc_state
	global pc_error
	global pc_goal_scored
	global pc_motor_speed_y
	global pc_motor_speed_x
	global pc_status_debug

	message = PCANBasic.Read(PCAN, PCAN_USBBUS1)
	#print "thing", message

	# Keep reading messages until there aren't any more
	while message[1].ID > 1:
		# Process PC Status X message
		if message[1].ID == ID_pc_status:
			pc_pos_status_mm_x_b0 = message[1].DATA[0]
			pc_pos_status_mm_x_b1 = message[1].DATA[1]
			pc_pos_status_mm_x = pc_pos_status_mm_x_b0 | (pc_pos_status_mm_x_b1 << 8)
			logging.debug("Incoming message from PC: Paddle Pos X: %s", pc_pos_status_mm_x)

			pc_pos_status_mm_y_b2 = message[1].DATA[2]
			pc_pos_status_mm_y_b3 = message[1].DATA[3]
			pc_pos_status_mm_y = pc_pos_status_mm_y_b2 | (pc_pos_status_mm_y_b3 << 8)
			logging.debug("Incoming message from PC: Paddle Pos Y: %s", pc_pos_status_mm_y)

			pc_status_motor_goal_b4 = message[1].DATA[4]
			pc_motor_speed_x = pc_status_motor_goal_b4 & mask_motor_speed_x_b4
			logging.debug("Incoming message from PC: Motor Speed X: %s", pc_motor_speed_x)

			pc_motor_speed_y = pc_status_motor_goal_b4 & mask_motor_speed_y_b4
			logging.debug("Incoming message from PC: Motor Speed Y: %s", pc_motor_speed_y)

			pc_goal_scored = pc_status_motor_goal_b4 & mask_goal_scored_b4
			logging.debug("Incoming message from PC: Goal Scored: %s", pc_goal_scored)
		
			pc_state = int(message[1].DATA[5])
			logging.debug("Incoming message from PC: State: %s", pc_state)
			
			pc_error = int(message[1].DATA[6])
			logging.debug("Incoming message from PC: Error: %s", pc_error)

			# empty byte for debugging
			#pc_status_debug = message[1].DATA[7]
			#logging.debug("Incoming message from PC: Debug: %s", pc_status_debug)

		# Read next message
		message = PCANBasic.Read(PCAN, PCAN_USBBUS1)

## end of function

## 
## Tx_PC_Cmd(device)
## Transmit the command message to the Paddle Controller
##
def Tx_PC_Cmd(device):
	global mc_pos_cmd_mm_x
	global mc_pos_cmd_mm_y
	global mc_pos_cmd_sent_mm_x
	global mc_pos_cmd_sent_mm_y
	global mc_motor_speed_cmd_x
	global mc_motor_speed_cmd_y
	global pc_state_cmd
	global mc_cmd_pc_debug
	
	# Don't send new position if PC is not in ON state
	if pc_state != pc_state_enum.on:
		mc_pos_cmd_mm_x = mc_pos_cmd_sent_mm_x
		mc_pos_cmd_mm_y = mc_pos_cmd_sent_mm_y

	message = TPCANMsg()

	message.ID = ID_mc_cmd_pc
	message.MSGTYPE = PCAN_MESSAGE_STANDARD
	message.LEN = 8
	message.DATA[0] = (int(mc_pos_cmd_mm_x) & mask_pos_cmd_mm_x_b0)
	message.DATA[1] = ((int(mc_pos_cmd_mm_x) & mask_pos_cmd_mm_x_b1) >> 8)
	message.DATA[2] = (int(mc_pos_cmd_mm_y) & mask_pos_cmd_mm_y_b2)
	message.DATA[3] = ((int(mc_pos_cmd_mm_y) & mask_pos_cmd_mm_y_b3) >> 8)
	message.DATA[4] = (mc_motor_speed_cmd_x & (mc_motor_speed_cmd_y << 2))
	message.DATA[5] = pc_state_cmd 
	#message.DATA[6] = 0 				# not defined yet
	#message.DATA[7] = mc_cmd_pc_debug  # for debugging

	# Save last sent position command
	mc_pos_cmd_sent_mm_x = mc_pos_cmd_mm_x
	mc_pos_cmd_sent_mm_y = mc_pos_cmd_mm_y

	logging.debug("Transmitting message to PC: %s", message)

	# Send the message and check if it was successful
	status = PCANBasic.Write(device, PCAN_USBBUS1, message)
	if status > 0:
		logging.error("Error transmitting CAN message")
		logging.error(PCANBasic.GetErrorText(device, status, 0))

## end of function


##############################################################################################
## HDF5 functions
##############################################################################################

##
## create_HDF5()
## Create/truncate logger HDF5 file (for MATLAB) using h5py library
## Example code used - http://download.nexusformat.org/sphinx/examples/h5py/index.html
##
def create_HDF5():
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

## end of function

##
## Close_HDF5()
## Close HDF5 file (for MATLAB) using h5py library
##
def Close_HDF5():
	global hdf5_file_handle
	# make sure to close the file
	hdf5_file_handle.close()
	logging.debug("Closed hdf5 file")

## end of function

##
## add_pos_sent_HDF5()
## Add new sent X-Y position and its' timestamp to HDF5 PC_data group
## ARGUMENTS: time_rcvd - timestamp of MC sent X-Y position to PC in a string format
##
def add_pos_sent_HDF5(time_rcvd):
	global hdf5_file_handle
	global hdf5_dset_count
	global mc_pos_cmd_sent_mm_x
	global mc_pos_cmd_sent_mm_x

	i = hdf5_dset_count

	# store received positions with a puck_position_mm_xtimestamp
	hdf5_file_handle['/PC_data/pos_sent_x'][i] = mc_pos_cmd_sent_mm_x
	hdf5_file_handle['/PC_data/pos_sent_y'][i] = mc_pos_cmd_sent_mm_y
	hdf5_file_handle['/PC_data/time_sent'][i] = time_rcvd
	logging.debug("Stored sent XY position no. %i", i)

## end of function

##
## add_pos_rcvd_HDF5()
## Add new received X-Y position and its' timestamp to HDF5 PC_data group
## ARGUMENTS: time_rcvd - timestamp of PC received X-Y position in a string format 
##
def add_pos_rcvd_HDF5(time_rcvd):
	global hdf5_file_handle
	global hdf5_dset_count
	global pc_pos_status_mm_x
	global pc_pos_status_mm_y

	i = hdf5_dset_count

	# store received positions with a timestamp
	hdf5_file_handle['/PC_data/pos_rcvd_x'][i] = pc_pos_status_mm_x
	hdf5_file_handle['/PC_data/pos_rcvd_y'][i] = pc_pos_status_mm_y
	hdf5_file_handle['/PC_data/time_rcvd'][i] = time_rcvd
	logging.debug("Stored received XY position no. %i", i)

## end of function

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

## end of function


##############################################################################################
## IPC functions
##############################################################################################

##
## init_IPC() 	TODO - error check
## Initialize multiprocessing between UI, Puck Tracker and MC
## Create arrays between those processes for IPC
## Start child processes
##
def init_IPC():
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
	global visualization_data_tx
	global visualization_data_rx

	# create arrays for bidirectional communication with other processes
	ui_rx = multiprocessing.Array('f', len(settings['user_interface']['enumerations']['ui_rx']))
	ui_tx = multiprocessing.Array('f', len(settings['user_interface']['enumerations']['ui_tx']))
	pt_rx = multiprocessing.Array('f', len(settings['puck_tracker']['enumerations']['pt_rx']))
	pt_tx = multiprocessing.Array('f', len(settings['puck_tracker']['enumerations']['pt_tx']))
	visualization_data_rx = multiprocessing.Queue(1)
	visualization_data_tx = multiprocessing.Queue(1)
	logging.debug("Created IPC Arrays & Queue")

	# create seperate processes for the User Interface and Puck Tracker and give them Arrays & Queue for IPC
	ui_process = multiprocessing.Process(target=ui.ui_process, name="ui", args=(ui_rx, ui_tx, visualization_data_tx))
	logging.debug("Created User Interface process with Arrays and a Queue")
	pt_process = multiprocessing.Process(target=pt.pt_process, name="pt", args=(pt_rx, pt_tx, visualization_data_rx))
	logging.debug("Created Puck Tracker process with Arrays and a Queue")

	# start child processes
	ui_process.start()
	logging.debug("Started User Interface process")
	pt_process.start()
	logging.debug("Started Puck Tracker process")

	ui_rx[ui_rx_enum.state_cmd] = ui_state_cmd_enum.run
	pt_rx[pt_rx_enum.state_cmd] = pt_state_cmd_enum.idle

## end of function

##
## rx_IPC()		TODO - error check
## Receive any pending IPC Queue messages and populate global variables as necessary
##
def rx_IPC():
	global puck_position_mm_x
	global puck_position_mm_y
	global puck_velocity_mmps_x 
	global puck_velocity_mmps_y
	global last_puck_position_mm_x
	global last_puck_position_mm_y
	global pt_state
	global pt_error
	global ui_state
	global ui_error
	global ui_diagnostic_request
	global ui_game_state
	global ui_screen
	global game_mode
	global mc_motor_speed_cmd_x
	global mc_motor_speed_cmd_y

	# store last received data values
	last_puck_position_mm_x = puck_position_mm_x
	last_puck_position_mm_y = puck_position_mm_y

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
	mc_motor_speed_cmd_x = int(ui_tx[ui_tx_enum.game_speed_x])
	mc_motor_speed_cmd_y = int(ui_tx[ui_tx_enum.game_speed_y])
	game_mode = int(ui_tx[ui_tx_enum.game_mode])

	# pass through data from ui to pt
	pt_rx[pt_rx_enum.lower_hue] = ui_tx[ui_tx_enum.lower_hue]
	pt_rx[pt_rx_enum.lower_sat] = ui_tx[ui_tx_enum.lower_sat]
	pt_rx[pt_rx_enum.lower_val] = ui_tx[ui_tx_enum.lower_val]
	pt_rx[pt_rx_enum.upper_hue] = ui_tx[ui_tx_enum.upper_hue]
	pt_rx[pt_rx_enum.upper_sat] = ui_tx[ui_tx_enum.upper_sat]
	pt_rx[pt_rx_enum.upper_val] = ui_tx[ui_tx_enum.upper_val]	

## end of function

##############################################################################################
## Decision Making/Logic functions
##############################################################################################

##
## filter_tx_PC_cmd()
## filter new pos value if the distance from last sent pos
## is below set threshold
##	
def filter_tx_PC_cmd():
	global mc_pos_cmd_mm_x
	global mc_pos_cmd_mm_y
	global mc_pos_cmd_sent_mm_x
	global mc_pos_cmd_sent_mm_y

	pos_diff_mm_x = mc_pos_cmd_mm_x - mc_pos_cmd_sent_mm_x
	pos_diff_mm_y = mc_pos_cmd_mm_y - mc_pos_cmd_sent_mm_y
	pos_diff_mm = math.sqrt(pos_diff_mm_x**2 + pos_diff_mm_y**2)
	
	if pos_diff_mm < filter_pos_value_mm:
		logging.debug("New pos(%i,%i) is filtered coz it's %imm(within %imm) away from last sent PC pos(%i,%i)", mc_pos_cmd_mm_x,
						mc_pos_cmd_mm_y, pos_diff_mm, filter_pos_value_mm, mc_pos_cmd_sent_mm_x, mc_pos_cmd_sent_mm_y)
		mc_pos_cmd_mm_x = mc_pos_cmd_sent_mm_x
		mc_pos_cmd_mm_y = mc_pos_cmd_sent_mm_y

## end of function

def paddle_control_offense_state_machine():
	global offense_sm_state
	global last_offense_sm_state
	global mc_pos_cmd_mm_x
	global mc_pos_cmd_mm_y
	global paddle_position_averaged_array
	global paddle_position_averaged_index

	# get frame for visualization
	if visualization_data_rx.empty():
		frame = [0]
		frame_received = False
	else:
		frame = visualization_data_rx.get(True)
		frame_received = True

	# when we change states, clear the averaging array
	if offense_sm_state != last_offense_sm_state:
		paddle_position_averaged_array.fill(0)
		paddle_position_averaged_index = 0

	# STATE MACHINE
	if offense_sm_state == mc_control_state_machine_enum.home:
		# go home
		mc_pos_cmd_mm_x = goal_center_mm_x
		mc_pos_cmd_mm_y = 0

		# if the puck is coming towards us from the opponents end - attack
		if ((puck_velocity_mmps_y < min_puck_velocity_mmps_y) and 
			(puck_position_mm_y > (table_length_mm_y/2))):
			offense_sm_state = mc_control_state_machine_enum.attack
		
		# if puck in our end and somewhat stationary - return
		if ((puck_velocity_stopped_low_mmps_y < puck_velocity_mmps_y < puck_velocity_stopped_high_mmps_y) and
			(puck_position_mm_y < (table_length_mm_y/2))):
			offense_sm_state = mc_control_state_machine_enum.return_puck
			   
		# if puck past attack line and coming towards us - defend
		if ((puck_position_mm_y < attack_line_mm_y) and
			(puck_velocity_mmps_y < min_puck_velocity_mmps_y)):
		   offense_sm_state = mc_control_state_machine_enum.defend

	elif offense_sm_state == mc_control_state_machine_enum.attack:
		# do attack things
		frame = get_paddle_position_mm_x(attack_line_mm_y, frame, frame_received)
		mc_pos_cmd_mm_x = paddle_position_mm_x
		mc_pos_cmd_mm_y = attack_line_mm_y

		# if puck not in our end and somewhat stationary/moving away - home
		if ((puck_velocity_mmps_y > min_puck_velocity_mmps_y) and
			(puck_position_mm_y > (table_length_mm_y/2))):
			defense_sm_state = mc_control_state_machine_enum.home

		# if puck moving away from us - home
		if (puck_velocity_mmps_y > 0):
			offense_sm_state = mc_control_state_machine_enum.home
		
		# if puck moved past attack line - defend
		if ((puck_position_mm_y < attack_line_mm_y) and
			(puck_velocity_mmps_y < min_puck_velocity_mmps_y)):
			offense_sm_state = mc_control_state_machine_enum.defend

		#if puck in our end and somewhat stationary - return
		if ((puck_velocity_stopped_low_mmps_y < puck_velocity_mmps_y < puck_velocity_stopped_high_mmps_y) and
			(puck_position_mm_y < (table_length_mm_y/2))):
			offense_sm_state = mc_control_state_machine_enum.return_puck

	elif offense_sm_state == mc_control_state_machine_enum.defend:
		# do defense things
		frame = get_paddle_position_mm_x(defense_line_mm_y, frame, frame_received)
		mc_pos_cmd_mm_x = paddle_position_mm_x
		mc_pos_cmd_mm_y = defense_line_mm_y

		# if puck not in our end and somewhat stationary/moving away - home
		if ((puck_velocity_mmps_y > min_puck_velocity_mmps_y) and
			(puck_position_mm_y > (table_length_mm_y/2))):
			defense_sm_state = mc_control_state_machine_enum.home

		#if puck in our end and somewhat stationary - return
		if ((puck_velocity_stopped_low_mmps_y < puck_velocity_mmps_y < puck_velocity_stopped_high_mmps_y) and
			(puck_position_mm_y < (table_length_mm_y/2))):
			offense_sm_state = mc_control_state_machine_enum.return_puck

	elif offense_sm_state == mc_control_state_machine_enum.return_puck:
		# do return things
		mc_pos_cmd_mm_x = puck_position_mm_x
		mc_pos_cmd_mm_y = puck_position_mm_y

		# if puck out of our end - home
		if (puck_position_mm_y > (table_length_mm_y/2)):
			offense_sm_state = mc_control_state_machine_enum.home

	else:
		pass # TODO - Errors?

	# if puck not seen - home
	if ((puck_position_mm_x == 0) and 
		(puck_position_mm_y == 0)):
		offense_sm_state = mc_control_state_machine_enum.home

	# send the puck tracker image on to the user interface
	if frame_received:
		frame = cv2.resize(frame, dsize=(800,600), interpolation=cv2.INTER_LINEAR)
		try:
			visualization_data_tx.put_nowait(frame)
		except:
			pass

	last_offense_sm_state = offense_sm_state

def paddle_control_defense_state_machine():
	global defense_sm_state
	global last_defense_sm_state
	global mc_pos_cmd_mm_x
	global mc_pos_cmd_mm_y
	global paddle_position_averaged_array
	global paddle_position_averaged_index

	# get frame for visualization
	if visualization_data_rx.empty():
		frame = [0]
		frame_received = False
	else:
		frame = visualization_data_rx.get(True)
		frame_received = True

	# when we change states, clear the averaging array
	if defense_sm_state != last_defense_sm_state:
		paddle_position_averaged_array.fill(0)
		paddle_position_averaged_index = 0
	
	# STATE MACHINE
	if defense_sm_state == mc_control_state_machine_enum.home:
		# go home
		mc_pos_cmd_mm_x = goal_center_mm_x
		mc_pos_cmd_mm_y = 0

		# if puck in our end and somewhat stationary - return
		if ((puck_velocity_stopped_low_mmps_y < puck_velocity_mmps_y < puck_velocity_stopped_high_mmps_y) and
			(puck_position_mm_y < (table_length_mm_y/2))):
			defense_sm_state = mc_control_state_machine_enum.return_puck
			   
		# if puck coming towards us - defend
		if (puck_velocity_mmps_y < min_puck_velocity_mmps_y):
			defense_sm_state = mc_control_state_machine_enum.defend

	elif defense_sm_state == mc_control_state_machine_enum.defend:
		# do defense things
		frame = get_paddle_position_mm_x(defense_line_mm_y, frame, frame_received)
		mc_pos_cmd_mm_x = paddle_position_mm_x
		mc_pos_cmd_mm_y = defense_line_mm_y

		# if puck not in our end and somewhat stationary/moving away - home
		if ((puck_velocity_mmps_y > min_puck_velocity_mmps_y) and
			(puck_position_mm_y > (table_length_mm_y/2))):
			defense_sm_state = mc_control_state_machine_enum.home
		
		# if puck in our end moving away - home
		if ((puck_velocity_mmps_y > puck_velocity_stopped_high_mmps_y) and
			(puck_position_mm_y < (table_length_mm_y/2))):
			defense_sm_state = mc_control_state_machine_enum.home
			
		# if puck in our end and somewhat stationary - return
		if ((puck_velocity_stopped_low_mmps_y < puck_velocity_mmps_y < puck_velocity_stopped_high_mmps_y) and
			(puck_position_mm_y < (table_length_mm_y/2))):
			defense_sm_state = mc_control_state_machine_enum.return_puck

	elif defense_sm_state == mc_control_state_machine_enum.return_puck:
		# do return things
		mc_pos_cmd_mm_x = puck_position_mm_x
		mc_pos_cmd_mm_y = puck_position_mm_y

		# if puck out of our end - home
		if (puck_position_mm_y > (table_length_mm_y/2)):
			defense_sm_state = mc_control_state_machine_enum.home

	else:
		pass # TODO - Errors?

	# if puck not seen - home
	if ((puck_position_mm_x == 0) and 
		(puck_position_mm_y == 0)):
		defense_sm_state = mc_control_state_machine_enum.home

	# send the puck tracker image on to the user interface
	if frame_received:
		frame = cv2.resize(frame, dsize=(800,600), interpolation=cv2.INTER_LINEAR)
		try:
			visualization_data_tx.put_nowait(frame)
		except:
			pass

	last_defense_sm_state = defense_sm_state

def get_paddle_position_mm_x(puck_intercept_position_mm_y, frame, frame_received):
	global paddle_position_mm_x
	global paddle_position_averaged_mm_x
	global paddle_position_averaged_array
	global paddle_position_averaged_index

	# using the equation of a line y = mx + b, find paddle position necessary to intercept the puck
	vector_mm_x = puck_position_mm_x - last_puck_position_mm_x
	vector_mm_y = puck_position_mm_y - last_puck_position_mm_y
			
	if (vector_mm_x == 0) or (vector_mm_y == 0):
		# avoid divide by zero TODO - logic?
		return frame
	else:
		slope = vector_mm_y/vector_mm_x
	
	# b = y - mx
	intercept_mm_y = puck_position_mm_y - (slope * puck_position_mm_x)
	
	# x = (y - b)/m
	paddle_position_mm_x = ((puck_intercept_position_mm_y + paddle_radius_mm) - intercept_mm_y) / slope

	# predict bounces and get a raw paddle x position prediction
	bounce_count = 0
	while True:
		if (table_width_mm_x - puck_radius_mm) >= paddle_position_mm_x >= puck_radius_mm:
			if frame_received:
				if bounce_count == 0:
					cv2.line(frame, (int(puck_position_mm_y/mm_per_pixel_y), int(puck_position_mm_x/mm_per_pixel_x)), (int((puck_intercept_position_mm_y)/mm_per_pixel_y), int(paddle_position_mm_x/mm_per_pixel_x)), (255,0,0), 3)
				else:
					cv2.line(frame, (int(last_bounce_mm_y/mm_per_pixel_y), int(last_bounce_mm_x/mm_per_pixel_x)), (int((puck_intercept_position_mm_y)/mm_per_pixel_y), int(paddle_position_mm_x/mm_per_pixel_x)), (255,0,0), 3)
			break

		elif paddle_position_mm_x < puck_radius_mm:
			bounce_mm_y = (slope * puck_radius_mm) + intercept_mm_y
			bounce_mm_x = puck_radius_mm
			slope = -slope
			intercept_mm_y = bounce_mm_y - (slope * puck_radius_mm)
			paddle_position_mm_x = ((puck_intercept_position_mm_y + paddle_radius_mm) - intercept_mm_y) / slope
			if frame_received:
				if bounce_count == 0:
					cv2.line(frame, (int(puck_position_mm_y/mm_per_pixel_y), int(puck_position_mm_x/mm_per_pixel_x)), (int(bounce_mm_y/mm_per_pixel_y), int(bounce_mm_x/mm_per_pixel_x)), (255,0,0), 3)
				else:
					cv2.line(frame, (int(last_bounce_mm_y/mm_per_pixel_y), int(last_bounce_mm_x/mm_per_pixel_x)), (int((bounce_mm_y)/mm_per_pixel_y), int(bounce_mm_x/mm_per_pixel_x)), (255,0,0), 3)

		elif paddle_position_mm_x > (table_width_mm_x - puck_radius_mm):
			bounce_mm_y = (slope * (table_width_mm_x - puck_radius_mm)) + intercept_mm_y
			bounce_mm_x = (table_width_mm_x - puck_radius_mm)
			slope = -slope
			intercept_mm_y = bounce_mm_y - (slope * (table_width_mm_x - puck_radius_mm))
			paddle_position_mm_x = ((puck_intercept_position_mm_y + paddle_radius_mm) - intercept_mm_y) / slope
			if frame_received:
				if bounce_count == 0:
					cv2.line(frame, (int(puck_position_mm_y/mm_per_pixel_y), int(puck_position_mm_x/mm_per_pixel_x)), (int(bounce_mm_y/mm_per_pixel_y), int(bounce_mm_x/mm_per_pixel_x)), (255,0,0), 3)
				else:
					cv2.line(frame, (int(last_bounce_mm_y/mm_per_pixel_y), int(last_bounce_mm_x/mm_per_pixel_x)), (int((bounce_mm_y)/mm_per_pixel_y), int(bounce_mm_x/mm_per_pixel_x)), (255,0,0), 3)
					
		last_bounce_mm_y = bounce_mm_y
		last_bounce_mm_x = bounce_mm_x
		bounce_count += 1

	logging.debug("Paddle position mm x: %i", paddle_position_mm_x)

	# draw a circle around the raw desired paddle position
	if frame_received:
		cv2.circle(frame, (int((puck_intercept_position_mm_y)/mm_per_pixel_y), int(paddle_position_mm_x/mm_per_pixel_x)), 10, (0, 0, 255), 2)
	
	# now that we have a predicted x position, take an average to improve accuracy  
	paddle_position_averaged_array[paddle_position_averaged_index] = paddle_position_mm_x
	number_non_zero_values = np.count_nonzero(paddle_position_averaged_array)
	if number_non_zero_values != 0:
		paddle_position_averaged_mm_x = (np.sum(paddle_position_averaged_array)) / number_non_zero_values
	else:
		paddle_position_averaged_mm_x = 0
	
	# manage index for array
	paddle_position_averaged_index += 1
	if paddle_position_averaged_index >= paddle_position_averaged_window_size:
		paddle_position_averaged_index = 0

	# draw a circle around the averaged desired paddle position
	if frame_received:
		cv2.circle(frame, (int(puck_intercept_position_mm_y/mm_per_pixel_y), int(paddle_position_averaged_mm_x/mm_per_pixel_x)), 10, (0, 255, 255), 2)

	logging.debug("Paddle position mm x averaged: %i", paddle_position_averaged_mm_x)

	# after our paddle postion prediction is drawn onto the frame, return the frame
	return frame

## 
## get_paddle_position()
## Calculates linear trajectory of the puck based on XY positions and Y velocity
## Outputs XY position for the paddle
##
def get_paddle_position():
	global last_puck_velocity_mmps_y
	global last_paddle_position_averaged_mm_x
	global paddle_position_averaged_array
	global paddle_position_averaged_index
	global mc_pos_cmd_mm_x
	global mc_pos_cmd_mm_y
	
	# get frame for visualization
	if visualization_data_rx.empty():
		frame_received = False
	else:
		frame = visualization_data_rx.get(True)
		frame_received = True

	if int(puck_position_mm_x) == 0 and int(puck_position_mm_y) == 0: 
		paddle_position_mm_x = goal_center_mm_x
		paddle_position_mm_y = 0
		mc_pos_cmd_mm_x = int(paddle_position_mm_x)
		mc_pos_cmd_mm_y = int(paddle_position_mm_y)

	elif puck_position_mm_x != last_puck_position_mm_x and puck_position_mm_y != last_puck_position_mm_y:
		# set the target paddle position based on game mode
		if game_mode == ui_game_mode_enum.offense:
			paddle_target_position_mm_y = paddle_offense_position_mm_y
		else:
			paddle_target_position_mm_y = paddle_defense_position_mm_y

		# default paddle position
		paddle_position_mm_x = last_paddle_position_averaged_mm_x
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
			if slope == 0:
				puck_prediction_mm_x = 0
			else:
				puck_prediction_mm_x = ((paddle_target_position_mm_y + paddle_radius_mm) - intercept_mm_y) / slope

			# predict bounces and get a real x prediction
			bounce_count = 0
			while True:
				if (table_width_mm_x - puck_radius_mm) >= puck_prediction_mm_x >= puck_radius_mm:
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

				elif puck_prediction_mm_x > (table_width_mm_x - puck_radius_mm):
					bounce_mm_y = (slope * (table_width_mm_x - puck_radius_mm)) + intercept_mm_y
					bounce_mm_x = (table_width_mm_x - puck_radius_mm)
					slope = -slope
					intercept_mm_y = bounce_mm_y - (slope * (table_width_mm_x - puck_radius_mm))
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
			paddle_position_averaged_array[paddle_position_averaged_index] = puck_prediction_mm_x
			number_non_zero_values = np.count_nonzero(paddle_position_averaged_array)
			if number_non_zero_values != 0:
				paddle_position_averaged_mm_x = (np.sum(paddle_position_averaged_array)) / number_non_zero_values
			else:
				paddle_position_averaged_mm_x = 0
			
			# manage index for array
			paddle_position_averaged_index += 1
			if paddle_position_averaged_index >= paddle_position_averaged_window_size:
				paddle_position_averaged_index = 0

			# draw a circle around the averaged desired paddle position
			if frame_received:
				cv2.circle(frame, (int((paddle_target_position_mm_y + paddle_radius_mm)/mm_per_pixel_y), int(paddle_position_averaged_mm_x/mm_per_pixel_x)), 10, (0, 255, 255), 2)

			if game_mode == ui_game_mode_enum.defense: # only goal post correct if defense
				# Goal post correction
				if paddle_position_averaged_mm_x < goal_left_post_mm_x:
					paddle_position_averaged_mm_x = goal_left_post_mm_x
				# puck pos after right goalpost then set to the right goalpost_pos+tolerance
				elif paddle_position_averaged_mm_x > goal_right_post_mm_x:
					paddle_position_averaged_mm_x = goal_right_post_mm_x

			# set paddle position
			paddle_position_mm_x = paddle_position_averaged_mm_x
			paddle_position_mm_y = paddle_target_position_mm_y

		if (puck_velocity_mmps_y > min_puck_velocity_mmps_y) and (last_puck_velocity_mmps_y < min_puck_velocity_mmps_y):
			paddle_position_averaged_array.fill(0)
			paddle_position_averaged_index = 0
			paddle_position_mm_x = goal_center_mm_x
			paddle_position_mm_y = 0

		last_puck_velocity_mmps_y = puck_velocity_mmps_y
		last_paddle_position_averaged_mm_x = paddle_position_mm_x

		logging.debug("Paddle defense position is: %i,0", paddle_position_mm_x)

		mc_pos_cmd_mm_x = int(paddle_position_mm_x)
		mc_pos_cmd_mm_y = int(paddle_position_mm_y)

	# send frame
	if frame_received:
		frame = cv2.resize(frame, dsize=(800,600), interpolation=cv2.INTER_LINEAR)
		try:
			visualization_data_tx.put_nowait(frame)
		except:
			pass

## end of function

## 
## make_decisions()
## Controls interface between puck tracker, user interface, and paddle controller
##
def make_decisions():
	global last_ui_screen
	global pc_state_cmd

	# pass state data to the UI
	send_UI_states()

	# Check ALL states
	if ((mc_state == mc_state_enum.error) or (pt_state == pt_state_enum.error) or (ui_state == ui_state_enum.error) or (pc_state == pc_state_enum.error)):
		handle_errors()
		return
	
	elif ((pt_state == pt_state_enum.quit) or (ui_state == ui_state_enum.request_quit) or (ui_state == ui_state_enum.quit)):
		handle_quits()
		return
	
	elif ui_state != ui_state_enum.running:
		return

	# Check which UI screen we are on, this dictates a large part of what state we'll be in
	if ui_screen == ui_screen_enum.visual:
		handle_visual_game()

	elif ui_screen == ui_screen_enum.manual:
		handle_manual_game()

	elif ui_screen == ui_screen_enum.menu:
		pt_rx[pt_rx_enum.state_cmd] = pt_state_cmd_enum.idle

	elif ui_screen == ui_screen_enum.fiducial_calibration:
		calibrate_fiducials()

	elif ui_screen == ui_screen_enum.puck_calibration:
		calibrate_puck()

	elif ui_screen == ui_screen_enum.diagnostic:
		pt_rx[pt_rx_enum.state_cmd] = pt_state_cmd_enum.idle

		if ui_diagnostic_request == ui_diagnostic_request_enum.calibrate_paddle_controller:
			ui_tx[ui_tx_enum.diagnostic_request] = ui_diagnostic_request_enum.idle
			pc_state_cmd = pc_state_cmd_enum.calibration
			Tx_PC_Cmd(PCAN)
			pc_state_cmd = pc_state_cmd_enum.off

		if ui_diagnostic_request == ui_diagnostic_request_enum.clear_errors:
			ui_tx[ui_tx_enum.diagnostic_request] = ui_diagnostic_request_enum.idle
			pc_state_cmd = pc_state_cmd_enum.clear_error
			Tx_PC_Cmd(PCAN)
			pc_state_cmd = pc_state_cmd_enum.off

## end of function

## 
## send_UI_states()
## pass state data of other modules to the UI
##
def send_UI_states():
	ui_rx[ui_rx_enum.pt_state] = pt_state
	ui_rx[ui_rx_enum.pt_error] = pt_error
	ui_rx[ui_rx_enum.mc_state] = mc_state
	ui_rx[ui_rx_enum.mc_error] = mc_error
	ui_rx[ui_rx_enum.pc_state] = pc_state
	ui_rx[ui_rx_enum.pc_error] = pc_error

	logging.debug("MC: pt_state: %s, pt_error: %s", pt_state, pt_error)
	logging.debug("MC: mc_state: %s, mc_error: %s", mc_state, mc_error)
	logging.debug("MC: pc_state: %s, pc_error: %s", pc_state, pc_error)
## end of function


##   
## handle_errors()
## Take care of all errors from UI, PT, PC
##
def handle_errors():
	global pc_state_cmd
	global mc_state
	global mc_error
	global visualization_data_tx
	global visualization_data_rx
	global ui_process
	global pt_process
	global PCAN

	# MC error
	if mc_state == mc_state_enum.error:
		logging.error("MC: MC Error: %i. Resolve the error and click Clear Error btn under Diagnostics menu", mc_error)

		if ui_diagnostic_request == ui_diagnostic_request_enum.clear_errors:
			if mc_error == mc_error_enum.pcan:
				mc_state = mc_state_enum.running
				mc_error = mc_error_enum.none
				init_PCAN(PCAN)

	# PC error
	if pc_state == pc_state_enum.error:
		logging.error("MC: PC Error: %i. Resolve the error and click Clear Error btn under Diagnostics menu", pc_error)
		
		if ui_diagnostic_request == ui_diagnostic_request_enum.clear_errors:
			pc_state_cmd = pc_state_cmd_enum.clear_error
			Tx_PC_Cmd(PCAN)
			logging.error("MC: Commanding PC to Clear Error State to resolve the issue")
			pc_state_cmd = pc_state_cmd_enum.off
	
	# UI error	
	if ui_state == ui_state_enum.error:
		logging.error("MC: UI Error: %i. Starting a process to shut off PC, PT, UI, MC", ui_error)
		# shut off PC
		if (pc_state != pc_state_enum.off):
			pc_state_cmd = pc_state_cmd_enum.off
			Tx_PC_Cmd(PCAN)

		# shut off PT and MC
		pt_rx[pt_rx_enum.state_cmd] = pt_state_cmd_enum.quit
		if (pt_state == pt_state_enum.quit):
			prepare_to_quit()
			sys.exit(0)

	# PT error
	if pt_state == pt_state_enum.error:
		if pt_error == pt_error_enum.calibration_failed:
			logging.error("MC: PT Error: %i (Calibration Failed), try recalibrating or restarting the system", ui_error)
		else:
			logging.error("MC: PT Error: %i, Starting a process to shut off PC, PT, UI, MC", ui_error)
			# shut off PC
			if (pc_state != pc_state_enum.off):
				pc_state_cmd = pc_state_cmd_enum.off
				Tx_PC_Cmd(PCAN)

			# shut off UI and MC
			ui_rx[ui_rx_enum.state_cmd] = ui_state_cmd_enum.quit
			if (ui_state == ui_state_enum.quit):
				prepare_to_quit()
				sys.exit(0)

	ui_tx[ui_tx_enum.diagnostic_request] = ui_diagnostic_request_enum.idle

## end of function

##
## prepare_to_quit()
## terminate processes, close files, uninit CAN, etc before exit
##
def prepare_to_quit():
	while True:
		if ui_process.is_alive() or pt_process.is_alive():
			logging.debug("Terminating UI and PT processes")
			ui_process.terminate()
			pt_process.terminate()
		else:
			logging.info("UI and PT processes are terminated")
			break
	Close_HDF5()
	Uninit_PCAN(PCAN)
	logging.info("Closing visualization pipes")
	visualization_data_tx.close()
	visualization_data_rx.close()
	logging.info("Ready to quit MC")

## end of function

##  
## handle_quits()
## go through steps of shutting down if UI requests
##
def handle_quits():
	global visualization_data_tx
	global visualization_data_rx
	global ui_process
	global pt_process
	global pc_state_cmd
	
	if ui_state == ui_state_enum.request_quit:
		logging.debug("MC: UI is requesting to quit")
		pt_rx[pt_rx_enum.state_cmd] = pt_state_cmd_enum.quit

	if pt_state == pt_state_enum.quit:
		logging.debug("MC: PT is in quit state")
		ui_rx[ui_rx_enum.state_cmd] = ui_state_cmd_enum.quit

	if (pc_state != pc_state_enum.off):
		pc_state_cmd = pc_state_cmd_enum.off
		Tx_PC_Cmd(PCAN)	
		
	if (ui_state == ui_state_enum.quit and pt_state == pt_state_enum.quit):
		logging.info("MC: UI and PT are in quit state, PC is in OFF, ready to be terminated")
		prepare_to_quit()
		sys.exit(0)	

## end of function

##  
## handle_visual_game()
## Take care of visual game decisions (robot vs human)
##
def handle_visual_game():
	global pc_state_cmd
	pt_rx[pt_rx_enum.state_cmd] = pt_state_cmd_enum.track

	# check if we're tracking
	if pt_state != pt_state_enum.tracking:
		logging.debug("MC: Camera isn't in tracking state, can't start visual game")	
		return

	if game_mode == ui_game_mode_enum.offense:
		paddle_control_offense_state_machine()
	elif game_mode == ui_game_mode_enum.defense:
		paddle_control_defense_state_machine()

	if ui_game_state == ui_game_state_enum.playing:
		ui_rx[ui_rx_enum.goal_scored] = pc_goal_scored
		pc_state_cmd = pc_state_cmd_enum.on
		Tx_PC_Cmd(PCAN)
	elif ui_game_state == ui_game_state_enum.stopped:
		pc_state_cmd = pc_state_cmd_enum.off
		Tx_PC_Cmd(PCAN)

## end of function

##  
## handle_manual_game()
## Take care of manual game decisions (human operating robot vs human)
##
def handle_manual_game():
	global mc_pos_cmd_mm_x
	global mc_pos_cmd_mm_y
	global pc_state_cmd

	if (pt_state != pt_state_enum.tracking)	and (pt_state != pt_state_enum.idle):
		logging.debug("MC: Camera isn't in tracking or idle state, can't start manual game")
		return

	if ui_game_state == ui_game_state_enum.playing:
		ui_rx[ui_rx_enum.goal_scored] = pc_goal_scored
		pc_state_cmd = pc_state_cmd_enum.on
		mc_pos_cmd_mm_x = ui_tx[ui_tx_enum.paddle_position_x]
		mc_pos_cmd_mm_y = ui_tx[ui_tx_enum.paddle_position_y]
		logging.info("MC Manual game: x=%s y=%s", mc_pos_cmd_mm_x, mc_pos_cmd_mm_y)
		Tx_PC_Cmd(PCAN)

	elif ui_game_state == ui_game_state_enum.stopped:
		pc_state_cmd = pc_state_cmd_enum.off
		Tx_PC_Cmd(PCAN)
## end of function

## 
## update_game_settings()
## Retrieve the game settings controlled by the user interface
##
def update_game_settings():
    global game_mode
    global game_speed_x
    global game_speed_y

    # get settings from file
    with open((settings_path + 'settings.json'), 'r') as fp:
        settings = json.load(fp)
        fp.close()

    game_mode = settings['user_interface']['game_mode']
    game_speed_x = settings['user_interface']['game_speed_x']
    game_speed_y = settings['user_interface']['game_speed_y']

## end of function

##  
## calibrate_fiducials()
## Calibrate fiducials when in the UI settings 
##
def calibrate_fiducials():
	global visualization_data_tx
	global visualization_data_rx

	if ui_diagnostic_request == ui_diagnostic_request_enum.calibrate_fiducials:
		pt_rx[pt_rx_enum.state_cmd] = pt_state_cmd_enum.calibrate_fiducials
	else:
		pt_rx[pt_rx_enum.state_cmd] = pt_state_cmd_enum.find_fiducials

	# get frame for visualization
	try:
		frame = visualization_data_rx.get(False)
	except Queue.Empty:
		pass
	else:
		try:
			visualization_data_tx.get_nowait()
			visualization_data_tx.put(frame)
		except Queue.Empty:
			visualization_data_tx.put(frame)
	
## end of function

##  
## calibrate_puck()
## Calibrate puck when in the UI settings
##
def calibrate_puck():
	pt_rx[pt_rx_enum.state_cmd] = pt_state_cmd_enum.find_puck

	# get frame for visualization
	try:
		frame = visualization_data_rx.get(False)
	except Queue.Empty:
		pass
	else:
		try:
			visualization_data_tx.get_nowait()
			visualization_data_tx.put(frame)
		except Queue.Empty:
			visualization_data_tx.put(frame)	

## end of function

##############################################################################################
## MAIN() function
##############################################################################################

## 
## main()
##
try:
	# Create enums
	get_enums()
	get_settings()

	# Set initial master controller state/error
	mc_state = mc_state_enum.running
	mc_error = mc_error_enum.none

	# Create HDF5 file for logging PC position data
	create_HDF5()

	# Initialize PCAN device
	init_PCAN(PCAN)

	# Initialize IPC between MC - PC - UI
	init_IPC()

	logging.info("MC: Entering main loop")

	# Master Controller loop
	while True:
		rx_IPC()
		rx_CAN(PCAN)
		add_pos_rcvd_HDF5(str(datetime.datetime.now()))
		make_decisions()
		add_pos_sent_HDF5(str(datetime.datetime.now()))
		update_dset_HDF5()
		sleep(timeout)

except KeyboardInterrupt:
	mc_state = mc_state_enum.stopped
	mc_error = mc_error_enum.crashed
	send_UI_states()
	prepare_to_quit()
	sys.exit()

except Exception as e:
	# Really Broken. Quit the puck tracker so we release the webcam and I don't have to reboot the computer over and over
	print e
	pt_rx[pt_rx_enum.state_cmd] = pt_state_cmd_enum.quit
## end of function

##############################################################################################
## THE END