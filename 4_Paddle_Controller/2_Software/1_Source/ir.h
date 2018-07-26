//;******************************************************************************
//; ir.h - Code to interface with the infrared sensors, also handles goal light logic
//; Name: Thomas Abdallah
//; Date: 2018-07-25
//;******************************************************************************
#include "TA_Header_W2016.h"  /* my macros and constants */

#ifndef IR_H
#define IR_H

// IR sensor macros
#define IR_FILTER_KERNEL_SIZE 10
#define IR_FILTER_THRESHOLD 3
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

#define GOAL_LIGHT_DDR DDRB
#define GOAL_LIGHT_PORT PORTB
#define GOAL_LIGHT_HUMAN_PIN 0b00010000
#define GOAL_LIGHT_ROBOT_PIN 0b00001000
#define GOAL_LIGHT_TIMER 3000

// Enumerated data types
typedef enum {
	ir_sensor_blocked = 0,
	ir_sensor_clear = 1
} ir_sensor_e;

typedef enum {
	ir_goal_human = 0,
	ir_goal_robot = 1,
	ir_light_screen_centre_ice = 2
} ir_sensor_name_e;

// Structure definitions
typedef struct ir_sensor_t {
	unsigned int goal_light_timer;
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
ir_sensor_e ir_get_output(ir_sensor_name_e sensor);

#endif