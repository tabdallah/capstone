//;******************************************************************************
//; pwm.c - PWM module setup
//; Name: Thomas Abdallah
//; Date: 2018-03-19
//;******************************************************************************
#include "derivative.h"      /* derivative-specific definitions */
#include "pwm.h"

//;**************************************************************
//;*                 pwm_configure(void)
//;*	Configure the PWM module.
//;**************************************************************
void pwm_configure(void)
{
	PWMCTL = PWM_MODE_8BIT;		// Configure PWM hardware for 8-bit mode
	PWMPRCLK = PWM_NO_PRESCALE;	// Set PWM Clock A = E-Clock (8MHz)
	PWMSCLA = PWM_CLKSA_SCALE;	// Set PWM Clock SA = 1/2 Clock A
}