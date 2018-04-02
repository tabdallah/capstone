# PCAN_Test.py

# Code for keyboard input from https://repolinux.wordpress.com/2012/10/09/non-blocking-read-from-stdin-in-python/

from PCANBasic import *
from time import sleep
from pprint import pprint
import sys
import select
import os

PCAN = PCANBasic() 		# Initialize an instance of the PCANBasic class
read_list = [sys.stdin] # Files monitored for input

##############################################################################################
## Global data storage
## Maybe improve this later
##############################################################################################

timeout = 0.1 			# Timeout for keyboard input in seconds

mc_pos_cmd_x_mm = -1
mc_pos_cmd_y_mm = -1
pc_pos_status_x_mm = -1
pc_pos_status_y_mm = -1

##############################################################################################
## CAN protocol definition
## Refer to: https://github.com/tabdallah/capstone/blob/master/1_Planning/System_Interface_Design.xlsx
##############################################################################################

# CAN message ID's
ID_mc_cmd_pc =		0x100		# CAN message ID for Master Controller Command to PC on X and Y position
ID_pc_status_x = 	0x101 		# CAN message ID for Paddle Controller Status on X-axis
ID_pc_status_y = 	0x102		# CAN message ID for Paddle Controller Status on Y-axis

# CAN signal masks
mask_pos_cmd_x_mm = 		0x0000FFFF		# Hex mask for pos_cmd_x_mm signal
mask_pos_cmd_y_mm = 		0xFFFF0000		# Hex mask for pos_cmd_y_mm signal
mask_pos_x_mm = 			0x0000FFFF		# Hex mask for pos_x_mm signal
mask_pos_y_mm = 			0x0000FFFF		# Hex mask for pos_y_mm signal

# CAN signal value tables

##############################################################################################
## Functions/methods
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
			pc_pos_status_x_mm_byte_0 = message[1].DATA[0] 

		# Process PC Status Y message
		elif message[1].ID == ID_pc_status_y:
			pc_pos_status_y_mm = message[1].DATA[0] & mask_pos_y_mm

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
	message.DATA[0] = (mc_pos_cmd_x_mm & 0x00FF)
	message.DATA[1] = ((mc_pos_cmd_x_mm & 0xFF00) >> 8)
	message.DATA[2] = (mc_pos_cmd_y_mm & 0x00FF)
	message.DATA[3] = ((mc_pos_cmd_y_mm & 0xFF00) >> 8)

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
	  		Tx_PC_Cmd(PCAN)
	  		sleep(0.5)  
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