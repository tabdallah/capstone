//;******************************************************************************
//; x_axis.h - Code specific to the X-Axis DC Motor and Encoder
//; Name: Thomas Abdallah
//; Date: 2018-03-19
//;******************************************************************************
#include "TA_Header_W2016.h"  /* my macros and constants */
#include "dcm.h"

#define SLOW

// Motor control PWM channel setup and control macros
#ifdef SLOW
	#define X_AXIS_PWM_DUTY_MAX 60
	#define X_AXIS_PWM_DUTY_MIN 40
#else
	#define X_AXIS_PWM_DUTY_MAX 95
	#define X_AXIS_PWM_DUTY_MIN 5
#endif

#define X_AXIS_PWM_DUTY_OFF 50
#define X_AXIS_PWM_PERIOD 100
#define X_AXIS_SET_PWM_PERIOD(period) PWMPER0 = period
#define X_AXIS_SET_PWM_DUTY(duty) PWMDTY0 = duty
#define X_AXIS_CLEAR_PWM_COUNT PWMCNT0 = 0
#define X_AXIS_ENABLE_PWM SET_BITS(PWME, PWME_PWME0_MASK)
#define X_AXIS_DISABLE_PWM CLEAR_BITS(PWME, PWME_PWME0_MASK)

// Mapping speed to PWM duty
#define X_AXIS_SPEED_MAX 100
#define X_AXIS_SPEED_MIN 0

#ifdef SLOW
	#define X_AXIS_SPEED_TO_PWM_FWD(speed) LOW((((10*(speed)) + 5000) / 100))
	#define X_AXIS_SPEED_TO_PWM_REV(speed) LOW((((-10*(speed)) + 5000) / 100))
#else
	#define X_AXIS_SPEED_TO_PWM_FWD(speed) LOW((((45*(speed)) + 5000) / 100))
	#define X_AXIS_SPEED_TO_PWM_REV(speed) LOW((((-45*(speed)) + 5000) / 100))
#endif

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
#define X_AXIS_LIMIT_1_ENC_TICKS 0		// Lower position limit in encoder ticks
#define X_AXIS_LIMIT_1_MM 85
#define X_AXIS_LIMIT_2_ENC_TICKS 4800	// Upper position limit in encoder ticks
#define X_AXIS_BOUNDARY_ENC_TICKS 25	// Virtual limit to the available travel
#define PUCK_RADIUS_MM 40
#define X_AXIS_POS_GAIN_P 1
#define X_AXIS_ENC_TICKS_PER_REV 256
#define X_AXIS_MM_PER_REV 40
#define X_AXIS_DCM_OVERLOAD_LIMIT_MM_PER_S 5		// If linaer speed is less than this for more than xx milliseconds, motor is blocked/overloaded
#define X_AXIS_DCM_OVERLOAD_STRIKE_COUNT 250		// In milliseconds since error check happens at 1kHz

// Function prototypes
void x_axis_configure(void);
void x_axis_home(void);
void x_axis_position_ctrl(void);
void x_axis_send_status_can(void);
void x_axis_dcm_overload_check(void);
void x_axis_calculate_speed(void);
void x_axis_set_dcm_drive(dcm_h_bridge_dir_e direction, unsigned char speed);

// Enumerated data types
typedef enum {
	x_axis_error_none = 0,
	x_axis_error_dcm_overload = 1,
	x_axis_error_can_buffer_full = 2,
	x_axis_error_can_tx = 3
} x_axis_error_e;