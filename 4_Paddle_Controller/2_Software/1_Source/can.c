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
#include <stdlib.h>

// Code from AN3034 app note (but not really because that code was hot garbage)

// Global data structures for debugging
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
	while ( (CANTFLG & txbuffer) != txbuffer) {
		tx_count ++;
		if (tx_count >= CAN_TX_LIMIT) {
			return CAN_ERR_TX;
		}
	}

	return CAN_ERR_NONE;
}

//;**************************************************************
//;*                 can_rx_handler()
//;*  Interrupt handler for CAN Rx
//;**************************************************************
interrupt 38 void can_rx_handler(void) {
  	unsigned char i;	      // Loop counter
	unsigned int ID0, ID1;   // To read CAN ID registers and manipulate 11-bit ID's into a single number
	unsigned long pos_cmd_calculation;
	dcm_t *x_axis;
	dcm_t *y_axis;

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
	if (can_msg_mc_cmd_pc.pos_cmd_x_mm > (X_AXIS_HOME_MM + PADDLE_RADIUS_MM)) {
		pos_cmd_calculation = can_msg_mc_cmd_pc.pos_cmd_x_mm - X_AXIS_HOME_MM - PADDLE_RADIUS_MM;
	} else {
		pos_cmd_calculation = 0;
	}
	pos_cmd_calculation = pos_cmd_calculation * DCM_ENC_TICKS_PER_REV;
	pos_cmd_calculation = pos_cmd_calculation / DCM_MM_PER_REV;
	x_axis = x_axis_get_data();
	x_axis->position_cmd_enc_ticks = 0xFFFF & pos_cmd_calculation;

	// Set Y-Axis position command
	if (can_msg_mc_cmd_pc.pos_cmd_y_mm > (Y_AXIS_HOME_MM + PADDLE_RADIUS_MM)) {
		pos_cmd_calculation = can_msg_mc_cmd_pc.pos_cmd_y_mm - Y_AXIS_HOME_MM - PADDLE_RADIUS_MM;
	} else {
		pos_cmd_calculation = 0;
	}
	pos_cmd_calculation = pos_cmd_calculation * DCM_ENC_TICKS_PER_REV;
	pos_cmd_calculation = pos_cmd_calculation / DCM_MM_PER_REV;
	y_axis = y_axis_get_data();
	y_axis->position_cmd_enc_ticks = 0xFFFF & pos_cmd_calculation;

	// Clear Rx flag
	SET_BITS(CANRFLG, CAN_RX_INTERRUPT);
}

/*
//;**************************************************************
//;*                 x_axis_send_status_can(void)
//;*	Send PC_Status_X message
//;**************************************************************
void x_axis_send_status_can(void)
{
	static unsigned char count = 1;
	static unsigned char error = 0;	// Set to non-zero to stop trying to send CAN messages
	unsigned char data[2];
	unsigned long pos_x_calc;

	// Return immediately if previous CAN error
	if (error != 0) {
		return;
	}

	// Only send message at 100Hz
	if ((count % 10) == 0) {
		DisableInterrupts;	// Start critical region
		pos_x_calc = x_axis.position_enc_ticks * 10;
		EnableInterrupts;	// End critical region
		pos_x_calc = pos_x_calc * X_AXIS_MM_PER_REV;
		can_msg_pc_status.pos_x_mm = 0xFFFF & (((pos_x_calc / X_AXIS_ENC_TICKS_PER_REV) / 10) + PUCK_RADIUS_MM + X_AXIS_HOME_MM);

		// This seems sloppy, fix this later.
		data[0] = can_msg_pc_status.pos_x_mm & 0x00FF;
		data[1] = (can_msg_pc_status.pos_x_mm & 0xFF00) >> 8;

		// Send message and handle errors
		switch (can_tx(CAN_ST_ID_PC_STATUS_X, CAN_DLC_PC_STATUS_X, &data[0]))
		{
			case CAN_ERR_NONE:
				break;
			case CAN_ERR_BUFFER_FULL:
				x_axis_error = x_axis_error_can_buffer_full;
				error = 1;
				break;
			case CAN_ERR_TX:
				x_axis_error = x_axis_error_can_tx;
				error = 1;
				break;
		}
	}

	// Limit counter to max value of 10
	if (count == 10) {
		count = 1;
	} else {
		count ++;
	}
}
*/


//;**************************************************************
//;*                 can_rx_handler()
//;*  Interrupt handler for CAN Rx
//;**************************************************************
/*

interrupt 38 void can_rx_handler(void) {
  	unsigned char i;		// Loop counter
	unsigned int ID0, ID1;	// To read CAN ID registers and manipulate 11-bit ID's into a single number
	unsigned long pos_cmd_calculation;

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
		// Bytes 2-3 Y-Axis position command
		can_msg_mc_cmd_pc.pos_cmd_y_mm = (can_msg_raw.data[2] | (can_msg_raw.data[3] << 8));
	}

	// Set motor position command in encoder ticks
	pos_cmd_calculation = (can_msg_mc_cmd_pc.pos_cmd_y_mm * 10) / Y_AXIS_MM_PER_REV;
	pos_cmd_calculation = (pos_cmd_calculation * Y_AXIS_ENC_TICKS_PER_REV) / 10;
	y_axis.position_cmd_enc_ticks = (0xFFFF) & (pos_cmd_calculation + Y_AXIS_LIMIT_1_ENC_TICKS);

	// Clear Rx flag
	SET_BITS(CANRFLG, CAN_RX_INTERRUPT);
}

//;**************************************************************
//;*                 y_axis_send_status_can(void)
//;*	Send PC_Status_Y message
//;**************************************************************
void y_axis_send_status_can(void)
{
	static unsigned char count = 1;
	static unsigned char error = 0;	// Set to non-zero to stop trying to send CAN messages
	unsigned char data[2];
	unsigned long pos_y_calc;

	// Return immediately if previous CAN error
	if (error != 0) {
		return;
	}

	// Only send message at 100Hz
	if ((count % 10) == 0) {
		DisableInterrupts;	// Start critical region
		if (y_axis.position_enc_ticks < Y_AXIS_BOUNDARY_ENC_TICKS) {
			pos_y_calc = 0;
		} else {
			pos_y_calc = (y_axis.position_enc_ticks - Y_AXIS_LIMIT_1_ENC_TICKS) * 10;
		}
		EnableInterrupts;	// End critical region
		pos_y_calc = pos_y_calc * Y_AXIS_MM_PER_REV;
		can_msg_pc_status.pos_y_mm = 0xFFFF & ((pos_y_calc / Y_AXIS_ENC_TICKS_PER_REV) / 10);

		// This seems sloppy, fix this later.
		data[0] = can_msg_pc_status.pos_y_mm & 0x00FF;
		data[1] = (can_msg_pc_status.pos_y_mm & 0xFF00) >> 8;

		// Send message and handle errors
		switch (can_tx(CAN_ST_ID_PC_STATUS_Y, CAN_DLC_PC_STATUS_Y, &data[0]))
		{
			case CAN_ERR_NONE:
				break;
			case CAN_ERR_BUFFER_FULL:
				y_axis_error = y_axis_error_can_buffer_full;
				error = 1;
				break;
			case CAN_ERR_TX:
				y_axis_error = y_axis_error_can_tx;
				error = 1;
				break;
		}
	}

	// Limit counter to max value of 10
	if (count == 10) {
		count = 1;
	} else {
		count ++;
	}
}


*/
