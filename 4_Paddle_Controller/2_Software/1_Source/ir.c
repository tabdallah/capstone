//;******************************************************************************
//; ir.c - Code to interface with the infrared sensors, also handles goal light logic
//; Name: Thomas Abdallah
//; Date: 2018-07-25
//;******************************************************************************
#include <stdlib.h>
#include <hidef.h>      /* common defines and macros */
#include "derivative.h"      /* derivative-specific definitions */
#include "ir.h"

// Define IR sensors
static ir_sensor_t ir_sensor_goal_human;

//;**************************************************************
//;*                 ir_configure
//;**************************************************************
void ir_configure(void)
{
	CLEAR_BITS(IR_DDR, IR_SENSOR_1_PIN);
	CLEAR_BITS(IR_DDR, IR_SENSOR_2_PIN);
	CLEAR_BITS(IR_DDR, IR_SENSOR_3_PIN);
	CLEAR_BITS(IR_DDR, IR_SENSOR_4_PIN);
	CLEAR_BITS(IR_DDR, IR_SENSOR_5_PIN);
	CLEAR_BITS(IR_DDR, IR_SENSOR_6_PIN);

	ir_sensor_goal_human.port_pin = IR_SENSOR_2_PIN;
	ir_sensor_goal_human.port_pin_shift = IR_SENSOR_2_SHIFT;

	SET_BITS(GOAL_LIGHT_DDR, GOAL_LIGHT_HUMAN_PIN);
	SET_BITS(GOAL_LIGHT_PORT, GOAL_LIGHT_HUMAN_PIN);
	SET_BITS(GOAL_LIGHT_DDR, GOAL_LIGHT_ROBOT_PIN);
	SET_BITS(GOAL_LIGHT_PORT, GOAL_LIGHT_ROBOT_PIN);
}

//;**************************************************************
//;*                 ir_read
//;**************************************************************
static void ir_sensor_read(ir_sensor_t *ir_sensor)
{
	// Record raw sensor data
	ir_sensor->output_raw = (((IR_PORT & (ir_sensor->port_pin)) >> (ir_sensor->port_pin_shift)) & 0x0001);
	ir_sensor->samples[ir_sensor->sample_index] = ir_sensor->output_raw;	
	ir_sensor->sample_index ++;
	if (ir_sensor->sample_index >= IR_FILTER_KERNEL_SIZE) {
		ir_sensor->sample_index = 0;
	}
}

//;**************************************************************
//;*                 ir_sensor_filter
//;**************************************************************
static void ir_sensor_filter(ir_sensor_t *ir_sensor)
{
	unsigned char sample_count = 0;
	unsigned char i;

	// Only activate output if # of consecutive samples are all blocked
	for (i=0; i<IR_FILTER_KERNEL_SIZE; i++) {
		if (ir_sensor->samples[i] == ir_sensor_blocked) {
			sample_count ++;
		}
	}
	if (sample_count >= IR_FILTER_THRESHOLD) {
		ir_sensor->goal_light_timer = GOAL_LIGHT_TIMER;
		ir_sensor->output_filtered = ir_sensor_blocked;
		ir_sensor->latch_count = 250;
	} else {
		if (ir_sensor->latch_count > 0) {
			ir_sensor->output_filtered = ir_sensor_blocked;
			ir_sensor->latch_count --;
		} else {
			ir_sensor->output_filtered = ir_sensor_clear;
		}
		if (ir_sensor->goal_light_timer > 0) {
			ir_sensor->goal_light_timer --;
		}
	}	
}

//;**************************************************************
//;*                 ir_10kHz_task
//;**************************************************************
void ir_10kHz_task(void)
{
	ir_sensor_read(&ir_sensor_goal_human);
}

//;**************************************************************
//;*                 ir_1kHz_task
//;**************************************************************
void ir_1kHz_task(void)
{
	ir_sensor_filter(&ir_sensor_goal_human);
	if (ir_sensor_goal_human.goal_light_timer > 0) {
		CLEAR_BITS(GOAL_LIGHT_PORT, GOAL_LIGHT_HUMAN_PIN);
	} else {
		SET_BITS(GOAL_LIGHT_PORT, GOAL_LIGHT_HUMAN_PIN);
	}
}

//;**************************************************************
//;*                 ir_get_output
//;**************************************************************
ir_sensor_e ir_get_output(ir_sensor_name_e sensor)
{
	ir_sensor_e output;

	switch (sensor)
	{
		case ir_goal_human:
			output = ir_sensor_goal_human.output_filtered;
			break;
		default:
			output = ir_sensor_clear;
	}

	return output;
}