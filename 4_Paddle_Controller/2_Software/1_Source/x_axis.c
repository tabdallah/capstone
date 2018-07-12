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
#include "dcm.h"
#include "can.h"

static dcm_t x_axis;
static can_msg_raw_t can_msg_raw;
static can_msg_mc_cmd_pc_t can_msg_mc_cmd_pc;
static can_msg_pc_status_t can_msg_pc_status;

//;**************************************************************
//;*                 x_axis_configure(void)
//;*	Configure H-Bridge direction control port pins.
//;*	Configure PWM channel for motor control.
//;*	Configure encoder port pins and input-capture interrupt.
//;**************************************************************
void x_axis_configure(void)
{
	// Set motor control parameters
	x_axis.axis_length_enc_ticks = X_AXIS_LENGTH_ENC_TICKS;
	x_axis.axis_boundary_enc_ticks = X_AXIS_BOUNDARY_ENC_TICKS;
	x_axis.home_position_enc_ticks = X_AXIS_HOME_ENC_TICKS;
	x_axis.max_speed = X_AXIS_SPEED_MAX;
	x_axis.gain_p = X_AXIS_GAIN_P;
	x_axis.gain_p_factor = X_AXIS_GAIN_P_FACTOR;
	x_axis.gain_i = X_AXIS_GAIN_I;
	x_axis.integral_limit = X_AXIS_INTEGRAL_LIMIT;
	x_axis.slew_rate = X_AXIS_SLEW_RATE;

	// Configure PWM channel
	SET_BITS(PWMCLK, PWMCLK_PCLK0_MASK);	// Use clock SA
	SET_BITS(PWMPOL, PWMPOL_PPOL0_MASK);	// Active high
	SET_BITS(PWMCAE, PWMCAE_CAE0_MASK);		// Centre aligned
	X_AXIS_SET_PWM_PERIOD(DCM_PWM_PERIOD);	// Set for 20kHz switching frequency
	X_AXIS_SET_PWM_DUTY(DCM_PWM_DUTY_OFF);	// Start with motor off
	X_AXIS_CLEAR_PWM_COUNT;
	X_AXIS_ENABLE_PWM;

	// Configure encoder port pins and input-capture interrupt.
	CLEAR_BITS(X_AXIS_ENC_DDR, X_AXIS_ENC_B);	// B-Phase input is read during ISR for A-Phase
	CLEAR_BITS(TIOS, TIOS_IOS0_MASK);	// Set A-Phase timer channel to input capture mode
	SET_BITS(TCTL4, X_AXIS_TCTL4_INIT);			// Capture on rising edge of TC0
	SET_BITS(TIE, TIOS_IOS0_MASK);		// Enable interrupts for A-Phase timer channel
	TFLG1 = (TFLG1_C0F_MASK);			// Clear the flag in case anything is pending

	// Configure home switch port pins.
	CLEAR_BITS(X_AXIS_HOME_DDR, X_AXIS_HOME_PIN);

	// Default to position control
	x_axis.ctrl_mode = dcm_ctrl_mode_enable;
}

//;**************************************************************
//;*                 x_axis_home(void)
//;*	Move paddle to home position in the X-Axis
//;**************************************************************
void x_axis_home(void)
{
	// Save current control mode to be restored before returning
	dcm_ctrl_mode_e ctrl_mode = x_axis.ctrl_mode;

	// Drive motor backwards
	X_AXIS_SET_PWM_DUTY(45);

	// Wait for limit switch to be hit
	// To Do: Should have some timeout here to handle broken switch
	// For now broken switch handled by dcm overload check
	while (X_AXIS_HOME == dcm_home_switch_unpressed) {};
	X_AXIS_SET_PWM_DUTY(DCM_PWM_DUTY_OFF);

	// Set target to center of table
	x_axis.position_cmd_enc_ticks = x_axis.axis_length_enc_ticks / 2;

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
	static unsigned char count = 0;

	// Speed calculation at 100 Hz
	if ((count % 10) == 0) {
		dcm_speed_calc(&x_axis);	
		dcm_overload_check(&x_axis);
		count = 0;
	} else {
		count ++;
	}

	// Perform position control at 1 kHz
	x_axis.home_switch = X_AXIS_HOME;
	dcm_position_ctrl(&x_axis);
	x_axis_set_dcm_drive();
}

//;**************************************************************
//;*                 x_axis_set_dcm_drive(void)
//;*	Helper function to set DC motor direction and speed
//;**************************************************************
void x_axis_set_dcm_drive(void)
{
	// Has effect of torque slew
	static unsigned int speed_old = 0;
	unsigned int set_speed = x_axis.calc_speed;
	if (set_speed > speed_old) {
		if ((set_speed - speed_old) > x_axis.slew_rate) {
			set_speed = speed_old + x_axis.slew_rate;
		}
		speed_old = set_speed;	
	}

	switch (x_axis.h_bridge_direction)
	{
		case dcm_h_bridge_dir_brake:
			x_axis.set_speed = 0;
			x_axis.pwm_duty = DCM_PWM_DUTY_OFF;
			x_axis.h_bridge_direction = dcm_h_bridge_dir_brake;
			X_AXIS_SET_PWM_DUTY(DCM_PWM_DUTY_OFF);
			break;
		case dcm_h_bridge_dir_forward:
			x_axis.set_speed = LOW(set_speed);
			x_axis.pwm_duty = DCM_SPEED_TO_PWM_FWD(set_speed);
			x_axis.h_bridge_direction = dcm_h_bridge_dir_forward;
			X_AXIS_SET_PWM_DUTY(x_axis.pwm_duty);
			break;
		case dcm_h_bridge_dir_reverse:
			x_axis.set_speed = LOW(set_speed);
			x_axis.pwm_duty = DCM_SPEED_TO_PWM_REV(set_speed);
			x_axis.h_bridge_direction = dcm_h_bridge_dir_reverse;
			X_AXIS_SET_PWM_DUTY(x_axis.pwm_duty);
			break;
		default:
			x_axis.set_speed = 0;
			x_axis.pwm_duty = DCM_PWM_DUTY_OFF;
			x_axis.h_bridge_direction = dcm_h_bridge_dir_brake;
			X_AXIS_SET_PWM_DUTY(DCM_PWM_DUTY_OFF);
	}
}

//;**************************************************************
//;*                 x_axis_get_data(void)
//;*	Returns a pointer to the x_axis data structure
//;**************************************************************
dcm_t *x_axis_get_data(void) {
	return &x_axis;
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
		x_axis.quadrature_direction = dcm_quad_dir_forward;
		if (x_axis.position_enc_ticks < MAX_UINT) {
			x_axis.position_enc_ticks ++;
		}
	} else {
		// Phase A leads Phase B
		x_axis.quadrature_direction = dcm_quad_dir_reverse;
		if (x_axis.position_enc_ticks > 0) {
			x_axis.position_enc_ticks --;
		}
	}

	(void) X_AXIS_ENC_A_TIMER;
}

/*
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
	if (can_msg_mc_cmd_pc.pos_cmd_x_mm > (X_AXIS_HOME_MM + PUCK_RADIUS_MM)) {
		pos_cmd_calculation = can_msg_mc_cmd_pc.pos_cmd_x_mm - X_AXIS_HOME_MM - PUCK_RADIUS_MM;
	} else {
		pos_cmd_calculation = 0;
	}
	pos_cmd_calculation = pos_cmd_calculation * X_AXIS_ENC_TICKS_PER_REV;
	pos_cmd_calculation = pos_cmd_calculation / X_AXIS_MM_PER_REV;
	x_axis.position_cmd_enc_ticks = 0xFFFF & pos_cmd_calculation;

	// Clear Rx flag
	SET_BITS(CANRFLG, CAN_RX_INTERRUPT);
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