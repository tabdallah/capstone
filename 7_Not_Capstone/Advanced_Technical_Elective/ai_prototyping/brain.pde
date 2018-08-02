int brain_input_neurons = 9;
int brain_hidden_neurons = 10;
int brain_output_neurons = 2;

class Brain {
  PVector output_command;
  int time_count_ms;      // Keeps track of how long the game went
  boolean robot_victory;  // True if the robot won the game
  float average_speed;
  
  // Input order: puck_pos_x, puck_pos_y, puck_vel_x, puck_vel_y, paddle_pos_x, paddle_pos_y, paddle_vel_x, paddle_vel_y, bias
  Neuron[] input;

  // Hidden layer neurons 1-9 are fed from input layer, 10 is bias
  Neuron[] hidden;

  // Output order: pos_cmd_x, pos_cmd_y
  Neuron[] output;

  Brain() {
    time_count_ms = 0;
    robot_victory = false;
    output_command = new PVector(0, 0);
    average_speed = 0;
    
    // All input layer neurons only have 1 input with no weight
    input = new Neuron[brain_input_neurons];
    for (int i=0; i < brain_input_neurons; i++) {
      input[i] = new Neuron(1);
      input[i].weights[0] = 1;
    }

    // Hidden layer neurons except for bias neuron take input from every input layer neuron
    hidden = new Neuron[brain_hidden_neurons];
    for (int i=0; i < brain_input_neurons; i++) {
      hidden[i] = new Neuron(brain_input_neurons);
    }
    hidden[brain_hidden_neurons-1] = new Neuron(1);  // Bias neuron in hidden layer

    // Output layer neurons take input from every hidden layer neuron
    output = new Neuron[brain_output_neurons];
    for (int i=0; i < brain_output_neurons; i++) {
      output[i] = new Neuron(brain_hidden_neurons);
    }
    output[0].upper_limit = width;
    output[0].lower_limit = 0;
    output[1].lower_limit = height/2;
    output[1].upper_limit = height;
  }
  
  //-----------------------------------------------------------------------------------------------------------------
  // Calculates the output of the neural network
  void update() {
    // Set inputs for input layer
    input[0].input_data[0] = puck.pos.x; 
    input[1].input_data[0] = puck.pos.y;
    input[2].input_data[0] = puck.vel.x; 
    input[3].input_data[0] = puck.vel.y;
    input[4].input_data[0] = robot_paddle.pos.x; 
    input[5].input_data[0] = robot_paddle.pos.y;
    input[6].input_data[0] = robot_paddle.vel.x;
    input[7].input_data[0] = robot_paddle.vel.y;
    input[8].input_data[0] = 1;  // Bias
    
    // Process input layer
    for (int i=0; i < brain_input_neurons; i++) {
      input[i].update();
    }
    
    // Set inputs for hidden layer
    for (int i=0; i < brain_input_neurons; i++) {
      for (int j=0; j < brain_input_neurons; j++) {
        hidden[i].input_data[j] = input[j].output;
      }
    }
    hidden[brain_hidden_neurons-1].input_data[0] = 1;
    
    // Process hidden layer
    for (int i=0; i < brain_hidden_neurons; i++) {
      hidden[i].update();
    }
    
    // Set inputs for output layer
    for (int i=0; i < brain_output_neurons; i++) {
      for (int j=0; j < brain_hidden_neurons; j++) {
        output[i].input_data[j] = hidden[j].output;
      }
    }
    
    // Process output layer
    for (int i=0; i < brain_output_neurons; i++) {
      output[i].update();
    }
    
    // Set output data
    output_command.x = output[0].output;
    output_command.y = output[1].output;
    
    time_count_ms ++;
  }
  
  //-----------------------------------------------------------------------------------------------------------------
  // Randomly selects an input weight to mutate (one in the hidden layer and one in the output layer)
  void mutate(int number_of_mutations) {
    for (int i=0; i < number_of_mutations; i++) {
      int hidden_neuron_to_mutate = int(random(0, brain_input_neurons-1));  // Don't mutate the bias neuron
      int output_neuron_to_mutate = int(random(0, brain_output_neurons-1));
      int hidden_weight_to_mutate = int(random(0, brain_input_neurons-1));
      int output_weight_to_mutate = int(random(0, brain_hidden_neurons-1));
      
      hidden[hidden_neuron_to_mutate].weights[hidden_weight_to_mutate] = random(-10, 10);
      output[output_neuron_to_mutate].weights[output_weight_to_mutate] = random(-10, 10);
    }
  }
  
  //-----------------------------------------------------------------------------------------------------------------
  // Returns an exact duplicates of the brain
  Brain copy() {
    Brain foo = new Brain();
    for (int i=0; i < brain_input_neurons; i++) {
      foo.input[i] = input[i].copy();
    }
    for (int i=0; i < brain_hidden_neurons; i++) {
      foo.hidden[i] = hidden[i].copy();
    }    
    for (int i=0; i < brain_output_neurons; i++) {
      foo.output[i] = output[i].copy();
    }
    return foo;
  }
  
  //-----------------------------------------------------------------------------------------------------------------
  // Records a copy of the brain in the brain_log.csv file  
  void log() {
    Table table = new Table();
    table.addColumn("generation");
    table.addColumn("brain");
    table.addColumn("1");
    
    
  }
}
