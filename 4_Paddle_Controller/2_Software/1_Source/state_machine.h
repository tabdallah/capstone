//;******************************************************************************
//; x_axis.h - Code specific to the X-Axis DC Motor and Encoder
//; Name: Thomas Abdallah
//; Date: 2018-03-19
//;******************************************************************************
#include "TA_Header_W2016.h"  /* my macros and constants */

#ifndef STATE_MACHINE_H
#define STATE_MACHINE_H

// Enumerated data types
typedef enum {
	sm_state_off = 0,
	sm_state_calibration = 1,
	sm_state_on = 2,
	sm_state_error = 3
} sm_state_e;

typedef enum {
	sm_state_cmd_off = 0,
	sm_state_cmd_calibration = 1,
	sm_state_cmd_on = 2,
	sm_state_cmd_clear_error = 3
} sm_state_cmd_e;

typedef enum {
	sm_error_none = 0,
	sm_error_y_axis_overload = 1,
	sm_error_x_axis_overload = 2,
	sm_error_can_buffer_full = 3,
	sm_error_can_tx = 4
} sm_error_e;

// Function prototypes
sm_state_e sm_get_state(void);
sm_error_e sm_get_error(void);
void sm_set_state_cmd(sm_state_cmd_e new_command);
void sm_step(void);
static void sm_enter_state(sm_state_e new_state);
void sm_error_handling(void);

#endif