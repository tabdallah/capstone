#include <hidef.h>      /* common defines and macros */
#include "derivative.h"      /* derivative-specific definitions */
#include "TA_Header_W2016.h"  /* my macros and constants */
#include "dcm.h"
#include "timer.h"
#include "lcd.h"

static dcm_t dcm_x = {0,0,0,0,0,0,0,0,0,0,0,0};
static unsigned char dcm_tcnt_overflow = 0;

//;**************************************************************
//;*                 dcm_configure(void)
//;*  Configures the lower nibble of Port B for Motor Direction Control
//;*  Sets up PWM module for period of 100 and duty cycle of zero  
//;**************************************************************
void dcm_configure(void) {
	lcd_printf("Configuring DC\nMotors.");

	// Configure direction ports for DC Motor H-Bridge
	DCM_DDR |= (DCM_X_DIR_FORWARD | DCM_X_DIR_REVERSE);	// Configure ports as outputs
	DCM_X_BRAKE;
	
	// Configure parameters for all PWM channels
	PWMCTL = DCM_PWM_MODE_8BIT;		// Configure PWM hardware for 8-bit mode
	PWMPRCLK = DCM_PWM_NO_PRESCALE;	// Set PWM Clock A = E-Clock (8MHz)
	PWMSCLA = DCM_PWM_CLKSA_SCALE;	// Set PWM Clock SA = 1/2 Clock A

	// Configure PWM Channel 4 and 5 for Motor A and Motor B respectively
	DCM_PWM_CLK_A;			    // Use clock A for PWM4 and PWM5
	DCM_PWM_ACTIVE_HIGH;		// Use active high output for PWM4 and PWM5
	DCM_PWM_CENTRE_ALIGNED;		// Use centre aligned mode for PWM4 and PWM5
	DCM_PWM_SET_PERIOD_X;		// Set period = 100 for PWM4
	DCM_PWM_SET_DUTY_X(DCM_PWM_MIN);	// Set duty = 0 to start.
	DCM_PWM_CLR_CNT_X;			// Reset counter for PWM4
	DCM_PWM_ENABLE_X;			// Enable the PWM output

  	//Configure IC for encoders
	TIOS &= LOW((~TIOS_IOS0_MASK)); 	// Enable TC0 as IC for X-Axis Encoder B Phase
	TIOS &= LOW((~TIOS_IOS1_MASK)); 	// Enable TC1 as IC for X-Axis Encoder A Phase
	TCTL4 = TCTL4_INIT;					// Capture on rising edges of TC0 and TC1
	TIE = (TIOS_IOS0_MASK | TIOS_IOS1_MASK);	// Enable interrupts for TC0 and TC1
	TFLG1 = (TFLG1_C0F_MASK | TFLG1_C1F_MASK);	// Clear the flag in case anything is pending

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
		DCM_PWM_SET_DUTY_X(DCM_PWM_MIN);
		dcm_x.pwm_duty = DCM_PWM_MIN;
		dcm_x.direction = 0;
		DCM_X_BRAKE;
		return;
	}

	// Drive motor to desired position
	if (dcm_x.position_error_ticks > 0) {
		if (dcm_x.direction < 0) {
			// Stop before changing direction
			DCM_PWM_SET_DUTY_X(DCM_PWM_MIN);
			dcm_x.pwm_duty = DCM_PWM_MIN;
			dcm_x.direction = 0;
			DCM_X_BRAKE;
			return;
		} else {
			DCM_PWM_SET_DUTY_X(DCM_PWM_MAX);
			dcm_x.pwm_duty = DCM_PWM_MAX;
			dcm_x.direction = 1;
			DCM_X_FORWARD;
			return;
		}
	} else {
		if (dcm_x.direction > 0) {
			// Stop before changing direction
			DCM_PWM_SET_DUTY_X(DCM_PWM_MIN);
			dcm_x.pwm_duty = DCM_PWM_MIN;
			dcm_x.direction = 0;
			DCM_X_BRAKE;
			return;
		} else {
			DCM_PWM_SET_DUTY_X(DCM_PWM_MAX);
			dcm_x.pwm_duty = DCM_PWM_MAX;
			dcm_x.direction = -1;
			DCM_X_REVERSE;
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
//;*                 dcm_calculate_speed_x()
//;*  	Calculate linear speed in mm/s
//;**************************************************************
void dcm_calculate_speed_x(void) {
	dcm_x.period_tcnt_ticks = (dcm_x.enc_edge_2_tcnt_ticks
		+ (dcm_x.enc_edge_2_tcnt_overflow * TNCT_OVF_FACTOR))
		- (dcm_x.enc_edge_1_tcnt_ticks
		+ (dcm_x.enc_edge_1_tcnt_overflow * TNCT_OVF_FACTOR));

	//unsigned int distance = DCM_X_DISTANCE_PER_ENC_TICK / 

	//dcm_x.speed_mm_s = 
}

//;**************************************************************
//;*                 dcm_encoder_b_x()
//;*  Handles IC function for X-Axis Encoder B Phase
//;**************************************************************
interrupt 8 void dcm_encoder_b_x(void) {
	static signed char previous_direction = 0;

	if (dcm_x.direction != 0) {
		previous_direction = dcm_x.direction;
	}

	// Track position by encoder ticks
	if (previous_direction > 0) {
		if (dcm_x.position_enc_ticks < MAX_UINT) {
			dcm_x.position_enc_ticks ++;
		}
	} else if (previous_direction < 0) {
		if (dcm_x.position_enc_ticks > 0) {
			dcm_x.position_enc_ticks --;
		}
	} else {
		// ToDo: Error handler, motor moving without applying torque
		// Unable to track position in this state
	}

	// Track speed by timestamps of encoder ticks
	if (dcm_x.enc_edge_tracker == 0) {
		dcm_x.enc_edge_1_tcnt_ticks = DCM_ENCODER_B_TIMER_X;
		dcm_x.enc_edge_1_tcnt_overflow = dcm_tcnt_overflow;
		dcm_x.enc_edge_tracker = 1;
	} else {
		dcm_x.enc_edge_2_tcnt_ticks = DCM_ENCODER_B_TIMER_X;
		dcm_x.enc_edge_2_tcnt_overflow = dcm_tcnt_overflow;
		dcm_x.enc_edge_tracker = 0;
	}
}

//;**************************************************************
//;*                 dcm_encoder_a_x()
//;*  Handles IC function for X-Axis Encoder A Phase
//;**************************************************************
interrupt 9 void dcm_encoder_a_x(void) {
	(void)DCM_ENCODER_A_TIMER_X;
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