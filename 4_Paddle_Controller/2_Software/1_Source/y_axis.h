//;******************************************************************************
//; x_axis.h - Code specific to the Y-Axis DC Motors and Encoders
//; Name: Thomas Abdallah
//; Date: 2018-03-19
//;******************************************************************************
#include "TA_Header_W2016.h"  /* my macros and constants */
#include "dcm.h"

#ifndef Y_AXIS_H
#define Y_AXIS_H

// Left motor PWM channel
#define Y_AXIS_L_SET_PWM_PERIOD(period) PWMPER4 = period
#define Y_AXIS_L_SET_PWM_DUTY(duty) PWMDTY4 = duty
#define Y_AXIS_L_CLEAR_PWM_COUNT PWMCNT4 = 0
#define Y_AXIS_L_ENABLE_PWM SET_BITS(PWME, PWME_PWME4_MASK)
#define Y_AXIS_L_DISABLE_PWM CLEAR_BITS(PWME, PWME_PWME4_MASK)

// Right motor PWM channel
#define Y_AXIS_R_SET_PWM_PERIOD(period) PWMPER5 = period
#define Y_AXIS_R_SET_PWM_DUTY(duty) PWMDTY5 = duty
#define Y_AXIS_R_CLEAR_PWM_COUNT PWMCNT5 = 0
#define Y_AXIS_R_ENABLE_PWM SET_BITS(PWME, PWME_PWME5_MASK)
#define Y_AXIS_R_DISABLE_PWM CLEAR_BITS(PWME, PWME_PWME5_MASK)

// Mapping speed to PWM duty
#define Y_AXIS_SPEED_MAX 25

// Encoder port setup and macros
#define Y_AXIS_ENC_PORT PTT
#define Y_AXIS_ENC_DDR DDRT
#define Y_AXIS_L_ENC_A 0b00000100
#define Y_AXIS_L_ENC_B 0b00001000
#define Y_AXIS_R_ENC_A 0b00010000
#define Y_AXIS_R_ENC_B 0b00100000
#define Y_AXIS_L_ENC_A_TIMER TC2
#define Y_AXIS_R_ENC_A_TIMER TC4
#define Y_AXIS_L_TCTL4_INIT 0b00010000 	// Capture on rising edge of TC2
#define Y_AXIS_R_TCTL3_INIT 0b00000001 	// Capture on rising edge of TC4

// Home switch port setup and macros
#define Y_AXIS_HOME_PORT PORTB
#define Y_AXIS_HOME_DDR DDRB
#define Y_AXIS_L_HOME_PIN 0b00000010
#define Y_AXIS_L_HOME_SHIFT 1
#define Y_AXIS_L_HOME ((Y_AXIS_HOME_PORT & Y_AXIS_L_HOME_PIN) >> Y_AXIS_L_HOME_SHIFT)
#define Y_AXIS_R_HOME_PIN 0b00000100
#define Y_AXIS_R_HOME_SHIFT 2
#define Y_AXIS_R_HOME ((Y_AXIS_HOME_PORT & Y_AXIS_R_HOME_PIN) >> Y_AXIS_R_HOME_SHIFT)

// Position control constants
#define Y_AXIS_HOME_MM 133		// Position of centre of paddle when home position switch is pressed
#define Y_AXIS_LENGTH_MM 1000
#define Y_AXIS_BOUNDARY_MM 230
#define Y_AXIS_SLOWDOWN_THRESHOLD_MM 100
#define Y_AXIS_SLOWDOWN_SPEED_MM_PER_S 50
#define Y_AXIS_GAIN_P 5
#define Y_AXIS_GAIN_P_FACTOR 10
#define Y_AXIS_GAIN_I 1
#define Y_AXIS_INTEGRAL_LIMIT 10
#define Y_AXIS_SLEW_RATE 1

// Function prototypes
void y_axis_configure(void);
void y_axis_home(void);
void y_axis_position_ctrl(void);
static void y_axis_set_dcm_drive(void);
dcm_t *y_axis_get_data(void);

#endif