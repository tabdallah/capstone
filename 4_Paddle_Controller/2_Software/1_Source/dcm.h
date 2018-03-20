//;******************************************************************************
//; dcm.h - Common code for all DC Motors + Encoders
//; Name: Thomas Abdallah
//; Date: 2018-03-19
//;******************************************************************************

// Enumerated data types
typedef enum {
	dcm_h_bridge_dir_brake = 0,
	dcm_h_bridge_dir_forward = 1,
	dcm_h_bridge_dir_reverse = 2
} dcm_h_bridge_dir_e;

typedef enum {
	dcm_quad_dir_init = 0,
	dcm_quad_dir_forward = 1,
	dcm_quad_dir_reverse = 2
} dcm_quad_dir_e;

typedef enum {
	dcm_quad_phase_a = 0,
	dcm_quad_phase_b = 1
} dcm_quad_phase_e;

// Structure definitions
typedef struct dcm_t {
	unsigned int position_cmd_enc_ticks;		// Commanded linear position
	unsigned int position_enc_ticks;			// Current linear position
	signed int position_error_ticks;			// Difference between current and commanded linear position
	dcm_h_bridge_dir_e h_bridge_direction;			// H-Bridge direction
	dcm_quad_dir_e quadrature_direction;			// Quadrature encoder measured direction
	unsigned char pwm_duty;						// Current PWM duty cycle

	unsigned int enc_a_edge_1_tcnt_ticks;		// Encoder first rising edge TCNT timestamp
	unsigned int enc_a_edge_2_tcnt_ticks;		// Encoder second rising edge TCNT timestamp
	unsigned char enc_a_edge_1_tcnt_overflow;	// Value of TCNT overflow counter at first rising edge
	unsigned char enc_a_edge_2_tcnt_overflow;	// Value of TCNT overflow counter at second rising edge
	unsigned char enc_a_edge_tracker;			// 0 = first rising edge, 1 = second rising edge

	unsigned long period_tcnt_ticks;			// Encoder period in TCNT ticks
	unsigned int speed_mm_s;					// Linear speed in mm/s
} dcm_t;