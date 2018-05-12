import Queue
import sys
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.scatter import Scatter
from kivy.properties import NumericProperty, ReferenceListProperty, ObjectProperty
from kivy.vector import Vector
from kivy.clock import Clock
from time import sleep

# globals
tableWidthMm = 660.4
tableHalfLengthMm = 846.1

# classes
class Paddle(Scatter):
    pass

class ManualControlScreen(Widget):
    paddle_object = ObjectProperty(None)
    
    def __init__(self, dataToUI, dataFromUI, **kwargs):
        super(ManualControlScreen, self).__init__(**kwargs)
        self.dataToUI = dataToUI
        self.dataFromUI = dataFromUI
        Clock.schedule_interval(self.update_screen, 0)
        
    def kill_app(self):
        App.get_running_app().stop()
    
    def update_screen(self, *args):
        sleep(0.1)
        paddleCoordinates = self.paddle_object.center
        scalingFactorWidth = tableWidthMm/self.width
        scalingFactorLength = tableHalfLengthMm/self.height
        try:
            self.dataFromUI.put("paddle_position_mm_x:{0:.0f}".format(paddleCoordinates[0]*scalingFactorWidth))
            self.dataFromUI.put("paddle_position_mm_y:{0:.0f}".format(paddleCoordinates[1]*scalingFactorLength))
        except Queue.Full:
            print "Queue Full?"

class user_interface_app(App):
    def __init__(self, ui_rx, ui_tx, **kwargs):
        super(user_interface_app, self).__init__(**kwargs)
        self.ui_rx = ui_rx
        self.ui_tx = ui_tx
    
    def build(self):
        mainWidget = ManualControlScreen(self.ui_rx, self.ui_tx)
        return mainWidget

def ui_process(ui_rx, ui_tx):
    """All things user interface happen here. Communicates directly with master controller"""
    ui_state = "idle" 

    while True:
        # retrieve commands from master controller
        try:
            mc_data = ui_rx.get(False)
            mc_data = mc_data.split(":")
            if mc_data[0] == "ui_state_cmd":
                mc_cmd = mc_data[1]

        except Queue.Empty:
            mc_cmd = "idle"
            
        # set desired state of the user interface to that commanded by mc    
        if mc_cmd == "run_ui":
            ui_desired_state = "run_ui"
        else:
            ui_desired_state = "idle"

        # do the required setup to enter state requested by mc
        if ui_desired_state == "run_ui" and ui_state != "run_ui":
            ui_state = "run_ui"
            ui_desired_state = "idle"
            user_interface_app(ui_rx, ui_tx).run()
            sys.exit(1)