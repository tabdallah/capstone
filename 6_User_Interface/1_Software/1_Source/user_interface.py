import Queue
import sys
import time
import json
import cv2
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.uix.slider import Slider
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.label import Label
from kivy.graphics import BorderImage, Rectangle, Color
from kivy.properties import ObjectProperty
from kivy.uix.scatter import Scatter
from kivy.graphics.texture import Texture
from time import sleep
from kivy.config import Config
from kivy.uix.popup import Popup

Config.set('graphics','width','1024')
Config.set('graphics','height','600')

images_path = "../../../6_User_Interface/1_Software/2_Images/"
audio_path = "../../../6_User_Interface/1_Software/3_Audio/"
settings_path = "../../../6_User_Interface/1_Software/4_Json/"

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
       
        # game difficulty setting
        self.game_difficulty_layout = BoxLayout(orientation='horizontal')
        self.game_difficulty_layout.add_widget(Label(text='Game Difficulty:'))
        self.easy_button = ToggleButton(text='Easy', group='game_difficulty_group', allow_no_selection=False, on_release=self.change_game_difficulty)
        self.medium_button = ToggleButton(text='Medium', group='game_difficulty_group', allow_no_selection=False, on_release=self.change_game_difficulty)
        self.hard_button = ToggleButton(text='Hard', group='game_difficulty_group', allow_no_selection=False, on_release=self.change_game_difficulty)
        self.game_difficulty_layout.add_widget(self.easy_button)
        self.game_difficulty_layout.add_widget(self.medium_button)
        self.game_difficulty_layout.add_widget(self.hard_button)

        # game length setting
        self.game_length_layout = BoxLayout(orientation='horizontal')
        self.game_length_layout.add_widget(Label(text='Game Length:'))
        self.one_min_button = ToggleButton(text='1:00', value=60, group='game_length_group', allow_no_selection=False, on_release=self.change_game_length)
        self.two_min_button = ToggleButton(text='2:00', value=120, group='game_length_group', allow_no_selection=False, on_release=self.change_game_length)
        self.five_min_button = ToggleButton(text='5:00', value=300, group='game_length_group', allow_no_selection=False, on_release=self.change_game_length)
        self.game_length_layout.add_widget(self.one_min_button)
        self.game_length_layout.add_widget(self.two_min_button)
        self.game_length_layout.add_widget(self.five_min_button)

        self.add_widget(Button(text='Main Menu', on_release=self.go_menu, size_hint=(1,0.2))) 
        self.add_widget(self.game_difficulty_layout)
        self.add_widget(self.game_length_layout)

        # load settings
        with open((settings_path + 'settings.json'), 'r') as fp:
            self.settings = json.load(fp)
            fp.close()

        self.game_difficulty = self.settings['user_interface']['game_difficulty']
        self.game_length = self.settings['user_interface']['game_length']

        if self.game_difficulty == "easy":
            self.easy_button.state = 'down'
        elif self.game_difficulty == "medium":
            self.medium_button.state = 'down'
        elif self.game_difficulty == "hard":
            self.hard_button.state = 'down'

        if self.game_length == 60:
            self.one_min_button.state = 'down'
        elif self.game_length == 120:
            self.two_min_button.state = 'down'
        elif self.game_length == 300:
            self.five_min_button.state = 'down'
    
    def go_menu(self, *args):
        self.manager.current = 'menu'

    def change_game_difficulty(self, *args):
        if self.easy_button.state == 'down':
            self.settings['user_interface']['game_difficulty'] = 'easy'
        elif self.medium_button.state == 'down':
            self.settings['user_interface']['game_difficulty'] = 'medium'
        elif self.hard_button.state == 'down':
            self.settings['user_interface']['game_difficulty'] = 'hard'

    def change_game_length(self, *args):
        if self.one_min_button.state == 'down':
            self.settings['user_interface']['game_length'] = 60
        elif self.two_min_button.state == 'down':
            self.settings['user_interface']['game_length'] = 120
        elif self.five_min_button.state == 'down':
            self.settings['user_interface']['game_length'] = 300

    def on_enter(self):
        with open((settings_path + 'settings.json'), 'r') as fp:
            self.settings = json.load(fp)
            fp.close()

    def on_leave(self):
        with open((settings_path + 'settings.json'), 'w+') as fp:
            json.dump(self.settings, fp, indent=4)
            fp.close()

class IntroScreen(BoxLayout, Screen):
    def __init__(self, **kwargs):
        super(IntroScreen, self).__init__(**kwargs)
        self.add_widget(Image(source=(images_path + 'logo.png'),allow_stretch=True))
        self.sound = SoundLoader.load(audio_path + 'organ.wav')
        if self.sound:
            self.sound.play()
        Clock.schedule_once(self.end_intro, 1)

    def end_intro(self, *args):
        self.manager.get_screen('visual').get_settings()
        self.manager.current = 'menu'

"""class ManualControl(Widget):
    def __init__(self, **kwargs):
        super(ManualControl, self).__init__(**kwargs)
        self.paddle_object = Paddle()
        self.add_widget(self.paddle_object)

        #with self.canvas:
        #    Rectangle(source=(images_path + 'hockeySurface.png'), pos=self.pos, size=self.size)
            #BorderImage(source=(images_path + 'hockeySurface.png'), size_hint=(1,0.9))
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
            pass"""

class ManualScreen(Screen, FloatLayout):
    def __init__(self, **kwargs):
        super(ManualScreen, self).__init__(**kwargs)

        #with self.canvas.before:
        #    Rectangle(source=(images_path + 'hockeySurface.png'), pos=self.pos, size=self.size)

        self.add_widget(Button(text='Main Menu', on_release=self.go_menu))
        
        #self.paddle_object = Paddle(size=(100,100))
        #self.add_widget(self.paddle_object)

    def go_menu(self, *args):
        self.manager.current = 'menu'

class VisualScreen(BoxLayout, Screen):
    def __init__(self, **kwargs):
        super(VisualScreen, self).__init__(**kwargs)

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
        self.clock_label = Label(name='game_clock',text='00:00',font_size=60)
        self.game_clock.add_widget(self.clock_label)
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
        self.start_reset_game_button = Button(text="Start Game", on_release=self.start_reset_game)
        self.pause_resume_game_button = Button(text="Pause Game", on_release=self.pause_resume_game)
        self.menu.add_widget(self.start_reset_game_button)
        self.menu.add_widget(self.pause_resume_game_button)
        self.menu.add_widget(Button(text="Main Menu",on_release=self.go_menu))
        self.add_widget(self.visualization_and_menu)
        self.pause_resume_game_button.disabled = True

    def get_settings(self, *args):
        self.game_length = self.manager.get_screen('settings').game_length
        self.game_difficulty = self.manager.get_screen('settings').game_difficulty
        
        # update 
        mins, secs = divmod(self.game_length, 60)
        self.clock_label.text = '{:02d}:{:02d}'.format(mins,secs)
        self.clock_label.value = self.game_length

    def decrement_clock(self, *args):
        self.clock_label.value -= 1
        mins, secs = divmod(self.clock_label.value, 60)
        timeformat = '{:02d}:{:02d}'.format(mins,secs)
        self.clock_label.text = timeformat

        if self.clock_label.value == 0:
            Clock.unschedule(self.decrement_clock)
            self.pause_resume_game_button.disabled = True

    def start_reset_game(self, *args):
        if self.start_reset_game_button.text == "Start Game":
            Clock.schedule_interval(self.decrement_clock, 1)
            self.pause_resume_game_button.disabled = False
            self.start_reset_game_button.text = "Reset Game"

        elif self.start_reset_game_button.text == "Reset Game":
            mins, secs = divmod(self.game_length, 60)
            self.clock_label.text = '{:02d}:{:02d}'.format(mins,secs)
            self.clock_label.value = self.game_length
            self.pause_resume_game_button.text = "Pause Game"
            self.pause_resume_game_button.disabled = True
            Clock.unschedule(self.decrement_clock)
            self.start_reset_game_button.text = "Start Game"

    def pause_resume_game(self, *args):
        if self.pause_resume_game_button.text == "Pause Game":
            Clock.unschedule(self.decrement_clock)
            self.pause_resume_game_button.text = "Resume Game"

        elif self.pause_resume_game_button.text == "Resume Game":
            Clock.schedule_interval(self.decrement_clock, 1)
            self.pause_resume_game_button.text = "Pause Game"

    def go_menu(self, *args):
        self.manager.current = 'menu'

class MenuScreen(BoxLayout, Screen):
    def __init__(self, **kwargs):
        super(MenuScreen, self).__init__(**kwargs)
        with self.canvas.before:
            Rectangle(source=(images_path + 'menu_background.jpg'), pos=self.pos, size=self.size)
        self.menu_label = Label(name='main_menu', text='Main Menu', size_hint=(1,0.2), font_size=40)
        #with self.menu_label.canvas:
        #    Color(0,1,0,0.5)
        #    Rectangle(pos=self.menu_label.pos, size=self.menu_label.size)
        menu_button_font_size = 30
        menu_button_background_color = (0,0,0,0.6)
        self.add_widget(self.menu_label)
        self.menu_box = BoxLayout(orientation='horizontal')
        self.menu_col_1 = BoxLayout(orientation='vertical')
        self.menu_col_2 = BoxLayout(orientation='vertical')
        self.menu_col_3 = BoxLayout(orientation='vertical')
        self.menu_box.add_widget(self.menu_col_1)
        self.menu_box.add_widget(self.menu_col_2)
        self.menu_box.add_widget(self.menu_col_3)
        self.menu_col_1.add_widget(Button(text="Visual", font_size=menu_button_font_size, background_color=menu_button_background_color, on_release=self.go_visual))
        self.menu_col_1.add_widget(Button(text="Settings", font_size=menu_button_font_size, background_color=menu_button_background_color, on_release=self.go_settings))
        self.menu_col_2.add_widget(Button(text="Manual", font_size=menu_button_font_size, background_color=menu_button_background_color, on_release=self.go_manual))
        self.menu_col_2.add_widget(Button(text="About", font_size=menu_button_font_size, background_color=menu_button_background_color, on_release=self.go_about))
        self.menu_col_3.add_widget(Button(text="Diagnostics", font_size=menu_button_font_size, background_color=menu_button_background_color, on_release=self.go_diagnostics))
        self.menu_col_3.add_widget(Button(text="Quit", font_size=menu_button_font_size, background_color=menu_button_background_color, on_release=self.go_quit))
        self.add_widget(self.menu_box)

    def go_visual(self, *args):
        self.manager.current = 'visual'

    def go_settings(self, *args):
        self.manager.current = 'settings'

    def go_manual(self, *args):
        self.manager.current = 'manual'

    def go_about(self, *args):
        self.manager.current = 'about'

    def go_diagnostics(self, *args):
        self.manager.current = 'diagnostics'
    
    def go_quit(self, *args):
        self.manager.ui_tx.put("quit")
        App.get_running_app().stop()

class AboutScreen(BoxLayout, Screen):
    def __init__(self, **kwargs):
        super(AboutScreen, self).__init__(**kwargs)
        self.add_widget(Label(text='Blurb about us, the project, and what we accomplished'))
        self.add_widget(Button(text='Main Menu', on_release=self.go_menu))

    def go_menu(self, *args):
        self.manager.current = 'menu'

class DiagnosticsScreen(BoxLayout, Screen):
    def __init__(self, **kwargs):
        super(DiagnosticsScreen, self).__init__(**kwargs)
        self.add_widget(Label(text='Relevant data'))
        self.add_widget(Button(text='Main Menu', on_release=self.go_menu))

    def go_menu(self, *args):
        self.manager.current = 'menu'

class ScreenManagement(ScreenManager):
    def __init__(self, ui_rx, ui_tx, visualization_data, **kwargs):
        super(ScreenManagement, self).__init__(**kwargs)
        self.ui_rx = ui_rx
        self.ui_tx = ui_tx
        self.visualization_data = visualization_data
        self.transition = FadeTransition()
        self.add_widget(IntroScreen(name='intro'))
        self.add_widget(SettingsScreen(name='settings', orientation='vertical', size=self.size))
        self.add_widget(MenuScreen(name='menu', orientation='vertical', size=self.size))
        self.add_widget(VisualScreen(name='visual', orientation='vertical', size=self.size))
        self.add_widget(ManualScreen(name='manual', size=self.size))
        self.add_widget(AboutScreen(name='about', orientation='vertical', size=self.size))
        self.add_widget(DiagnosticsScreen(name='diagnostics', orientation='vertical', size=self.size))

class UserInterfaceApp(App):
    def __init__(self, ui_rx, ui_tx, visualization_data, **kwargs):
        super(UserInterfaceApp, self).__init__(**kwargs)
        self.ui_rx = ui_rx
        self.ui_tx = ui_tx
        self.visualization_data = visualization_data

    def build(self):
        return ScreenManagement(self.ui_rx, self.ui_tx, self.visualization_data, name='manager', size=(1024,600)) #Builder.load_file("user_interface_kivy.kv")

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