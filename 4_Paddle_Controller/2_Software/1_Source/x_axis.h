//;******************************************************************************
//; x_axis.h - Code specific to the X-Axis DC Motor and Encoder
//; Name: Thomas Abdallah
//; Date: 2018-03-19
//;******************************************************************************
#include "TA_Header_W2016.h"  /* my macros and constants */
#include "dcm.h"

#ifndef X_AXIS_H
#define X_AXIS_H

// Motor control PWM channel setup and control macros
#define X_AXIS_SET_PWM_PERIOD(period) PWMPER0 = period
#define X_AXIS_SET_PWM_DUTY(duty) PWMDTY0 = duty
#define X_AXIS_CLEAR_PWM_COUNT PWMCNT0 = 0
#define X_AXIS_ENABLE_PWM SET_BITS(PWME, PWME_PWME0_MASK)
#define X_AXIS_DISABLE_PWM CLEAR_BITS(PWME, PWME_PWME0_MASK)

// Mapping speed to PWM duty
#define X_AXIS_SPEED_MAX 50

// Encoder port setup and macros
#define X_AXIS_ENC_PORT PTT
#define X_AXIS_ENC_DDR DDRT
#define X_AXIS_ENC_A 0b00000001
#define X_AXIS_ENC_B 0b00000010
#define X_AXIS_ENC_A_TIMER TC0
#define X_AXIS_TCTL4_INIT 0b00000001	// Capture on rising edge of TC0

// Home switch port setup and macros
#define X_AXIS_HOME_PORT PORTB
#define X_AXIS_HOME_DDR DDRB
#define X_AXIS_HOME_PIN 0b00000001 // PB0
#define X_AXIS_HOME_SHIFT 0
#define X_AXIS_HOME ((X_AXIS_HOME_PORT & X_AXIS_HOME_PIN) >> X_AXIS_HOME_SHIFT)

// Position control constants
#define X_AXIS_HOME_ENC_TICKS 0	
#define X_AXIS_HOME_MM 25
#define X_AXIS_LENGTH_ENC_TICKS 4650
#define X_AXIS_BOUNDARY_ENC_TICKS 500
#define X_AXIS_GAIN_P 1
#define X_AXIS_GAIN_P_FACTOR 10
#define X_AXIS_GAIN_I 1
#define X_AXIS_INTEGRAL_LIMIT 0
#define X_AXIS_SLEW_RATE 1

// Function prototypes
void x_axis_configure(void);
void x_axis_home(void);
void x_axis_position_ctrl(void);
static void x_axis_set_dcm_drive(void);
dcm_t *x_axis_get_data(void);

#endif