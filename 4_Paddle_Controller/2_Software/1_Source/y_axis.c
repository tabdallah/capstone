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
#include "dcm.h"
#include "y_axis.h"
#include "can.h"

static dcm_t y_axis_l = {Y_AXIS_ENC_OFFSET_TICKS, Y_AXIS_ENC_OFFSET_TICKS, 0,0,0,0,0,0,0,0,0,0,0,0,dcm_limit_switch_pressed, dcm_ctrl_mode_disable};
static dcm_t y_axis_r = {Y_AXIS_ENC_OFFSET_TICKS, Y_AXIS_ENC_OFFSET_TICKS, 0,0,0,0,0,0,0,0,0,0,0,0,dcm_limit_switch_pressed, dcm_ctrl_mode_disable};
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
	unsigned int error_l_p, error_r_p;

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
	error_l_p = abs(y_axis_l.position_error_ticks) * Y_AXIS_L_POS_GAIN_P;
	
	// Drive left motor to desired position
	if (y_axis_l.position_error_ticks > 0) {
		if (y_axis_l.h_bridge_direction == dcm_h_bridge_dir_reverse) {
			// Stop before reversing direction
			Y_AXIS_L_SET_PWM_DUTY(Y_AXIS_PWM_DUTY_MIN);
			y_axis_l.pwm_duty = Y_AXIS_PWM_DUTY_MIN;
			y_axis_l.h_bridge_direction = dcm_h_bridge_dir_brake;
			Y_AXIS_L_H_BRIDGE_BRAKE;
		} else {
			if (error_l_p > Y_AXIS_PWM_DUTY_MAX) {
				y_axis_l.pwm_duty = Y_AXIS_PWM_DUTY_MAX;
			} else {
				y_axis_l.pwm_duty = LOW(error_l_p);
			}
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
			if (error_l_p > Y_AXIS_PWM_DUTY_MAX) {
				y_axis_l.pwm_duty = Y_AXIS_PWM_DUTY_MAX;
			} else {
				y_axis_l.pwm_duty = LOW(error_l_p);
			}
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
	error_r_p = abs(y_axis_r.position_error_ticks) * Y_AXIS_R_POS_GAIN_P;

	// Drive right motor to desired position
	if (y_axis_r.position_error_ticks > 0) {
		if (y_axis_r.h_bridge_direction == dcm_h_bridge_dir_reverse) {
			// Stop before reversing direction
			Y_AXIS_R_SET_PWM_DUTY(Y_AXIS_PWM_DUTY_MIN);
			y_axis_r.pwm_duty = Y_AXIS_PWM_DUTY_MIN;
			y_axis_r.h_bridge_direction = dcm_h_bridge_dir_brake;
			Y_AXIS_R_H_BRIDGE_BRAKE;
		} else {
			if (error_r_p > Y_AXIS_PWM_DUTY_MAX) {
				y_axis_r.pwm_duty = Y_AXIS_PWM_DUTY_MAX;
			} else {
				y_axis_r.pwm_duty = LOW(error_r_p);
			}
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
			if (error_r_p > Y_AXIS_PWM_DUTY_MAX) {
				y_axis_r.pwm_duty = Y_AXIS_PWM_DUTY_MAX;
			} else {
				y_axis_r.pwm_duty = LOW(error_r_p);
			}
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
//;*                 y_axis_send_status_can(void)
//;*	Send PC_Status_Y message
//;**************************************************************
void y_axis_send_status_can(void)
{
	unsigned char data[2];
	unsigned int pos_y_calc;
	if (y_axis_l.position_enc_ticks < Y_AXIS_ENC_OFFSET_TICKS) {
		pos_y_calc = 0;
	} else {
		pos_y_calc = (y_axis_l.position_enc_ticks - Y_AXIS_ENC_OFFSET_TICKS) * 10;
	}
	pos_y_calc = pos_y_calc / Y_AXIS_ENC_TICKS_PER_REV;
	can_msg_pc_status.pos_y_mm = ((pos_y_calc * Y_AXIS_MM_PER_REV) / 10);

	// This seems sloppy, fix this later.
	data[0] = can_msg_pc_status.pos_y_mm & 0x00FF;
	data[1] = (can_msg_pc_status.pos_y_mm & 0xFF00) >> 8;

	if (can_tx(CAN_ST_ID_PC_STATUS_Y, CAN_DLC_PC_STATUS_Y, &data[0]) != CAN_ERR_NONE) {
		// ToDo: Handle CAN errors
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
	static unsigned char count = 1;

    y_axis_position_ctrl();

   	// Send status message at 100Hz
	if ((count % 10) == 0) {
		y_axis_send_status_can();
	}
	if (count == 10) {
		count = 1;
	} else {
		count ++;
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
		// Bytes 2-3 Y-Axis position command
		can_msg_mc_cmd_pc.pos_cmd_x_mm = (can_msg_raw.data[2] | (can_msg_raw.data[3] << 8));
	}

	// Set motor position command in encoder ticks
	pos_cmd_calculation = (can_msg_mc_cmd_pc.pos_cmd_x_mm * 10) / Y_AXIS_MM_PER_REV;
	y_axis_l.position_cmd_enc_ticks = (0xFFFF) & (pos_cmd_calculation * (Y_AXIS_ENC_TICKS_PER_REV / 10) + Y_AXIS_ENC_OFFSET_TICKS);

	// Clear Rx flag
	SET_BITS(CANRFLG, CAN_RX_INTERRUPT);
}