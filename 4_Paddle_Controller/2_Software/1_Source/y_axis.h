//;******************************************************************************
//; x_axis.h - Code specific to the Y-Axis DC Motors and Encoders
//; Name: Thomas Abdallah
//; Date: 2018-03-19
//;******************************************************************************
#include "TA_Header_W2016.h"  /* my macros and constants */

// H-Bridge port setup and direction control macros
#define Y_AXIS_H_BRIDGE_PORT PORTB
#define Y_AXIS_H_BRIDGE_DDR DDRB
#define Y_AXIS_L_H_BRIDGE_FORWARD 0b00000001
#define Y_AXIS_L_H_BRIDGE_REVERSE 0b00000010
#define Y_AXIS_L_H_BRIDGE_FORWARD (FORCE_BITS(Y_AXIS_H_BRIDGE_PORT, (Y_AXIS_L_H_BRIDGE_FORWARD | Y_AXIS_L_H_BRIDGE_FORWARD), Y_AXIS_L_H_BRIDGE_FORWARD))
#define Y_AXIS_L_H_BRIDGE_REVERSE (FORCE_BITS(Y_AXIS_H_BRIDGE_PORT, (Y_AXIS_L_H_BRIDGE_FORWARD | Y_AXIS_L_H_BRIDGE_FORWARD), Y_AXIS_L_H_BRIDGE_REVERSE))
#define Y_AXIS_L_H_BRIDGE_BRAKE (CLEAR_BITS(Y_AXIS_H_BRIDGE_PORT, (Y_AXIS_L_H_BRIDGE_FORWARD | Y_AXIS_L_H_BRIDGE_REVERSE))
#define Y_AXIS_R_H_BRIDGE_FORWARD 0b00000100
#define Y_AXIS_R_H_BRIDGE_REVERSE 0b00001000
#define Y_AXIS_R_H_BRIDGE_FORWARD (FORCE_BITS(Y_AXIS_H_BRIDGE_PORT, (Y_AXIS_R_H_BRIDGE_FORWARD | Y_AXIS_R_H_BRIDGE_FORWARD), Y_AXIS_R_H_BRIDGE_FORWARD))
#define Y_AXIS_R_H_BRIDGE_REVERSE (FORCE_BITS(Y_AXIS_H_BRIDGE_PORT, (Y_AXIS_R_H_BRIDGE_FORWARD | Y_AXIS_R_H_BRIDGE_FORWARD), Y_AXIS_R_H_BRIDGE_REVERSE))
#define Y_AXIS_R_H_BRIDGE_BRAKE (CLEAR_BITS(Y_AXIS_H_BRIDGE_PORT, (Y_AXIS_R_H_BRIDGE_FORWARD | Y_AXIS_R_H_BRIDGE_REVERSE))

// Motor control PWM channel setup and control macros
#define Y_AXIS_PWM_PERIOD 100
#define Y_AXIS_PWM_DUTY_MAX 100
#define Y_AXIS_PWM_DUTY_MIN 0
#define Y_AXIS_L_SET_PWM_PERIOD PWMPER4 = Y_AXIS_PWM_PERIOD
#define Y_AXIS_L_SET_PWM_DUTY(duty) PWMDTY4 = duty
#define Y_AXIS_L_CLEAR_PWM_COUNT PWMCNT4 = 0
#define Y_AXIS_L_ENABLE_PWM SET_BITS(PWME, PWME_PWME4_MASK)
#define Y_AXIS_L_DISABLE_PWM CLEAR_BITS(PWME, PWME_PWME4_MASK)
#define Y_AXIS_R_SET_PWM_PERIOD PWMPER5 = Y_AXIS_PWM_PERIOD
#define Y_AXIS_R_SET_PWM_DUTY(duty) PWMDTY5 = duty
#define Y_AXIS_R_CLEAR_PWM_COUNT PWMCNT5 = 0
#define Y_AXIS_R_ENABLE_PWM SET_BITS(PWME, PWME_PWME5_MASK)
#define Y_AXIS_R_DISABLE_PWM CLEAR_BITS(PWME, PWME_PWME5_MASK)

// Encoder port setup and macros
#define Y_AXIS_ENC_PORT PTT
#define Y_AXIS_ENC_DDR DDRT
#define Y_AXIS_L_ENC_A 0b00000001
#define Y_AXIS_L_ENC_B 0b00000010
#define Y_AXIS_R_ENC_A 0b00000100
#define Y_AXIS_R_ENC_B 0b00001000
#define Y_AXIS_ENC_A_TIMER TC0
#define Y_AXIS_ENC_B_TIMER TC2
#define Y_AXIS_ENC_OFFSET_TICKS 100	// Encoder offset to allow for closed loop control back to position zero

// Function prototypes
void x_axis_configure(void);
void x_axis_position_ctrl(void);