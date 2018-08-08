int paddle_diameter = 100;

class Paddle {
  PVector pos;
  PVector vel;
  PVector acc;
  boolean robot;  // If true this paddle is the robot side

  Paddle(boolean robot_option) {
    pos = new PVector(width/2, height/2);
    vel = new PVector(0, 0);
    acc = new PVector(0, 0);
    
    robot = robot_option;
    if (robot) {
      pos.y = height - (paddle_diameter * 2);
    } else {
      pos.y = paddle_diameter * 2;
    }
  }  
  
  //-----------------------------------------------------------------------------------------------------------------
  // Draws the paddle on the screen
  void show() {
    if (robot) {
      fill(255, 0, 0);
    } else {
      fill(0, 0, 255);
    }
    ellipse(pos.x, pos.y, paddle_diameter, paddle_diameter);
  }
  
  //-----------------------------------------------------------------------------------------------------------------
  // Moves the paddle
  void move() {
    if (robot) {
      acc.limit(0.5);
    } else {
      acc.limit(0.8);  // Artificially make the human faster than the robot
    }
    vel.add(acc);
    vel.limit(2);  // limit to 4m/s
    pos.add(vel);
  }

  //-------------------------------------------------------------------------------------------------------------------
  // Calls the move function and check for collisions and stuff
  void update(PVector pos_command) {
    // Handle position commands
    if (abs(pos_command.x - pos.x) <= 4) {
      vel.x = 0;
    }
    if (abs(pos_command.y - pos.y) <= 4) {
      vel.y = 0;
    }
    
    if (pos_command.x > pos.x) {
      acc.x = 1;
    } else if (pos_command.x < pos.x) {
      acc.x = -1;
    } else {
      acc.x = 0;
      vel.x = 0;
    }
    if (pos_command.y > pos.y) {
      acc.y = 1;
    } else if (pos_command.y < pos.y) {
      acc.y = -1;
    } else {
      acc.y = 0;
      vel.y = 0;
    }
    
    // Move paddle to new position
    move();
    
    // Limit to edges of table
    if (pos.x < (paddle_diameter/2 + puck_diameter)) {
      pos.x = paddle_diameter/2 + puck_diameter;
    }
    if (pos.x > width - (paddle_diameter/2) - puck_diameter) {
      pos.x = width - (paddle_diameter/2) - puck_diameter;
    }
    if (robot) {
      // Robot is on bottom half of table
      if (pos.y > height - (paddle_diameter/2)) {
        pos.y = height - (paddle_diameter/2);
      }
      if (pos.y < (height/2) + (paddle_diameter/2)) {
        pos.y = (height/2) + (paddle_diameter/2);
      }
    } else {
      // Human is on top half
      if (pos.y < (paddle_diameter/2)) {
        pos.y = paddle_diameter/2;
      }
      if (pos.y > (height/2) - (paddle_diameter/2)) {
        pos.y = (height/2) - (paddle_diameter/2);
      }
    }
  }
}
