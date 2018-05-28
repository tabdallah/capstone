# Check for input every 100mS
# Process input if received
# Display elevator status otherwise

import sys
import select
import time
import os

# files monitored for input
read_list = [sys.stdin]

# select() timeout for input in seconds
timeout = 0.1

# global variables
enable = 0
floor = 1

def process_input(linein):
  print "Elevator Command Input"
  global floor
  global enable
  
  floor = input("Enter floor number:")
  enable = input("Enter enable value:")

def update_elevator_status():
  os.system('clear')
  print("Elevator Status")
  print("---------------")
  print "Floor: ", floor
  print "Enable: ", enable
  print " "
  print "Press 'Enter' for debug mode"


# If there is keyboard input, print the menu and process commands
# Otherwise just display elevator status
def main():
  
  # Infinite loop
  while 1:

    # Wait for keyboard input, or do other stuff
    while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
      line = sys.stdin.readline()
      if line:
        process_input(line)
    else:
      update_elevator_status()
      time.sleep(0.1)  

main()