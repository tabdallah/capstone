//;******************************************************************************
//; x_axis.h - Code specific to the Y-Axis DC Motors and Encoders
//; Name: Thomas Abdallah
//; Date: 2018-03-19
//;******************************************************************************
#include "TA_Header_W2016.h"  /* my macros and constants */
#include "dcm.h"

// H-Bridge port setup and direction control macros
#define Y_AXIS_H_BRIDGE_PORT PORTB
#define Y_AXIS_H_BRIDGE_DDR DDRB
#define Y_AXIS_L_H_BRIDGE_FORWARD_PIN 0b00000010
#define Y_AXIS_L_H_BRIDGE_REVERSE_PIN 0b00000001
#define Y_AXIS_L_H_BRIDGE_FORWARD (FORCE_BITS(Y_AXIS_H_BRIDGE_PORT, (Y_AXIS_L_H_BRIDGE_FORWARD_PIN | Y_AXIS_L_H_BRIDGE_REVERSE_PIN), Y_AXIS_L_H_BRIDGE_FORWARD_PIN))
#define Y_AXIS_L_H_BRIDGE_REVERSE (FORCE_BITS(Y_AXIS_H_BRIDGE_PORT, (Y_AXIS_L_H_BRIDGE_FORWARD_PIN | Y_AXIS_L_H_BRIDGE_REVERSE_PIN), Y_AXIS_L_H_BRIDGE_REVERSE_PIN))
#define Y_AXIS_L_H_BRIDGE_BRAKE (CLEAR_BITS(Y_AXIS_H_BRIDGE_PORT, (Y_AXIS_L_H_BRIDGE_FORWARD_PIN | Y_AXIS_L_H_BRIDGE_REVERSE_PIN)))
#define Y_AXIS_R_H_BRIDGE_FORWARD_PIN 0b00001000
#define Y_AXIS_R_H_BRIDGE_REVERSE_PIN 0b00000100
#define Y_AXIS_R_H_BRIDGE_FORWARD (FORCE_BITS(Y_AXIS_H_BRIDGE_PORT, (Y_AXIS_R_H_BRIDGE_FORWARD_PIN | Y_AXIS_R_H_BRIDGE_REVERSE_PIN), Y_AXIS_R_H_BRIDGE_FORWARD_PIN))
#define Y_AXIS_R_H_BRIDGE_REVERSE (FORCE_BITS(Y_AXIS_H_BRIDGE_PORT, (Y_AXIS_R_H_BRIDGE_FORWARD_PIN | Y_AXIS_R_H_BRIDGE_REVERSE_PIN), Y_AXIS_R_H_BRIDGE_REVERSE_PIN))
#define Y_AXIS_R_H_BRIDGE_BRAKE (CLEAR_BITS(Y_AXIS_H_BRIDGE_PORT, (Y_AXIS_R_H_BRIDGE_FORWARD_PIN | Y_AXIS_R_H_BRIDGE_REVERSE_PIN)))

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
#define Y_AXIS_L_ENC_A 0b00001000
#define Y_AXIS_L_ENC_B 0b00000001
#define Y_AXIS_R_ENC_A 0b00000100
#define Y_AXIS_R_ENC_B 0b00000010
#define Y_AXIS_L_ENC_B_TIMER TC0
#define Y_AXIS_R_ENC_B_TIMER TC1
#define Y_AXIS_L_ENC_B_TIOS_MASK TIOS_IOS0_MASK
#define Y_AXIS_R_ENC_B_TIOS_MASK TIOS_IOS1_MASK
#define Y_AXIS_L_ENC_B_TFLG1_MASK TFLG1_C0F_MASK
#define Y_AXIS_R_ENC_B_TFLG1_MASK TFLG1_C1F_MASK
#define Y_AXIS_TCTL4_INIT 0b00000101	// Capture on rising edge of TC0 and TC1

// Position control constants
#define Y_AXIS_LIMIT_1_ENC_TICKS 0		// Limit switch 1 position in encoder ticks
#define Y_AXIS_LIMIT_2_ENC_TICKS 4300	// Limit switch 2 position in encoder ticks
#define Y_AXIS_BOUNDARY_ENC_TICKS 50	// Virtual limit to the available travel
#define Y_AXIS_L_POS_GAIN_P 5
#define Y_AXIS_R_POS_GAIN_P 5
#define Y_AXIS_LR_POS_GAIN_P 5
#define Y_AXIS_LR_POS_ERROR_LIMIT_ENC_TICKS 200		// Shut down system if left vs right motor position differs by more than this
#define Y_AXIS_ENC_TICKS_PER_REV 374
#define Y_AXIS_MM_PER_REV 60
#define Y_AXIS_DCM_OVERLOAD_LIMIT_TCNT_TICKS 1500	// If encoder period is greater than this for more than xx milliseconds, motor is blocked/overloaded
#define Y_AXIS_DCM_OVERLOAD_STRIKE_COUNT 250		// In milliseconds since error check happens at 1kHz

// Limit switch port setup and macros
#define Y_AXIS_LIMIT_PORT PTAD
#define Y_AXIS_LIMIT_DDR ATDDIEN
#define Y_AXIS_L_LIMIT_1_PIN 0b01000000 // PAD06
#define Y_AXIS_L_LIMIT_1_SHIFT 6
#define Y_AXIS_L_LIMIT_1 ((Y_AXIS_LIMIT_PORT & Y_AXIS_L_LIMIT_1_PIN) >> Y_AXIS_L_LIMIT_1_SHIFT)
#define Y_AXIS_L_LIMIT_2_PIN 0b10000000 // PAD07
#define Y_AXIS_L_LIMIT_2_SHIFT 7
#define Y_AXIS_L_LIMIT_2 ((Y_AXIS_LIMIT_PORT & Y_AXIS_L_LIMIT_2_PIN) >> Y_AXIS_L_LIMIT_2_SHIFT)
#define Y_AXIS_R_LIMIT_1_PIN 0b00100000 // PAD05
#define Y_AXIS_R_LIMIT_1_SHIFT 5
#define Y_AXIS_R_LIMIT_1 ((Y_AXIS_LIMIT_PORT & Y_AXIS_R_LIMIT_1_PIN) >> Y_AXIS_R_LIMIT_1_SHIFT)
#define Y_AXIS_R_LIMIT_2_PIN 0b00010000 // PAD04
#define Y_AXIS_R_LIMIT_2_SHIFT 4
#define Y_AXIS_R_LIMIT_2 ((Y_AXIS_LIMIT_PORT & Y_AXIS_R_LIMIT_2_PIN) >> Y_AXIS_R_LIMIT_2_SHIFT)

// Function prototypes
void y_axis_configure(void);
void y_axis_home(void);
void y_axis_position_ctrl(void);
void y_axis_send_status_can(void);
void y_axis_dcm_overload_check(void);
static void y_axis_l_set_dcm_drive(dcm_h_bridge_dir_e direction, unsigned int pwm_duty);
static void y_axis_r_set_dcm_drive(dcm_h_bridge_dir_e direction, unsigned int pwm_duty);

// Enumerated data types
typedef enum {
	y_axis_error_none = 0,
	y_axis_error_dcm_overload = 1,
	y_axis_error_lr_pos_mism = 2,
	y_axis_error_can_buffer_full = 3,
	y_axis_error_can_tx = 4
} y_axis_error_e;