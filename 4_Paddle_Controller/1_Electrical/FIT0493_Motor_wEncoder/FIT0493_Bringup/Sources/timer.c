#include <hidef.h>      /* common defines and macros */
#include "derivative.h"      /* derivative-specific definitions */
#include "TA_Header_W2016.h"  /* my macros and constants */
#include "timer.h"  // Macros and constants for timer3handler.
#include "lcd.h"

//;**************************************************************
//;*                 timer_configure(void)
//;*  Configures the timer module with parameters for PWM operation
//;**************************************************************   
void timer_configure(void) {
    TSCR1 = TSCR1_INIT; // Turn on timer module and enable fast-clear and freeze in debug
    TSCR2 = TSCR2_INIT; // Set pre-scaler to 4 for finest resolution @50Hz PWM frequency
}

// Interrupt handler for encoder IC in dcm.c
// Interrupt handler for timer overflow in dcm.c

//;**************************************************************
//;*                 timer_configure_1kHz()
//;*  Set up Timer Channel 6 to act as a clock that will cause
//;*  an interrupt at 1kHz
//;**************************************************************
void timer_configure_1kHz(void) {
    TIOS |= TIOS_IOS6_MASK;       // Enable TC6 as OC for motor control loop
    SET_OC_ACTION(6,OC_OFF);      // Set TC6 to not touch the port pin
    TC6 = TCNT + TCNT_mS;         // Delay 1mS
    TIE |= TIOS_IOS6_MASK;        // Enable interrupts on timer channel 5
}

// Interrupt handler for 1kHz loop in dcm.c

//;**************************************************************
//;*                 timer_delay_ms(time)
//;*  Delay program execution by time mS (busy wait)
//;*  Delays on TC7
//;**************************************************************
void timer_delay_ms(unsigned char time) {
    // 1 TCNT tick = 0.5uS so 2000 TCNT ticks = 1mS
    volatile unsigned char count;

    SET_OC_ACTION(7,OC_OFF);     // Set TC7 to not touch the port pin
    TC7 = TCNT + TCNT_mS; // Set first OC event timer (for 1mS)
    TIOS |= TIOS_IOS7_MASK; // Enable TC1 as OC

    for(count = 0; count < time; count ++)
    {
        while(!(TFLG1 & TFLG1_C7F_MASK)); // Wait for the OC event
        TC7 += TCNT_mS;
    }

    TIOS &= LOW(~TIOS_IOS7_MASK);  // Turn off OC on TC1
}

//;**************************************************************
//;*                 timer_delay_us(time)
//;*  Delay program execution by time uS (busy wait)
//;*  Delays on TC7
//;**************************************************************
void timer_delay_us(unsigned char time) {
    // 1 TCNT tick = 0.5uS so 2 TCNT ticks = 1uS
    volatile unsigned char count;

    SET_OC_ACTION(7,OC_OFF);     // Set TC7 to not touch the port pin
    TC7 = TCNT + TCNT_uS; // Set first OC event timer (for 1mS)
    TIOS |= TIOS_IOS7_MASK; // Enable TC7 as OC

    for(count = 0; count < time; count ++)
    {
        while(!(TFLG1 & TFLG1_C7F_MASK)); // Wait for the OC event
        TC7 += TCNT_uS;
    }

    TIOS &= LOW(~TIOS_IOS7_MASK);  // Turn off OC on TC7
}