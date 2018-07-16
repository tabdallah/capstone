//;******************************************************************************
//; dcm.c - Code to control the DC motors
//; Name: Thomas Abdallah
//; Date: 2018-07-11
//;******************************************************************************
#include <stdlib.h>
#include <hidef.h>      /* common defines and macros */
#include "derivative.h"      /* derivative-specific definitions */
#include "dcm.h"

//;**************************************************************
//;*                 dcm_control
//;**************************************************************
void dcm_control(dcm_t *dcm)
{
	static signed int error_i = 0;
	signed int error_p, error_calc;

	// Sanity check control mode
	if (dcm->ctrl_mode != dcm_ctrl_mode_enable) {
		dcm->calc_speed = 0;
		return;
	}

	// Limit position commands to stay inside the virtual limit
	if (dcm->position_cmd_mm > (dcm->axis_length_mm - dcm->axis_boundary_mm)) {
		dcm->position_cmd_mm = dcm->axis_length_mm - dcm->axis_boundary_mm;
	}
	if (dcm->position_cmd_mm < dcm->axis_boundary_mm) {
		dcm->position_cmd_mm = dcm->axis_boundary_mm;
	}

	// Read home position switches
	if (dcm->home_switch == dcm_home_switch_pressed) {
		DisableInterrupts;
		dcm->position_mm = dcm->home_position_mm;
		dcm->position_enc_ticks = (dcm->position_mm * DCM_ENC_TICKS_PER_REV) / DCM_MM_PER_REV;
		EnableInterrupts;
	}

	// Calculate position error
	DisableInterrupts;	// Start critical region
	dcm->position_mm = (dcm->position_enc_ticks * DCM_MM_PER_REV) / DCM_ENC_TICKS_PER_REV;
	dcm->position_error_mm = dcm->position_cmd_mm - dcm->position_mm;
	EnableInterrupts;	// End critical region

	// Stop if at desired position
	if (abs(dcm->position_error_mm) <= 2) {
		error_i = 0;
		dcm->calc_speed = 0;
		dcm->h_bridge_direction = dcm_h_bridge_dir_brake;
		return;
	}

	// Accumulate integral error to eliminate steady-state position error
	error_i += (dcm->position_error_mm / dcm->gain_i);
	if (error_i > dcm->integral_limit) {
		error_i = dcm->integral_limit;
	}
	if (error_i < -(dcm->integral_limit)) {
		error_i = -(dcm->integral_limit);
	}

	// Calculate proportional error contribution
	error_p = (dcm->position_error_mm * dcm->gain_p) / dcm->gain_p_factor;

	// Calculate total effective error
	error_calc = error_i + error_p;

	// Limit speed when close to limit switches
	if ((abs(dcm->position_mm - dcm->axis_boundary_mm) < dcm->slow_down_threshold_mm) && 
		(dcm->h_bridge_direction == dcm_h_bridge_dir_reverse)) {
		// Close to lower limit switch
		if ((dcm->position_mm > dcm->axis_boundary_mm) && (dcm->speed_mm_per_s > dcm->slow_down_speed_mm_per_s)) {
			error_calc = (dcm->slow_down_speed_mm_per_s - dcm->speed_mm_per_s) / 10;
		}
	} else if ((abs((dcm->axis_length_mm - dcm->axis_boundary_mm) - dcm->position_mm) < dcm->slow_down_threshold_mm) &&
		(dcm->h_bridge_direction == dcm_h_bridge_dir_forward)) {
		// Close to upper limit switch
		if ((dcm->position_mm < (dcm->axis_length_mm - dcm->axis_boundary_mm)) && (dcm->speed_mm_per_s > dcm->slow_down_speed_mm_per_s)) {
			error_calc = (dcm->speed_mm_per_s - dcm->slow_down_speed_mm_per_s) / 10;
		}
	}

	// Drive motor to desired position
	if (error_calc > 0) {
		dcm->calc_speed = MIN(dcm->max_speed, error_calc);
		dcm->h_bridge_direction = dcm_h_bridge_dir_forward;
	} else {
		dcm->calc_speed = MIN(dcm->max_speed, abs(error_calc));
		dcm->h_bridge_direction = dcm_h_bridge_dir_reverse;
	}
}

//;**************************************************************
//;*                 dcm_set_error
//;**************************************************************
void dcm_set_error(dcm_t *dcm, dcm_error_e error)
{
	dcm->error = error;
	dcm->calc_speed = 0;
	dcm->set_speed = 0;
	dcm->pwm_duty = DCM_PWM_DUTY_OFF;
	dcm->ctrl_mode = dcm_ctrl_mode_disable;
}

//;**************************************************************
//;*                 dcm_speed_calc
//;**************************************************************
void dcm_speed_calc(dcm_t *dcm)
{
	unsigned long speed_calc_mm_per_s;

	speed_calc_mm_per_s = 100 * abs(dcm->position_mm - dcm->position_mm_old);
	speed_calc_mm_per_s = (speed_calc_mm_per_s * DCM_MM_PER_REV) / DCM_ENC_TICKS_PER_REV;
	dcm->speed_mm_per_s = 0xFFFF & speed_calc_mm_per_s;
	dcm->position_mm_old = dcm->position_mm;
}

//;**************************************************************
//;*                 dcm_overload_check
//;**************************************************************
void dcm_overload_check(dcm_t *dcm)
{
	// Reset strike counter if motor changes direction
	if (dcm->h_bridge_direction != dcm->h_bridge_direction_old) {
		dcm->overload_strike_counter = 0;
	}
	dcm->h_bridge_direction_old = dcm->h_bridge_direction;

	// Only checking overload condition at max set speed
	if (dcm->set_speed == dcm->max_speed) {
		if (dcm->speed_mm_per_s < DCM_OVERLOAD_SPEED_MM_PER_S) {
			dcm->overload_strike_counter ++;
		}
		else {
			dcm->overload_strike_counter = 0;
		}
	}

	// Throw error if strike count limit reached
	if (dcm->overload_strike_counter >= DCM_OVERLOAD_STRIKE_COUNT_LIMIT) {
		dcm_set_error(dcm, dcm_error_overload);
	}
}