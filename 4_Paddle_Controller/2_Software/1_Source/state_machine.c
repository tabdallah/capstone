//;******************************************************************************
//; x_axis.c - Code specific to the X-Axis DC Motor and Encoder
//; Name: Thomas Abdallah
//; Date: 2018-03-19
//;******************************************************************************
#include <stdlib.h>
#include <hidef.h>      /* common defines and macros */
#include "derivative.h"      /* derivative-specific definitions */
#include "state_machine.h"
#include "x_axis.h"
#include "y_axis.h"
#include "can.h"

static sm_state_cmd_e state_cmd = sm_state_cmd_off;
static sm_state_e state = sm_state_off;
static sm_error_e error = sm_error_none;

//;**************************************************************
//;*                 sm_get_state
//;*	Returns the current state
//;**************************************************************
sm_state_e sm_get_state(void)
{
	return state;
}

//;**************************************************************
//;*                 sm_get_error
//;*	Returns the current error
//;**************************************************************
sm_error_e sm_get_error(void)
{
	return error;
}

//;**************************************************************
//;*                 sm_set_state_cmd
//;*	Set the state machine state command
//;**************************************************************
void sm_set_state_cmd(sm_state_cmd_e new_command)
{
	state_cmd = new_command;
}

//;**************************************************************
//;*                 sm_step
//;*	Runs the state machine
//;**************************************************************
void sm_step(void)
{
	// Check for error first
	if ((error != sm_error_none) && (state != sm_state_error)) {
		sm_enter_state(sm_state_error);
		return;
	}

	// Logic for state transitions
	switch (state)
	{
		case sm_state_off:
			if ((state_cmd == sm_state_cmd_on) || (state_cmd == sm_state_cmd_calibration)) {
				sm_enter_state(sm_state_calibration);
			}
			break;
		case sm_state_calibration:
			// This is bad since it blocks everything else, but for now it's fine
			y_axis_home();
			x_axis_home();
			state_cmd = sm_state_cmd_on;
			sm_enter_state(sm_state_on);
			break;
		case sm_state_on:
			if (state_cmd == sm_state_cmd_off) {
				sm_enter_state(sm_state_off);
				break;
			}
			if (state_cmd == sm_state_cmd_calibration) {
				sm_enter_state(sm_state_calibration);
				break;
			}
			break;
		case sm_state_error:
			if ((error == sm_error_none) && (state_cmd == sm_state_cmd_clear_error)) {
				sm_enter_state(sm_state_off);
			}
			break;
	}
}

//;**************************************************************
//;*                 sm_enter_state
//;*	Logic for state entry actions
//;**************************************************************
static void sm_enter_state(sm_state_e new_state)
{
	dcm_t *x_axis = x_axis_get_data();
	dcm_t *y_axis = y_axis_get_data();

	switch (new_state)
	{
		case sm_state_off:
			state = sm_state_off;
			x_axis->ctrl_mode = dcm_ctrl_mode_disable;
			y_axis->ctrl_mode = dcm_ctrl_mode_disable;
			break;
		case sm_state_calibration:
			state = sm_state_calibration;
			x_axis->ctrl_mode = dcm_ctrl_mode_enable;
			y_axis->ctrl_mode = dcm_ctrl_mode_enable;
			break;
		case sm_state_on:
			state = sm_state_on;
			x_axis->ctrl_mode = dcm_ctrl_mode_enable;
			y_axis->ctrl_mode = dcm_ctrl_mode_enable;
			break;
		case sm_state_error:
			state = sm_state_error;
			x_axis->ctrl_mode = dcm_ctrl_mode_disable;
			y_axis->ctrl_mode = dcm_ctrl_mode_disable;
			break;
	}

	can_send_status();	// Send status message immediately upon entering new state
}

//;**************************************************************
//;*                 sm_error_handling
//;*	Logic for error handling
//;**************************************************************
void sm_error_handling(void)
{
	dcm_t *x_axis = x_axis_get_data();
	dcm_t *y_axis = y_axis_get_data();
	can_error_e *can_error = can_get_error();

	// Execute clear error command if it is active
	if (state_cmd == sm_state_cmd_clear_error) {
		error = sm_error_none;
		x_axis->error = dcm_error_none;
		y_axis->error = dcm_error_none;
		*can_error = can_error_none;
	}

	// Do not overwrite existing error
	if (error != sm_error_none) {
		return;
	}

	// Check for CAN errors
	if (*can_error != can_error_none) {
		switch (*can_error)
		{
			case can_error_buffer_full:
				error = sm_error_can_buffer_full;
				break;
			case can_error_tx:
				error = sm_error_can_tx;
				break;
		}
		return;
	}

	// Check for y-axis errors
	if (y_axis->error != dcm_error_none) {
		switch (y_axis->error)
		{
			case dcm_error_overload:
				error = sm_error_y_axis_overload;
				break;
		}
		return;
	}

	// Check for x-axis errors
	if (x_axis->error != dcm_error_none) {
		switch (x_axis->error)
		{
			case dcm_error_overload:
				error = sm_error_x_axis_overload;
				break;
		}
		return;
	}
}