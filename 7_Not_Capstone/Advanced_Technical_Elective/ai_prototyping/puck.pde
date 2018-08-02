int puck_diameter = 80;

class Puck {
  PVector pos;
  PVector vel;
  PVector acc;
  boolean goal_robot;  // True when the robot scores a goal
  boolean goal_human;  // True when the human scores a goal

  Puck() {
    // Start the puck at centre ice
    pos = new PVector(width/2, height/2);
    vel = new PVector(0, 0);
    acc = new PVector(0, 0);
  }  
  
  //-----------------------------------------------------------------------------------------------------------------
  // Draws the puck on the screen
  void show() {
    fill(0, 255, 0);
    ellipse(pos.x, pos.y, puck_diameter, puck_diameter);
  }
  
  //-----------------------------------------------------------------------------------------------------------------
  // Moves the puck
  void move() {
    // Apply the acceleration and move the paddle
    vel.add(acc);
    vel.limit(4);  // Limit to 4m/s
    pos.add(vel);
  }

  //-------------------------------------------------------------------------------------------------------------------
  // Calls the move function and check for collisions and stuff
  void update() {
    float distance_to_paddle = 0;
    
    // Check for collision with paddles, first human then robot
    distance_to_paddle = sqrt(pow(pos.x - human_paddle.pos.x, 2) + pow(pos.y - human_paddle.pos.y, 2));
    if (distance_to_paddle <= ((puck_diameter/2) + (paddle_diameter/2))) {
      // Collision with human paddle
      if (human_paddle.vel.x > 0) {
        vel.x = human_paddle.vel.x;
      } else {
        vel.x = -vel.x;
      }
      if (human_paddle.pos.y < pos.y) {
        if (human_paddle.vel.y > 0) {
          vel.y = human_paddle.vel.y;
        } else {
          vel.y = -vel.y;
        }
      } else {
        if (human_paddle.vel.y < 0) {
          vel.y = human_paddle.vel.y;
        } else {
          vel.y = -vel.y;
        }
      }
    }
    distance_to_paddle = sqrt( pow(pos.x - robot_paddle.pos.x, 2) + pow(pos.y - robot_paddle.pos.y, 2));
    if (distance_to_paddle <= ((puck_diameter/2) + (paddle_diameter/2))) {
      // Collision with robot paddle
      if (robot_paddle.vel.x > 0) {
        vel.x = robot_paddle.vel.x;
      } else {
        vel.x = -vel.x;
      }
      if (robot_paddle.pos.y > pos.y) {
        if (robot_paddle.vel.y < 0) {
          vel.y = robot_paddle.vel.y;
        } else {
          vel.y = -vel.y;
        }
      } else {
        if (robot_paddle.vel.y > 0) {
          vel.y = human_paddle.vel.y;
        } else {
          vel.y = -vel.y;
        }
      }
    }
      
    // Move puck to new position and handle bounces
    move();  
    if (pos.x < (puck_diameter/2)) {
      pos.x = puck_diameter/2;
      vel.x = -vel.x;
    }
    if (pos.x > width - (puck_diameter/2)) {
      pos.x = width - (puck_diameter/2);
      vel.x = -vel.x;
    }
    if (pos.y < (puck_diameter/2)) {
      pos.y = (puck_diameter/2);
      vel.y = -vel.y;
    }
    if (pos.y > height - (puck_diameter/2)) {
      pos.y = height - (puck_diameter/2);
      vel.y = -vel.y;
    }
    
    // Check for goals scored
    if ((((width/2) - (goal_width_x/2)) < pos.x) && (pos.x < ((width/2) - (goal_width_x/2) + goal_width_x))) {
      // X position is close to goal
      if (pos.y == (height - (puck_diameter/2))) {
        goal_human = true;
      } else if (pos.y == (goal_height_y - (puck_diameter/2))) {
        goal_robot = true;
      } else {
        goal_human = false;
        goal_robot = false;
      }
    }
  }
}
