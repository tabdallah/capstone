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

//;**************************************************************
//;*                 y_axis_configure(void)
//;*	Configure H-Bridge direction control port pins.
//;*	Configure PWM channel for motor control.
//;*	Configure encoder port pins and input-capture interrupt.
//;**************************************************************
void y_axis_configure(void)
{
	// Set motor control parameters
	y_axis.axis_length_mm = Y_AXIS_LENGTH_MM;
	y_axis.axis_boundary_mm = Y_AXIS_BOUNDARY_MM;
	y_axis.home_position_mm = Y_AXIS_HOME_MM;
	y_axis.max_speed = Y_AXIS_SPEED_MAX;
	y_axis.gain_p = Y_AXIS_GAIN_P;
	y_axis.gain_p_factor = Y_AXIS_GAIN_P_FACTOR;
	y_axis.gain_i = Y_AXIS_GAIN_I;
	y_axis.integral_limit = Y_AXIS_INTEGRAL_LIMIT;
	y_axis.slew_rate = Y_AXIS_SLEW_RATE;
	y_axis.speed_limit_distance_factor = Y_AXIS_SPEED_LIMIT_DISTANCE_FACTOR;

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

	// Default to off
	y_axis.ctrl_mode = dcm_ctrl_mode_disable;
}

//;**************************************************************
//;*                 Y_axis_home(void)
//;*	Move paddle to home position in the Y-Axis
//;**************************************************************
void y_axis_home(void)
{
	// Drive motors backwards
	Y_AXIS_L_SET_PWM_DUTY(45);
	Y_AXIS_R_SET_PWM_DUTY(45);

	// Wait for limit switches to be hit
	// To Do: Should have some timeout here to handle broken switch
	// For now broken switch handled by dcm overload check
	while (Y_AXIS_L_HOME == dcm_home_switch_unpressed) {};
	Y_AXIS_L_SET_PWM_DUTY(DCM_PWM_DUTY_OFF);
	Y_AXIS_R_SET_PWM_DUTY(DCM_PWM_DUTY_OFF);
	y_axis.position_mm = y_axis.home_position_mm;
	y_axis.position_enc_ticks = (y_axis.position_mm * DCM_ENC_TICKS_PER_REV) / DCM_MM_PER_REV;

	// Set target to boundary
	y_axis.position_cmd_mm = y_axis.axis_boundary_mm;
}

//;**************************************************************
//;*                 y_axis_position_ctrl(void)
//;**************************************************************
void y_axis_position_ctrl(void)
{
	static unsigned char count = 0;

	// Speed calculation at 100 Hz
	dcm_speed_calc(&y_axis);
	dcm_overload_check(&y_axis);

	// Perform position control at 1 kHz
	y_axis.home_switch = Y_AXIS_L_HOME;
	dcm_control(&y_axis);
	y_axis_set_dcm_drive();
}

//;**************************************************************
//;*                 y_axis_set_dcm_drive(void)
//;*	Helper function to set y-axis DC motors direction and speed
//;**************************************************************
static void y_axis_set_dcm_drive(void)
{
	static unsigned int speed_old = 0;
	unsigned int set_speed = y_axis.calc_speed;
	if (set_speed > speed_old) {
		if ((set_speed - speed_old) > y_axis.slew_rate) {
			set_speed = speed_old + y_axis.slew_rate;
		}
	}
	speed_old = set_speed;

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