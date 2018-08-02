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
    PVector new_direction = new PVector(0, 0);
    float vel_magnitude = 0;
    
    // Check for collision with human paddle
    distance_to_paddle = sqrt(pow(pos.x - human_paddle.pos.x, 2) + pow(pos.y - human_paddle.pos.y, 2));
    if (distance_to_paddle <= ((puck_diameter/2) + (paddle_diameter/2))) {
      // determine new direction vector based on line drawn between centre of paddle and puck
      new_direction.x = pos.x - human_paddle.pos.x;
      new_direction.y = pos.y - human_paddle.pos.y;
      new_direction.normalize();
      
      // determine magnitude of new velocity
      vel_magnitude = max(sqrt(pow(human_paddle.vel.x, 2) + pow(human_paddle.vel.y, 2)), sqrt(pow(vel.x, 2) + pow(vel.y, 2)));
      
      // scale new direction to create new puck velocity
      vel.x = new_direction.x * vel_magnitude;
      vel.y = new_direction.y * vel_magnitude;
    }

    // Check for collision with robot paddle
    distance_to_paddle = sqrt( pow(pos.x - robot_paddle.pos.x, 2) + pow(pos.y - robot_paddle.pos.y, 2));
    if (distance_to_paddle <= ((puck_diameter/2) + (paddle_diameter/2))) {
      // determine new direction vector based on line drawn between centre of paddle and puck
      new_direction.x = pos.x - robot_paddle.pos.x;
      new_direction.y = pos.y - robot_paddle.pos.y;
      new_direction.normalize();
      
      // determine magnitude of new velocity
      vel_magnitude = max(sqrt(pow(robot_paddle.vel.x, 2) + pow(robot_paddle.vel.y, 2)), sqrt(pow(vel.x, 2) + pow(vel.y, 2)));
      
      // scale new direction to create new puck velocity
      vel.x = new_direction.x * vel_magnitude;
      vel.y = new_direction.y * vel_magnitude;
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
