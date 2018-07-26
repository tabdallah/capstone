//;******************************************************************************
//; ir.h - Code to interface with the infrared sensors
//; Name: Thomas Abdallah
//; Date: 2018-07-25
//;******************************************************************************
#include "TA_Header_W2016.h"  /* my macros and constants */

#ifndef IR_H
#define IR_H

// IR sensor macros
#define IR_FILTER_KERNEL_SIZE 10
//#define IR_FILTER_THRESHOLD 10
#define IR_DDR DDRA
#define IR_PORT PORTA
#define IR_SENSOR_1_PIN 0b00000001	// PA0
#define IR_SENSOR_1_SHIFT 0
#define IR_SENSOR_2_PIN 0b00000010	// PA1
#define IR_SENSOR_2_SHIFT 1
#define IR_SENSOR_3_PIN 0b00000100	// PA2
#define IR_SENSOR_3_SHIFT 2
#define IR_SENSOR_4_PIN 0b00001000	// PA3
#define IR_SENSOR_4_SHIFT 3
#define IR_SENSOR_5_PIN 0b00010000	// PA4
#define IR_SENSOR_5_SHIFT 4
#define IR_SENSOR_6_PIN 0b00100000	// PA5
#define IR_SENSOR_6_SHIFT 5

// Enumerated data types
typedef enum {
	ir_sensor_clear = 0,
	ir_sensor_blocked = 1
} ir_sensor_e;

// Structure definitions
typedef struct ir_sensor_t {
	unsigned char port_pin;
	unsigned char port_pin_shift;
	unsigned char samples[IR_FILTER_KERNEL_SIZE];
	unsigned char sample_index;
	unsigned char latch_count;
	ir_sensor_e output_raw;
	ir_sensor_e output_filtered;
} ir_sensor_t;

// Function prototypes
void ir_configure(void);
static void ir_sensor_read(ir_sensor_t *ir_sensor);
static void ir_sensor_filter(ir_sensor_t *ir_sensor);
void ir_10kHz_task(void);
void ir_1kHz_task(void);

#endif