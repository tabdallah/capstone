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
#define X_AXIS_ENC_OFFSET_TICKS 100	// Encoder offset to allow for closed loop control back to position zero
#define X_AXIS_POS_GAIN_P 2

// Function prototypes
void x_axis_configure(void);
void x_axis_position_ctrl(void);