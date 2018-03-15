#include <hidef.h>      /* common defines and macros */
#include "derivative.h"      /* derivative-specific definitions */
#include "TA_Header_W2016.h"
#include "timer.h"
#include "lcd.h"
#include "dcm.h"

void main(void) {

    /* put your own code here */
    CONFIGURE_5VA;
    ENABLE_5VA;
    CONFIGURE_LEDS;
    LED1_ON;
    LED2_OFF;
    
    timer_configure();
    lcd_configure();
    dcm_configure();
    timer_configure_1kHz();
    
    lcd_printf("Hello World");

    EnableInterrupts;

    for(;;) {
    }
}
