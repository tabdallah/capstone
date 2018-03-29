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
#include "dcm.h"
#include "x_axis.h"
#include "can.h"

static dcm_t x_axis = {X_AXIS_LEFT_POS_LIMIT_TICKS, X_AXIS_LEFT_POS_LIMIT_TICKS, 0,0,0,0,0,0,0,0,0,0,0,dcm_limit_switch_pressed,dcm_limit_switch_pressed, dcm_ctrl_mode_disable};
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
	x_axis.pwm_duty = X_AXIS_PWM_DUTY_MAX;
	X_AXIS_SET_PWM_DUTY(x_axis.pwm_duty);
	x_axis.h_bridge_direction = dcm_h_bridge_dir_reverse;
	X_AXIS_H_BRIDGE_REVERSE;

	// Wait for limit switch to be hit
	// To Do: Should have some timeout here to handle broken switch
	while (X_AXIS_LIMIT_1 == dcm_limit_switch_unpressed) {};
	x_axis.position_enc_ticks = X_AXIS_LEFT_POS_LIMIT_TICKS;

	// Stop motor
	X_AXIS_SET_PWM_DUTY(X_AXIS_PWM_DUTY_MIN);
	x_axis.pwm_duty = X_AXIS_PWM_DUTY_MIN;
	x_axis.h_bridge_direction = dcm_h_bridge_dir_brake;
	X_AXIS_H_BRIDGE_BRAKE;

	// Move off the hard stop
	x_axis.pwm_duty = X_AXIS_PWM_DUTY_MAX;
	X_AXIS_SET_PWM_DUTY(x_axis.pwm_duty);
	x_axis.h_bridge_direction = dcm_h_bridge_dir_forward;
	X_AXIS_H_BRIDGE_FORWARD;

	while (x_axis.position_enc_ticks < 200) {};
	x_axis.position_enc_ticks = X_AXIS_LEFT_POS_LIMIT_TICKS;	

	// Stop motor
	X_AXIS_SET_PWM_DUTY(X_AXIS_PWM_DUTY_MIN);
	x_axis.pwm_duty = X_AXIS_PWM_DUTY_MIN;
	x_axis.h_bridge_direction = dcm_h_bridge_dir_brake;
	X_AXIS_H_BRIDGE_BRAKE;

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

	// Limit position commands to sane values
	if (x_axis.position_cmd_enc_ticks > X_AXIS_RIGHT_POS_LIMIT_TICKS) {
		x_axis.position_cmd_enc_ticks = X_AXIS_RIGHT_POS_LIMIT_TICKS;
	}
	if (x_axis.position_cmd_enc_ticks < X_AXIS_LEFT_POS_LIMIT_TICKS) {
		x_axis.position_cmd_enc_ticks = X_AXIS_LEFT_POS_LIMIT_TICKS;
	}

	// Read limit switch states
	x_axis.limit_switch_1 = X_AXIS_LIMIT_1;
	x_axis.limit_switch_2 = X_AXIS_LIMIT_2;
	if (x_axis.limit_switch_1 == dcm_limit_switch_pressed) {
		x_axis.position_enc_ticks = X_AXIS_LEFT_POS_LIMIT_TICKS;
	}
	if (x_axis.limit_switch_2 == dcm_limit_switch_pressed) {
		x_axis.position_enc_ticks = X_AXIS_RIGHT_POS_LIMIT_TICKS;
	}

	// Calculate position error
	x_axis.position_error_ticks = x_axis.position_cmd_enc_ticks - x_axis.position_enc_ticks;
	error_p = abs(x_axis.position_error_ticks) * X_AXIS_POS_GAIN_P;

	// Stop if at desired position
	if (x_axis.position_error_ticks == 0) {
		X_AXIS_SET_PWM_DUTY(X_AXIS_PWM_DUTY_MIN);
		x_axis.pwm_duty = X_AXIS_PWM_DUTY_MIN;
		x_axis.h_bridge_direction = dcm_h_bridge_dir_brake;
		X_AXIS_H_BRIDGE_BRAKE;
		return;
	}

	// Drive motor to desired position
	if (x_axis.position_error_ticks > 0) {
		if (x_axis.h_bridge_direction == dcm_h_bridge_dir_reverse) {
			// Stop before reversing direction
			X_AXIS_SET_PWM_DUTY(X_AXIS_PWM_DUTY_MIN);
			x_axis.pwm_duty = X_AXIS_PWM_DUTY_MIN;
			x_axis.h_bridge_direction = dcm_h_bridge_dir_brake;
			X_AXIS_H_BRIDGE_BRAKE;
		} else {
			if (error_p > X_AXIS_PWM_DUTY_MAX) {
				x_axis.pwm_duty = X_AXIS_PWM_DUTY_MAX;
			} else {
				x_axis.pwm_duty = LOW(error_p);
			}
			X_AXIS_SET_PWM_DUTY(x_axis.pwm_duty);
			x_axis.h_bridge_direction = dcm_h_bridge_dir_forward;
			X_AXIS_H_BRIDGE_FORWARD;
		}
		return;
	} else {
		if (x_axis.h_bridge_direction == dcm_h_bridge_dir_forward) {
			// Stop before reversing direction
			X_AXIS_SET_PWM_DUTY(X_AXIS_PWM_DUTY_MIN);
			x_axis.pwm_duty = X_AXIS_PWM_DUTY_MIN;
			x_axis.h_bridge_direction = dcm_h_bridge_dir_brake;
			X_AXIS_H_BRIDGE_BRAKE;
		} else {
			if (error_p > X_AXIS_PWM_DUTY_MAX) {
				x_axis.pwm_duty = X_AXIS_PWM_DUTY_MAX;
			} else {
				x_axis.pwm_duty = LOW(error_p);
			}
			X_AXIS_SET_PWM_DUTY(x_axis.pwm_duty);
			x_axis.h_bridge_direction = dcm_h_bridge_dir_reverse;
			X_AXIS_H_BRIDGE_REVERSE;
		}
		return;
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
	} else {
		// Phase A leads Phase B
		x_axis.quadrature_direction = dcm_quad_dir_forward;
	}

	// Track position by encoder ticks
	if (x_axis.quadrature_direction == dcm_quad_dir_forward) {
		if (x_axis.position_enc_ticks < MAX_UINT) {
			x_axis.position_enc_ticks ++;
		}
	} else {
		if (x_axis.position_enc_ticks > 0) {
			x_axis.position_enc_ticks --;
		}
	}

	// Calculate Encoder A period for speed measurements
	if (x_axis.enc_a_edge_tracker == 0) {
		x_axis.enc_a_edge_1_tcnt_ticks = X_AXIS_ENC_A_TIMER;
		x_axis.enc_a_edge_1_tcnt_overflow = timer_get_overflow();
		x_axis.enc_a_edge_tracker = 1;
	} else {
		x_axis.enc_a_edge_2_tcnt_ticks = X_AXIS_ENC_A_TIMER;
		x_axis.enc_a_edge_2_tcnt_overflow = timer_get_overflow();
		x_axis.enc_a_edge_tracker = 0;
		x_axis.period_tcnt_ticks = (x_axis.enc_a_edge_2_tcnt_ticks
		+ (x_axis.enc_a_edge_2_tcnt_overflow * TNCT_OVF_FACTOR))
		- (x_axis.enc_a_edge_1_tcnt_ticks
		+ (x_axis.enc_a_edge_1_tcnt_overflow * TNCT_OVF_FACTOR));
	}
}

//;**************************************************************
//;*                 timer_1kHz_loop()
//;*    1kHz loop triggered by timer channel 6
//;**************************************************************
interrupt 14 void timer_1kHz_loop(void)
{
	if (x_axis.ctrl_mode == dcm_ctrl_mode_position) {
		x_axis_position_ctrl();
	}

	TC6 = TCNT + TCNT_mS;   // Delay 1mS
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
	pos_cmd_calculation = (can_msg_mc_cmd_pc.pos_cmd_x_mm * 10) / X_AXIS_MM_PER_REV;
	x_axis.position_cmd_enc_ticks = (0xFFFF) & (pos_cmd_calculation * (X_AXIS_ENC_TICKS_PER_REV / 10) + X_AXIS_LEFT_POS_LIMIT_TICKS);

	// Clear Rx flag
	SET_BITS(CANRFLG, CAN_RX_INTERRUPT);
}