//;******************************************************************************
//; pwm.h - PWM module setup
//; Name: Thomas Abdallah
//; Date: 2018-03-19
//;******************************************************************************
#include "TA_Header_W2016.h"  /* my macros and constants */

#define PWM_MODE_8BIT 0x00			//8-bit mode for all PWM channels
#define PWM_NO_PRESCALE 0x00		//Don't prescale, count E-clocks directly for A and B
#define PWM_HALF_PRESCALE 0x01		//PWM Clock = 1/2 E-Clock
#define PWM_CLKSA_SCALE 0x01		//Makes clock SA = 1/2 Clock A

#define PWM_CENTRE_ALIGNED SET_BITS(PWMCAE, (PWMCAE_CAE4_MASK | PWMCAE_CAE5_MASK))	// Use centre aligned for DC motor PWM signal
#define PWM_LEFT_ALIGNED CLEAR_BITS(PWMCAE, (PWMCAE_CAE4_MASK | PWMCAE_CAE5_MASK))	// Use left aligned for DC motor PWM signal
#define PWM_CLK_A CLEAR_BITS(PWMCLK, (PWMCLK_PCLK4_MASK | PWMCLK_PCLK5_MASK))		// Use Clock A as source for DC motor PWM signals
#define PWM_CLK_SA SET_BITS(PWMCLK, (PWMCLK_PCLK4_MASK | PWMCLK_PCLK5_MASK))		// Use Clock SA as source for DC motor PWM signals
#define PWM_ACTIVE_LOW CLEAR_BITS(PWMPOL, (PWMPOL_PPOL4_MASK | PWMPOL_PPOL5_MASK))	// Active low output for DC motor PWM signals
#define PWM_ACTIVE_HIGH SET_BITS(PWMPOL, (PWMPOL_PPOL4_MASK | PWMPOL_PPOL5_MASK))	// Active high  output for DC motor PWM signals\

// Function prototypes
void pwm_configure(void);