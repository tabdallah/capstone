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

// Function prototypes
void pwm_configure(void);