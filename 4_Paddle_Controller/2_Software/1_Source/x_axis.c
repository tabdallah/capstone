//;******************************************************************************
//; x_axis.c - Code specific to the X-Axis DC Motor and Encoder
//; Name: Thomas Abdallah
//; Date: 2018-03-19
//;******************************************************************************
#include <stdlib.h>
#include <hidef.h>      /* common defines and macros */
#include "derivative.h"      /* derivative-specific definitions */
#include "timer.h"
#include "pwm.h"
#include "x_axis.h"
#include "can.h"

static dcm_t x_axis = {X_AXIS_LIMIT_1_ENC_TICKS, X_AXIS_LIMIT_1_ENC_TICKS, 0,0,0,0,0,0,0,0,0,0,0, dcm_limit_switch_pressed, dcm_limit_switch_pressed, dcm_ctrl_mode_disable};
static x_axis_error_e x_axis_error = x_axis_error_none;
static can_msg_raw_t can_msg_raw;
static can_msg_mc_cmd_pc_t can_msg_mc_cmd_pc;
static can_msg_pc_status_t can_msg_pc_status;

unsigned int encoder_ticks = 0;

//;**************************************************************
//;*                 x_axis_configure(void)
//;*	Configure H-Bridge direction control port pins.
//;*	Configure PWM channel for motor control.
//;*	Configure encoder port pins and input-capture interrupt.
//;**************************************************************
void x_axis_configure(void)
{
	// Configure H-Bridge direction control port pins.
	SET_BITS(X_AXIS_H_BRIDGE_DDR, (X_AXIS_H_BRIDGE_FORWARD_PIN | X_AXIS_H_BRIDGE_REVERSE_PIN));
	X_AXIS_H_BRIDGE_BRAKE;

	// Configure PWM channel for motor control.
	X_AXIS_SET_PWM_PERIOD;
	X_AXIS_SET_PWM_DUTY(X_AXIS_PWM_DUTY_MIN);
	X_AXIS_CLEAR_PWM_COUNT;
	X_AXIS_ENABLE_PWM;

	// Configure encoder port pins and input-capture interrupt.
	CLEAR_BITS(X_AXIS_ENC_DDR, X_AXIS_ENC_B);	// B-Phase input is read during ISR for A-Phase
	CLEAR_BITS(TIOS, X_AXIS_ENC_A_TIOS_MASK);	// Set A-Phase timer channel to input capture mode
	TCTL4 = X_AXIS_TCTL4_INIT;					// Capture on rising edge
	SET_BITS(TIE, X_AXIS_ENC_A_TIOS_MASK);		// Enable interrupts for A-Phase timer channel
	TFLG1 = (X_AXIS_ENC_A_TFLG1_MASK);			// Clear the flag in case anything is pending

	// Configure limit switch port pins.
	SET_BITS(X_AXIS_LIMIT_DDR, (X_AXIS_LIMIT_1_PIN | X_AXIS_LIMIT_2_PIN));

	// Default to position control
	x_axis.ctrl_mode = dcm_ctrl_mode_position;
}

//;**************************************************************
//;*                 x_axis_home(void)
//;*	Move paddle to home position in the X-Axis
//;**************************************************************
void x_axis_home(void)
{
	// Save current control mode to be restored before returning
	dcm_ctrl_mode_e ctrl_mode = x_axis.ctrl_mode;

	// Disable position/velocity controllers
	x_axis.ctrl_mode = dcm_ctrl_mode_manual;

	// Drive motor backwards
	x_axis_set_dcm_drive(dcm_h_bridge_dir_reverse, 75);

	// Wait for limit switch to be hit
	// To Do: Should have some timeout here to handle broken switch
	// For now broken switch handled by dcm overload check
	while (X_AXIS_LIMIT_1 == dcm_limit_switch_unpressed) {};
	x_axis_set_dcm_drive(dcm_h_bridge_dir_brake, X_AXIS_PWM_DUTY_MIN);

	// Set target to center of table
	x_axis.position_cmd_enc_ticks = X_AXIS_LIMIT_2_ENC_TICKS / 2;

	// Return control to position/velocity controllers
	x_axis.ctrl_mode = ctrl_mode;
	return;
}

//;**************************************************************
//;*                 x_axis_position_ctrl(void)
//;*	Closed loop position control for the X-Axis motor.
//;**************************************************************
void x_axis_position_ctrl(void)
{
	unsigned int error_p;

	// Sanity check control mode
	if (x_axis.ctrl_mode != dcm_ctrl_mode_position) {
		return;
	}

	// Limit position commands to stay inside the virtual limit
	if (x_axis.position_cmd_enc_ticks > (X_AXIS_LIMIT_2_ENC_TICKS - X_AXIS_BOUNDARY_ENC_TICKS)) {
		x_axis.position_cmd_enc_ticks = X_AXIS_LIMIT_2_ENC_TICKS - X_AXIS_BOUNDARY_ENC_TICKS;
	}
	if (x_axis.position_cmd_enc_ticks < X_AXIS_BOUNDARY_ENC_TICKS) {
		x_axis.position_cmd_enc_ticks = X_AXIS_BOUNDARY_ENC_TICKS;
	}

	// Read limit switch states
	x_axis.limit_switch_1 = X_AXIS_LIMIT_1;
	x_axis.limit_switch_2 = X_AXIS_LIMIT_2;
	if (x_axis.limit_switch_1 == dcm_limit_switch_pressed) {
		x_axis.position_enc_ticks = X_AXIS_LIMIT_1_ENC_TICKS;
	}
	if (x_axis.limit_switch_2 == dcm_limit_switch_pressed) {
		x_axis.position_enc_ticks = X_AXIS_LIMIT_2_ENC_TICKS;
	}

	// Calculate position error
	x_axis.position_error_ticks = x_axis.position_cmd_enc_ticks - x_axis.position_enc_ticks;
	error_p = abs(x_axis.position_error_ticks) * X_AXIS_POS_GAIN_P;

	// Stop if at desired position
	if (x_axis.position_error_ticks == 0) {
		x_axis_set_dcm_drive(dcm_h_bridge_dir_brake, X_AXIS_PWM_DUTY_MIN);
		return;
	}

	// Drive motor to desired position
	if (x_axis.position_error_ticks > 0) {
		if (x_axis.h_bridge_direction == dcm_h_bridge_dir_reverse) {
			// Stop before reversing direction
			x_axis_set_dcm_drive(dcm_h_bridge_dir_brake, X_AXIS_PWM_DUTY_MIN);
		} else {
			if (error_p > X_AXIS_PWM_DUTY_MAX) {
				x_axis.pwm_duty = X_AXIS_PWM_DUTY_MAX;
			} else {
				x_axis.pwm_duty = LOW(error_p);
			}
			x_axis_set_dcm_drive(dcm_h_bridge_dir_forward, x_axis.pwm_duty);
		}
		return;
	} else {
		if (x_axis.h_bridge_direction == dcm_h_bridge_dir_forward) {
			// Stop before reversing direction
			x_axis_set_dcm_drive(dcm_h_bridge_dir_brake, X_AXIS_PWM_DUTY_MIN);
		} else {
			if (error_p > X_AXIS_PWM_DUTY_MAX) {
				x_axis.pwm_duty = X_AXIS_PWM_DUTY_MAX;
			} else {
				x_axis.pwm_duty = LOW(error_p);
			}
			x_axis_set_dcm_drive(dcm_h_bridge_dir_reverse, x_axis.pwm_duty);
		}
		return;
	}
}

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
		pos_x_calc = x_axis.position_enc_ticks * 10;
		pos_x_calc = pos_x_calc * X_AXIS_MM_PER_REV;
		can_msg_pc_status.pos_x_mm = 0xFFFF & (((pos_x_calc / X_AXIS_ENC_TICKS_PER_REV) / 10) + PUCK_RADIUS_MM + X_AXIS_LIMIT_1_MM);

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

//;**************************************************************
//;*                 x_axis_dcm_overload_check(void)
//;*	Check that DC motor is not blocked/overloaded
//;**************************************************************
void x_axis_dcm_overload_check(void)
{
	static unsigned int strike_counter = 0;
	static dcm_h_bridge_dir_e previous_direction = dcm_h_bridge_dir_brake;

	// Reset strike counter if motor changes direction
	if (previous_direction != x_axis.h_bridge_direction) {
		previous_direction = x_axis.h_bridge_direction;
		strike_counter = 0;
		return;
	}

	// Only checking for overload condition at max speed.
	// ToDo: Do some sort of interpolation to determine expected period from PWM duty
	if (x_axis.pwm_duty != X_AXIS_PWM_DUTY_MAX) {
		return;
	}

	if (x_axis.speed_mm_per_s < X_AXIS_DCM_OVERLOAD_LIMIT_MM_PER_S) {
		//strike_counter ++;
	} else {
		strike_counter = 0;
	}

	// Throw error and stop motor if strike limit is reached
	if (strike_counter >= X_AXIS_DCM_OVERLOAD_STRIKE_COUNT) {
		x_axis_error = x_axis_error_dcm_overload;
		x_axis.ctrl_mode = dcm_ctrl_mode_disable;
		x_axis_set_dcm_drive(dcm_h_bridge_dir_brake, X_AXIS_PWM_DUTY_MIN);
	}
}

//;**************************************************************
//;*                 x_axis_calculate_speed(void)
//;*	Calculate speed in mm per second
//;**************************************************************
void x_axis_calculate_speed(void)
{
	static unsigned int position_enc_ticks_old = 0; 
	static unsigned char count = 1;
	unsigned long speed_x_calc;

	// Only calculate speed every 10 ms to get better accuracy
	if ((count % 10) == 0) {
		x_axis.speed_enc_ticks_per_s = 100 * abs(x_axis.position_enc_ticks - position_enc_ticks_old);
		speed_x_calc = x_axis.speed_enc_ticks_per_s * X_AXIS_MM_PER_REV;
		x_axis.speed_mm_per_s = 0xFFFF & ((speed_x_calc / X_AXIS_ENC_TICKS_PER_REV));
		position_enc_ticks_old = x_axis.position_enc_ticks;
	}

	// Limit counter to max value of 10
	if (count == 10) {
		count = 1;
	} else {
		count ++;
	}
}

//;**************************************************************
//;*                 x_axis_set_dcm_drive(void)
//;*	Helper function to set DC motor direction and speed
//;**************************************************************
//static void x_axis_set_dcm_drive(dcm_h_bridge_dir_e direction, unsigned char pwm_duty)
void x_axis_set_dcm_drive(dcm_h_bridge_dir_e direction, unsigned char pwm_duty)
{
	switch (direction)
	{
		case dcm_h_bridge_dir_brake:
			X_AXIS_SET_PWM_DUTY(X_AXIS_PWM_DUTY_MIN);
			x_axis.pwm_duty = X_AXIS_PWM_DUTY_MIN;
			x_axis.h_bridge_direction = dcm_h_bridge_dir_brake;
			X_AXIS_H_BRIDGE_BRAKE;
			break;
		case dcm_h_bridge_dir_forward:
			X_AXIS_SET_PWM_DUTY(pwm_duty);
			x_axis.pwm_duty = pwm_duty;
			x_axis.h_bridge_direction = dcm_h_bridge_dir_forward;
			X_AXIS_H_BRIDGE_FORWARD;
			break;
		case dcm_h_bridge_dir_reverse:
			X_AXIS_SET_PWM_DUTY(pwm_duty);
			x_axis.pwm_duty = pwm_duty;
			x_axis.h_bridge_direction = dcm_h_bridge_dir_reverse;
			X_AXIS_H_BRIDGE_REVERSE;
			break;
		default:
			X_AXIS_SET_PWM_DUTY(X_AXIS_PWM_DUTY_MIN);
			x_axis.pwm_duty = X_AXIS_PWM_DUTY_MIN;
			x_axis.h_bridge_direction = dcm_h_bridge_dir_brake;
			X_AXIS_H_BRIDGE_BRAKE;
	}
}

//;**************************************************************
//;*                 x_axis_encoder_a()
//;*  Handles IC function for X-Axis Encoder A Phase
//;**************************************************************
interrupt 8 void x_axis_encoder_a(void)
{
	// Track direction
	if (X_AXIS_ENC_PORT & X_AXIS_ENC_B) {
		// Phase B leads Phase A
		x_axis.quadrature_direction = dcm_quad_dir_reverse;
		if (x_axis.position_enc_ticks > 0) {
			x_axis.position_enc_ticks --;
		}
	} else {
		// Phase A leads Phase B
		x_axis.quadrature_direction = dcm_quad_dir_forward;
		if (x_axis.position_enc_ticks < MAX_UINT) {
			x_axis.position_enc_ticks ++;
		}
	}

	(void) X_AXIS_ENC_A_TIMER;
}

//;**************************************************************
//;*                 can_rx_handler()
//;*  Interrupt handler for CAN Rx
//;**************************************************************
interrupt 38 void can_rx_handler(void) {
  	unsigned char i;	      // Loop counter
	unsigned int ID0, ID1;   // To read CAN ID registers and manipulate 11-bit ID's into a single number
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
		// Bytes 0-1 X-Axis position command
		can_msg_mc_cmd_pc.pos_cmd_x_mm = (can_msg_raw.data[0] | (can_msg_raw.data[1] << 8));
	}

	// Set motor position command in encoder ticks
	if (can_msg_mc_cmd_pc.pos_cmd_x_mm > (X_AXIS_LIMIT_1_MM + PUCK_RADIUS_MM)) {
		pos_cmd_calculation = can_msg_mc_cmd_pc.pos_cmd_x_mm - X_AXIS_LIMIT_1_MM - PUCK_RADIUS_MM;
	} else {
		pos_cmd_calculation = 0;
	}
	pos_cmd_calculation = pos_cmd_calculation * X_AXIS_ENC_TICKS_PER_REV;
	pos_cmd_calculation = pos_cmd_calculation / X_AXIS_MM_PER_REV;
	x_axis.position_cmd_enc_ticks = 0xFFFF & pos_cmd_calculation;

	// Clear Rx flag
	SET_BITS(CANRFLG, CAN_RX_INTERRUPT);
}