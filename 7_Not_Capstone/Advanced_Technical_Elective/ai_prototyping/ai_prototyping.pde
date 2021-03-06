// All dimensions in millimetres to match real table
Puck puck;
Paddle human_paddle;
Paddle robot_paddle;
Human human_player;
Brain[] brains;
int number_brains = 5;
int current_brain = 0;
int generation = 1;
int max_game_time_ms = 10000;
int goal_width_x = 200;
int goal_height_y = 10;
PVector pos_old;

//-----------------------------------------------------------------------------------------------------------------
// Gets called at the very beginning of the program
void setup()
{
  size(775, 1000);  // size of the window
  frameRate(10000);  // Run as fast as the CPU will handle
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
  int number_of_mutations = 1;
  int similar_brains = 0;
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
      // Calculate the "loser fitness" i.e. how long did it last and how high was its average speed
      brains[i].loser_fitness = (brains[i].time_count_ms * 10) + brains[i].average_dist_to_puck;
      
      // Calculate the "winner fitness" i.e. how long did it take to win
      brains[i].winner_fitness = ((max_game_time_ms - brains[i].time_count_ms) * 10);
      
      // First priority: brains that win (higher fitness score is better)
      if (brains[best_brain].robot_victory) {
        if (brains[i].robot_victory) {
          if (brains[i].winner_fitness > brains[best_brain].winner_fitness) {
            best_brain = i;        
          }
        }
      } else {
        // Second priority: Brains that last the longest and have highest average speed (higher fitness score is better)
        if (brains[i].loser_fitness > brains[best_brain].loser_fitness) {
          best_brain = i;
        }
      }
    }
    
    // Make sure all the brains aren't the same
    if (!brains[best_brain].robot_victory) {
      for (int i=0; i < (number_brains-1); i++) {
        if (brains[i].loser_fitness == brains[i+1].loser_fitness) {
          similar_brains++;
        }
      }
    }
    if (similar_brains >= (number_brains-1)) {
      println("All brains are the same, big mutation");
      best_brain = int(random(0, number_brains-1));
      number_of_mutations = 2;
    }
    
    // Copy the best brain and mutate each child
    brains[best_brain].redirections = 0;
    brains[best_brain].average_speed = 0;
    brains[best_brain].average_dist_to_puck = 0;
    best_brain_copy = brains[best_brain].copy();
    for (int i=1; i < number_brains; i++) {
      brains[i].log(i);
      brains[i] = best_brain_copy.copy();
      brains[i].mutate(number_of_mutations);
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
  PVector dist_to_puck = new PVector(0, 0);
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
  puck.update(brains[brain]);
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
    println(brains[brain].average_speed);
    println(brains[brain].redirections);
    println(brains[brain].average_dist_to_puck);
    return;
  }
  if (puck.goal_human) {
    print("Brain: ");
    println(brain);
    println("Human wins");
    println(brains[brain].time_count_ms);
    println(brains[brain].average_speed);
    println(brains[brain].redirections);
    println(brains[brain].average_dist_to_puck);
    return;
  }
  
  if (brains[brain].time_count_ms >= max_game_time_ms) {
    // Robot can't take forever to win or lose
    print("Brain: ");
    println(brain);
    println("Robot took too long");
    println(brains[brain].average_speed);
    println(brains[brain].redirections);
    println(brains[brain].average_dist_to_puck);
    puck.goal_human = true;
    return;
  }

  brains[brain].average_speed += abs(robot_paddle.pos.x - pos_old.x) + abs(robot_paddle.pos.y - pos_old.y);
  if (puck.pos.y > height/2) {
    // Determine how close the paddle is to the puck (reverse logic, higher is better)
    dist_to_puck.x = robot_paddle.pos.x - puck.pos.x;
    dist_to_puck.y = robot_paddle.pos.y - puck.pos.y;
    brains[brain].average_dist_to_puck += (height/2) - (dist_to_puck.mag());
  }  
  
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
