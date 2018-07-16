//;******************************************************************************
//; dcm.h - Common code for all DC Motors + Encoders
//; Name: Thomas Abdallah
//; Date: 2018-03-19
//;******************************************************************************
#include "TA_Header_W2016.h"  /* my macros and constants */

#ifndef DCM_H
#define DCM_H

// Motor control macros
#define DCM_PWM_DUTY_MAX 95
#define DCM_PWM_DUTY_MIN 5
#define DCM_PWM_DUTY_OFF 50
#define DCM_PWM_PERIOD 100
#define DCM_SPEED_TO_PWM_FWD(speed) LOW((((45*(speed)) + 5000) / 100))
#define DCM_SPEED_TO_PWM_REV(speed) LOW((((-45*(speed)) + 5000) / 100))

#define DCM_MM_PER_REV 40
#define DCM_ENC_TICKS_PER_REV 48

#define DCM_OVERLOAD_STRIKE_COUNT_LIMIT 25
#define DCM_OVERLOAD_SPEED_MM_PER_S	5

// Enumerated data types
typedef enum {
	dcm_h_bridge_dir_brake = 0,
	dcm_h_bridge_dir_forward = 1,
	dcm_h_bridge_dir_reverse = 2
} dcm_h_bridge_dir_e;

typedef enum {
	dcm_quad_dir_init = 0,
	dcm_quad_dir_forward = 1,
	dcm_quad_dir_reverse = 2
} dcm_quad_dir_e;

typedef enum {
	dcm_quad_phase_a = 0,
	dcm_quad_phase_b = 1
} dcm_quad_phase_e;

typedef enum {
	dcm_home_switch_unpressed = 0,
	dcm_home_switch_pressed = 1
} dcm_home_switch_e;

typedef enum {
	dcm_ctrl_mode_disable = 0,
	dcm_ctrl_mode_enable = 1
} dcm_ctrl_mode_e;

typedef enum {
	dcm_error_none = 0,
	dcm_error_overload = 1,
} dcm_error_e;

// Structure definitions
typedef struct dcm_t {
	unsigned int position_cmd_mm;
	unsigned int position_mm;
	unsigned int position_mm_old;
	unsigned int position_enc_ticks;
	signed int position_error_mm;
	unsigned int axis_length_mm;
	unsigned int axis_boundary_mm;
	unsigned int home_position_mm;
	unsigned int slow_down_threshold_mm;
	unsigned int slow_down_speed_mm_per_s;
	unsigned int speed_mm_per_s;
	unsigned int calc_speed;
	unsigned char pwm_duty;
	unsigned char set_speed;
	unsigned char max_speed;
	unsigned char gain_p;
	unsigned char gain_p_factor;
	unsigned char gain_i;
	unsigned char integral_limit;
	unsigned char slew_rate;
	unsigned char overload_strike_counter;
	dcm_h_bridge_dir_e h_bridge_direction;
	dcm_h_bridge_dir_e h_bridge_direction_old;
	dcm_quad_dir_e quadrature_direction;
	dcm_home_switch_e home_switch;
	dcm_ctrl_mode_e ctrl_mode;
	dcm_error_e error;
} dcm_t;

// Function prototypes
void dcm_control(dcm_t *dcm);
void dcm_set_error(dcm_t *dcm, dcm_error_e error);
void dcm_speed_calc(dcm_t *dcm);
void dcm_overload_check(dcm_t *dcm);

#endif