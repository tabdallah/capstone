//;******************************************************************************
//; x_axis.h - Code specific to the Y-Axis DC Motors and Encoders
//; Name: Thomas Abdallah
//; Date: 2018-03-19
//;******************************************************************************
#include "TA_Header_W2016.h"  /* my macros and constants */
#include "dcm.h"

//#define SLOW

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

// Shared PWM constants
#define Y_AXIS_PWM_DUTY_MAX 95
#define Y_AXIS_PWM_DUTY_MIN 5
#define Y_AXIS_PWM_DUTY_OFF 50
#define Y_AXIS_PWM_PERIOD 100

// Mapping speed to PWM duty
//#define Y_AXIS_SPEED_MAX 10
#define Y_AXIS_SPEED_MIN 0
#define Y_AXIS_SPEED_TO_PWM_FWD(speed) LOW((((45*(speed)) + 5000) / 100))
#define Y_AXIS_SPEED_TO_PWM_REV(speed) LOW((((-45*(speed)) + 5000) / 100))

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
#define Y_AXIS_HOME_ENC_TICKS 0
#define Y_AXIS_LIMIT_1_ENC_TICKS 0		// Limit switch 1 position in encoder ticks
#define Y_AXIS_LIMIT_2_ENC_TICKS 4300	// Limit switch 2 position in encoder ticks
#define Y_AXIS_BOUNDARY_ENC_TICKS 50	// Virtual limit to the available travel
#define Y_AXIS_LR_POS_ERROR_LIMIT_ENC_TICKS 200		// Shut down system if left vs right motor position differs by more than this
#define Y_AXIS_ENC_TICKS_PER_REV 256
#define Y_AXIS_MM_PER_REV 40
#define Y_AXIS_DCM_OVERLOAD_LIMIT_MM_PER_S 5		// If linear speed is less than this for more than xx milliseconds, motor is blocked/overloaded
#define Y_AXIS_DCM_OVERLOAD_STRIKE_COUNT 250		// In milliseconds since error check happens at 1kHz

// Function prototypes
void y_axis_configure(void);
void y_axis_home(void);
void y_axis_position_ctrl(void);
void y_axis_send_status_can(void);
void y_axis_dcm_overload_check(void);
void y_axis_calculate_speed(void);
static void y_axis_l_set_dcm_drive(dcm_h_bridge_dir_e direction, unsigned int speed);
static void y_axis_r_set_dcm_drive(dcm_h_bridge_dir_e direction, unsigned int speed);

// Enumerated data types
typedef enum {
	y_axis_error_none = 0,
	y_axis_error_dcm_overload = 1,
	y_axis_error_lr_pos_mism = 2,
	y_axis_error_can_buffer_full = 3,
	y_axis_error_can_tx = 4
} y_axis_error_e;