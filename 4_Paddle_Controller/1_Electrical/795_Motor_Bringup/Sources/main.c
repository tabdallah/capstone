#include <hidef.h>      /* common defines and macros */
#include "derivative.h"      /* derivative-specific definitions */

void main(void) {
  /* put your own code here */
  
  PWMCTL = 0x00;
  PWMPRCLK = 0x00;        // Clock A & B no prescale (i.e. 8 MHz)
  PWMSCLA = 0x01;         // Clock SA = 1/2 clock A
  PWMCLK |= PWMCLK_PCLK0_MASK;  // Use clock SA for channel 0
  PWMPOL |= PWMPOL_PPOL0_MASK;  // Set active high polarity
  PWMCAE |= PWMCAE_CAE0_MASK;   // Centre aligned
  
  PWMPER0 = 100;
  PWMDTY0 = 50;  
  PWMCNT0 = 0;
  PWME |= PWME_PWME0_MASK;


	EnableInterrupts;


  for(;;) {
    _FEED_COP(); /* feeds the dog */
  } /* loop forever */
  /* please make sure that you never leave main */
}
