#include <hidef.h>      /* common defines and macros */
#include "derivative.h"      /* derivative-specific definitions */
#include "TA_Header_W2016.h"  /* my macros and constants */
#include "dcm.h"
#include "timer.h"
#include "lcd.h"

static dcm_t dcm_x = {0,0,0,0,0,0,0,0,0,0,0};
static unsigned char dcm_tcnt_overflow = 0;

//;**************************************************************
//;*                 dcm_configure(void)
//;*  Configures the lower nibble of Port B for Motor Direction Control
//;*  Sets up PWM module for period of 100 and duty cycle of zero  
//;**************************************************************
void dcm_configure(void) {
	lcd_printf("Configuring DC\nMotors.");

	// Configure direction ports for DC Motor H-Bridge
	dcmDDR |= (dcm_x_dir_fwd | dcm_x_dir_rev);	// Configure ports as outputs
	dcm_x_brk;
	
	// Configure parameters for all PWM channels
	PWMCTL = MODE_8BIT;		// Configure PWM hardware for 8-bit mode
	PWMPRCLK = NO_PRESCALE;	// Set PWM Clock A = E-Clock (8MHz)
	PWMSCLA = CLKSA_SCALE;	// Set PWM Clock SA = 1/2 Clock A

	// Configure PWM Channel 4 and 5 for Motor A and Motor B respectively
	dcmPWM_CLK_A;			    // Use clock A for PWM4 and PWM5
	dcmPWM_ACTIVE_HIGH;			// Use active high output for PWM4 and PWM5
	dcmPWM_CENTRE_ALIGNED;		// Use centre aligned mode for PWM4 and PWM5
	dcmPWM_SET_PERIOD_X;		// Set period = 100 for PWM4
	dcmPWM_SET_DUTY_X(0);		// Set duty = 0 to start.
	dcmPWM_CLR_CNT_X;			// Reset counter for PWM4
	dcmPWM_ENABLE_X;			// Enable the PWM output

  	//Configure IC for encoders (X-Axis = PT0)
	TIOS &= LOW((~TIOS_IOS0_MASK)); 	// Enable TC0 as IC for X-Axis encoder
	TCTL4 = TCTL4_INIT;					// Capture on rising edges of TC0
	TIE = (TIOS_IOS0_MASK);				// Enable interrupts for TC0
	TFLG1 = (TFLG1_C0F_MASK);			// Clear the flag in case anything is pending

	lcd_printf("DC Motors\nConfigured.");
}

//;**************************************************************
//;*                 dcm_position_ctrl_x()
//;*  Position control loop for X-Axis DC Motor
//;**************************************************************
void dcm_position_ctrl_x(void) {
	dcm_x.position_error_ticks = dcm_x.position_cmd_enc_ticks - dcm_x.position_enc_ticks;
	
	// Stop if at desired position
	if (dcm_x.position_error_ticks == 0) {
		dcmPWM_SET_DUTY_X(PWM_LIMIT_MIN);
		dcm_x.pwm_duty = PWM_LIMIT_MIN;
		dcm_x.direction = 0;
		dcm_x_brk;
		return;
	}

	// Drive motor to desired position
	if (dcm_x.position_error_ticks > 0) {
		if (dcm_x.direction < 0) {
			// Stop before changing direction
			dcmPWM_SET_DUTY_X(PWM_LIMIT_MIN);
			dcm_x.pwm_duty = PWM_LIMIT_MIN;
			dcm_x.direction = 0;
			dcm_x_brk;
			return;
		} else {
			dcmPWM_SET_DUTY_X(PWM_LIMIT_MAX);
			dcm_x.pwm_duty = PWM_LIMIT_MAX;
			dcm_x.direction = 1;
			dcm_x_fwd;
			return;
		}
	} else {
		if (dcm_x.direction > 0) {
			// Stop before changing direction
			dcmPWM_SET_DUTY_X(PWM_LIMIT_MIN);
			dcm_x.pwm_duty = PWM_LIMIT_MIN;
			dcm_x.direction = 0;
			dcm_x_brk;
			return;
		} else {
			dcmPWM_SET_DUTY_X(PWM_LIMIT_MAX);
			dcm_x.pwm_duty = PWM_LIMIT_MAX;
			dcm_x.direction = -1;
			dcm_x_rev;
			return;
		}
	}
}

//;**************************************************************
//;*                 dcm_safety_limit_x()
//;*  	Check that motor speed is within reasonible limits based
//;*	on applied voltage
//;**************************************************************
void dcm_safety_limit_x(void) {


}

//;**************************************************************
//;*                 dcm_enc_x()
//;*  Handles IC function for X-Axis encoder
//;**************************************************************
interrupt 8 void dcm_enc_x(void) {
	// Track position by encoder ticks
	if (dcm_x.direction > 0) {
		if (dcm_x.position_enc_ticks < MAX_UINT) {
			dcm_x.position_enc_ticks ++;
		}
	} else if (dcm_x.direction < 0) {
		if (dcm_x.position_enc_ticks > 0) {
			dcm_x.position_enc_ticks --;
		}
	} else {
		// ToDo: Error handler, motor moving without applying torque
		// Unable to track position in this state
	}

	// Track speed by timestamps of encoder ticks
	if (dcm_x.enc_edge_tracker == 0) {
		dcm_x.enc_edge_1_tcnt_ticks = ENC_X_TIMER;
		dcm_x.enc_edge_1_tcnt_overflow = dcm_tcnt_overflow;
		dcm_x.enc_edge_tracker = 1;
	} else {
		dcm_x.enc_edge_2_tcnt_ticks = ENC_X_TIMER;
		dcm_x.enc_edge_2_tcnt_overflow = dcm_tcnt_overflow;
		dcm_x.enc_edge_tracker = 0;
	}
}

//;**************************************************************
//;*                 dcm_tcnt_overflow_handler()
//;*  Increments global variable to track timer overflow events
//;**************************************************************
interrupt 16 void dcm_tcnt_overflow_handler(void) {
    dcm_tcnt_overflow ++; //Increment the overflow counter
    (void)TCNT;   //To clear the interrupt flag with fast-clear enabled.
}

//;**************************************************************
//;*                 dcm_1kHz_loop()
//;*  1kHz loop triggered by timer channel 6
//;**************************************************************
interrupt 14 void dcm_1kHz_loop(void) {
    dcm_position_ctrl_x();
    TC6 = TCNT + TCNT_mS;   // Delay 1mS
}