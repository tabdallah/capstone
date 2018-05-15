import Queue
import sys
import time
import cv2
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.uix.slider import Slider
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.label import Label
from kivy.graphics import BorderImage
from kivy.properties import ObjectProperty
from kivy.uix.scatter import Scatter
from kivy.graphics.texture import Texture
from time import sleep
from kivy.config import Config

Config.set('graphics','width','1024')
Config.set('graphics','height','600')

images_path = "../../../6_User_Interface/1_Software/2_Images/"
audio_path = "../../../6_User_Interface/1_Software/3_Audio/"

# globals
tableWidthMm = 660.4
tableHalfLengthMm = 846.1

# class definitions
class Paddle(Scatter):
    def __init__(self, **kwargs):
        super(Paddle, self).__init__(**kwargs)
        self.paddle_image = Image(source=(images_path + 'paddle.png'), pos=self.pos)
        self.add_widget(self.paddle_image)

class VisualizationData(Image):
    def __init__(self, **kwargs):
        super(VisualizationData, self).__init__(**kwargs)
        Clock.schedule_interval(self.updateData, 0)

    def updateData(self, *args):
        try:
            frame = self.parent.parent.parent.manager.visualization_data.get(False)
        except Queue.Empty:
            pass
        else:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_flipped = cv2.flip(frame_rgb, 0)
            frame_string = frame_flipped.tostring()
            image_texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='rgb')
            image_texture.blit_buffer(frame_string, colorfmt='rgb', bufferfmt='ubyte')
            self.texture = image_texture


class SettingsScreen(BoxLayout, Screen):
    def __init__(self, **kwargs):
        super(SettingsScreen, self).__init__(**kwargs)
        self.orientation = 'vertical'

        self.returnMenuBtn = Button(text='Home', on_release=self.change,size_hint=(1,0.1))
        self.add_widget(self.returnMenuBtn)        
        self.game_mode = BoxLayout(orientation='horizontal', size_hint=(1,0.1))
        self.game_mode.add_widget(Label(text='Game Difficulty:'))
        self.game_mode.add_widget(ToggleButton(text='Easy',group='game_mode'))
        self.game_mode.add_widget(ToggleButton(text='Medium',group='game_mode',state='down'))
        self.game_mode.add_widget(ToggleButton(text='Hard',group='game_mode'))
        self.add_widget(self.game_mode)
    
    def change(self, *args):
        self.manager.current = 'main'

class IntroScreen(BoxLayout, Screen):
    def __init__(self, **kwargs):
        super(IntroScreen, self).__init__(**kwargs)
        self.add_widget(Image(source=(images_path + 'logo.png'),allow_stretch=True))
        self.sound = SoundLoader.load(audio_path + 'organ.wav')
        if self.sound:
            self.sound.play()
        Clock.schedule_once(self.end_intro, 1)

    def end_intro(self, *args):
        self.manager.current = 'main'

class ManualControl(Widget):
    def __init__(self, **kwargs):
        super(ManualControl, self).__init__(**kwargs)
        self.paddle_object = Paddle(center=self.center)
        self.add_widget(self.paddle_object)

        with self.canvas.before:
            BorderImage(source=(images_path + 'hockeySurface.png'),pos=self.pos,size=self.size)
        #Clock.schedule_interval(self.update_screen, 0)

    def update_screen(self, *args):
        sleep(0.1)
        paddleCoordinates = self.paddle_object.center
        scalingFactorWidth = tableWidthMm/self.width
        scalingFactorLength = tableHalfLengthMm/self.height
        if self.parent.manager.current == 'manual':
            try:
                self.parent.manager.ui_tx.put("paddle_position_mm_x:{0:.0f}".format(paddleCoordinates[0]*scalingFactorWidth))
                self.parent.manager.ui_tx.put("paddle_position_mm_y:{0:.0f}".format(paddleCoordinates[1]*scalingFactorLength))
            except Queue.Full:
              print "Queue Full?"
        else:
            pass

class ManualScreen(BoxLayout, Screen):
    def __init__(self, **kwargs):
        super(ManualScreen, self).__init__(**kwargs)
        paddle_widget = ManualControl()
        self.return_btn = Button(text='Home', on_release=self.change,size_hint=(1,0.1))
        self.add_widget(self.return_btn)  
        self.add_widget(paddle_widget)     

    def change(self, *args):
        self.manager.current = 'main'

class MainScreen(BoxLayout, Screen):
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)

        # scoreboard stuff
        self.scoreboard = BoxLayout(orientation='horizontal',size_hint=(1,0.2),color=(255,0,0))
        self.robot = BoxLayout(orientation='vertical')
        self.game_clock = BoxLayout(orientation='vertical')
        self.human = BoxLayout(orientation='vertical')
        self.scoreboard.add_widget(self.robot)
        self.scoreboard.add_widget(self.game_clock)
        self.scoreboard.add_widget(self.human)
        self.robot.add_widget(Label(name='name',text='roboMan',font_size=20))
        self.robot.add_widget(Label(name='score',text='0',font_size=40))
        self.game_clock.add_widget(Label(name='game_clock',text='00:00',font_size=40))
        self.human.add_widget(Label(name='name',text='someGuy',font_size=20))
        self.human.add_widget(Label(name='score',text='0',font_size=40))
        self.add_widget(self.scoreboard)

        # visualization & menu
        self.visualization_and_menu = BoxLayout(orientation='horizontal',)
        self.visualization = BoxLayout(orientation='vertical')
        self.menu = BoxLayout(orientation='vertical',size_hint=(0.2,1))
        self.visualization_and_menu.add_widget(self.visualization)
        self.visualization_and_menu.add_widget(self.menu)
        self.visualization.add_widget(VisualizationData())
        self.settings_button = Button(text="Settings",on_release=self.go_settings)
        self.menu.add_widget(self.settings_button)
        self.menu.add_widget(Button(text="Manual",on_release=self.go_manual))
        self.menu.add_widget(Button(text="Diagnostics",on_release=self.go_diagnostics))
        self.menu.add_widget(Button(text="Quit",on_release=self.go_quit))
        self.add_widget(self.visualization_and_menu)

    def go_settings(self, *args):
        self.manager.current = 'settings'
        self.manager.ui_tx.put("settingsRequest")

    def go_manual(self, *args):
        self.manager.current = 'manual'
        self.manager.ui_tx.put("manualRequest")

    def go_diagnostics(self, *args):
        self.manager.ui_tx.put("diagnosticsRequest")

    def go_quit(self, *args):
        self.manager.ui_tx.put("quit")
        App.get_running_app().stop()

class ScreenManagement(ScreenManager):
    def __init__(self, ui_rx, ui_tx, visualization_data, **kwargs):
        super(ScreenManagement, self).__init__(**kwargs)
        self.ui_rx = ui_rx
        self.ui_tx = ui_tx
        self.visualization_data = visualization_data
        self.transition = FadeTransition()
        self.add_widget(IntroScreen(name='intro'))
        self.add_widget(MainScreen(name='main',orientation='vertical'))
        self.add_widget(SettingsScreen(name='settings'))
        self.add_widget(ManualScreen(name='manual',orientation='vertical'))

class UserInterfaceApp(App):
    def __init__(self, ui_rx, ui_tx, visualization_data, **kwargs):
        super(UserInterfaceApp, self).__init__(**kwargs)
        self.ui_rx = ui_rx
        self.ui_tx = ui_tx
        self.visualization_data = visualization_data

    def build(self):
        return ScreenManagement(self.ui_rx, self.ui_tx, self.visualization_data, name='manager') #Builder.load_file("user_interface_kivy.kv")

def ui_process(ui_rx, ui_tx, visualization_data):
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
            UserInterfaceApp(ui_rx, ui_tx, visualization_data).run()
            sys.exit(1)