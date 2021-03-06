//;******************************************************************************
//; x_axis.c - HCS12 MSCAN implementation
//; Name: Thomas Abdallah
//; Date: 2018-03-29
//;******************************************************************************
#include <hidef.h>      /* common defines and macros */
#include "derivative.h"      /* derivative-specific definitions */
#include "can.h"
#include "dcm.h"
#include "x_axis.h"
#include "y_axis.h"
#include "ir.h"
#include <stdlib.h>

// Code from AN3034 app note (but not really because that code was hot garbage)

static can_error_e error = can_error_none;
static can_msg_raw_t can_msg_raw;
static can_msg_mc_cmd_pc_t can_msg_mc_cmd_pc;
static can_msg_pc_status_t can_msg_pc_status;

//;**************************************************************
//;*                 can_configure(void)
//;*  Configures & enables the CAN controller
//;**************************************************************  
void can_configure(void) {
	// Enter initialization mode
	CANCTL0 = CAN_INIT;

	// Wait for initialization mode acknowledge
	while (!(CANCTL1 & CAN_INIT)) {};

	CANCTL1 = CAN_NORMAL;		// Enable module in normal mode with bus clock
	CANBTR0 = BTR0_125K;		// Set baud rate to 125KBaud
	CANBTR1 = BTR1_125K;		// Set baud rate to 125KBaud

	CANIDAC = CAN_FILTER_16b;	// Define four 16-bit filters
	
	CANIDMR0 = MASK_CODE_ST_ID_HIGH;
	CANIDMR1 = MASK_CODE_ST_ID_LOW;

	// Accept CAN ID 0x100 only
	CANIDAR0 = ACC_CODE_ID100_HIGH;
	CANIDAR1 = ACC_CODE_ID100_LOW;

	// Exit initialization mode
	CANCTL0 = CAN_START;

	// Wait for normal mode acknowledge
	while ((CANCTL1 & CAN_START) != 0) {};

	// Enable Rx interrupts and clear flag
	SET_BITS(CANRFLG, CAN_RX_INTERRUPT);
	SET_BITS(CANRIER, CAN_RX_INTERRUPT);
}

//;**************************************************************
//;*                 can_tx(id, length, *txdata)
//;*  Outputs a CAN frame using polling
//;**************************************************************   
unsigned char can_tx(unsigned long id, unsigned char length, unsigned char *txdata) {
	unsigned int tx_count = 0;	// Count number of Tx attempts
	unsigned char txbuffer;	// To store the selected buffer for transmitting
	unsigned char index;    // Index into the data array

	// Check if transmit buffer is full
	if (!CANTFLG) {
		return CAN_ERR_BUFFER_FULL;
	}

	CANTBSEL = CANTFLG; 	// Select lowest empty buffer
	txbuffer = CANTBSEL;	// Backup selected buffer

	// Load CAN ID to IDR register
	*((unsigned long *) ((unsigned long)(&CANTXIDR0))) = id;

	// Load message data to data segment registers
	for (index=0; index<length; index++) {
		*(&CANTXDSR0 + index) = txdata[index]; // Load data to Tx buffer data segment registers
	}

	CANTXDLR = length;		// Set DLC
	CANTXTBPR = 0x00;		// Set priority to highest always (not enough traffic to matter)
	CANTFLG = txbuffer; 	// Start transmission

	// Wait for transmit to complete
	/*
	while ( (CANTFLG & txbuffer) != txbuffer) {
		tx_count ++;
		if (tx_count >= CAN_TX_LIMIT) {
			return CAN_ERR_TX;
		}
	} */

	return CAN_ERR_NONE;
}

//;**************************************************************
//;*                 can_rx_handler()
//;*  Interrupt handler for CAN Rx
//;**************************************************************
interrupt 38 void can_rx_handler(void) {
  	unsigned char i;	      // Loop counter
	unsigned int ID0, ID1;   // To read CAN ID registers and manipulate 11-bit ID's into a single number
	dcm_t *x_axis, *y_axis;
	sm_state_e sm_state = sm_get_state();

	// Store 11-bit CAN ID as a single number
	ID0 = (CANRXIDR0 << 3);
	ID1 = (CANRXIDR1 >> 5);
	can_msg_raw.id = (0x0FFF) & (ID0 | ID1);
	
	// Store DLC
	can_msg_raw.dlc = LO_NYBBLE(CANRXDLR);

	// Read data one byte at a time
	for (i=0; i < can_msg_raw.dlc; i++) {
		can_msg_raw.data[i] = *(&CANRXDSR0 + i);
	}

	// Process commands from Master Controller
	if (can_msg_raw.id == CAN_ID_MC_CMD_PC) {
		// Bytes 0-1 X-Axis position command in millimetres
		can_msg_mc_cmd_pc.pos_cmd_x_mm = (can_msg_raw.data[0] | (can_msg_raw.data[1] << 8));

		// Bytes 2-3 Y-Axis position command in millimetres
		can_msg_mc_cmd_pc.pos_cmd_y_mm = (can_msg_raw.data[2] | (can_msg_raw.data[3] << 8));

		// Byte 4 bits 0-1 contain X-Axis speed command
		can_msg_mc_cmd_pc.speed_cmd_x = (can_msg_raw.data[4] & 0b00000011);

		// Byte 4 bits 2-3 contain Y-Axis speed command
		can_msg_mc_cmd_pc.speed_cmd_y = ((can_msg_raw.data[4] >> 2) & (0b00000011));

		// Byte 5 is state command
		can_msg_mc_cmd_pc.state_cmd = can_msg_raw.data[5];
	}

	// Set X-Axis position command
	x_axis = x_axis_get_data();
	x_axis->position_cmd_mm = can_msg_mc_cmd_pc.pos_cmd_x_mm;

	// Set Y-Axis position command
	if (sm_state != sm_state_calibration) {
		y_axis = y_axis_get_data();
		y_axis->position_cmd_mm = can_msg_mc_cmd_pc.pos_cmd_y_mm;
	}

	// Set state machine command
	sm_set_state_cmd(can_msg_mc_cmd_pc.state_cmd);

	// Clear Rx flag
	SET_BITS(CANRFLG, CAN_RX_INTERRUPT);
}

//;**************************************************************
//;*                 can_send_status
//;*	Send PC_Status message
//;**************************************************************
void can_send_status(void)
{
	static unsigned char count = 0;
	unsigned char data[8];
	unsigned long pos_x_calc, pos_y_calc;
	dcm_t *x_axis, *y_axis;
	ir_sensor_e ir_sensor_human, ir_sensor_robot;

	// Calculate X and Y axis positions in mm
	x_axis = x_axis_get_data();
	y_axis = y_axis_get_data();
	DisableInterrupts;	// Start critical region
	pos_x_calc = x_axis->position_enc_ticks * 10;
	pos_y_calc = y_axis->position_enc_ticks * 10;
	EnableInterrupts;	// End critical region
	pos_x_calc = pos_x_calc * DCM_MM_PER_REV;
	pos_y_calc = pos_y_calc * DCM_MM_PER_REV;
	can_msg_pc_status.pos_x_mm = 0xFFFF & (((pos_x_calc / DCM_ENC_TICKS_PER_REV) / 10) + PADDLE_RADIUS_MM + X_AXIS_HOME_MM);
	can_msg_pc_status.pos_y_mm = 0xFFFF & (((pos_y_calc / DCM_ENC_TICKS_PER_REV) / 10) + PADDLE_RADIUS_MM + Y_AXIS_HOME_MM);

	// Get state and error
	can_msg_pc_status.state = sm_get_state();
	can_msg_pc_status.error = sm_get_error();

	// Get goal data
	ir_sensor_human = ir_get_output(ir_goal_human);
	ir_sensor_robot = ir_get_output(ir_goal_robot);
	if (ir_sensor_human == ir_sensor_blocked) {
		can_msg_pc_status.goal = can_goal_human;
	} else if (ir_sensor_robot == ir_sensor_blocked) {
		can_msg_pc_status.goal = can_goal_robot;
	} else {
		can_msg_pc_status.goal = can_goal_none;
	}

	// Pack data into 8 byte array
	// This seems sloppy, fix this later.
	data[0] = can_msg_pc_status.pos_x_mm & 0x00FF;
	data[1] = (can_msg_pc_status.pos_x_mm & 0xFF00) >> 8;
	data[2] = can_msg_pc_status.pos_y_mm & 0x00FF;
	data[3] = (can_msg_pc_status.pos_y_mm & 0xFF00) >> 8;
	data[4] = (can_msg_pc_status.goal & 0xF0);	// TODO add speed settings
	data[5] = can_msg_pc_status.state;
	data[6] = can_msg_pc_status.error;
	data[7] = 0;	// Debug

	// Send message and handle errors
	switch (can_tx(CAN_ST_ID_PC_STATUS, CAN_DLC_PC_STATUS, &data[0]))
	{
		case CAN_ERR_NONE:
			break;
		case CAN_ERR_BUFFER_FULL:
			error = can_error_buffer_full;
			break;
		case CAN_ERR_TX:
			error = can_error_tx;
			break;
	}
}

//;**************************************************************
//;*                 can_get_error
//;*	Returns value of CAN error
//;**************************************************************
can_error_e *can_get_error(void)
{
	return &error;
}