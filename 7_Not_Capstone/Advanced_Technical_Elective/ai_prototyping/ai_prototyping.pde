// All dimensions in millimetres to match real table
Puck puck;
Paddle human_paddle;
Paddle robot_paddle;
Human human_player;
Brain[] brains;
int number_brains = 5;
int current_brain = 0;
int generation = 1;
int max_game_time_ms = 5000;
int goal_width_x = 200;
int goal_height_y = 10;
PVector pos_old;
int max_speed_counter = 0;

//-----------------------------------------------------------------------------------------------------------------
// Gets called at the very beginning of the program
void setup()
{
  size(775, 1000);  // size of the window
  frameRate(1000);  // 1kHz operation
  puck = new Puck();
  puck.vel.x = 1;
  puck.vel.y = 1;
  human_paddle = new Paddle(false);
  human_paddle.robot = false;
  robot_paddle = new Paddle(true);
  robot_paddle.robot = true;
  human_player = new Human();
  brains = new Brain[number_brains];
  pos_old = new PVector(0, 0);
  for (int i=0; i < number_brains; i++) {
      brains[i] = new Brain();
  }
  println("Game started");
}

//-----------------------------------------------------------------------------------------------------------------
// Gets called at whatever the framerate is
void draw()
{
  int best_brain = 0;
  Brain best_brain_copy = new Brain();
  
  // Let the brains play
  play(current_brain);
  if (puck.goal_robot) {
    brains[current_brain].robot_victory = true;
    reset();
  } else if (puck.goal_human) {
    brains[current_brain].robot_victory = false;
    reset();
  }
  
  // Check if the generation is complete
  if (current_brain >= number_brains) {
    print("generation ");
    print(generation);
    println(" complete");
    
    // Pick the best brain
    for (int i=0; i < number_brains; i++) {
      print("avg speed: ");
      println(brains[i].average_speed);
      
      // First priority: brains that win
      if (brains[best_brain].robot_victory) {
        if (brains[i].robot_victory) {
          // Who won the fastest?
          if (brains[i].time_count_ms < brains[best_brain].time_count_ms) {
            best_brain = i;        
          }
        }
      } else {
        // Second priority: Brains that last the longest
        if (brains[i].time_count_ms > brains[best_brain].time_count_ms) {
          best_brain = i;
        }
      }
    }
    
    // Ensure best brain isn't just sitting still forever and not winning
    if ((brains[best_brain].robot_victory == false) && (abs(brains[best_brain].time_count_ms - max_game_time_ms) < 10)) {
      // Just select the brain with the highest average speed to encourage movement 
      max_speed_counter = 0;
      best_brain = 0;
      for (int i=0; i < number_brains; i++) {
        if (brains[i].average_speed > brains[best_brain].average_speed) {
          best_brain = i;
        } else if (brains[i].average_speed == brains[best_brain].average_speed) {
          max_speed_counter ++;
        }
      }
      if (max_speed_counter >= number_brains) {
        best_brain = 0;
        brains[0] = new Brain();
      }
    }
    
    // Copy the best brain and mutate each child
    best_brain_copy = brains[best_brain].copy();
    for (int i=1; i < number_brains; i++) {
      brains[i] = best_brain_copy.copy();
      brains[i].mutate();
    }
    brains[0] = best_brain_copy;  // Keep one unmutated copy
    print("best brain: ");
    println(best_brain);
    generation ++;
    reset();
    current_brain = 0;
  }
}

//-----------------------------------------------------------------------------------------------------------------
// Logic to play a game of air hockey with visualization
void play(int brain)
{
  String info_text;
  info_text = "generation: " + generation + "\nbrain: " + brain + "\ntime: " + (brains[brain].time_count_ms);
  
  background(255);
  text(info_text, width - 100, 60);

  //draw goals
  fill(0, 0, 255);
  rect((width/2) - (goal_width_x/2), (height - goal_height_y), goal_width_x, goal_height_y);  // Robot goal
  rect((width/2) - (goal_width_x/2), 0, goal_width_x, goal_height_y);  // Human goal
  
  // draw puck and paddles
  brains[brain].update();
  puck.update();
  puck.show();
  human_player.update(human_paddle.pos, puck.pos, puck.vel);
  human_paddle.update(human_player.pos_command);
  human_paddle.show();
  robot_paddle.update(brains[brain].output_command);
  robot_paddle.show(); 
  
  // End the game if a goal is scored
  if (puck.goal_robot) {
    print("Brain: ");
    println(brain);
    println("Robot wins");
    println(brains[brain].time_count_ms);
    return;
  }
  if (puck.goal_human) {
    print("Brain: ");
    println(brain);
    println("Human wins");
    println(brains[brain].time_count_ms);
    return;
  }
  
  if (brains[brain].time_count_ms >= max_game_time_ms) {
    // Robot can't take forever to win or lose
    print("Brain: ");
    println(brain);
    println("Robot took too long");
    puck.goal_human = true;
    return;
  }

  brains[brain].average_speed += abs(robot_paddle.pos.x - pos_old.x) + abs(robot_paddle.pos.y - pos_old.y);
  pos_old.x = robot_paddle.pos.x;
  pos_old.y = robot_paddle.pos.y;
}

void reset()
{
  current_brain ++;
  puck = new Puck();
  puck.vel.x = 1;
  puck.vel.y = 1;
  robot_paddle.pos.x = width/2;
  robot_paddle.pos.y = height - (paddle_diameter * 2);
  robot_paddle.vel.x = 0;
  robot_paddle.vel.y = 0;
  pos_old.x = 0;
  pos_old.y = 0;
}
