//;******************************************************************************
//; x_axis.h - Code specific to the X-Axis DC Motor and Encoder
//; Name: Thomas Abdallah
//; Date: 2018-03-19
//;******************************************************************************
#include "TA_Header_W2016.h"  /* my macros and constants */

// H-Bridge port setup and direction control macros
#define X_AXIS_H_BRIDGE_PORT PORTB
#define X_AXIS_H_BRIDGE_DDR DDRB
#define X_AXIS_H_BRIDGE_FORWARD_PIN 0b00000001
#define X_AXIS_H_BRIDGE_REVERSE_PIN 0b00000010
#define X_AXIS_H_BRIDGE_FORWARD (FORCE_BITS(X_AXIS_H_BRIDGE_PORT, (X_AXIS_H_BRIDGE_FORWARD_PIN | X_AXIS_H_BRIDGE_REVERSE_PIN), X_AXIS_H_BRIDGE_FORWARD_PIN))
#define X_AXIS_H_BRIDGE_REVERSE (FORCE_BITS(X_AXIS_H_BRIDGE_PORT, (X_AXIS_H_BRIDGE_FORWARD_PIN | X_AXIS_H_BRIDGE_REVERSE_PIN), X_AXIS_H_BRIDGE_REVERSE_PIN))
#define X_AXIS_H_BRIDGE_BRAKE (CLEAR_BITS(X_AXIS_H_BRIDGE_PORT, (X_AXIS_H_BRIDGE_FORWARD_PIN | X_AXIS_H_BRIDGE_REVERSE_PIN)))

// Motor control PWM channel setup and control macros
#define X_AXIS_PWM_PERIOD 100
#define X_AXIS_PWM_DUTY_MAX 100
#define X_AXIS_PWM_DUTY_MIN 0
#define X_AXIS_SET_PWM_PERIOD PWMPER4 = X_AXIS_PWM_PERIOD
#define X_AXIS_SET_PWM_DUTY(duty) PWMDTY4 = duty
#define X_AXIS_CLEAR_PWM_COUNT PWMCNT4 = 0
#define X_AXIS_ENABLE_PWM SET_BITS(PWME, PWME_PWME4_MASK)
#define X_AXIS_DISABLE_PWM CLEAR_BITS(PWME, PWME_PWME4_MASK)

// Encoder port setup and macros
#define X_AXIS_ENC_PORT PTT
#define X_AXIS_ENC_DDR DDRT
#define X_AXIS_ENC_A 0b00000001
#define X_AXIS_ENC_B 0b00000010
#define X_AXIS_ENC_A_TIMER TC0
#define X_AXIS_ENC_A_TIOS_MASK TIOS_IOS0_MASK
#define X_AXIS_ENC_A_TFLG1_MASK TFLG1_C0F_MASK
#define X_AXIS_TCTL4_INIT 0b00000001	// Capture on rising edge of TC0

// Position control constants
#define X_AXIS_LEFT_POS_LIMIT_TICKS 100		// Zero/Home position
#define X_AXIS_RIGHT_POS_LIMIT_TICKS 4500	// Opposite edge of table, measured from home position
#define X_AXIS_POS_GAIN_P 10

// Limit switch port setup and macros
#define X_AXIS_LIMIT_PORT PTAD
#define X_AXIS_LIMIT_DDR ATDDIEN
#define X_AXIS_LIMIT_1_PIN 0b01000000 // PAD06
#define X_AXIS_LIMIT_1_SHIFT 6
#define X_AXIS_LIMIT_1 ((X_AXIS_LIMIT_PORT & X_AXIS_LIMIT_1_PIN) >> X_AXIS_LIMIT_1_SHIFT)
#define X_AXIS_LIMIT_2_PIN 0b10000000 // PAD07
#define X_AXIS_LIMIT_2_SHIFT 7
#define X_AXIS_LIMIT_2 ((X_AXIS_LIMIT_PORT & X_AXIS_LIMIT_2_PIN) >> X_AXIS_LIMIT_2_SHIFT)

// Function prototypes
void x_axis_configure(void);
void x_axis_home(void);
void x_axis_position_ctrl(void);