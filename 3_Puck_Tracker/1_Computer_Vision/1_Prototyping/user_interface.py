import Queue
import sys
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.scatter import Scatter
from kivy.properties import NumericProperty, ReferenceListProperty, ObjectProperty
from kivy.vector import Vector
from kivy.clock import Clock

# globals
tableWidthMm = 774.7
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
        
    def kill_thing(self):
        sys.exit()
    
    def update_screen(self, *args):
        paddleCoordinates = self.paddle_object.center
        scalingFactorWidth = tableWidthMm/self.width
        scalingFactorLength = tableHalfLengthMm/self.height
        try:
            self.dataFromUI.put("paddle_position_mm_x: {0}".format(paddleCoordinates[0]*scalingFactorWidth))
            self.dataFromUI.put("paddle_position_mm_y: {0}".format(paddleCoordinates[1]*scalingFactorLength))
        except Queue.Full:
            print "Queue Full?"

class UserInterfaceApp(App):
    def __init__(self, dataToUI, dataFromUI, **kwargs):
        super(UserInterfaceApp, self).__init__(**kwargs)
        self.dataToUI = dataToUI
        self.dataFromUI = dataFromUI
    
    def build(self):
        mainWidget = ManualControlScreen(self.dataToUI, self.dataFromUI)
        return mainWidget

def uiProcess(dataToUI, dataFromUI):
    """All things user interface happen here. Communicates directly with master controller"""
    uiState = "Idle" 

    while True:
        # retrieve commands from master controller
        try:
            mcCmd = dataToUI.get(False)
        except Queue.Empty:
            mcCmd = "Idle"
            
        # set state of user interface to that commanded by mc    
        if mcCmd == "RunUI":
            uiDesiredState = "RunUI"
        else:
            uiDesiredState = "Idle"
    
        # do the required setup to enter state requested by mc
        if uiDesiredState == "RunUI" and uiState != "RunUI":
            uiState = "RunUI"
            uiDesiredState = "Idle"
            UserInterfaceApp(dataToUI, dataFromUI).run()
            