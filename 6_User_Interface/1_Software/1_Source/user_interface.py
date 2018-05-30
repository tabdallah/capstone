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
class Paddle(Scatter):
    def __init__(self, **kwargs):
        super(Paddle, self).__init__(**kwargs)
        self.paddle_image = Image(source=(images_path + 'paddle.png'), pos=self.pos)
        self.add_widget(self.paddle_image)

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

class VisualizationData(Image):
    def __init__(self, **kwargs):
        super(VisualizationData, self).__init__(**kwargs)
        Clock.schedule_interval(self.updateData, 0)

    def updateData(self, *args):
        while(self.parent.parent.parent.manager.visualization_data.poll()):
            frame = self.parent.parent.parent.manager.visualization_data.recv()
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_flipped = cv2.flip(frame_rgb, 0)
            frame_string = frame_flipped.tostring()
            image_texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='rgb')
            image_texture.blit_buffer(frame_string, colorfmt='rgb', bufferfmt='ubyte')
            self.texture = image_texture

# screen class definitions
class IntroScreen(BoxLayout, Screen):
    def __init__(self, **kwargs):
        super(IntroScreen, self).__init__(**kwargs)
        self.add_widget(Image(source=(images_path + 'logo.png'),allow_stretch=True))
        #self.sound = SoundLoader.load(audio_path + 'organ.wav')
        #if self.sound:
        #    self.sound.play()
        Clock.schedule_once(self.end_intro, 0)

    def end_intro(self, *args):
        self.manager.get_screen('visual').get_settings()
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

        #with self.canvas.after:
        #    Color(1,0,0,0.3)
        #    Rectangle(pos=self.pos, size=self.size)
        
        # scoreboard stuff
        self.scoreboard = BoxLayout(orientation='vertical', size_hint=(1,1.5))
        
        self.clock_label = Label(text='00:00', font_size=80, color=(1,0,0,1))
        self.scoreboard.add_widget(self.clock_label)

        self.score = BoxLayout(orientation='horizontal')
        self.robot = BoxLayout(orientation='vertical')
        self.human = BoxLayout(orientation='vertical')
        
        self.robot.add_widget(Label(text='Robot',font_size=20, size_hint=(1,0.4)))
        self.robot_score = Label(text='0', font_size=50)
        self.robot_score.value = 0
        self.robot.add_widget(self.robot_score)

        self.human.add_widget(Label(text='Human',font_size=20, size_hint=(1,0.4)))
        self.human_score = Label(text='0', font_size=50)
        self.human_score.value = 0
        self.human.add_widget(self.human_score)

        self.score.add_widget(self.robot)
        self.score.add_widget(self.human)
        self.scoreboard.add_widget(self.score)

        # visualization & menu
        self.visualization_and_menu = BoxLayout(orientation='horizontal')
        self.visualization = BoxLayout(orientation='vertical')
        self.menu = BoxLayout(orientation='vertical', size_hint=(0.29,1))
        self.visualization_and_menu.add_widget(self.visualization)
        self.visualization_and_menu.add_widget(self.menu)
        self.visualization.add_widget(VisualizationData())
        self.start_reset_game_button = Button(text="Start Game", font_size=30, on_release=self.start_reset_game)
        self.pause_resume_game_button = Button(text="Pause Game", font_size=30, on_release=self.pause_resume_game)
        self.menu.add_widget(self.scoreboard)
        self.menu.add_widget(self.start_reset_game_button)
        self.menu.add_widget(self.pause_resume_game_button)
        self.menu.add_widget(Button(text="Main Menu", font_size=30, on_release=self.go_menu))
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
            self.manager.ui_tx[ui_tx_enum.game_state] = ui_game_state_enum.playing
            Clock.schedule_interval(self.decrement_clock, 1)
            self.pause_resume_game_button.disabled = False
            self.start_reset_game_button.text = "Reset Game"

        elif self.start_reset_game_button.text == "Reset Game":
            mins, secs = divmod(self.game_length, 60)
            self.clock_label.text = '{:02d}:{:02d}'.format(mins,secs)
            self.clock_label.value = self.game_length
            self.pause_resume_game_button.text = "Pause Game"
            self.pause_resume_game_button.disabled = True
            self.manager.ui_tx[ui_tx_enum.game_state] = ui_game_state_enum.stopped
            Clock.unschedule(self.decrement_clock)
            self.start_reset_game_button.text = "Start Game"

    def pause_resume_game(self, *args):
        if self.pause_resume_game_button.text == "Pause Game":
            self.manager.ui_tx[ui_tx_enum.game_state] = ui_game_state_enum.stopped
            Clock.unschedule(self.decrement_clock)
            self.pause_resume_game_button.text = "Resume Game"

        elif self.pause_resume_game_button.text == "Resume Game":
            self.manager.ui_tx[ui_tx_enum.game_state] = ui_game_state_enum.playing
            Clock.schedule_interval(self.decrement_clock, 1)
            self.pause_resume_game_button.text = "Pause Game"

    def on_enter(self):
        self.manager.ui_tx[ui_tx_enum.screen] = ui_screen_enum.visual
        if self.manager.get_screen('settings').updated_settings == True:
            self.get_settings()
            self.manager.get_screen('settings').updated_settings = False

    def go_menu(self, *args):
        if self.pause_resume_game_button.text == "Pause Game" and self.pause_resume_game_button.disabled == False:
            self.manager.ui_tx[ui_tx_enum.game_state] = ui_game_state_enum.stopped
            Clock.unschedule(self.decrement_clock)
            self.pause_resume_game_button.text = "Resume Game"
        self.manager.current = 'menu'

    def add_goal(self, goal_scorer):
        if self.pause_resume_game_button.text == "Pause Game" and self.pause_resume_game_button.disabled == False:
            if goal_scorer == ui_goal_enum.human:
                self.human_score.value += 1
                self.human_score.text = str(self.human_score.value)
            elif goal_scorer == ui_goal_enum.robot:
                self.robot_score.value += 1
                self.robot_score.text = str(self.robot_score.value)
            self.sound = SoundLoader.load(audio_path + 'goal_horn.mp3')
            if self.sound:
                self.sound.play()

class MenuScreen(BoxLayout, Screen):
    def __init__(self, **kwargs):
        super(MenuScreen, self).__init__(**kwargs)
        
        # add background image
        with self.canvas.before:
            Rectangle(source=(images_path + 'menu_background.jpg'), pos=self.pos, size=self.size)

        self.menu_label = Label(name='main_menu', text='Main Menu', size_hint=(1,0.2), font_size=40)
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
        self.menu_col_1.add_widget(Button(text="Play Against Robot", font_size=menu_button_font_size, background_color=menu_button_background_color, on_release=self.go_visual))
        self.menu_col_1.add_widget(Button(text="Settings", font_size=menu_button_font_size, background_color=menu_button_background_color, on_release=self.go_settings))
        self.menu_col_2.add_widget(Button(text="Play Using Robot", font_size=menu_button_font_size, background_color=menu_button_background_color, on_release=self.go_manual))
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
    
    def on_enter(self):
        self.manager.ui_tx[ui_tx_enum.screen] = ui_screen_enum.menu

    def go_quit(self, *args):
        self.manager.ui_tx[ui_tx_enum.state] = ui_state_enum.quit

    def okay_to_quit(self, *args):
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

        # font size
        diagnostic_font_size = 30
        label_size_hint = (1.5,1)

        # add background image
        with self.canvas.before:
            Color(1,1,1,0.3)
            Rectangle(source=(images_path + 'menu_background.jpg'), pos=self.pos, size=self.size)

        # top label
        self.add_widget(Label(text='Diagnostics', font_size=40))
        # all diagnostic data in this layout
        self.diagnostic_data_layout = BoxLayout(orientation='vertical')
        # ui state/error diagnostics
        self.ui_state_error_layout = BoxLayout(orientation='horizontal')
        self.ui_state_error_layout.add_widget(Label(text='User Interface', font_size=diagnostic_font_size, size_hint=label_size_hint))
        self.ui_state_error_layout.add_widget(Label(text='State:', font_size=diagnostic_font_size))
        self.ui_state_data = Label(text='NULL', font_size=diagnostic_font_size)
        self.ui_state_error_layout.add_widget(self.ui_state_data)
        self.ui_state_error_layout.add_widget(Label(text='Error:', font_size=diagnostic_font_size))
        self.ui_error_data = Label(text='NULL', font_size=diagnostic_font_size)
        self.ui_state_error_layout.add_widget(self.ui_error_data)
        # pt state/error
        self.pt_state_error_layout = BoxLayout(orientation='horizontal')
        self.pt_state_error_layout.add_widget(Label(text='Puck Tracker', font_size=diagnostic_font_size, size_hint=label_size_hint))
        self.pt_state_error_layout.add_widget(Label(text='State:', font_size=diagnostic_font_size))
        self.pt_state_data = Label(text='NULL', font_size=diagnostic_font_size)
        self.pt_state_error_layout.add_widget(self.pt_state_data)
        self.pt_state_error_layout.add_widget(Label(text='Error:', font_size=diagnostic_font_size))
        self.pt_error_data = Label(text='NULL', font_size=diagnostic_font_size)
        self.pt_state_error_layout.add_widget(self.pt_error_data)
        # pc state/error diagnostics
        self.pc_state_error_layout = BoxLayout(orientation='horizontal')
        self.pc_state_error_layout.add_widget(Label(text='Paddle Controller', font_size=diagnostic_font_size, size_hint=label_size_hint))
        self.pc_state_error_layout.add_widget(Label(text='State:', font_size=diagnostic_font_size))
        self.pc_state_data = Label(text='NULL', font_size=diagnostic_font_size)
        self.pc_state_error_layout.add_widget(self.pc_state_data)
        self.pc_state_error_layout.add_widget(Label(text='Error:', font_size=diagnostic_font_size))
        self.pc_error_data = Label(text='NULL', font_size=diagnostic_font_size)
        self.pc_state_error_layout.add_widget(self.pc_error_data)
        # mc state/error
        self.mc_state_error_layout = BoxLayout(orientation='horizontal')
        self.mc_state_error_layout.add_widget(Label(text='Master Controller', font_size=diagnostic_font_size, size_hint=label_size_hint))
        self.mc_state_error_layout.add_widget(Label(text='State:', font_size=diagnostic_font_size))
        self.mc_state_data = Label(text='NULL', font_size=diagnostic_font_size)
        self.mc_state_error_layout.add_widget(self.mc_state_data)
        self.mc_state_error_layout.add_widget(Label(text='Error:', font_size=diagnostic_font_size))
        self.mc_error_data = Label(text='NULL', font_size=diagnostic_font_size)
        self.mc_state_error_layout.add_widget(self.mc_error_data)
        # add diagnostics to layouts
        self.diagnostic_data_layout.add_widget(self.ui_state_error_layout)
        self.diagnostic_data_layout.add_widget(self.pt_state_error_layout)
        self.diagnostic_data_layout.add_widget(self.pc_state_error_layout)
        self.diagnostic_data_layout.add_widget(self.mc_state_error_layout)
        self.add_widget(self.diagnostic_data_layout)

        self.add_widget(Button(text='Calibrate Puck Tracker', on_release=self.calibrate_pt))
        self.add_widget(Button(text='Main Menu', on_release=self.go_menu))

    def go_menu(self, *args):
        self.manager.current = 'menu'

    def calibrate_pt(self, *args):
        self.manager.ui_tx[ui_tx_enum.diagnostic_request] = ui_diagnostic_request_enum.calibrate_pt
    
# screen manager (also does IPC)
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
        self.add_widget(SettingsScreen(name='settings', orientation='vertical', size=self.size))
        self.add_widget(MenuScreen(name='menu', orientation='vertical', size=self.size))
        self.add_widget(VisualScreen(name='visual', orientation='vertical', size=self.size))
        self.add_widget(ManualScreen(name='manual', size=self.size))
        self.add_widget(AboutScreen(name='about', orientation='vertical', size=self.size))
        self.add_widget(DiagnosticsScreen(name='diagnostics', orientation='vertical', size=self.size))

        # run the UI state machine
        Clock.schedule_interval(self.receive_data, 0)

    def receive_data(self, *args):
        self.update_diagnostic_screen()
        
        # keep track of score
        if int(self.ui_rx[ui_rx_enum.goal]) != ui_goal_enum.idle:
            self.get_screen('visual').add_goal(self.ui_rx[ui_rx_enum.goal])
            self.ui_rx[ui_rx_enum.goal] = ui_goal_enum.idle

        # only quit this app once everything else has shut down properly
        if int(self.ui_rx[ui_rx_enum.state_cmd]) == ui_state_cmd_enum.quit:
            self.get_screen('menu').okay_to_quit()

    def update_diagnostic_screen(self, *args):
        self.get_screen('diagnostics').ui_state_data.text = ui_state_enum.reverse_mapping[ui_state]
        self.get_screen('diagnostics').ui_error_data.text = ui_error_enum.reverse_mapping[ui_error]
        self.get_screen('diagnostics').pt_state_data.text = pt_state_enum.reverse_mapping[self.ui_rx[ui_rx_enum.pt_state]]
        self.get_screen('diagnostics').pt_error_data.text = pt_error_enum.reverse_mapping[self.ui_rx[ui_rx_enum.pt_error]]
        self.get_screen('diagnostics').mc_state_data.text = mc_state_enum.reverse_mapping[self.ui_rx[ui_rx_enum.mc_state]]
        self.get_screen('diagnostics').mc_error_data.text = mc_error_enum.reverse_mapping[self.ui_rx[ui_rx_enum.mc_error]]
        self.get_screen('diagnostics').pc_state_data.text = pc_state_enum.reverse_mapping[self.ui_rx[ui_rx_enum.pc_state]]
        self.get_screen('diagnostics').pc_error_data.text = pc_error_enum.reverse_mapping[self.ui_rx[ui_rx_enum.pc_error]]

# main app
class UserInterfaceApp(App):
    def __init__(self, ui_rx, ui_tx, visualization_data, **kwargs):
        super(UserInterfaceApp, self).__init__(**kwargs)
        self.ui_rx = ui_rx
        self.ui_tx = ui_tx
        self.visualization_data = visualization_data

    def build(self):
        return ScreenManagement(self.ui_rx, self.ui_tx, self.visualization_data, size=(1024,600))

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