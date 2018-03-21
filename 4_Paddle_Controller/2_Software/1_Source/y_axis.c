//;******************************************************************************
//; y_axis.c - Code specific to the Y-Axis DC Motors and Encoders
//; Name: Thomas Abdallah
//; Date: 2018-03-19
//;******************************************************************************
#include <hidef.h>      /* common defines and macros */
#include "derivative.h"      /* derivative-specific definitions */
#include "timer.h"
#include "pwm.h"
#include "dcm.h"
#include "y_axis.h"

static dcm_t y_axis_l = {Y_AXIS_ENC_OFFSET_TICKS, Y_AXIS_ENC_OFFSET_TICKS, 0,0,0,0,0,0,0,0,0,0,0};
static dcm_t y_axis_r = {Y_AXIS_ENC_OFFSET_TICKS, Y_AXIS_ENC_OFFSET_TICKS, 0,0,0,0,0,0,0,0,0,0,0};
static signed int y_axis_lr_position_error_enc_ticks = 0;
static y_axis_error_e y_axis_error = y_axis_error_none;

//;**************************************************************
//;*                 y_axis_configure(void)
//;*	Configure H-Bridge direction control port pins.
//;*	Configure PWM channel for motor control.
//;*	Configure encoder port pins and input-capture interrupt.
//;**************************************************************
void y_axis_configure(void)
{
	// Configure H-Bridge direction control port pins.
	SET_BITS(Y_AXIS_H_BRIDGE_DDR, (Y_AXIS_L_H_BRIDGE_FORWARD_PIN | Y_AXIS_L_H_BRIDGE_REVERSE_PIN));
	SET_BITS(Y_AXIS_H_BRIDGE_DDR, (Y_AXIS_R_H_BRIDGE_FORWARD_PIN | Y_AXIS_R_H_BRIDGE_REVERSE_PIN));
	Y_AXIS_L_H_BRIDGE_BRAKE;
	Y_AXIS_R_H_BRIDGE_BRAKE;

	// Configure PWM channel for motor control.
	Y_AXIS_L_SET_PWM_PERIOD;
	Y_AXIS_L_SET_PWM_DUTY(Y_AXIS_PWM_DUTY_MIN);
	Y_AXIS_L_CLEAR_PWM_COUNT;
	Y_AXIS_L_ENABLE_PWM;
	Y_AXIS_R_SET_PWM_PERIOD;
	Y_AXIS_R_SET_PWM_DUTY(Y_AXIS_PWM_DUTY_MIN);
	Y_AXIS_R_CLEAR_PWM_COUNT;
	Y_AXIS_R_ENABLE_PWM;

	// Configure encoder port pins and input-capture interrupt.
	CLEAR_BITS(Y_AXIS_ENC_DDR, Y_AXIS_L_ENC_B);	// B-Phase input is read during ISR for A-Phase
	CLEAR_BITS(Y_AXIS_ENC_DDR, Y_AXIS_R_ENC_B);	// B-Phase input is read during ISR for A-Phase
	CLEAR_BITS(TIOS, Y_AXIS_L_ENC_A_TIOS_MASK);	// Set A-Phase timer channel to input capture mode
	CLEAR_BITS(TIOS, Y_AXIS_R_ENC_A_TIOS_MASK);	// Set A-Phase timer channel to input capture mode
	TCTL4 = Y_AXIS_TCTL4_INIT;					// Capture on rising edges
	SET_BITS(TIE, Y_AXIS_L_ENC_A_TIOS_MASK);	// Enable intterupts for A-Phase timer channel
	SET_BITS(TIE, Y_AXIS_R_ENC_A_TIOS_MASK);	// Enable intterupts for A-Phase timer channel
	TFLG1 = (Y_AXIS_L_ENC_A_TFLG1_MASK);		// Clear the flag in case anything is pending
	TFLG1 = (Y_AXIS_R_ENC_A_TFLG1_MASK);		// Clear the flag in case anything is pending
}

//;**************************************************************
//;*                 y_axis_position_ctrl(void)
//;**************************************************************
void y_axis_position_ctrl(void)
{	
	// Always force right (slave) position command to match left (master) position command
	y_axis_r.position_cmd_enc_ticks = y_axis_l.position_cmd_enc_ticks;

	// Calculate error between left (master) and right (slave) motor position
	y_axis_lr_position_error_enc_ticks = y_axis_l.position_enc_ticks - y_axis_r.position_enc_ticks;
	if ((y_axis_lr_position_error_enc_ticks >= Y_AXIS_LR_POS_ERROR_LIMIT_ENC_TICKS) ||
		(y_axis_lr_position_error_enc_ticks <= -Y_AXIS_LR_POS_ERROR_LIMIT_ENC_TICKS)) {
		if (y_axis_error == y_axis_error_none) {
			y_axis_error = y_axis_error_lr_pos_mism;
		}
		Y_AXIS_L_SET_PWM_DUTY(Y_AXIS_PWM_DUTY_MIN);
		y_axis_l.pwm_duty = Y_AXIS_PWM_DUTY_MIN;
		y_axis_l.h_bridge_direction = dcm_h_bridge_dir_brake;
		Y_AXIS_L_H_BRIDGE_BRAKE;
		Y_AXIS_R_SET_PWM_DUTY(Y_AXIS_PWM_DUTY_MIN);
		y_axis_r.pwm_duty = Y_AXIS_PWM_DUTY_MIN;
		y_axis_r.h_bridge_direction = dcm_h_bridge_dir_brake;
		Y_AXIS_R_H_BRIDGE_BRAKE;
		return;
	}

	// Calculate error for left motor (master)
	y_axis_l.position_error_ticks = y_axis_l.position_cmd_enc_ticks - y_axis_l.position_enc_ticks;
	
	// Drive left motor to desired position
	if (y_axis_l.position_error_ticks > 0) {
		if (y_axis_l.h_bridge_direction == dcm_h_bridge_dir_reverse) {
			// Stop before reversing direction
			Y_AXIS_L_SET_PWM_DUTY(Y_AXIS_PWM_DUTY_MIN);
			y_axis_l.pwm_duty = Y_AXIS_PWM_DUTY_MIN;
			y_axis_l.h_bridge_direction = dcm_h_bridge_dir_brake;
			Y_AXIS_L_H_BRIDGE_BRAKE;
		} else {
			y_axis_l.pwm_duty = MIN(Y_AXIS_PWM_DUTY_MAX, (y_axis_l.position_error_ticks * Y_AXIS_L_POS_GAIN_P));
			Y_AXIS_L_SET_PWM_DUTY(y_axis_l.pwm_duty);
			y_axis_l.h_bridge_direction = dcm_h_bridge_dir_forward;
			Y_AXIS_L_H_BRIDGE_FORWARD;
		}
	} else if (y_axis_l.position_error_ticks < 0) {
		if (y_axis_l.h_bridge_direction == dcm_h_bridge_dir_forward) {
			// Stop before reversing direction
			Y_AXIS_L_SET_PWM_DUTY(Y_AXIS_PWM_DUTY_MIN);
			y_axis_l.pwm_duty = Y_AXIS_PWM_DUTY_MIN;
			y_axis_l.h_bridge_direction = dcm_h_bridge_dir_brake;
			Y_AXIS_L_H_BRIDGE_BRAKE;
		} else {
			y_axis_l.pwm_duty = MIN(Y_AXIS_PWM_DUTY_MAX, (-y_axis_l.position_error_ticks * Y_AXIS_L_POS_GAIN_P));
			Y_AXIS_L_SET_PWM_DUTY(y_axis_l.pwm_duty);
			y_axis_l.h_bridge_direction = dcm_h_bridge_dir_reverse;
			Y_AXIS_L_H_BRIDGE_REVERSE;
		}
	} else {
		// Stop at desired position
		Y_AXIS_L_SET_PWM_DUTY(Y_AXIS_PWM_DUTY_MIN);
		y_axis_l.pwm_duty = Y_AXIS_PWM_DUTY_MIN;
		y_axis_l.h_bridge_direction = dcm_h_bridge_dir_brake;
		Y_AXIS_L_H_BRIDGE_BRAKE;
	}

	// Calculate error for right motor (slave)
	y_axis_r.position_error_ticks = y_axis_r.position_cmd_enc_ticks - y_axis_r.position_enc_ticks;
	y_axis_r.position_error_ticks = MIN(y_axis_r.position_error_ticks, y_axis_lr_position_error_enc_ticks);

	// Drive right motor to desired position
	if (y_axis_r.position_error_ticks > 0) {
		if (y_axis_r.h_bridge_direction == dcm_h_bridge_dir_reverse) {
			// Stop before reversing direction
			Y_AXIS_R_SET_PWM_DUTY(Y_AXIS_PWM_DUTY_MIN);
			y_axis_r.pwm_duty = Y_AXIS_PWM_DUTY_MIN;
			y_axis_r.h_bridge_direction = dcm_h_bridge_dir_brake;
			Y_AXIS_R_H_BRIDGE_BRAKE;
		} else {
			y_axis_r.pwm_duty = MIN(Y_AXIS_PWM_DUTY_MAX, (y_axis_r.position_error_ticks * Y_AXIS_R_POS_GAIN_P));
			Y_AXIS_R_SET_PWM_DUTY(y_axis_r.pwm_duty);
			y_axis_r.h_bridge_direction = dcm_h_bridge_dir_forward;
			Y_AXIS_R_H_BRIDGE_FORWARD;
		}
	} else if (y_axis_r.position_error_ticks < 0) {
		if (y_axis_r.h_bridge_direction == dcm_h_bridge_dir_forward) {
			// Stop before reversing direction
			Y_AXIS_R_SET_PWM_DUTY(Y_AXIS_PWM_DUTY_MIN);
			y_axis_r.pwm_duty = Y_AXIS_PWM_DUTY_MIN;
			y_axis_r.h_bridge_direction = dcm_h_bridge_dir_brake;
			Y_AXIS_R_H_BRIDGE_BRAKE;
		} else {
			y_axis_r.pwm_duty = MIN(Y_AXIS_PWM_DUTY_MAX, (-y_axis_r.position_error_ticks * Y_AXIS_R_POS_GAIN_P));
			Y_AXIS_R_SET_PWM_DUTY(y_axis_r.pwm_duty);
			y_axis_r.h_bridge_direction = dcm_h_bridge_dir_reverse;
			Y_AXIS_R_H_BRIDGE_REVERSE;
		}
	} else {
		// Stop at desired position
		Y_AXIS_R_SET_PWM_DUTY(Y_AXIS_PWM_DUTY_MIN);
		y_axis_r.pwm_duty = Y_AXIS_PWM_DUTY_MIN;
		y_axis_r.h_bridge_direction = dcm_h_bridge_dir_brake;
		Y_AXIS_R_H_BRIDGE_BRAKE;
	}
}

//;**************************************************************
//;*                 y_axis_l_encoder_a()
//;*  Handles IC function for Y-Axis Left Motor Encoder A Phase
//;**************************************************************
interrupt 8 void y_axis_l_encoder_a(void)
{
	// Track direction
	if (Y_AXIS_ENC_PORT & Y_AXIS_L_ENC_B) {
		// Phase B leads Phase A
		y_axis_l.quadrature_direction = dcm_quad_dir_forward;				
	} else {
		// Phase A leads Phase B
		y_axis_l.quadrature_direction = dcm_quad_dir_reverse;
	}

	// Track position by encoder ticks
	if (y_axis_l.quadrature_direction == dcm_quad_dir_forward) {
		if (y_axis_l.position_enc_ticks < MAX_UINT) {
			y_axis_l.position_enc_ticks ++;
		}
	} else {
		if (y_axis_l.position_enc_ticks > 0) {
			y_axis_l.position_enc_ticks --;
		}
	}

	// Calculate Encoder A period for speed measurements
	if (y_axis_l.enc_a_edge_tracker == 0) {
		y_axis_l.enc_a_edge_1_tcnt_ticks = Y_AXIS_L_ENC_A_TIMER;
		y_axis_l.enc_a_edge_1_tcnt_overflow = timer_get_overflow();
		y_axis_l.enc_a_edge_tracker = 1;
	} else {
		y_axis_l.enc_a_edge_2_tcnt_ticks = Y_AXIS_L_ENC_A_TIMER;
		y_axis_l.enc_a_edge_2_tcnt_overflow = timer_get_overflow();
		y_axis_l.enc_a_edge_tracker = 0;
		y_axis_l.period_tcnt_ticks = (y_axis_l.enc_a_edge_2_tcnt_ticks
		+ (y_axis_l.enc_a_edge_2_tcnt_overflow * TNCT_OVF_FACTOR))
		- (y_axis_l.enc_a_edge_1_tcnt_ticks
		+ (y_axis_l.enc_a_edge_1_tcnt_overflow * TNCT_OVF_FACTOR));
	}
}

//;**************************************************************
//;*                 y_axis_r_encoder_a()
//;*  Handles IC function for Y-Axis Right Motor Encoder A Phase
//;**************************************************************
interrupt 10 void y_axis_r_encoder_a(void)
{
	// Track direction
	if (Y_AXIS_ENC_PORT & Y_AXIS_R_ENC_B) {
		// Phase B leads Phase A
		y_axis_r.quadrature_direction = dcm_quad_dir_reverse;				
	} else {
		// Phase A leads Phase B
		y_axis_r.quadrature_direction = dcm_quad_dir_forward;
	}

	// Track position by encoder ticks
	if (y_axis_r.quadrature_direction == dcm_quad_dir_forward) {
		if (y_axis_r.position_enc_ticks < MAX_UINT) {
			y_axis_r.position_enc_ticks ++;
		}
	} else {
		if (y_axis_r.position_enc_ticks > 0) {
			y_axis_r.position_enc_ticks --;
		}
	}

	// Calculate Encoder A period for speed measurements
	// Not needed for right motor, position control only as slave to left motor
	(void) Y_AXIS_R_ENC_A_TIMER;
}

//;**************************************************************
//;*                 timer_1kHz_loop()
//;*    1kHz loop triggered by timer channel 6
//;**************************************************************
interrupt 14 void timer_1kHz_loop(void)
{
    y_axis_position_ctrl();
    TC6 = TCNT + TCNT_mS;   // Delay 1mS
}