class Human {
  final static int state_Home = 1;
  final static int state_Attack = 2;
  final static int state_Defend = 3;
  final static int state_Return = 4;
  final static float attack_line_y = 400;
  int state;
  PVector pos_command;
  boolean attack_move_active = false;
  
  Human() {
    state = state_Home;
    pos_command = new PVector(width/2, paddle_diameter * 2);
  }  
  
  //-----------------------------------------------------------------------------------------------------------------
  // Logic for "human player" control
  void update(PVector paddle_pos, PVector puck_pos, PVector puck_vel) {
    float paddle_vel_y_calc = 0;
    float paddle_distance_to_attack_line_y = 0;
    float puck_distance_to_attack_line_y = 0;
    float paddle_time_to_attack_line_y = 0;
    float puck_time_to_attack_line_y = 0;
    String debug_text;
    
    // Logic for 'home' state
    if (state == state_Home) {
      text("state: home", 10, 10);
      pos_command.x = width/2;
      pos_command.y = paddle_diameter/2;

      // Check conditions for state transitions
      if ((puck_pos.y > attack_line_y) && (puck_vel.y < 0)) {
        state = state_Attack;
        return;
      }
      if ((puck_pos.y < attack_line_y) && (puck_vel.y < 0)) {
         state = state_Defend;
         return;
      }
      if ((puck_pos.y < height/2) && (abs(puck_vel.y) < 1)) {
        state = state_Return;
        return;
      }
    }
    
    // Logic for 'attack' state
    if (state == state_Attack) {
      text("state: attack", 10, 10);
      
      if (attack_move_active) {
        pos_command.x = puck_pos.x;
        pos_command.y = attack_line_y;
      } else {
        // Calculate distance and time to attack line for paddle and puck
        paddle_distance_to_attack_line_y = abs(attack_line_y - paddle_pos.y);
        puck_distance_to_attack_line_y = abs(attack_line_y - puck_pos.y);
        debug_text = "puck d: " + puck_distance_to_attack_line_y + "\npaddle d: " + paddle_distance_to_attack_line_y;
        text(debug_text, 10, 30);
        
        // Calculate time to travel to attack line for paddle and puck
        while(paddle_distance_to_attack_line_y > 0) {
          paddle_time_to_attack_line_y ++;
          if (paddle_vel_y_calc < 4) {
            paddle_vel_y_calc ++;
          }
          paddle_distance_to_attack_line_y -= paddle_vel_y_calc;
        }
        while(puck_distance_to_attack_line_y > 0) {
          puck_time_to_attack_line_y ++;
          puck_distance_to_attack_line_y -= abs(puck_vel.y);
        }
        debug_text = "puck t: " + puck_time_to_attack_line_y + "\npaddle t: " + paddle_time_to_attack_line_y;
        text(debug_text, 10, 60);
        
        // Start moving paddle when timing for collision is good
        if (abs(puck_time_to_attack_line_y - paddle_time_to_attack_line_y) <= 1) {
          pos_command.x = puck_pos.x;
          pos_command.y = attack_line_y;
          attack_move_active = true;
        }
      }
      
      if ((puck_vel.y > 0) || (puck_pos.y < attack_line_y)) {
        attack_move_active = false;
        state = state_Home;
        return;
      }
    }
    
    // Logic for 'defend' state
    if (state == state_Defend) {
      text("state: defend", 10, 10);
      pos_command.x = puck_pos.x;
      pos_command.y = paddle_diameter/2;
      
      if (puck_vel.y > 0) {
        state = state_Home;
        return;
      }
    }
    
    // Logic for 'return' state
    if (state == state_Return) {
      text("state: return", 10, 10);
      pos_command.x = puck_pos.x;
      pos_command.y = puck_pos.y;
      
      if (puck_pos.y > height/2) {
        state = state_Home;
        return;
      }
    }
  }
}
