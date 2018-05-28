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
timeout = 0.1 			# Timeout for keyboard input in seconds

# Global variables
enable_cmd = 0
floor_cmd = 0
enable_status = -1
floor_status = -1

##
## Init_PCAN()
## Initialize the PCAN USB Dongle & Check for Errors
##
def Init_PCAN(device):
	status = PCANBasic.Initialize(device, PCAN_USBBUS1, PCAN_BAUD_125K)
	if status > 0:
		print "Error Initializing PCAN USB"
		exit
	else:
		print "PCAN USB Initialized"	
## end of method


##
## Uninit_PCAN()
## Uninitialize the PCAN USB Dongle & check for errors
##
def Uninit_PCAN(device):
	status = PCANBasic.Uninitialize(device, PCAN_USBBUS1)
	if status > 0:
		print "Error Uninitializing PCAN USB"
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
	print "Elevator Command Input"
	global floor_cmd
	global enable_cmd

	floor_cmd = input("Enter floor number:")
	enable_cmd = input("Enter enable value:")			

## end of method


##
## update_display()
## Show elevator status and command
##
def update_display():
	global floor_cmd
	global enable_cmd
	global floor_status
	global enable_status

	os.system('clear')
	print("Elevator Status")
	print("---------------")
	print "Floor Command: ", floor_cmd
	print "Floor Status: ", floor_status
	print "Enable Command: ", enable_cmd
	print "Enable Status: ", enable_status
	print " "
	print "Press 'Enter' for debug mode"
## end of method


##
## Rx_CAN(device)
## Receive any pending CAN messages and populate global variables as necessary
##
def Rx_CAN(device):
	global floor_status
	global enable_status

	message = PCANBasic.Read(PCAN, PCAN_USBBUS1)

	# Keep reading messages until there aren't any more
	#while message[1].ID > 1:
	if message[1].ID > 1:
		
		# Process EC_Status message
		if message[1].ID == 0x101:
			floor_status = message[1].DATA[0] & 3			# Bit mask hardcoded which is shitty
			enable_status = ((message[1].DATA[0] & 4) >> 2)	# Same here
			message = PCANBasic.Read(PCAN, PCAN_USBBUS1)		
## end of method


## 
## Tx_EC_Cmd(device)
## Transmit the command message to the elevator controller
##
def Tx_EC_Cmd(device):
	global floor_cmd
	global enable_cmd
	message = TPCANMsg()

	message.ID = 0x100
	message.MSGTYPE = PCAN_MESSAGE_STANDARD
	message.LEN = 1
	message.DATA[0] = (floor_cmd | (enable_cmd << 2))

	status = PCANBasic.Write(device, PCAN_USBBUS1, message)	# Transmit, could check later if it was successful
	if status > 0:
		print "Error transmitting CAN message"
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
	  		Tx_EC_Cmd(PCAN)
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