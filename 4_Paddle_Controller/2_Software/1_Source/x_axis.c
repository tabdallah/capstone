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

//;**************************************************************
//;*                 x_axis_configure(void)
//;*	Configure H-Bridge direction control port pins.
//;*	Configure PWM channel for motor control.
//;*	Configure encoder port pins and input-capture interrupt.
//;**************************************************************
void x_axis_configure(void)
{
	// Set motor control parameters
	x_axis.axis_length_mm = X_AXIS_LENGTH_MM;
	x_axis.axis_boundary_mm = X_AXIS_BOUNDARY_MM;
	x_axis.home_position_mm = X_AXIS_HOME_MM;
	x_axis.max_speed = X_AXIS_SPEED_MAX;
	x_axis.gain_p = X_AXIS_GAIN_P;
	x_axis.gain_p_factor = X_AXIS_GAIN_P_FACTOR;
	x_axis.gain_i = X_AXIS_GAIN_I;
	x_axis.integral_limit = X_AXIS_INTEGRAL_LIMIT;
	x_axis.slow_down_threshold_mm = X_AXIS_SLOWDOWN_THRESHOLD_MM;
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

	// Default to off
	x_axis.ctrl_mode = dcm_ctrl_mode_disable;
}

//;**************************************************************
//;*                 x_axis_home(void)
//;*	Move paddle to home position in the X-Axis
//;**************************************************************
void x_axis_home(void)
{
	// Drive motor backwards
	X_AXIS_SET_PWM_DUTY(45);

	// Wait for limit switch to be hit
	// To Do: Should have some timeout here to handle broken switch
	// For now broken switch handled by dcm overload check
	while (X_AXIS_HOME == dcm_home_switch_unpressed) {};
	X_AXIS_SET_PWM_DUTY(DCM_PWM_DUTY_OFF);
	x_axis.position_mm = x_axis.home_position_mm;
	x_axis.position_enc_ticks = (x_axis.position_mm * DCM_ENC_TICKS_PER_REV) / DCM_MM_PER_REV;

	// Set target to center of table
	x_axis.position_cmd_mm = (x_axis.axis_length_mm / 2);
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
	dcm_control(&x_axis);
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
	}
	speed_old = set_speed;

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