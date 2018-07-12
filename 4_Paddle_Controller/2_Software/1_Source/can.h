//;******************************************************************************
//; can.h - HCS12 MSCAN macros and constants
//; Name: Thomas Abdallah
//; Date: 2018-03-29
//;******************************************************************************
#include "TA_Header_W2016.h"  /* my macros and constants */
#include "state_machine.h"

#define CAN_INIT 0x01
#define CAN_START 0x00
#define CAN_SYNC 0x10
#define CAN_RX_INTERRUPT 0x01		// Write to CANRFLG to acknowledge the interrupt and release the buffer
#define CAN_LOOPBACK 0xE0			// Enable module in loopback mode with bus clock
#define CAN_NORMAL 0xC0				// Enable module in normal mode with bus clock
#define BTR0_125K 0x07
#define BTR1_125K 0x23
#define CAN_FILTER_16b 0x10			// Define four 16-bit filters

// Acceptance filter definitions
#define ACC_CODE_ID100 0x2000
#define ACC_CODE_ID100_HIGH ((ACC_CODE_ID100 & 0xFF00)>>8)
#define ACC_CODE_ID100_LOW (ACC_CODE_ID100 & 0x00FF)

// Mask code definitions
#define MASK_CODE_ST_ID 0x0007
#define MASK_CODE_ST_ID_HIGH ((MASK_CODE_ST_ID & 0xFF00)>>8)
#define MASK_CODE_ST_ID_LOW (MASK_CODE_ST_ID & 0xFF)

// CAN module errors
#define CAN_ERR_NONE 0x00
#define CAN_ERR_BUFFER_FULL 0x01
#define CAN_ERR_TX 0x02

// Max number of Tx attempts
#define CAN_TX_LIMIT 1000
// ID definition
#define CAN_ID_MC_CMD_PC 0x100
#define CAN_ST_ID_MC_CMD_PC 0x20000000
#define CAN_ID_PC_STATUS 0x101
#define CAN_ST_ID_PC_STATUS 0x20200000
#define CAN_DLC_PC_STATUS 8

// Radius of the paddle in mm
#define PADDLE_RADIUS_MM 48

// Enumerated data types
typedef enum {
	can_error_none = 0,
	can_error_buffer_full = 1,
	can_error_tx = 2
} can_error_e;

// CAN message structure definitions
typedef struct {
	unsigned int id;
	unsigned char dlc;
	unsigned char data[8];	// This is wasteful but avoids overhead of dynamic memory allocation
} can_msg_raw_t;

typedef struct {
	unsigned int pos_cmd_x_mm;
	unsigned int pos_cmd_y_mm;
	unsigned char speed_cmd_x;
	unsigned char speed_cmd_y;
	sm_state_cmd_e state_cmd;
} can_msg_mc_cmd_pc_t;

typedef struct {
	unsigned int pos_x_mm;
	unsigned int pos_y_mm;
	sm_state_e state;
	sm_error_e error;
} can_msg_pc_status_t;

// Function prototypes
void can_configure(void);
unsigned char can_tx(unsigned long id, unsigned char length, unsigned char *txdata);
void can_send_status(void);
can_error_e *can_get_error(void);