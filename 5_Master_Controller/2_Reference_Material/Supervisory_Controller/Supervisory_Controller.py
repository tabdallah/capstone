# Supervisory_Controller.py

# Code for keyboard input from https://repolinux.wordpress.com/2012/10/09/non-blocking-read-from-stdin-in-python/

from PCANBasic import *
import time
import datetime
from pprint import pprint
import sys
import select
import os
from tabulate import tabulate
import MySQLdb

PCAN = PCANBasic() 		# Initialize an instance of the PCANBasic class
read_list = [sys.stdin] # Files monitored for input


##############################################################################################
## CAN protocol definition
## Refer to: https://github.com/eelmand/S6Project/blob/master/Project%20Plan/Shared_CAN_Protocol_Proposal.xlsx
##############################################################################################

# CAN message ID's
ID_sc = 0x100 			# CAN message ID for Supervisory Controller
ID_ec = 0x101			# CAN message ID for Elevator controller
ID_cc = 0x200			# CAN message ID for elevator Car Controller
ID_f1 = 0x201			# CAN message ID for Floor Controller 1
ID_f2 = 0x202			# CAN message ID for Floor Controller 2
ID_f3 = 0x203			# CAN message ID for Floor Controller 3

# CAN signal masks
mask_sc_enable = 		0b00000100	# Bit mask for sc_enable signal
mask_sc_sc_floor_cmd =	0b00000011	# Bit mask for sc_sc_floor_cmd signal
mask_ec_state =			0b00000100	# Bit mask for ec_state signal
mask_ec_car_pos = 		0b00000011 	# Bit mask for ec_car_pos signal
mask_cc_door_state = 	0b00000100	# Bit mask for cc_door_state signal
mask_cc_floor_req = 	0b00000011	# Bit mask for cc_floor_req signal
mask_f1_call_req = 		0b00000001	# Bit mask for f1_call_req signal
mask_f2_call_req = 		0b00000001	# Bit mask for f2_call_req signal
mask_f3_call_req = 		0b00000001	# Bit mask for f3_call_req signal

# CAN signal value tables
sig_sc_enable = ["Cmd Disable Elevator", "Cmd Enable Elevator"]
sig_sc_floor_cmd = ["Cmd None", "Cmd Floor 1", "Cmd Floor 2", "Cmd Floor 3"]
sig_ec_state = ["Elevator Disabled", "Elevator Enabled"]
sig_ec_car_pos = ["In Transit", "Floor 1", "Floor 2", "Floor 3"]
sig_cc_door_state = ["Door Open", "Door Closed"]
sig_cc_floor_req = ["No Request", "Req Floor 1", "Req Floor 2", "Req Floor 3"]
sig_f1_call_req = ["No Request", "Car Requested"]
sig_f2_call_req = ["No Request", "Car Requested"]
sig_f3_call_req = ["No Request", "Car Requested"]

##############################################################################################
## Global data storage
## Maybe improve this later
##############################################################################################

# Supervisory Controller Data
sc_enable = 0 					# Enable bit value to be sent to EC
sc_floor_cmd = 0 				# Floor number to be sent to EC

# Elevator Controller Data
ec_state = 0 					# Enable bit value reported from EC
ec_car_pos = 0 					# Floor number reported from EC

# Floor Controller Data
f1_call_req = 0 				# Value of request bit from Floor Controller 1
f2_call_req = 0 				# Value of request bit from Floor Controller 2
f3_call_req = 0 				# Value of request bit from Floor Controller 3

# Car Controller Data
cc_floor_req = 0 				# Floor number requested from Car Controller
cc_door_state = 0 				# Door state reported from Car Controller, init to 0 (open)
cc_door_open = 0
cc_door_closed = 1

# Remote Interface Data
remote_floor_req = 0 			# Floor number requested from Remote Operator

# State machine data
sm_floor_req = 0 				# Floor request input to the state machine
sm_state = 0 					# State machine current state
sm_state_values = ["Car Not Moving", "Request New Floor", "Car Moving"]
sm_state_car_not_moving = 0
sm_state_request_new_floor = 1
sm_state_car_moving = 2


##############################################################################################
## Functions/methods
##############################################################################################


##
## Init_MySQL()
## Connect to the MySQL database
##
def Init_MySQL():
	global db
	global db_cursor

	db = MySQLdb.connect(host="23.229.227.71", user="adequateadmin", passwd="adequatepassword", db="adequateelevators")

	if db.errno():
		print "Error connecting to database"
		exit
	else:
		print "Connected to database"
		db_cursor = db.cursor()

## end of method


##
## Uninit_MySQL()
## Close connection to MySQL database
##
def Uninit_MySQL():
	db.close()
	print "Disconnected from database"


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


##
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
## Basically a playground for now
##
def process_input():
	print "Elevator Command Input"
	global remote_floor_req

	remote_floor_req = input("Enter floor number:")		
## end of method


##
## update_display()
## Show elevator status and command
##
def update_display():
	global sc_floor_cmd
	global sc_enable
	global ec_car_pos
	global ec_state
	
	os.system('clear')	# Clear screen

	# Display current state
	print "STATE: ", sm_state_values[sm_state]
	print "SM_FLOOR_REQ: ", sm_floor_req
	print ""


	# Print data nicely https://stackoverflow.com/questions/9535954/printing-lists-as-tabular-data
	header = ["Signal", "Value"]
	data_sc_enable = ['SC_ENABLE', sig_sc_enable[sc_enable]]
	data_sc_floor_cmd = ['SC_FLOOR_CMD', sig_sc_floor_cmd[sc_floor_cmd]]
	data_ec_state = ['EC_STATE', sig_ec_state[ec_state]]
	data_ec_car_pos = ['EC_CAR_POS', sig_ec_car_pos[ec_car_pos]]
	data_f1_call_req = ['F1_CALL_REQ', sig_f1_call_req[f1_call_req]]
	data_f2_call_req = ['F2_CALL_REQ', sig_f2_call_req[f2_call_req]]
	data_f3_call_req = ['F3_CALL_REQ', sig_f3_call_req[f3_call_req]]
	data_cc_floor_req = ['CC_FLOOR_REQ', sig_cc_floor_req[cc_floor_req]]
	data_cc_door_state = ['CC_DOOR_STATE', sig_cc_door_state[cc_door_state]]
	data_remote_req = ['REMOTE_REQ', sig_cc_floor_req[remote_floor_req]]

	data_table = [data_sc_enable, data_sc_floor_cmd, data_ec_state, data_ec_car_pos, 
					data_f1_call_req, data_f2_call_req, data_f3_call_req, 
					data_cc_floor_req, data_cc_door_state, data_remote_req]

	print tabulate(data_table, headers=header)

	# Add note at bottom to enter debug mode
	print ""
	print "Press 'Enter' for debug mode"
## end of method


##
## Rx_CAN(device)
## Receive any pending CAN messages and populate global variables as necessary
##
def Rx_CAN(device):
	global ec_car_pos
	global ec_state
	global f1_call_req
	global f2_call_req
	global f3_call_req
	global cc_floor_req
	global cc_door_state

	# Read a message
	message = PCANBasic.Read(PCAN, PCAN_USBBUS1)
	
	# Don't update database if no messages read
	if message[1].ID <= 1:
		return;

	# Read all the messages - then update the database ONCE
	while message[1].ID > 1:					
		# Process EC Status Message
		if message[1].ID == ID_ec:
			ec_car_pos = message[1].DATA[0] & mask_ec_car_pos
			ec_state = ((message[1].DATA[0] & mask_ec_state) >> 2)	# Any good way to dynamically shift bits based on bit number??? Think about this later
		
		# Process F1 Status Message
		elif message[1].ID == ID_f1:
			f1_call_req = message[1].DATA[0] & mask_f1_call_req

		# Process F2 Status Message
		elif message[1].ID == ID_f2:
			f2_call_req = message[1].DATA[0] & mask_f2_call_req

		# Process F3 Status Message
		elif message[1].ID == ID_f3:
			f3_call_req = message[1].DATA[0] & mask_f3_call_req

		# Process CC Status Message
		elif message[1].ID == ID_cc:
			cc_floor_req = message[1].DATA[0] & mask_cc_floor_req
			cc_door_state = ((message[1].DATA[0] & mask_cc_door_state) >> 2) # Any good way to dynamically shift bits based on bit number??? Think about this later

		# Read next message
		message = PCANBasic.Read(PCAN, PCAN_USBBUS1)

	# Update the database (all messages)
	Insert_MySQL('EC_CAR_POS', ec_car_pos, sig_ec_car_pos[ec_car_pos])
	Insert_MySQL('EC_STATE', ec_state, sig_ec_state[ec_state])
	Insert_MySQL('F1_CALL_REQ', f1_call_req, sig_f1_call_req[f1_call_req])
	Insert_MySQL('F2_CALL_REQ', f2_call_req, sig_f2_call_req[f2_call_req])
	Insert_MySQL('F3_CALL_REQ', f3_call_req, sig_f3_call_req[f3_call_req])
	Insert_MySQL('CC_FLOOR_REQ', cc_floor_req, sig_cc_floor_req[cc_floor_req])
	Insert_MySQL('CC_DOOR_STATE', cc_door_state, sig_cc_door_state[cc_door_state])

## end of method


## 
## Tx_EC_Cmd(device)
## Transmit the command message to the elevator controller
##
def Tx_EC_Cmd(device):
	global sc_floor_cmd
	global sc_enable
	message = TPCANMsg()

	message.ID = ID_sc
	message.MSGTYPE = PCAN_MESSAGE_STANDARD
	message.LEN = 1
	message.DATA[0] = (sc_floor_cmd | (sc_enable << 2)) # Any good way to dynamically shift bits based on bit number??? Think about this later

	# Send the message and check if it was successful
	status = PCANBasic.Write(device, PCAN_USBBUS1, message)
	if status > 0:
		print "Error transmitting CAN message"
		print PCANBasic.GetErrorText(device, status, 0)
		exit()

	# Add the signals to the database
	Insert_MySQL('SC_FLOOR_CMD', sc_floor_cmd, sig_sc_floor_cmd[sc_floor_cmd])
	Insert_MySQL('SC_ENABLE', sc_enable, sig_sc_enable[sc_enable])

## end of method


##
## Insert_MySQL(signal, raw, phys)
## Insert a signal into the MySQL database
##
def Insert_MySQL(signal, raw, phys):
	# Generate a timestamp
	ts = time.time()
	timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

	# Build the query
	query = "INSERT INTO signals(name, timestamp, raw, phys) VALUES(%s,%s,%s,%s)"
	#query = "INSERT INTO signals(name, raw, phys) VALUES(%s,%s,%s)"
	values = (signal, timestamp, raw, phys)
	#values = (signal, raw, phys)
	db_cursor.execute(query, values)
## end of method

##
## Get_Remote_Req()
## Pull the most recent value of the REMOTE_REQ signal from the database
##
def Get_Remote_Req():
	global remote_floor_req
	global ec_car_pos

	query = "SELECT name, timestamp, raw, phys FROM signals WHERE name='REMOTE_REQ' ORDER BY timestamp DESC LIMIT 1"
	db_cursor.execute(query)
	numrows = db_cursor.rowcount

	## If there is data, process it
	if numrows > 0:
		row = db_cursor.fetchone()
		remote_floor_req = row[2]

	## Logic to cancel remote floor request when we get to the correct floor
	if ec_car_pos == remote_floor_req:
		remote_floor_req = 0

## end of method

##
## Calc_Floor_Req()
## Logic for determining what floor to request
## Priority (highest to lowest): Remote request, car controller request, floor controller request
## See: S6Project/Phase_1/Supervisory_Controller_State_Machine.pdf
##
def Calc_Floor_Req():
	global sm_floor_req
	global sm_state
	global remote_floor_req
	global cc_floor_req
	global f1_call_req
	global f2_call_req
	global f3_call_req

	if remote_floor_req > 0:
		sm_floor_req = remote_floor_req
		#remote_floor_req = 0
	elif (cc_floor_req > 0) and (sm_state == sm_state_car_not_moving):
		sm_floor_req = cc_floor_req
	elif (f1_call_req > 0) and (sm_state == sm_state_car_not_moving):
		sm_floor_req = 1
	elif (f2_call_req > 0) and (sm_state == sm_state_car_not_moving):
		sm_floor_req = 2
	elif (f3_call_req > 0) and (sm_state == sm_state_car_not_moving):
		sm_floor_req = 3
## end of method


##
## Calc_State():
## Main state machine
## See: S6Project/Phase_1/Supervisory_Controller_State_Machine.pdf
##
def Calc_State():
	global sm_state
	global sm_floor_req
	global remote_floor_req
	global cc_door_state
	global ec_car_pos
	global sc_enable
	global sc_floor_cmd

	# Note: Data is set on exit of a state

	# Car not moving state (init)
	if sm_state == sm_state_car_not_moving:
		if (ec_car_pos != sm_floor_req) and (sm_floor_req > 0) and (cc_door_state == cc_door_closed):
			sc_enable = 1
			sc_floor_cmd = sm_floor_req
			sm_state = sm_state_request_new_floor

	# Request new floor state
	if sm_state == sm_state_request_new_floor:
		if (ec_car_pos == 0):					# Wait for car to start moving
			sm_state = sm_state_car_moving
		if (ec_car_pos == sm_floor_req):		# Handle case where car movement happens super fast
			sc_enable = 0
			sc_floor_cmd = 0
			sm_floor_req = 0
			sm_state = sm_state_car_not_moving

	# Car moving state
	if sm_state == sm_state_car_moving:
		if (ec_car_pos == sm_floor_req) and (cc_door_state == cc_door_open):
			sc_enable = 0
			sc_floor_cmd = 0
			sm_state = sm_state_car_not_moving
		elif (remote_floor_req > 0):
			sc_enable = 1
			sc_floor_cmd = remote_floor_req
			sm_state = sm_state_request_new_floor

	Insert_MySQL('SM_STATE', sm_state, sm_state_values[sm_state])
	Insert_MySQL('SM_FLOOR_REQ', sm_floor_req, sig_cc_floor_req[sm_floor_req])
## end of method

## 
## main()
##
def main():
	# Initialize device
	Init_PCAN(PCAN)
	Init_MySQL()

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
			Get_Remote_Req()
			Calc_Floor_Req()
			Calc_State()
	  		update_display()
	  		Tx_EC_Cmd(PCAN)
## end of method


try:
	main()
except KeyboardInterrupt:
	print " "
	Uninit_MySQL()
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




	db_cursor.execute("SELECT * FROM signals")
	for x in range(0, db_cursor.rowcount):
		row = db_cursor.fetchone()
		print row[0], "-->", row[1], "-->", row[2], "-->", row[3]
