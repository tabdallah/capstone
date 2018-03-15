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
#define dcmPort PORTB
#define dcmDDR DDRB
#define dcm_x_dir_fwd 0b00000001
#define dcm_x_dir_rev 0b00000010

// DC Motors direction control masks
#define dcm_x_fwd (FORCE_BITS(dcmPort, (dcm_x_dir_fwd | dcm_x_dir_rev), dcm_x_dir_fwd))
#define dcm_x_rev (FORCE_BITS(dcmPort, (dcm_x_dir_fwd | dcm_x_dir_rev), dcm_x_dir_rev))
#define dcm_x_brk CLEAR_BITS(dcmPort, (dcm_x_dir_fwd | dcm_x_dir_rev))

// DC Motor PWM signal control
#define MODE_8BIT 0x00		//8-bit mode for all PWM channels
#define NO_PRESCALE 0x00	//Don't prescale, count E-clocks directly for A and B
#define HALF_PRESCALE 0x01	//PWM Clock = 1/2 E-Clock
#define CLKSA_SCALE 0x01	//Makes clock SA = 1/2 Clock A
#define PWMPER 100u			//PWM period = 100 for easy control of PWM duty from 0-100%
#define PWM_LIMIT_MAX 100 	//255
#define PWM_LIMIT_MIN 0

// DC Motor PWM Macros
#define dcmPWM_CENTRE_ALIGNED SET_BITS(PWMCAE, (PWMCAE_CAE4_MASK | PWMCAE_CAE5_MASK))	// Use centre aligned for DC motor PWM signal
#define dcmPWM_LEFT_ALIGNED CLEAR_BITS(PWMCAE, (PWMCAE_CAE4_MASK | PWMCAE_CAE5_MASK))	// Use left aligned for DC motor PWM signal
#define dcmPWM_CLK_A CLEAR_BITS(PWMCLK, (PWMCLK_PCLK4_MASK | PWMCLK_PCLK5_MASK))		// Use Clock A as source for DC motor PWM signals
#define dcmPWM_CLK_SA SET_BITS(PWMCLK, (PWMCLK_PCLK4_MASK | PWMCLK_PCLK5_MASK))			// Use Clock SA as source for DC motor PWM signals
#define dcmPWM_ACTIVE_LOW CLEAR_BITS(PWMPOL, (PWMPOL_PPOL4_MASK | PWMPOL_PPOL5_MASK))	// Active low output for DC motor PWM signals
#define dcmPWM_ACTIVE_HIGH SET_BITS(PWMPOL, (PWMPOL_PPOL4_MASK | PWMPOL_PPOL5_MASK))	// Active high  output for DC motor PWM signals
#define dcmPWM_SET_PERIOD_X PWMPER4 = PWMPER					// Set period = PWMPER for DC motor PWM signals
#define dcmPWM_SET_DUTY_X(dty) PWMDTY4 = dty 					// Set duty cycle for X-Axis motor
#define dcmPWM_CLR_CNT_X PWMCNT4 = 0							// Reset counter for X-Axis motor

#define dcmPWM_ENABLE_X SET_BITS(PWME, PWME_PWME4_MASK)		// Enable X-Axis PWM channel
#define dcmPWM_DISABLE_X CLEAR_BITS(PWME, PWME_PWME4_MASK)	// Disable X-Axis PWM channel

// Encoder Port, DDR, Masks, conversion factors
#define encPort PTT
#define encDDR DDRT
#define enc_x_mask 0b00000001
#define ENC_TICKS_PER_REV 374		// One RPM at output shaft = 374 encoder ticks
#define DCM_X_PITCH_DIAMETER_UM 191	// X-Axis drive pulley pitch diameter in micrometres

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
	unsigned long dcm_period_tcnt_ticks;		// Encoder period in TCNT ticks
} dcm_t;

// Function prototypes
void dcm_configure(void);
void dcm_position_ctrl_x(void);
void dcm_safety_limit_x(void);