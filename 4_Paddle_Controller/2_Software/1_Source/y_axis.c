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
#include "dcm.h"
#include "can.h"

static dcm_t y_axis;
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
	// Set motor control parameters
	y_axis.axis_length_enc_ticks = Y_AXIS_LENGTH_ENC_TICKS;
	y_axis.axis_boundary_enc_ticks = Y_AXIS_BOUNDARY_ENC_TICKS;
	y_axis.home_position_enc_ticks = Y_AXIS_HOME_ENC_TICKS;
	y_axis.max_speed = Y_AXIS_SPEED_MAX;
	y_axis.gain_p = Y_AXIS_GAIN_P;
	y_axis.gain_p_factor = Y_AXIS_GAIN_P_FACTOR;
	y_axis.gain_i = Y_AXIS_GAIN_I;
	y_axis.integral_limit = Y_AXIS_INTEGRAL_LIMIT;
	y_axis.slew_rate = Y_AXIS_SLEW_RATE;

	// Configure PWM channel for left motor
	SET_BITS(PWMCLK, PWMCLK_PCLK4_MASK);	// Use clock SA
	SET_BITS(PWMPOL, PWMPOL_PPOL4_MASK);	// Active high
	SET_BITS(PWMCAE, PWMCAE_CAE4_MASK);		// Centre aligned
	Y_AXIS_L_SET_PWM_PERIOD(DCM_PWM_PERIOD);	// Set for 20kHz switching frequency
	Y_AXIS_L_SET_PWM_DUTY(DCM_PWM_DUTY_OFF);	// Start with motor off
	Y_AXIS_L_CLEAR_PWM_COUNT;
	Y_AXIS_L_ENABLE_PWM;

	// Configure PWM channel for right motor
	SET_BITS(PWMCLK, PWMCLK_PCLK5_MASK);	// Use clock SA
	SET_BITS(PWMPOL, PWMPOL_PPOL5_MASK);	// Active high
	SET_BITS(PWMCAE, PWMCAE_CAE5_MASK);		// Centre aligned
	Y_AXIS_R_SET_PWM_PERIOD(DCM_PWM_PERIOD);	// Set for 20kHz switching frequency
	Y_AXIS_R_SET_PWM_DUTY(DCM_PWM_DUTY_OFF);	// Start with motor off
	Y_AXIS_R_CLEAR_PWM_COUNT;
	Y_AXIS_R_ENABLE_PWM;

	// Configure encoder port pins and input-capture interrupt.
	CLEAR_BITS(Y_AXIS_ENC_DDR, Y_AXIS_L_ENC_B);	// B-Phase input is read during ISR for A-Phase
	CLEAR_BITS(TIOS, TIOS_IOS2_MASK);			// Set A-Phase timer channel to input capture mode
	SET_BITS(TCTL4, Y_AXIS_L_TCTL4_INIT);		// Capture on rising edge of TC2
	SET_BITS(TIE, TIOS_IOS2_MASK);				// Enable interrupts for A-Phase timer channels
	TFLG1 = (TFLG1_C2F_MASK);					// Clear the flag in case anything is pending

	// Configure home switch port pins.
	CLEAR_BITS(Y_AXIS_HOME_DDR, Y_AXIS_L_HOME_PIN);
	CLEAR_BITS(Y_AXIS_HOME_DDR, Y_AXIS_R_HOME_PIN);

	// Default to position control
	y_axis.ctrl_mode = dcm_ctrl_mode_enable;
}

//;**************************************************************
//;*                 Y_axis_home(void)
//;*	Move paddle to home position in the Y-Axis
//;**************************************************************
void y_axis_home(void)
{
	// Save current control mode to be restored before returning
	dcm_ctrl_mode_e ctrl_mode = y_axis.ctrl_mode;

	// Drive motors backwards
	Y_AXIS_L_SET_PWM_DUTY(45);
	Y_AXIS_R_SET_PWM_DUTY(45);

	// Wait for limit switches to be hit
	// To Do: Should have some timeout here to handle broken switch
	// For now broken switch handled by dcm overload check
	while (Y_AXIS_L_HOME == dcm_home_switch_unpressed) {};
	Y_AXIS_L_SET_PWM_DUTY(DCM_PWM_DUTY_OFF);
	Y_AXIS_R_SET_PWM_DUTY(DCM_PWM_DUTY_OFF);

	// Set target to boundary
	y_axis.position_cmd_enc_ticks = y_axis.axis_boundary_enc_ticks;

	// Return control to position/velocity controllers
	y_axis.ctrl_mode = ctrl_mode;
	return;
}

//;**************************************************************
//;*                 y_axis_position_ctrl(void)
//;**************************************************************
void y_axis_position_ctrl(void)
{
	static unsigned char count = 0;

	// Speed calculation at 100 Hz
	if ((count % 10) == 0) {
		dcm_speed_calc(&y_axis);	
		dcm_overload_check(&y_axis);
		count = 0;
	} else {
		count ++;
	}

	// Perform position control at 1 kHz
	y_axis.home_switch = Y_AXIS_L_HOME;
	dcm_position_ctrl(&y_axis);
	y_axis_set_dcm_drive();
}

//;**************************************************************
//;*                 y_axis_set_dcm_drive(void)
//;*	Helper function to set y-axis DC motors direction and speed
//;**************************************************************
static void y_axis_set_dcm_drive(void)
{
	// Has effect of torque slew
	static unsigned int speed_old = 0;
	unsigned int set_speed = y_axis.calc_speed;
	if (set_speed > speed_old) {
		if ((set_speed - speed_old) > y_axis.slew_rate) {
			set_speed = speed_old + y_axis.slew_rate;
		}
		speed_old = set_speed;	
	}

	switch (y_axis.h_bridge_direction)
	{
		case dcm_h_bridge_dir_brake:
			y_axis.set_speed = 0;
			y_axis.pwm_duty = DCM_PWM_DUTY_OFF;
			y_axis.h_bridge_direction = dcm_h_bridge_dir_brake;
			Y_AXIS_L_SET_PWM_DUTY(DCM_PWM_DUTY_OFF);
			Y_AXIS_R_SET_PWM_DUTY(DCM_PWM_DUTY_OFF);
			break;
		case dcm_h_bridge_dir_forward:
			y_axis.set_speed = LOW(set_speed);
			y_axis.pwm_duty = DCM_SPEED_TO_PWM_FWD(set_speed);
			y_axis.h_bridge_direction = dcm_h_bridge_dir_forward;
			Y_AXIS_L_SET_PWM_DUTY(y_axis.pwm_duty);
			Y_AXIS_R_SET_PWM_DUTY(y_axis.pwm_duty);
			break;
		case dcm_h_bridge_dir_reverse:
			y_axis.set_speed = LOW(set_speed);
			y_axis.pwm_duty = DCM_SPEED_TO_PWM_REV(set_speed);
			y_axis.h_bridge_direction = dcm_h_bridge_dir_reverse;
			Y_AXIS_L_SET_PWM_DUTY(y_axis.pwm_duty);
			Y_AXIS_R_SET_PWM_DUTY(y_axis.pwm_duty);
			break;
		default:
			y_axis.set_speed = 0;
			y_axis.pwm_duty = DCM_PWM_DUTY_OFF;
			y_axis.h_bridge_direction = dcm_h_bridge_dir_brake;
			Y_AXIS_L_SET_PWM_DUTY(DCM_PWM_DUTY_OFF);
			Y_AXIS_R_SET_PWM_DUTY(DCM_PWM_DUTY_OFF);
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
		y_axis.quadrature_direction = dcm_quad_dir_reverse;
		if (y_axis.position_enc_ticks > 0) {
			y_axis.position_enc_ticks --;
		}
	} else {
		// Phase A leads Phase B
		y_axis.quadrature_direction = dcm_quad_dir_forward;
		if (y_axis.position_enc_ticks < MAX_UINT) {
			y_axis.position_enc_ticks ++;
		}
	}
	
	(void) Y_AXIS_L_ENC_A_TIMER;
}

//;**************************************************************
//;*                 y_axis_get_data(void)
//;*	Returns a pointer to the y_axis data structure
//;**************************************************************
dcm_t *y_axis_get_data(void) {
	return &y_axis;
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
