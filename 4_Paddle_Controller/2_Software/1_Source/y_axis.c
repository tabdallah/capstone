//;******************************************************************************
//; y_axis.c - Code specific to the Y-Axis DC Motors and Encoders
//; Name: Thomas Abdallah
//; Date: 2018-03-19
//;******************************************************************************
#include <stdlib.h>
#include <hidef.h>      /* common defines and macros */
#include "derivative.h"      /* derivative-specific definitions */
#include "timer.h"
#include "pwm.h"
#include "y_axis.h"
#include "can.h"

unsigned char Y_AXIS_L_GAIN_P = 10;
unsigned char Y_AXIS_L_GAIN_I = 1;
unsigned char Y_AXIS_L_INTEGRAL_LIMIT = 0;
unsigned char Y_AXIS_R_GAIN_P = 3;
unsigned char Y_AXIS_R_GAIN_I = 1;
unsigned char Y_AXIS_R_INTEGRAL_LIMIT = 0;

static dcm_t y_axis_l = {Y_AXIS_LIMIT_1_ENC_TICKS, Y_AXIS_LIMIT_1_ENC_TICKS, 0,0,0,0,0,0,0,0,0,0,0,0, dcm_home_switch_pressed, dcm_ctrl_mode_disable};
static dcm_t y_axis_r = {Y_AXIS_LIMIT_1_ENC_TICKS, Y_AXIS_LIMIT_1_ENC_TICKS, 0,0,0,0,0,0,0,0,0,0,0,0, dcm_home_switch_pressed, dcm_ctrl_mode_disable};
static signed int y_axis_lr_position_error_enc_ticks = 0;
static y_axis_error_e y_axis_error = y_axis_error_none;
static can_msg_raw_t can_msg_raw;
static can_msg_mc_cmd_pc_t can_msg_mc_cmd_pc;
static can_msg_pc_status_t can_msg_pc_status;

//;**************************************************************
//;*                 y_axis_configure(void)
//;*	Configure H-Bridge direction control port pins.
//;*	Configure PWM channel for motor control.
//;*	Configure encoder port pins and input-capture interrupt.
//;**************************************************************
void y_axis_configure(void)
{
	// Configure PWM channel for left motor
	SET_BITS(PWMCLK, PWMCLK_PCLK4_MASK);	// Use clock SA
	SET_BITS(PWMPOL, PWMPOL_PPOL4_MASK);	// Active high
	SET_BITS(PWMCAE, PWMCAE_CAE4_MASK);		// Centre aligned
	Y_AXIS_L_SET_PWM_PERIOD(Y_AXIS_PWM_PERIOD);	// Set for 20kHz switching frequency
	Y_AXIS_L_SET_PWM_DUTY(Y_AXIS_PWM_DUTY_OFF);	// Start with motor off
	Y_AXIS_L_CLEAR_PWM_COUNT;
	Y_AXIS_L_ENABLE_PWM;

	// Configure PWM channel for right motor
	SET_BITS(PWMCLK, PWMCLK_PCLK5_MASK);	// Use clock SA
	SET_BITS(PWMPOL, PWMPOL_PPOL5_MASK);	// Active high
	SET_BITS(PWMCAE, PWMCAE_CAE5_MASK);		// Centre aligned
	Y_AXIS_R_SET_PWM_PERIOD(Y_AXIS_PWM_PERIOD);	// Set for 20kHz switching frequency
	Y_AXIS_R_SET_PWM_DUTY(Y_AXIS_PWM_DUTY_OFF);	// Start with motor off
	Y_AXIS_R_CLEAR_PWM_COUNT;
	Y_AXIS_R_ENABLE_PWM;

	// Configure encoder port pins and input-capture interrupt.
	CLEAR_BITS(Y_AXIS_ENC_DDR, Y_AXIS_L_ENC_B);	// B-Phase input is read during ISR for A-Phase
	CLEAR_BITS(Y_AXIS_ENC_DDR, Y_AXIS_R_ENC_B);	// B-Phase input is read during ISR for A-Phase
	CLEAR_BITS(TIOS, TIOS_IOS2_MASK);			// Set A-Phase timer channel to input capture mode
	CLEAR_BITS(TIOS, TIOS_IOS4_MASK);			// Set A-Phase timer channel to input capture mode
	SET_BITS(TCTL4, Y_AXIS_L_TCTL4_INIT);		// Capture on rising edge of TC2
	SET_BITS(TCTL3, Y_AXIS_R_TCTL3_INIT);		// Capture on rising edge of TC4
	SET_BITS(TIE, TIOS_IOS2_MASK);				// Enable interrupts for A-Phase timer channels
	SET_BITS(TIE, TIOS_IOS4_MASK);				// Enable interrupts for A-Phase timer channels
	TFLG1 = (TFLG1_C2F_MASK);					// Clear the flag in case anything is pending
	TFLG1 = (TFLG1_C4F_MASK);					// Clear the flag in case anything is pending

	// Configure home switch port pins.
	CLEAR_BITS(Y_AXIS_HOME_DDR, Y_AXIS_L_HOME_PIN);
	CLEAR_BITS(Y_AXIS_HOME_DDR, Y_AXIS_R_HOME_PIN);

	// Default to position control
	y_axis_l.ctrl_mode = dcm_ctrl_mode_position;
	y_axis_r.ctrl_mode = dcm_ctrl_mode_position;
}

//;**************************************************************
//;*                 Y_axis_home(void)
//;*	Move paddle to home position in the Y-Axis
//;**************************************************************
void y_axis_home(void)
{
	// Save current control mode to be restored before returning
	dcm_ctrl_mode_e ctrl_mode = y_axis_l.ctrl_mode;

	// Disable position/velocity controllers
	y_axis_l.ctrl_mode = dcm_ctrl_mode_manual;

	// Drive motors backwards
	y_axis_l_set_dcm_drive(dcm_h_bridge_dir_reverse, 75);
	y_axis_r_set_dcm_drive(dcm_h_bridge_dir_reverse, 75);

	// Wait for limit switches to be hit
	// To Do: Should have some timeout here to handle broken switch
	// For now broken switch handled by dcm overload check
	for(;;)
	{
		if (Y_AXIS_L_HOME == dcm_home_switch_pressed) {
			y_axis_l_set_dcm_drive(dcm_h_bridge_dir_brake, Y_AXIS_SPEED_MIN);
		}
		if (Y_AXIS_R_HOME == dcm_home_switch_pressed) {
			y_axis_r_set_dcm_drive(dcm_h_bridge_dir_brake, Y_AXIS_SPEED_MIN);
		}
		if ((Y_AXIS_L_HOME == dcm_home_switch_pressed) && (Y_AXIS_R_HOME == dcm_home_switch_pressed)) {
			y_axis_l.position_enc_ticks = Y_AXIS_LIMIT_1_ENC_TICKS;
			y_axis_r.position_enc_ticks = Y_AXIS_LIMIT_1_ENC_TICKS;
			break;
		}
	}

	// Return control to position/velocity controllers
	y_axis_l.ctrl_mode = ctrl_mode;
	return;
}

//;**************************************************************
//;*                 y_axis_l_position_ctrl(void)
//;**************************************************************
void y_axis_l_position_ctrl(void)
{
	static signed int error_i = 0;
	signed int error_p, error_calc;

	// Sanity check control mode
	if (y_axis_l.ctrl_mode != dcm_ctrl_mode_position) {
		return;
	}

	// Limit position commands to stay inside the virtual limit
	if (y_axis_l.position_cmd_enc_ticks > (Y_AXIS_LIMIT_2_ENC_TICKS - Y_AXIS_BOUNDARY_ENC_TICKS)) {
		y_axis_l.position_cmd_enc_ticks = Y_AXIS_LIMIT_2_ENC_TICKS - Y_AXIS_BOUNDARY_ENC_TICKS;
	}
	if (y_axis_l.position_cmd_enc_ticks < Y_AXIS_BOUNDARY_ENC_TICKS) {
		y_axis_l.position_cmd_enc_ticks = Y_AXIS_BOUNDARY_ENC_TICKS;
	}

	// Read home position switch
	y_axis_l.home_switch = Y_AXIS_L_HOME;
	if (y_axis_l.home_switch == dcm_home_switch_pressed) {
		DisableInterrupts;
		y_axis_l.position_enc_ticks = Y_AXIS_HOME_ENC_TICKS;
		EnableInterrupts;
	}

	// Calculate position error
	DisableInterrupts;	// Start critical region
	y_axis_l.position_error_ticks = y_axis_l.position_cmd_enc_ticks - y_axis_l.position_enc_ticks;
	EnableInterrupts;	// End critical region

	// Stop if at desired position
	if (y_axis_l.position_error_ticks == 0) {
		error_i = 0;
		y_axis_l_set_dcm_drive(dcm_h_bridge_dir_brake, Y_AXIS_SPEED_MIN);
		return;
	}

	error_i -= (y_axis_l.position_error_ticks / Y_AXIS_L_GAIN_I);
	if (error_i > Y_AXIS_L_INTEGRAL_LIMIT) {
		error_i = Y_AXIS_L_INTEGRAL_LIMIT;
	}
	if (error_i < -Y_AXIS_L_INTEGRAL_LIMIT) {
		error_i = -Y_AXIS_L_INTEGRAL_LIMIT;
	}
	error_p = y_axis_l.position_error_ticks / Y_AXIS_L_GAIN_P;
	error_calc = error_i + error_p;

	// Drive motor to desired position
	if (error_calc > 0) {
		y_axis_l.set_speed = MIN(Y_AXIS_SPEED_MAX, LOW(error_calc));
		y_axis_l_set_dcm_drive(dcm_h_bridge_dir_forward, y_axis_l.set_speed);
		return;
	} else {
		y_axis_l.set_speed = MIN(Y_AXIS_SPEED_MAX, LOW(abs(error_calc)));
		y_axis_l_set_dcm_drive(dcm_h_bridge_dir_reverse, y_axis_l.set_speed);
		return;
	}
}

//;**************************************************************
//;*                 y_axis_r_position_ctrl(void)
//;**************************************************************
void y_axis_r_position_ctrl(void)
{
	static signed int error_i = 0;
	signed int error_p, error_calc;

	// Right motor is slave to left motor
	y_axis_r.position_cmd_enc_ticks = y_axis_l.position_cmd_enc_ticks;

	// Sanity check control mode
	if (y_axis_r.ctrl_mode != dcm_ctrl_mode_position) {
		return;
	}

	// Limit position commands to stay inside the virtual limit
	if (y_axis_r.position_cmd_enc_ticks > (Y_AXIS_LIMIT_2_ENC_TICKS - Y_AXIS_BOUNDARY_ENC_TICKS)) {
		y_axis_r.position_cmd_enc_ticks = Y_AXIS_LIMIT_2_ENC_TICKS - Y_AXIS_BOUNDARY_ENC_TICKS;
	}
	if (y_axis_r.position_cmd_enc_ticks < Y_AXIS_BOUNDARY_ENC_TICKS) {
		y_axis_r.position_cmd_enc_ticks = Y_AXIS_BOUNDARY_ENC_TICKS;
	}

	// Read home position switch
	y_axis_r.home_switch = Y_AXIS_R_HOME;
	if (y_axis_r.home_switch == dcm_home_switch_pressed) {
		DisableInterrupts;
		y_axis_r.position_enc_ticks = Y_AXIS_HOME_ENC_TICKS;
		EnableInterrupts;
	}

	// Calculate position error
	DisableInterrupts;	// Start critical region
	//y_axis_r.position_error_ticks = y_axis_r.position_cmd_enc_ticks - y_axis_r.position_enc_ticks;
	y_axis_r.position_error_ticks = y_axis_l.position_enc_ticks - y_axis_r.position_enc_ticks;
	EnableInterrupts;	// End critical region

	// Stop if at desired position
	if (y_axis_r.position_error_ticks == 0) {
		error_i = 0;
		y_axis_r_set_dcm_drive(dcm_h_bridge_dir_brake, Y_AXIS_SPEED_MIN);
		return;
	}

	error_i -= (y_axis_r.position_error_ticks * Y_AXIS_R_GAIN_I);
	if (error_i > Y_AXIS_R_INTEGRAL_LIMIT) {
		error_i = Y_AXIS_R_INTEGRAL_LIMIT;
	}
	if (error_i < -Y_AXIS_R_INTEGRAL_LIMIT) {
		error_i = -Y_AXIS_R_INTEGRAL_LIMIT;
	}
	error_p = y_axis_r.position_error_ticks * Y_AXIS_R_GAIN_P;
	error_calc = error_i + error_p;

	// Drive motor to desired position
	if (error_calc > 0) {
		y_axis_r.set_speed = MIN(Y_AXIS_SPEED_MAX, LOW(error_calc));
		y_axis_r_set_dcm_drive(dcm_h_bridge_dir_forward, y_axis_r.set_speed);
		return;
	} else {
		y_axis_r.set_speed = MIN(Y_AXIS_SPEED_MAX, LOW(abs(error_calc)));
		y_axis_r_set_dcm_drive(dcm_h_bridge_dir_reverse, y_axis_r.set_speed);
		return;
	}
}

/*
void y_axis_position_ctrl(void)
{	
	unsigned int error_l_p, error_r_p, speed_calc_l, speed_calc_r;

	// Sanity check control mode
	if (y_axis_l.ctrl_mode != dcm_ctrl_mode_position) {
    	return;
	}

	// Limit position commands to sane values
	if (y_axis_l.position_cmd_enc_ticks > (Y_AXIS_LIMIT_2_ENC_TICKS - Y_AXIS_BOUNDARY_ENC_TICKS)) {
		y_axis_l.position_cmd_enc_ticks = Y_AXIS_LIMIT_2_ENC_TICKS - Y_AXIS_BOUNDARY_ENC_TICKS;
	}
	if (y_axis_l.position_cmd_enc_ticks < Y_AXIS_BOUNDARY_ENC_TICKS) {
		y_axis_l.position_cmd_enc_ticks = Y_AXIS_BOUNDARY_ENC_TICKS;
	}

	// Read home position switches
	y_axis_l.home_switch = Y_AXIS_L_HOME;
	y_axis_r.home_switch = Y_AXIS_R_HOME;
	if (y_axis_l.home_switch == dcm_home_switch_pressed) {
		DisableInterrupts;	// Start critical region
		y_axis_l.position_enc_ticks = Y_AXIS_HOME_ENC_TICKS;
		EnableInterrupts;	// End critical region
	}
	if (y_axis_r.home_switch == dcm_home_switch_pressed) {
		DisableInterrupts;	// Start critical region
		y_axis_r.position_enc_ticks = Y_AXIS_HOME_ENC_TICKS;
		EnableInterrupts;	// End critical region
	}

	// Always force right (slave) position command to match left (master) position command
	y_axis_r.position_cmd_enc_ticks = y_axis_l.position_cmd_enc_ticks;

	// Throw error and stop if left and right motor positions diverge
	DisableInterrupts;	// Start critical region
	y_axis_lr_position_error_enc_ticks = y_axis_l.position_enc_ticks - y_axis_r.position_enc_ticks;
	EnableInterrupts;	// End critical region
	if ((y_axis_lr_position_error_enc_ticks >= Y_AXIS_LR_POS_ERROR_LIMIT_ENC_TICKS) ||
		(y_axis_lr_position_error_enc_ticks <= -Y_AXIS_LR_POS_ERROR_LIMIT_ENC_TICKS)) {
		if (y_axis_error == y_axis_error_none) {
			y_axis_error = y_axis_error_lr_pos_mism;
		}
		y_axis_l_set_dcm_drive(dcm_h_bridge_dir_brake, Y_AXIS_SPEED_MIN);
		y_axis_r_set_dcm_drive(dcm_h_bridge_dir_brake, Y_AXIS_SPEED_MIN);
		return;
	}

	// Calculate error for left motor (master)
	DisableInterrupts;	// Start critical region
	y_axis_l.position_error_ticks = y_axis_l.position_cmd_enc_ticks - y_axis_l.position_enc_ticks;
	EnableInterrupts;	// End critical region
	error_l_p = abs(y_axis_l.position_error_ticks) * Y_AXIS_L_POS_GAIN_P;
	
	// Drive left motor to desired position
	if (y_axis_l.position_error_ticks > 0) {
		if (y_axis_l.h_bridge_direction == dcm_h_bridge_dir_reverse) {
			// Stop before reversing direction
			y_axis_l_set_dcm_drive(dcm_h_bridge_dir_brake, Y_AXIS_SPEED_MIN);
		} else {
			if (error_l_p > Y_AXIS_SPEED_MAX) {
				speed_calc_l = Y_AXIS_SPEED_MAX;
			} else {
				speed_calc_l = LOW(error_l_p);
			}
			y_axis_l_set_dcm_drive(dcm_h_bridge_dir_forward, speed_calc_l);
		}
	} else if (y_axis_l.position_error_ticks < 0) {
		if (y_axis_l.h_bridge_direction == dcm_h_bridge_dir_forward) {
			// Stop before reversing direction
			y_axis_l_set_dcm_drive(dcm_h_bridge_dir_brake, Y_AXIS_SPEED_MIN);
		} else {
			if (error_l_p > Y_AXIS_SPEED_MAX) {
				speed_calc_l = Y_AXIS_SPEED_MAX;
			} else {
				speed_calc_l = LOW(error_l_p);
			}
			y_axis_l_set_dcm_drive(dcm_h_bridge_dir_reverse, speed_calc_l);
		}
	} else {
		// Stop at desired position
		y_axis_l_set_dcm_drive(dcm_h_bridge_dir_brake, Y_AXIS_SPEED_MIN);
	}

	// Calculate position error for right motor (slave)
	DisableInterrupts;	// Start critical region
	y_axis_r.position_error_ticks = y_axis_r.position_cmd_enc_ticks - y_axis_r.position_enc_ticks;
	EnableInterrupts;	// End critical region
	error_r_p = abs(y_axis_r.position_error_ticks) * Y_AXIS_R_POS_GAIN_P;
	speed_calc_r = MIN(Y_AXIS_SPEED_MAX, error_r_p);

	// Drive right motor to desired position
	if (y_axis_r.position_error_ticks > 0) {
		if (y_axis_r.h_bridge_direction == dcm_h_bridge_dir_reverse) {
			// Stop before reversing direction
			y_axis_r_set_dcm_drive(dcm_h_bridge_dir_brake, Y_AXIS_SPEED_MIN);
		} else {
			if (y_axis_r.position_error_ticks > Y_AXIS_BOUNDARY_ENC_TICKS) {
				speed_calc_r += (y_axis_lr_position_error_enc_ticks * Y_AXIS_LR_POS_GAIN_P);	
			}
			speed_calc_r = MIN(Y_AXIS_SPEED_MAX, speed_calc_r);
			speed_calc_r = LOW(speed_calc_r);
			y_axis_r_set_dcm_drive(dcm_h_bridge_dir_forward, speed_calc_r);
		}
	} else if (y_axis_r.position_error_ticks < 0) {
		if (y_axis_r.h_bridge_direction == dcm_h_bridge_dir_forward) {
			// Stop before reversing direction
			y_axis_r_set_dcm_drive(dcm_h_bridge_dir_brake, Y_AXIS_SPEED_MIN);
		} else {
			if (y_axis_r.position_error_ticks < Y_AXIS_BOUNDARY_ENC_TICKS) {
				speed_calc_r -= (y_axis_lr_position_error_enc_ticks * Y_AXIS_LR_POS_GAIN_P);
			}
			speed_calc_r = MIN(Y_AXIS_SPEED_MAX, speed_calc_r);
			speed_calc_r = LOW(speed_calc_r);
			y_axis_r_set_dcm_drive(dcm_h_bridge_dir_reverse, speed_calc_r);
		}
	} else {
		// Stop at desired position
		y_axis_r_set_dcm_drive(dcm_h_bridge_dir_brake, Y_AXIS_SPEED_MIN);
	}
}*/

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
		if (y_axis_l.position_enc_ticks < Y_AXIS_BOUNDARY_ENC_TICKS) {
			pos_y_calc = 0;
		} else {
			pos_y_calc = (y_axis_l.position_enc_ticks - Y_AXIS_LIMIT_1_ENC_TICKS) * 10;
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

//;**************************************************************
//;*                 y_axis_dcm_overload_check(void)
//;*	Check that DC motor is not blocked/overloaded
//;**************************************************************
void y_axis_dcm_overload_check(void)
{
	static unsigned int strike_counter = 0;
	static dcm_h_bridge_dir_e previous_direction = dcm_h_bridge_dir_brake;

	// Reset strike counter if motor changes direction
	if (previous_direction != y_axis_l.h_bridge_direction) {
		previous_direction = y_axis_l.h_bridge_direction;
		strike_counter = 0;
		return;
	}

	// Only checking for overload condition at max speed.
	// ToDo: Do some sort of interpolation to determine expected period from PWM duty
	if (y_axis_l.pwm_duty != Y_AXIS_SPEED_MAX) {
		return;
	}

	// Check for overload condition
	if (y_axis_l.speed_mm_per_s < Y_AXIS_DCM_OVERLOAD_LIMIT_MM_PER_S) {
		//strike_counter ++;
	//} else if (y_axis_r.period_tcnt_ticks > Y_AXIS_DCM_OVERLOAD_LIMIT_TCNT_TICKS) {
	//	strike_counter ++;
	} else {
		strike_counter = 0;
	}

	// Throw error and stop motor if strike limit is reached
	if (strike_counter >= Y_AXIS_DCM_OVERLOAD_STRIKE_COUNT) {
		y_axis_error = y_axis_error_dcm_overload;
		y_axis_l.ctrl_mode = dcm_ctrl_mode_disable;
		y_axis_l_set_dcm_drive(dcm_h_bridge_dir_brake, Y_AXIS_SPEED_MIN);
		y_axis_r_set_dcm_drive(dcm_h_bridge_dir_brake, Y_AXIS_SPEED_MIN);
	}
}

//;**************************************************************
//;*                 y_axis_calculate_speed(void)
//;*	Calculate speed in mm per second
//;**************************************************************
void y_axis_calculate_speed(void)
{
	static unsigned int position_enc_ticks_old = 0; 
	static unsigned char count = 1;
	unsigned long speed_y_calc;

	// Only calculate speed every 10 ms to get better accuracy
	if ((count % 10) == 0) {
		y_axis_l.speed_enc_ticks_per_s = 100 * abs(y_axis_l.position_enc_ticks - position_enc_ticks_old);
		speed_y_calc = y_axis_l.speed_enc_ticks_per_s * Y_AXIS_MM_PER_REV;
		y_axis_l.speed_mm_per_s = 0xFFFF & ((speed_y_calc / Y_AXIS_ENC_TICKS_PER_REV));
		position_enc_ticks_old = y_axis_l.position_enc_ticks;
	}

	// Limit counter to max value of 10
	if (count == 10) {
		count = 1;
	} else {
		count ++;
	}
}

//;**************************************************************
//;*                 y_axis_l_set_dcm_drive(void)
//;*	Helper function to set left DC motor direction and speed
//;**************************************************************
static void y_axis_l_set_dcm_drive(dcm_h_bridge_dir_e direction, unsigned int speed)
{
	switch (direction)
	{
		case dcm_h_bridge_dir_brake:
			y_axis_l.set_speed = Y_AXIS_SPEED_MIN;
			y_axis_l.pwm_duty = Y_AXIS_PWM_DUTY_OFF;
			Y_AXIS_L_SET_PWM_DUTY(Y_AXIS_PWM_DUTY_OFF);
			y_axis_l.h_bridge_direction = dcm_h_bridge_dir_brake;
			break;
		case dcm_h_bridge_dir_forward:
			y_axis_l.set_speed = LOW(speed);
			y_axis_l.pwm_duty = Y_AXIS_SPEED_TO_PWM_FWD(speed);
			Y_AXIS_L_SET_PWM_DUTY(y_axis_l.pwm_duty);
			y_axis_l.h_bridge_direction = dcm_h_bridge_dir_forward;
			break;
		case dcm_h_bridge_dir_reverse:
			y_axis_l.set_speed = LOW(speed);
			y_axis_l.pwm_duty = Y_AXIS_SPEED_TO_PWM_REV(speed);
			Y_AXIS_L_SET_PWM_DUTY(y_axis_l.pwm_duty);
			y_axis_l.h_bridge_direction = dcm_h_bridge_dir_reverse;
			break;
		default:
			y_axis_l.set_speed = Y_AXIS_SPEED_MIN;
			y_axis_l.pwm_duty = Y_AXIS_PWM_DUTY_OFF;
			Y_AXIS_L_SET_PWM_DUTY(Y_AXIS_PWM_DUTY_OFF);
			y_axis_l.h_bridge_direction = dcm_h_bridge_dir_brake;
	}
}

//;**************************************************************
//;*                 y_axis_r_set_dcm_drive(void)
//;*	Helper function to set right DC motor direction and speed
//;**************************************************************
static void y_axis_r_set_dcm_drive(dcm_h_bridge_dir_e direction, unsigned int speed)
{
	switch (direction)
	{
		case dcm_h_bridge_dir_brake:
			y_axis_r.set_speed = Y_AXIS_SPEED_MIN;
			y_axis_r.pwm_duty = Y_AXIS_PWM_DUTY_OFF;
			Y_AXIS_R_SET_PWM_DUTY(Y_AXIS_PWM_DUTY_OFF);
			y_axis_r.h_bridge_direction = dcm_h_bridge_dir_brake;
			break;
		case dcm_h_bridge_dir_forward:
			y_axis_r.set_speed = LOW(speed);
			y_axis_r.pwm_duty = Y_AXIS_SPEED_TO_PWM_FWD(speed);
			Y_AXIS_R_SET_PWM_DUTY(y_axis_r.pwm_duty);
			y_axis_r.h_bridge_direction = dcm_h_bridge_dir_forward;
			break;
		case dcm_h_bridge_dir_reverse:
			y_axis_r.set_speed = LOW(speed);
			y_axis_r.pwm_duty = Y_AXIS_SPEED_TO_PWM_REV(speed);
			Y_AXIS_R_SET_PWM_DUTY(y_axis_r.pwm_duty);
			y_axis_r.h_bridge_direction = dcm_h_bridge_dir_reverse;
			break;
		default:
			y_axis_r.set_speed = Y_AXIS_SPEED_MIN;
			y_axis_r.pwm_duty = Y_AXIS_PWM_DUTY_OFF;
			Y_AXIS_R_SET_PWM_DUTY(Y_AXIS_PWM_DUTY_OFF);
			y_axis_r.h_bridge_direction = dcm_h_bridge_dir_brake;
	}
}

//;**************************************************************
//;*                 y_axis_l_encoder_a()
//;*  Handles IC function for Y-Axis Left Motor Encoder A Phase
//;**************************************************************
interrupt 10 void y_axis_l_encoder_b(void)
{
	// Track direction
	if (Y_AXIS_ENC_PORT & Y_AXIS_L_ENC_B) {
		// Phase B leads Phase A
		y_axis_l.quadrature_direction = dcm_quad_dir_reverse;
		if (y_axis_l.position_enc_ticks > 0) {
			y_axis_l.position_enc_ticks --;
		}
	} else {
		// Phase A leads Phase B
		y_axis_l.quadrature_direction = dcm_quad_dir_forward;
		if (y_axis_l.position_enc_ticks < MAX_UINT) {
			y_axis_l.position_enc_ticks ++;
		}
	}
	
	(void) Y_AXIS_L_ENC_A_TIMER;
}

//;**************************************************************
//;*                 y_axis_r_encoder_a()
//;*  Handles IC function for Y-Axis Right Motor Encoder A Phase
//;**************************************************************
interrupt 12 void y_axis_r_encoder_b(void)
{
	// Track direction and position
	if (Y_AXIS_ENC_PORT & Y_AXIS_R_ENC_B) {
		// Phase B leads Phase A
		y_axis_r.quadrature_direction = dcm_quad_dir_forward;
		if (y_axis_r.position_enc_ticks < MAX_UINT) {
			y_axis_r.position_enc_ticks ++;
		}
	} else {
		// Phase A leads Phase B
		y_axis_r.quadrature_direction = dcm_quad_dir_reverse;
		if (y_axis_r.position_enc_ticks > 0) {
			y_axis_r.position_enc_ticks --;
		}
	}

	(void) Y_AXIS_R_ENC_A_TIMER;
}

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
	y_axis_l.position_cmd_enc_ticks = (0xFFFF) & (pos_cmd_calculation + Y_AXIS_LIMIT_1_ENC_TICKS);

	// Clear Rx flag
	SET_BITS(CANRFLG, CAN_RX_INTERRUPT);
}
*/
