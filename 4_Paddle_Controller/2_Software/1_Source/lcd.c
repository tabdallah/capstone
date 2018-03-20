#include <hidef.h>      /* common defines and macros */
#include <stdio.h>
#include "derivative.h"      /* derivative-specific definitions */
#include "TA_Header_W2016.h"  /* my macros and constants */
#include "lcd.h"
#include "timer.h"

//;**************************************************************
//;*                 lcd_configure()
//;*  Configures the LCD module with parameters from lcd.h
//;**************************************************************   
void lcd_configure(void) {
	// Configure LCD Port as outputs
	LCD_PORT_DDR = 0xFF;	// FF for all pins as outputs

	// Below code copied directly from Bills slides.
	// run through sync sequence from datasheet to start 4-bit interface    
    LCD_E_HI;
    LCD_BUS( 0x03 );      // wake up display & sync
    LCD_E_LO;
    
    timer_delay_ms( 5 );

    LCD_E_HI;
    LCD_BUS( 0x03 );      // wake up display & sync
    LCD_E_LO;

    timer_delay_ms( 1 );   
    
    LCD_E_HI;
    LCD_BUS( 0x03 );      // wake up display & sync
    LCD_E_LO;
    
    LCD_E_HI;
    LCD_BUS( 0x02 );      // wake up display & sync - go to 4-bit mode
    LCD_E_LO;

	timer_delay_ms( 2 );

	// now that we're sync'd and in 4-bit mode, issue commands to configure the display
    lcd_cmd( LCD_CMD_FUNCTION | LCD_FUNCTION_4BIT | LCD_FUNCTION_2LINES | LCD_FUNCTION_5X8FONT );
    lcd_cmd( LCD_CMD_DISPLAY | LCD_DISPLAY_OFF );
    lcd_cmd( LCD_CMD_CLEAR );
    lcd_cmd( LCD_CMD_ENTRY | LCD_ENTRY_MOVE_CURSOR | LCD_ENTRY_INC );
    lcd_cmd( LCD_CMD_DISPLAY | LCD_DISPLAY_ON | LCD_DISPLAY_NOCURSOR | LCD_DISPLAY_NOBLINK );
}//end of lcd_configure()


//;**************************************************************
//;*                 lcd_data(cx)
//;*  Writes 8 bits of data to the LCD
//;**************************************************************   
void lcd_data(unsigned char cx) {
	LCD_E_LO;
	SET_BITS(LCD_PORT, LCD_RS_BIT);		// Set RS high for data
	CLEAR_BITS(LCD_PORT, LCD_RW_BIT);	// Write mode
	LCD_E_HI;
	LCD_BUS(HI_NYBBLE(cx));
	LCD_E_LO;
	LCD_E_HI;
	LCD_BUS(LO_NYBBLE(cx));
	LCD_E_LO;
	timer_delay_ms(2);
}//end of lcd_data()

//;**************************************************************
//;*                 lcd_cmd(cx)
//;*  Writes an 8-bit command to the LCD
//;**************************************************************   
void lcd_cmd(unsigned char cx) {
	LCD_E_LO;
	CLEAR_BITS(LCD_PORT, LCD_RS_BIT);	// Clear RS for command
	CLEAR_BITS(LCD_PORT, LCD_RW_BIT);	// Write mode
	LCD_E_HI;
	LCD_BUS(HI_NYBBLE(cx));
	LCD_E_LO;
	LCD_E_HI;
	LCD_BUS(LO_NYBBLE(cx));
	LCD_E_LO;
	timer_delay_ms(2);
}//end of lcd_cmd()

//;**************************************************************
//;*                 lcd_puts()
//;*  Writes a string to the LCD
//;*  Input: char *str = string to write
//;************************************************************** 
void lcd_puts(unsigned char *str) {
	lcd_cmd(LCD_CMD_CLEAR);
	timer_delay_ms(2);
	while(*str)
		if(*str == '\n') {	// Handle linefeed characters.
			lcd_cmd(LCD_CMD_SET_DDRAM | LCD_SET_LINE2);
			str++;
		}
		else {
			lcd_data( *str++ );
		}
}//end of lcd_puts()

//;**************************************************************
//;*                 lcd_printf()
//;*  Writes a formatted string to the LCD
//;*  Input: char *format = formatted string to write
//;*	Other input parameters for each formatted item as with printf
//;************************************************************** 
void lcd_printf(char* format, ...) {
	va_list myArgs;
	char buffer[LCD_MAX_BUF_SIZE];
	va_start(myArgs, format);
	(void)vsprintf(buffer, format, myArgs);
	va_end(myArgs);
	lcd_puts((unsigned char*)buffer);
}//end of lcd_printf()