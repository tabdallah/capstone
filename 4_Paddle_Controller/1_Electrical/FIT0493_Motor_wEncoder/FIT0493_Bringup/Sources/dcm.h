//;******************************************************************************
//; dcm.h - Header file for DC motor functions
//:
//; Name: Thomas Abdallah
//; Date: 2016-04-06
//;
//;******************************************************************************
#include "TA_Header_W2016.h"  /* my macros and constants */
#include "timer.h"

// DC Motors directions Port, DDR, Masks
#define DCM_PORT PORTB
#define DCM_DDR DDRB
#define DCM_X_DIR_FORWARD 0b00000001
#define DCM_X_DIR_REVERSE 0b00000010

// DC Motors direction control masks
#define DCM_X_FORWARD (FORCE_BITS(DCM_PORT, (DCM_X_DIR_FORWARD | DCM_X_DIR_REVERSE), DCM_X_DIR_FORWARD))
#define DCM_X_REVERSE (FORCE_BITS(DCM_PORT, (DCM_X_DIR_FORWARD | DCM_X_DIR_REVERSE), DCM_X_DIR_REVERSE))
#define DCM_X_BRAKE CLEAR_BITS(DCM_PORT, (DCM_X_DIR_FORWARD | DCM_X_DIR_REVERSE))

// DC Motor PWM signal control
#define DCM_PWM_MODE_8BIT 0x00			//8-bit mode for all PWM channels
#define DCM_PWM_NO_PRESCALE 0x00		//Don't prescale, count E-clocks directly for A and B
#define DCM_PWM_HALF_PRESCALE 0x01		//PWM Clock = 1/2 E-Clock
#define DCM_PWM_CLKSA_SCALE 0x01		//Makes clock SA = 1/2 Clock A
#define DCM_PWM_PER 100u				//PWM period = 100 for easy control of PWM duty from 0-100%
#define DCM_PWM_MAX 100
#define DCM_PWM_MIN 0

// DC Motor PWM Macros
#define DCM_PWM_CENTRE_ALIGNED SET_BITS(PWMCAE, (PWMCAE_CAE4_MASK | PWMCAE_CAE5_MASK))	// Use centre aligned for DC motor PWM signal
#define DCM_PWM_LEFT_ALIGNED CLEAR_BITS(PWMCAE, (PWMCAE_CAE4_MASK | PWMCAE_CAE5_MASK))	// Use left aligned for DC motor PWM signal
#define DCM_PWM_CLK_A CLEAR_BITS(PWMCLK, (PWMCLK_PCLK4_MASK | PWMCLK_PCLK5_MASK))		// Use Clock A as source for DC motor PWM signals
#define DCM_PWM_CLK_SA SET_BITS(PWMCLK, (PWMCLK_PCLK4_MASK | PWMCLK_PCLK5_MASK))		// Use Clock SA as source for DC motor PWM signals
#define DCM_PWM_ACTIVE_LOW CLEAR_BITS(PWMPOL, (PWMPOL_PPOL4_MASK | PWMPOL_PPOL5_MASK))	// Active low output for DC motor PWM signals
#define DCM_PWM_ACTIVE_HIGH SET_BITS(PWMPOL, (PWMPOL_PPOL4_MASK | PWMPOL_PPOL5_MASK))	// Active high  output for DC motor PWM signals
#define DCM_PWM_SET_PERIOD_X PWMPER4 = DCM_PWM_PER				// Set period = PWMPER for DC motor PWM signals
#define DCM_PWM_SET_DUTY_X(dty) PWMDTY4 = dty 					// Set duty cycle for X-Axis motor
#define DCM_PWM_CLR_CNT_X PWMCNT4 = 0							// Reset counter for X-Axis motor

#define DCM_PWM_ENABLE_X SET_BITS(PWME, PWME_PWME4_MASK)		// Enable X-Axis PWM channel
#define DCM_PWM_DISABLE_X CLEAR_BITS(PWME, PWME_PWME4_MASK)		// Disable X-Axis PWM channel

// Encoder macros
#define DCM_ENCODER_B_TIMER_X TC0	// Timer channel for X-Axis Encoder B Phase readings
#define DCM_ENCODER_A_TIMER_X TC1	// Timer channel for X-Axis Encoder A Phase readings

//#define DCM_X_DISTANCE_PER_ENC_TICK 1604 // Distance in m^-7 per encoder tick
//#define DCM_X_DISTANCE_FACTOR 10000		 // Conversion factor to get distance in mm



// Structure definitions
typedef struct dcm_t {
	unsigned int position_cmd_enc_ticks;		// Commanded linear position
	unsigned int position_enc_ticks;			// Current linear position
	signed int position_error_ticks;			// Difference between current and commanded linear position
	signed char direction;						// Motor direction, 1 = forward, 0 = off, -1 = reverse
	unsigned char pwm_duty;						// Current PWM duty cycle
	unsigned int enc_edge_1_tcnt_ticks;			// Encoder first rising edge TCNT timestamp
	unsigned int enc_edge_2_tcnt_ticks;			// Encoder second rising edge TCNT timestamp
	unsigned char enc_edge_1_tcnt_overflow;		// Value of TCNT overflow counter at first rising edge
	unsigned char enc_edge_2_tcnt_overflow;		// Value of TCNT overflow counter at second rising edge
	unsigned char enc_edge_tracker;				// 0 = first rising edge, 1 = second rising edge
	unsigned long period_tcnt_ticks;			// Encoder period in TCNT ticks
	unsigned int speed_mm_s;					// Linear speed in mm/s
} dcm_t;

// Function prototypes
void dcm_configure(void);
void dcm_position_ctrl_x(void);
void dcm_safety_limit_x(void);