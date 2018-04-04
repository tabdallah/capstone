//;******************************************************************************
//; x_axis.c - HCS12 MSCAN implementation
//; Name: Thomas Abdallah
//; Date: 2018-03-29
//;******************************************************************************
#include <hidef.h>      /* common defines and macros */
#include "derivative.h"      /* derivative-specific definitions */
#include "can.h"
#include <stdlib.h>

// Code from AN3034 app note (but not really because that code was hot garbage)

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


// CAN Rx handler contained in x_axis.c and y_axis.c for now since they are running on separate hardware.