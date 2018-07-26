#include <hidef.h>      /* common defines and macros */
#include "derivative.h"      /* derivative-specific definitions */
#include "TA_Header_W2016.h"  /* my macros and constants */
#include "timer.h"  // Macros and constants for timer3handler.
#include "ir.h"

static unsigned char timer_tcnt_overflow = 0;

//;**************************************************************
//;*                 timer_configure(void)
//;*    Configures the timer module with parameters for PWM operation
//;*    Sets up channel 6 for a 10kHz interrupt timer
//;**************************************************************   
void timer_configure(void) {
    TSCR1 = TSCR1_INIT; // Turn on timer module and enable fast-clear and freeze in debug
    TSCR2 = TSCR2_INIT; // Set pre-scaler to 4 for finest resolution @50Hz PWM frequency

    // Use TC6 as 10kHz interrupt timer
    TIOS |= TIOS_IOS6_MASK;
    SET_OC_ACTION(6, OC_OFF);
    TC6 = TCNT + (TCNT_uS * 100);
    TIE |= TIOS_IOS6_MASK;
}

interrupt 14 void timer_10kHz(void)
{
    ir_10kHz_task();
    TC6 = TCNT + (TCNT_uS * 100);
}

//;**************************************************************
//;*                 timer_delay_ms(time)
//;*    Delay program execution by time mS (busy wait)
//;*    Delays on TC7
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
//;*    Delay program execution by time uS (busy wait)
//;*    Delays on TC7
//;**************************************************************
void timer_delay_us(unsigned char time) {
    // 1 TCNT tick = 0.5uS so 2000 TCNT ticks = 1mS
    volatile unsigned char count;

    SET_OC_ACTION(7,OC_OFF);     // Set TC7 to not touch the port pin
    TC7 = TCNT + TCNT_uS; // Set first OC event timer (for 1mS)
    TIOS |= TIOS_IOS7_MASK; // Enable TC1 as OC

    for(count = 0; count < time; count ++)
    {
        while(!(TFLG1 & TFLG1_C7F_MASK)); // Wait for the OC event
        TC7 += TCNT_uS;
    }

    TIOS &= LOW(~TIOS_IOS7_MASK);  // Turn off OC on TC1
}

//;**************************************************************
//;*                 timer_delay_100us(time)
//;*    Delay program execution by time uS (busy wait)
//;*    Delays on TC7
//;**************************************************************
void timer_delay_100us(unsigned char time) {
    // 1 TCNT tick = 0.5uS so 2 TCNT ticks = 1uS
    volatile unsigned char count;

    SET_OC_ACTION(7,OC_OFF);     // Set TC7 to not touch the port pin
    TC7 = TCNT + 200; // Set first OC event timer (for 1mS)
    TIOS |= TIOS_IOS7_MASK; // Enable TC1 as OC

    for(count = 0; count < time; count ++)
    {
        while(!(TFLG1 & TFLG1_C7F_MASK)); // Wait for the OC event
        TC7 += 200;
    }

    TIOS &= LOW(~TIOS_IOS7_MASK);  // Turn off OC on TC1
}

//;**************************************************************
//;*                 timer_tcnt_overflow_handler()
//;*    Increments global variable to track timer overflow events
//;**************************************************************
interrupt 16 void timer_tcnt_overflow_handler(void)
{
    timer_tcnt_overflow ++; //Increment the overflow counter
    (void)TCNT;   //To clear the interrupt flag with fast-clear enabled.
}

//;**************************************************************
//;*                 timer_get_overflow()
//;*    Returns current value of the TCNT overflow counter
//;**************************************************************
unsigned char timer_get_overflow(void)
{
    // No critical region - this must only be accessed by an ISR
    return timer_tcnt_overflow;
}