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

static dcm_t x_axis = {X_AXIS_LEFT_POS_LIMIT_TICKS, X_AXIS_LEFT_POS_LIMIT_TICKS, 0,0,0,0,0,0,0,0,0,0,0,dcm_limit_switch_pressed,dcm_limit_switch_pressed, dcm_ctrl_mode_disable};

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