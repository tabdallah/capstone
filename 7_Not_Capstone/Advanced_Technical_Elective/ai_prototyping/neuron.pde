class Neuron {
  float upper_limit;
  float lower_limit;
  float[] weights;
  float[] input_data;
  float output;
  int num_inputs;
  
  Neuron(int inputs) {
    upper_limit = 1000;
    lower_limit = -1000;
    num_inputs = inputs;
    weights = new float[num_inputs];
    input_data = new float[num_inputs];
    output = 0;
    
    // Randomize all weights
    for (int i = 0; i < num_inputs; i++) {
      weights[i] = random(-10, 10);
    }
  }
  
  //-----------------------------------------------------------------------------------------------------------------
  // Calculates the output of the neuron
  void update() {
    output = 0;
    for (int i = 0; i < num_inputs; i++) {
      output += (input_data[i] * weights[i]);      
    }
    output = output * upper_limit / sqrt(1 + pow(output, 2));  // Apply sigmoid function x / sqrt(1 + x^2)    
    
    if (output > upper_limit) {
      output = upper_limit;
    } else if (output < lower_limit) {
      output = lower_limit;
    }
  }
  
  //-----------------------------------------------------------------------------------------------------------------
  // Returns an exact duplicates of the brain
  Neuron copy() {
    Neuron foo = new Neuron(num_inputs);
    foo.upper_limit = upper_limit;
    foo.lower_limit = lower_limit;
    foo.weights = weights;
    foo.num_inputs = num_inputs;
    return foo;
  }
}
