# modules
import Queue
import sys
import time
import copy
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
from kivy.animation import Animation
from kivy.graphics import Line
from kivy.properties import NumericProperty, StringProperty

# customize screen size/cursor visibility
#Config.set('graphics','width','1024')
#Config.set('graphics','height','600')
Config.set('graphics', 'fullscreen', 'auto')
Config.set('graphics', 'show_cursor', '1')

# paths to import external files
images_path = "../../../6_User_Interface/1_Software/2_Images/"
audio_path = "../../../6_User_Interface/1_Software/3_Audio/"
settings_path = "../../../6_User_Interface/1_Software/4_Json/"

# globals
tableWidthMm = 660.4
tableHalfLengthMm = 846.1
ui_state_cmd_enum = 0
ui_diagnostic_request_enum = 0
ui_state_enum = 0
ui_error_enum = 0
ui_rx_enum = 0
ui_tx_enum = 0
ui_state = 0
ui_error = 0

# miscellaneous class definitions
class ManualPaddle(Scatter):
    images_path_local = StringProperty(images_path)

class ManualPlayingSurface(Widget):
    images_path_local = StringProperty(images_path)

class ManualScreen(BoxLayout, Screen):
    def on_enter(self):
        self.ids['game_control'].on_enter()

class VisualizationData(Image):
    def __init__(self, **kwargs):
        super(VisualizationData, self).__init__(**kwargs)
        Clock.schedule_interval(self.updateData, 0)

    def updateData(self, *args):
        while(self.parent.manager.visualization_data.poll()):
            frame = self.parent.manager.visualization_data.recv()
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_flipped = cv2.flip(frame_rgb, 0)
            frame_string = frame_flipped.tostring()
            image_texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='rgb')
            image_texture.blit_buffer(frame_string, colorfmt='rgb', bufferfmt='ubyte')
            self.texture = image_texture

# screen class definitions
class IntroScreen(BoxLayout, Screen):
    images_path_local = StringProperty(images_path)
    def __init__(self, **kwargs):
        super(IntroScreen, self).__init__(**kwargs)
        Clock.schedule_once(self.end_intro, 3)

        """#self.sound = SoundLoader.load(audio_path + 'organ.wav')
        #if self.sound:
        #    self.sound.play()"""
        

    def end_intro(self, *args):
        self.manager.current = 'menu'

class SettingsScreen(BoxLayout, Screen):
    def __init__(self, **kwargs):
        super(SettingsScreen, self).__init__(**kwargs)

        # game strategy setting
        self.game_strategy_layout = BoxLayout(orientation='horizontal')
        self.game_strategy_layout.add_widget(Label(text='Game Strategy:'))
        self.offense_button = ToggleButton(text='Offense', group='game_strategy_group', allow_no_selection=False, on_release=self.change_game_strategy)
        self.defense_button = ToggleButton(text='Defense', group='game_strategy_group', allow_no_selection=False, on_release=self.change_game_strategy)
        self.game_strategy_layout.add_widget(self.offense_button)
        self.game_strategy_layout.add_widget(self.defense_button)

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
        self.add_widget(self.game_strategy_layout)
        self.add_widget(self.game_difficulty_layout)
        self.add_widget(self.game_length_layout)

        # load settings
        with open((settings_path + 'settings.json'), 'r') as fp:
            self.settings = json.load(fp)
            fp.close()

        self.game_strategy = self.settings['user_interface']['settings']['game_strategy']
        self.game_difficulty = self.settings['user_interface']['settings']['game_difficulty']
        self.game_length = self.settings['user_interface']['settings']['game_length']
        self.updated_settings = True

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

        if self.game_strategy == "defense":
            self.defense_button.state = "down"
        elif self.game_strategy == "offense":
            self.offense_button.state = "down"

    def go_menu(self, *args):
        self.manager.current = 'menu'

    def change_game_difficulty(self, *args):
        if self.easy_button.state == 'down':
            self.settings['user_interface']['settings']['game_difficulty'] = 'easy'
        elif self.medium_button.state == 'down':
            self.settings['user_interface']['settings']['game_difficulty'] = 'medium'
        elif self.hard_button.state == 'down':
            self.settings['user_interface']['settings']['game_difficulty'] = 'hard'

    def change_game_length(self, *args):
        if self.one_min_button.state == 'down':
            self.settings['user_interface']['settings']['game_length'] = 60
        elif self.two_min_button.state == 'down':
            self.settings['user_interface']['settings']['game_length'] = 120
        elif self.five_min_button.state == 'down':
            self.settings['user_interface']['settings']['game_length'] = 300

    def change_game_strategy(self, *args):
        if self.defense_button.state == "down":
            self.settings['user_interface']['settings']['game_strategy'] = "defense"
        elif self.offense_button.state == "down":
            self.settings['user_interface']['settings']['game_strategy'] = "offense"

    def on_enter(self):
        with open((settings_path + 'settings.json'), 'r') as fp:
            self.settings = json.load(fp)
            self.old_settings = copy.deepcopy(self.settings)
            fp.close()

    def on_leave(self):
        with open((settings_path + 'settings.json'), 'w+') as fp:
            json.dump(self.settings, fp, indent=4)
            fp.close()

        self.game_length = self.settings['user_interface']['settings']['game_length']
        self.game_difficulty = self.settings['user_interface']['settings']['game_difficulty']
        self.game_strategy = self.settings['user_interface']['settings']['game_strategy']

        if self.old_settings != self.settings:
            self.updated_settings = True

class GameControl(BoxLayout):
    robot_score = 0
    human_score = 0
    game_clock = 0
    robot_score_label = StringProperty(str(robot_score))
    human_score_label = StringProperty(str(human_score))
    game_clock_label = StringProperty("00:00")
    game_running = True
    game_length = 60

    def get_settings(self, *args):
        self.game_length = self.parent.manager.get_screen('settings').game_length
        self.game_difficulty = self.parent.manager.get_screen('settings').game_difficulty
        
        # update 
        mins, secs = divmod(self.game_length, 60)
        self.game_clock_label = '{:02d}:{:02d}'.format(mins,secs)
        self.game_clock = self.game_length

    def decrement_clock(self, *args):
        self.game_clock -= 1
        mins, secs = divmod(self.game_clock, 60)
        timeformat = '{:02d}:{:02d}'.format(mins,secs)
        self.game_clock_label = timeformat

        if self.game_clock == 0:
            Clock.unschedule(self.decrement_clock)
            self.ids['pause_resume_game_button'].disabled = True

    def start_reset_game(self, *args):
        if self.ids['start_reset_game_button'].text == "Start Game":
            self.parent.manager.ui_tx[ui_tx_enum.game_state] = ui_game_state_enum.playing
            Clock.schedule_interval(self.decrement_clock, 1)
            self.ids['pause_resume_game_button'].disabled = False
            self.ids['start_reset_game_button'].text = "Reset Game"

        elif self.ids['start_reset_game_button'].text == "Reset Game":
            mins, secs = divmod(self.game_length, 60)
            self.game_clock_label = '{:02d}:{:02d}'.format(mins,secs)
            self.game_clock = self.game_length
            self.ids['pause_resume_game_button'].text = "Pause Game"
            self.ids['pause_resume_game_button'].disabled = True
            self.parent.manager.ui_tx[ui_tx_enum.game_state] = ui_game_state_enum.stopped
            Clock.unschedule(self.decrement_clock)
            self.ids['start_reset_game_button'].text = "Start Game"

    def pause_resume_game(self, *args):
        if self.ids['pause_resume_game_button'].text == "Pause Game":
            self.parent.manager.ui_tx[ui_tx_enum.game_state] = ui_game_state_enum.stopped
            Clock.unschedule(self.decrement_clock)
            self.ids['pause_resume_game_button'].text = "Resume Game"

        elif self.ids['pause_resume_game_button'].text == "Resume Game":
            self.parent.manager.ui_tx[ui_tx_enum.game_state] = ui_game_state_enum.playing
            Clock.schedule_interval(self.decrement_clock, 1)
            self.ids['pause_resume_game_button'].text = "Pause Game"

    def on_enter(self):
        self.parent.manager.ui_tx[ui_tx_enum.screen] = ui_screen_enum.visual
        if self.parent.manager.get_screen('settings').updated_settings == True:
            self.get_settings()
            self.parent.manager.get_screen('settings').updated_settings = False

    def go_menu(self, *args):
        if self.ids['pause_resume_game_button'].text == "Pause Game" and self.ids['pause_resume_game_button'].disabled == False:
            self.parent.manager.ui_tx[ui_tx_enum.game_state] = ui_game_state_enum.stopped
            Clock.unschedule(self.decrement_clock)
            self.ids['pause_resume_game_button'].text = "Resume Game"
        self.parent.manager.current = 'menu'

    def add_goal(self, goal_scorer):
        if game_running:
            if goal_scorer == ui_goal_enum.human:
                self.human_score += 1
                self.human_score_label = str(self.human_score)
            elif goal_scorer == ui_goal_enum.robot:
                self.robot_score += 1
                self.robot_score_label = str(self.robot_score)
            self.sound = SoundLoader.load(audio_path + 'goal_horn.mp3')
            if self.sound:
                self.sound.play()

class VisualScreen(BoxLayout, Screen):
    def on_enter(self):
        self.ids['game_control'].on_enter()

class MenuScreen(BoxLayout, Screen):
    images_path_local = StringProperty(images_path)
    menu_button_font_size = ObjectProperty(30)
    menu_button_background_color = ObjectProperty((0,0,0,0.6))

    def on_enter(self):
        self.manager.ui_tx[ui_tx_enum.screen] = ui_screen_enum.menu

    def go_quit(self, *args):
        self.manager.ui_tx[ui_tx_enum.state] = ui_state_enum.quit

    def okay_to_quit(self, *args):
        App.get_running_app().stop()

class AboutScreen(BoxLayout, Screen):
    about_label_font_size = NumericProperty(30)
    images_path_local = StringProperty(images_path)

class DiagnosticsScreen(BoxLayout, Screen):
    diagnostic_label_font_size = NumericProperty(30)
    images_path_local = StringProperty(images_path)

    def calibrate_pt(self, *args):
        self.manager.ui_tx[ui_tx_enum.diagnostic_request] = ui_diagnostic_request_enum.calibrate_pt    
    
class ScreenManagement(ScreenManager):
    def __init__(self, ui_rx, ui_tx, visualization_data, **kwargs):
        super(ScreenManagement, self).__init__(**kwargs)
        
        # IPC management
        self.ui_rx = ui_rx
        self.ui_tx = ui_tx
        self.visualization_data = visualization_data

        # screen management
        self.transition = FadeTransition()
        self.add_widget(IntroScreen(name='intro'))
        self.add_widget(SettingsScreen(name='settings'))
        self.add_widget(MenuScreen(name='menu'))
        self.add_widget(VisualScreen(name='visual'))
        self.add_widget(ManualScreen(name='manual'))
        self.add_widget(AboutScreen(name='about'))
        self.add_widget(DiagnosticsScreen(name='diagnostics'))

        # run the UI state machine
        Clock.schedule_interval(self.process_data, 0)

    def process_data(self, *args):
        self.update_diagnostic_screen()
        
        # keep track of score
        if int(self.ui_rx[ui_rx_enum.goal]) != ui_goal_enum.idle:
            self.get_screen('visual').add_goal(self.ui_rx[ui_rx_enum.goal])
            self.ui_rx[ui_rx_enum.goal] = ui_goal_enum.idle

        # only quit this app once everything else has shut down properly
        if int(self.ui_rx[ui_rx_enum.state_cmd]) == ui_state_cmd_enum.quit:
            self.get_screen('menu').okay_to_quit()

    def update_diagnostic_screen(self, *args):
        self.get_screen('diagnostics').ids['ui_state_label'].text = ui_state_enum.reverse_mapping[ui_state]
        self.get_screen('diagnostics').ids['ui_error_label'].text = ui_error_enum.reverse_mapping[ui_error]
        self.get_screen('diagnostics').ids['pt_state_label'].text = pt_state_enum.reverse_mapping[self.ui_rx[ui_rx_enum.pt_state]]
        self.get_screen('diagnostics').ids['pt_error_label'].text = pt_error_enum.reverse_mapping[self.ui_rx[ui_rx_enum.pt_error]]
        self.get_screen('diagnostics').ids['mc_state_label'].text = mc_state_enum.reverse_mapping[self.ui_rx[ui_rx_enum.mc_state]]
        self.get_screen('diagnostics').ids['mc_error_label'].text = mc_error_enum.reverse_mapping[self.ui_rx[ui_rx_enum.mc_error]]
        self.get_screen('diagnostics').ids['pc_state_label'].text = pc_state_enum.reverse_mapping[self.ui_rx[ui_rx_enum.pc_state]]
        self.get_screen('diagnostics').ids['pc_error_label'].text = pc_error_enum.reverse_mapping[self.ui_rx[ui_rx_enum.pc_error]]

# main app
class UserInterfaceApp(App):
    def __init__(self, ui_rx, ui_tx, visualization_data, **kwargs):
        super(UserInterfaceApp, self).__init__(**kwargs)
        self.ui_rx = ui_rx
        self.ui_tx = ui_tx
        self.visualization_data = visualization_data

    def build(self):
        return ScreenManagement(self.ui_rx, self.ui_tx, self.visualization_data)

# enum creator
def enum(list_of_enums):
    enums = dict(zip(list_of_enums, range(len(list_of_enums))))
    reverse = dict((value, key) for key, value in enums.iteritems())
    enums['reverse_mapping'] = reverse
    return type('Enum', (), enums)

# enum retriever
def get_enums():
    global ui_state_cmd_enum
    global ui_diagnostic_request_enum
    global ui_state_enum
    global ui_error_enum
    global ui_rx_enum
    global ui_tx_enum
    global ui_game_state_enum
    global ui_screen_enum
    global ui_goal_enum

    global pt_state_enum
    global pt_error_enum
    
    global mc_state_enum
    global mc_error_enum
    
    global pc_state_enum
    global pc_error_enum

    # get settings from file
    with open((settings_path + 'settings.json'), 'r') as fp:
        settings = json.load(fp)
        fp.close()

    ui_state_cmd_enum = enum(settings['user_interface']['enumerations']['ui_state_cmd'])
    ui_state_enum = enum(settings['user_interface']['enumerations']['ui_state'])
    ui_error_enum = enum(settings['user_interface']['enumerations']['ui_error'])   
    ui_rx_enum = enum(settings['user_interface']['enumerations']['ui_rx'])
    ui_tx_enum = enum(settings['user_interface']['enumerations']['ui_tx'])
    ui_diagnostic_request_enum = enum(settings['user_interface']['enumerations']['ui_diagnostic_request'])
    ui_game_state_enum = enum(settings['user_interface']['enumerations']['ui_game_state'])
    ui_screen_enum = enum(settings['user_interface']['enumerations']['ui_screen'])
    ui_goal_enum = enum(settings['user_interface']['enumerations']['ui_goal'])
    
    pt_state_enum = enum(settings['puck_tracker']['enumerations']['pt_state'])
    pt_error_enum = enum(settings['puck_tracker']['enumerations']['pt_error'])

    mc_state_enum = enum(settings['master_controller']['enumerations']['mc_state'])
    mc_error_enum = enum(settings['master_controller']['enumerations']['mc_error'])

    pc_state_enum = enum(settings['paddle_controller']['enumerations']['pc_state'])
    pc_error_enum = enum(settings['paddle_controller']['enumerations']['pc_error'])

def ui_process(ui_rx, ui_tx, visualization_data):
    """All things user interface happen here. Communicates directly with master controller"""
    global ui_state
    global ui_error

    get_enums()

    ui_state = ui_state_enum.idle
    ui_error = ui_error_enum.idle

    while True:
        # retrieve commands from master controller
        mc_cmd = int(ui_rx[ui_rx_enum.state_cmd])
        ui_rx[ui_rx_enum.state_cmd] = ui_state_cmd_enum.idle

        # set desired state of the user interface to that commanded by mc    
        if mc_cmd == ui_state_cmd_enum.run:
            ui_state = ui_state_enum.running
            UserInterfaceApp(ui_rx, ui_tx, visualization_data).run()
        elif mc_cmd == ui_state_cmd_enum.quit:
            ui_state = ui_state_enum.quit
            quit(0)