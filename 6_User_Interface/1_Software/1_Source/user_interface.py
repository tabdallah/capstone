##############################################################################################
# user_interface.py - Code specific to the User Interface implemented using the Kivy framework
# Name: David Eelman
# Date: 2018-06-12
##############################################################################################
import cv2
import json
import Queue
import sys
from kivy.app import App
from kivy.clock import Clock
from kivy.config import Config
from kivy.core.audio import SoundLoader
from kivy.graphics.texture import Texture
from kivy.properties import ObjectProperty, NumericProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.scatter import Scatter
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.widget import Widget

# paths to import external files
images_filepath = "../../../6_User_Interface/1_Software/2_Images/"
audio_filepath = "../../../6_User_Interface/1_Software/3_Audio/"
settings_filepath = "../../../6_User_Interface/1_Software/4_Json/"

# configuration parameter for touchscreen or normal monitor
touchscreen = False
if touchscreen:
    Config.set('graphics', 'fullscreen', 'auto')
    Config.set('graphics', 'show_cursor', '0') 
else:
    Config.set('graphics','width','1024')
    Config.set('graphics','height','600')
    Config.set('graphics', 'show_cursor', '1') 

##############################################################################################
# Class Definitions for all the User Interface Screens
##############################################################################################
class IntroScreen(BoxLayout, Screen):
    def __init__(self, **kwargs):
        super(IntroScreen, self).__init__(**kwargs)
        # intro/splash screen will show for 3 seconds on start
        Clock.schedule_once(self.go_menu, 2)

        # play intro music
        self.sound = SoundLoader.load(audio_filepath + 'organ.wav')
        if self.sound:
            self.sound.play()
    
    def on_enter(self):
        self.manager.ui_tx[ui_tx_enum.screen] = ui_screen_enum.intro

    def go_menu(self, *args):
        self.manager.current = 'menu'

class MenuScreen(BoxLayout, Screen):
    def on_enter(self):
        self.manager.ui_tx[ui_tx_enum.screen] = ui_screen_enum.menu

    def go_quit(self, *args):
        self.manager.ui_tx[ui_tx_enum.state] = ui_state_enum.request_quit

    def okay_to_quit(self, *args):
        self.manager.ui_tx[ui_tx_enum.state] = ui_state_enum.quit
        App.get_running_app().stop()

class VisualScreen(BoxLayout, Screen):
    def on_enter(self):
        self.manager.ui_tx[ui_tx_enum.screen] = ui_screen_enum.visual
        self.ids['game_control'].on_enter()
        self.ids['camera_data'].on_enter()
    def on_leave(self):
        self.ids['camera_data'].on_leave()

class ManualScreen(BoxLayout, Screen):
    def on_enter(self):
        self.manager.ui_tx[ui_tx_enum.screen] = ui_screen_enum.manual
        # for debugging
        self.manager.ui_tx[ui_tx_enum.state] = ui_state_enum.running
        self.manager.ui_tx[ui_tx_enum.paddle_position_x] = 120
        self.manager.ui_tx[ui_tx_enum.paddle_position_y] = 20
        self.ids['game_control'].on_enter()

class DiagnosticsScreen(BoxLayout, Screen):
    def on_enter(self):
        self.manager.ui_tx[ui_tx_enum.screen] = ui_screen_enum.diagnostic

class SettingsScreen(BoxLayout, Screen):
    def on_enter(self):
        get_settings() #TODO: remove as this is likely up to date already

        if game_difficulty == ui_game_difficulty_enum.easy:
            self.ids['easy_button'].state = 'down'
        elif game_difficulty == ui_game_difficulty_enum.medium:
            self.ids['medium_button'].state = 'down'
        elif game_difficulty == ui_game_difficulty_enum.hard:
            self.ids['hard_button'].state = 'down'

        if game_length == 60:
            self.ids['one_min_button'].state = 'down'
        elif game_length == 120:
            self.ids['two_min_button'].state = 'down'
        elif game_length == 300:
            self.ids['five_min_button'].state = 'down'

        if game_mode == ui_game_mode_enum.defense:
            self.ids['defense_button'].state = 'down'
        elif game_mode == ui_game_mode_enum.offense:
            self.ids['offense_button'].state = 'down'

    def change_game_difficulty(self, *args):
        global game_difficulty
        if self.ids['easy_button'].state == 'down':
            game_difficulty = ui_game_difficulty_enum.easy
        elif self.ids['medium_button'].state == 'down':
            game_difficulty = ui_game_difficulty_enum.medium
        elif self.ids['hard_button'].state == 'down':
            game_difficulty = ui_game_difficulty_enum.hard

    def change_game_length(self, *args):
        global game_length
        if self.ids['one_min_button'].state == 'down':
            game_length = 60
        elif self.ids['two_min_button'].state == 'down':
            game_length = 120
        elif self.ids['five_min_button'].state == 'down':
            game_length = 300

    def change_game_mode(self, *args):
        global game_mode
        if self.ids['offense_button'].state == 'down':
            game_mode = ui_game_mode_enum.offense
        elif self.ids['defense_button'].state == 'down':
            game_mode = ui_game_mode_enum.defense

    def go_menu(self, *args):
        self.manager.current = 'menu'

    def on_leave(self):
        update_game_settings()

class AboutScreen(BoxLayout, Screen):
    pass

class FiducialCalibrationScreen(BoxLayout, Screen):
    action_label = StringProperty()
    instruction_label = StringProperty()

    def on_enter(self):
        self.manager.ui_tx[ui_tx_enum.screen] = ui_screen_enum.fiducial_calibration
        self.action_label = "Find Fiducials"
        self.instruction_label = "Adjust the sliders until you only see the four pink fiducial markers"
        self.ids['camera_data'].on_enter()
        get_settings()
        self.ids['lower_hue'].value = fiducial_lower_hsv[0]
        self.ids['lower_sat'].value = fiducial_lower_hsv[1]
        self.ids['lower_val'].value = fiducial_lower_hsv[2]
        self.ids['upper_hue'].value = fiducial_upper_hsv[0]
        self.ids['upper_sat'].value = fiducial_upper_hsv[1]
        self.ids['upper_val'].value = fiducial_upper_hsv[2]

    def calibrate_continue_button(self, *args):
        global fiducial_lower_hsv
        global fiducial_upper_hsv
        if self.ids['calibrate_continue_button'].text == "Save & Calibrate":
            self.ids['slider_layout'].disabled = True
            fiducial_lower_hsv = (self.ids['lower_hue'].value, self.ids['lower_sat'].value, self.ids['lower_val'].value)
            fiducial_upper_hsv = (self.ids['upper_hue'].value, self.ids['upper_sat'].value, self.ids['upper_val'].value)
            update_fiducial_values()
            self.manager.ui_tx[ui_tx_enum.diagnostic_request] = ui_diagnostic_request_enum.calibrate_fiducials
            self.ids['skip_redo_button'].text = "Redo"
            self.action_label = "Calibrated Fiducials"
            self.instruction_label = "Was the fiducial calibration successful? You should see just the playing surface. If not, redo"
            self.ids['calibrate_continue_button'].text = "Continue"
        elif self.ids['calibrate_continue_button'].text == "Continue":
            self.ids['calibrate_continue_button'].text = "Save & Calibrate"
            self.manager.current = 'puck_calibration'

    def skip_redo_button(self, *args):
        if self.ids['skip_redo_button'].text == "Skip":
            self.manager.current = 'puck_calibration'
        elif self.ids['skip_redo_button'].text == "Redo":
            self.manager.ui_tx[ui_tx_enum.diagnostic_request] = ui_diagnostic_request_enum.idle
            self.ids['slider_layout'].disabled = False
            self.ids['calibrate_continue_button'].text = "Save & Calibrate"
            self.ids['skip_redo_button'].text = "Skip"
            self.on_enter()

    def on_leave(self):
        self.manager.ui_tx[ui_tx_enum.diagnostic_request] = ui_diagnostic_request_enum.idle
        self.ids['skip_redo_button'].text = "Skip"
        self.ids['calibrate_continue_button'].text = "Save & Calibrate"
        self.ids['slider_layout'].disabled = False
        self.ids['camera_data'].on_leave()

class PuckCalibrationScreen(BoxLayout, Screen):
    images_path_local = StringProperty(images_filepath)
    action_label = StringProperty()
    instruction_label = StringProperty()
    
    def on_enter(self):
        self.manager.ui_tx[ui_tx_enum.screen] = ui_screen_enum.puck_calibration
        get_settings()
        self.action_label = "Find Puck"
        self.instruction_label = "Adjust the sliders until you see only the one green puck"
        self.ids['camera_data'].on_enter()
        self.ids['lower_hue'].value = puck_lower_hsv[0]
        self.ids['lower_sat'].value = puck_lower_hsv[1]
        self.ids['lower_val'].value = puck_lower_hsv[2]
        self.ids['upper_hue'].value = puck_upper_hsv[0]
        self.ids['upper_sat'].value = puck_upper_hsv[1]
        self.ids['upper_val'].value = puck_upper_hsv[2]

    def skip_redo_button(self, *args):
        if self.ids['skip_redo_button'].text == "Skip":
            self.manager.current = 'diagnostics'

    def calibrate_continue_button(self, *args):
        global puck_lower_hsv
        global puck_upper_hsv
        if self.ids['calibrate_continue_button'].text == "Save & Calibrate":
            puck_lower_hsv = (self.ids['lower_hue'].value, self.ids['lower_sat'].value, self.ids['lower_val'].value)
            puck_upper_hsv = (self.ids['upper_hue'].value, self.ids['upper_sat'].value, self.ids['upper_val'].value)
            update_puck_values()
            self.manager.current = 'diagnostics'

    def on_leave(self):
        self.ids['camera_data'].on_leave()

##############################################################################################
# Screen Manager
##############################################################################################
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
        self.add_widget(FiducialCalibrationScreen(name='fiducial_calibration'))
        self.add_widget(PuckCalibrationScreen(name='puck_calibration'))

        # run the UI state machine
        Clock.schedule_interval(self.process_data, 0.1)

    def process_data(self, *args):
        self.update_diagnostic_screen()
        
        # keep track of score
        if int(self.ui_rx[ui_rx_enum.goal_scored]) != ui_goal_enum.none:
            self.get_screen('visual').add_goal(self.ui_rx[ui_rx_enum.goal_scored])
            self.ui_rx[ui_rx_enum.goal_scored] = ui_goal_enum.none

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
        if self.current == 'fiducial_calibration':
            self.ui_tx[ui_tx_enum.lower_hue] = self.get_screen('fiducial_calibration').ids['lower_hue'].value
            self.ui_tx[ui_tx_enum.lower_sat] = self.get_screen('fiducial_calibration').ids['lower_sat'].value
            self.ui_tx[ui_tx_enum.lower_val] = self.get_screen('fiducial_calibration').ids['lower_val'].value
            self.ui_tx[ui_tx_enum.upper_hue] = self.get_screen('fiducial_calibration').ids['upper_hue'].value
            self.ui_tx[ui_tx_enum.upper_sat] = self.get_screen('fiducial_calibration').ids['upper_sat'].value
            self.ui_tx[ui_tx_enum.upper_val] = self.get_screen('fiducial_calibration').ids['upper_val'].value
        elif self.current == 'puck_calibration':
            self.ui_tx[ui_tx_enum.lower_hue] = self.get_screen('puck_calibration').ids['lower_hue'].value
            self.ui_tx[ui_tx_enum.lower_sat] = self.get_screen('puck_calibration').ids['lower_sat'].value
            self.ui_tx[ui_tx_enum.lower_val] = self.get_screen('puck_calibration').ids['lower_val'].value
            self.ui_tx[ui_tx_enum.upper_hue] = self.get_screen('puck_calibration').ids['upper_hue'].value
            self.ui_tx[ui_tx_enum.upper_sat] = self.get_screen('puck_calibration').ids['upper_sat'].value
            self.ui_tx[ui_tx_enum.upper_val] = self.get_screen('puck_calibration').ids['upper_val'].value

##############################################################################################
# Widget definitions
##############################################################################################
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
        self.game_length = game_length
        self.game_difficulty = game_difficulty
        
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
        self.get_settings()

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
            self.sound = SoundLoader.load(audio_filepath + 'goal_horn.mp3')
            if self.sound:
                self.sound.play()

class CameraData(Image):
    def __init__(self, **kwargs):
        super(CameraData, self).__init__(**kwargs)
        #self.source = (images_filepath + 'loading.gif')

    def on_enter(self):
        Clock.schedule_interval(self.update_data, 0)

    def on_leave(self):
        Clock.unschedule(self.update_data)
        #self.source = (images_filepath + 'loading.gif')

    def update_data(self, *args):
        try:
            frame = app.root.visualization_data.get(False)
        except Queue.Empty:
            pass
        else:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_flipped = cv2.flip(frame_rgb, 0)
            frame_string = frame_flipped.tostring()
            image_texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='rgb')
            image_texture.blit_buffer(frame_string, colorfmt='rgb', bufferfmt='ubyte')
            self.texture = image_texture

class ManualPaddle(Scatter):
    pass

class ManualPlayingSurface(Widget):
    pass

class LineSeparator(Widget):
    pass

class LineSeparator2(Widget):
    pass

##############################################################################################
# The Application
##############################################################################################
class UserInterfaceApp(App):
    app_images_filepath = StringProperty(images_filepath)
    def __init__(self, ui_rx, ui_tx, visualization_data, **kwargs):
        super(UserInterfaceApp, self).__init__(**kwargs)
        global app
        app = App.get_running_app() 
        self.ui_rx = ui_rx
        self.ui_tx = ui_tx
        self.visualization_data = visualization_data

    def build(self):
        return ScreenManagement(self.ui_rx, self.ui_tx, self.visualization_data)

##############################################################################################
# Miscellaneous Functions
##############################################################################################
def enum(list_of_enums):
    """Enum creator"""
    enums = dict(zip(list_of_enums, range(len(list_of_enums))))
    reverse = dict((value, key) for key, value in enums.iteritems())
    enums['reverse_mapping'] = reverse
    return type('Enum', (), enums)

def get_enums():
    """Enum retriever"""
    global mc_error_enum
    global mc_state_enum
    global pc_error_enum
    global pc_state_enum
    global pt_error_enum
    global pt_state_enum
    global ui_error_enum
    global ui_diagnostic_request_enum
    global ui_game_difficulty_enum
    global ui_game_mode_enum
    global ui_game_state_enum
    global ui_goal_enum
    global ui_paddle_pos_enum
    global ui_rx_enum
    global ui_screen_enum
    global ui_state_cmd_enum
    global ui_state_enum
    global ui_tx_enum

    # load enums from settings file
    with open((settings_filepath + 'settings.json'), 'r') as fp:
        settings = json.load(fp)
        fp.close()

    # master controller enums
    mc_error_enum = enum(settings['master_controller']['enumerations']['mc_error'])
    mc_state_enum = enum(settings['master_controller']['enumerations']['mc_state'])
    # paddle controller enums
    pc_error_enum = enum(settings['paddle_controller']['enumerations']['pc_error'])
    pc_state_enum = enum(settings['paddle_controller']['enumerations']['pc_state'])
    # puck tracker enums
    pt_error_enum = enum(settings['puck_tracker']['enumerations']['pt_error'])
    pt_state_enum = enum(settings['puck_tracker']['enumerations']['pt_state'])
    # user interface enums
    ui_error_enum = enum(settings['user_interface']['enumerations']['ui_error'])   
    ui_diagnostic_request_enum = enum(settings['user_interface']['enumerations']['ui_diagnostic_request'])
    ui_game_difficulty_enum = enum(settings['user_interface']['enumerations']['ui_game_difficulty'])
    ui_game_mode_enum = enum(settings['user_interface']['enumerations']['ui_game_mode'])
    ui_game_state_enum = enum(settings['user_interface']['enumerations']['ui_game_state'])
    ui_goal_enum = enum(settings['user_interface']['enumerations']['ui_goal_scored'])
    ui_rx_enum = enum(settings['user_interface']['enumerations']['ui_rx'])
    ui_screen_enum = enum(settings['user_interface']['enumerations']['ui_screen'])
    ui_state_cmd_enum = enum(settings['user_interface']['enumerations']['ui_state_cmd'])
    ui_state_enum = enum(settings['user_interface']['enumerations']['ui_state'])
    ui_tx_enum = enum(settings['user_interface']['enumerations']['ui_tx'])

def get_settings():
    """Load settings saved in JSON file"""
    global fiducial_lower_hsv
    global fiducial_upper_hsv
    global puck_lower_hsv
    global puck_upper_hsv
    global game_mode
    global game_difficulty
    global game_length

    # get settings from file
    with open((settings_filepath + 'settings.json'), 'r') as fp:
        settings = json.load(fp)
        fp.close()

    fiducial_lower_hsv = (settings['puck_tracker']['fiducial']['color']['hue']['lower'],
                          settings['puck_tracker']['fiducial']['color']['sat']['lower'],
                          settings['puck_tracker']['fiducial']['color']['val']['lower'])
    fiducial_upper_hsv = (settings['puck_tracker']['fiducial']['color']['hue']['upper'],
                          settings['puck_tracker']['fiducial']['color']['sat']['upper'],
                          settings['puck_tracker']['fiducial']['color']['val']['upper'])

    puck_lower_hsv = (settings['puck_tracker']['puck']['color']['hue']['lower'],
                      settings['puck_tracker']['puck']['color']['sat']['lower'],
                      settings['puck_tracker']['puck']['color']['val']['lower'])
    puck_upper_hsv = (settings['puck_tracker']['puck']['color']['hue']['upper'],
                      settings['puck_tracker']['puck']['color']['sat']['upper'],
                      settings['puck_tracker']['puck']['color']['val']['upper'])

    game_mode = settings['user_interface']['game_mode']
    game_difficulty = settings['user_interface']['game_difficulty']
    game_length = settings['user_interface']['game_length']

def update_fiducial_values():
    """Update things. TODO: Fix this"""
    global fiducial_lower_hsv
    global fiducial_upper_hsv
    
    with open((settings_filepath + "settings.json"), 'r') as fp:
        settings = json.load(fp)
        fp.close()
    
    settings['puck_tracker']['fiducial']['color']['hue']['lower'] = int(fiducial_lower_hsv[0])
    settings['puck_tracker']['fiducial']['color']['sat']['lower'] = int(fiducial_lower_hsv[1])
    settings['puck_tracker']['fiducial']['color']['val']['lower'] = int(fiducial_lower_hsv[2])
    settings['puck_tracker']['fiducial']['color']['hue']['upper'] = int(fiducial_upper_hsv[0])
    settings['puck_tracker']['fiducial']['color']['sat']['upper'] = int(fiducial_upper_hsv[1])
    settings['puck_tracker']['fiducial']['color']['val']['upper'] = int(fiducial_upper_hsv[2])
    
    with open((settings_filepath + "settings.json"), 'w+') as fp:
        json.dump(settings, fp, indent=4)
        fp.close()

def update_puck_values():
    """Update things. TODO: Fix this"""
    with open((settings_filepath + "settings.json"), 'r') as fp:
        settings = json.load(fp)
        fp.close()
    
    settings['puck_tracker']['puck']['color']['hue']['lower'] = int(puck_lower_hsv[0])
    settings['puck_tracker']['puck']['color']['sat']['lower'] = int(puck_lower_hsv[1])
    settings['puck_tracker']['puck']['color']['val']['lower'] = int(puck_lower_hsv[2])
    settings['puck_tracker']['puck']['color']['hue']['upper'] = int(puck_upper_hsv[0])
    settings['puck_tracker']['puck']['color']['sat']['upper'] = int(puck_upper_hsv[1])
    settings['puck_tracker']['puck']['color']['val']['upper'] = int(puck_upper_hsv[2])
    
    with open((settings_filepath + "settings.json"), 'w+') as fp:
        json.dump(settings, fp, indent=4)
        fp.close()

def update_game_settings():
    """Update things. TODO: Fix this"""
    global game_difficulty
    global game_mode
    global game_length
    
    with open((settings_filepath + "settings.json"), 'r') as fp:
        settings = json.load(fp)
        fp.close()
    
    settings['user_interface']['game_mode'] = game_mode
    settings['user_interface']['game_difficulty'] = game_difficulty
    settings['user_interface']['game_length'] = game_length
    
    with open((settings_filepath + "settings.json"), 'w+') as fp:
        json.dump(settings, fp, indent=4)
        fp.close()

'''
def update_paddle_position():
    
    with open((settings_path + "settings.json"), 'r') as fp:
        settings = json.load(fp)
        fp.close()
    
    #debugging
    ui_tx[ui_tx_enum.paddle_position_x] = 120
    ui_tx[ui_tx_enum.paddle_position_y] = 20
    
    with open((settings_path + "settings.json"), 'w+') as fp:
        json.dump(settings, fp, indent=4)
        fp.close()
'''

##############################################################################################
# Main Process
##############################################################################################
def ui_process(ui_rx, ui_tx, visualization_data):
    """All things user interface happen here. Communicates directly with master controller"""
    global ui_state
    global ui_error

    get_enums()
    get_settings()

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
            visualization_data.close()
            quit(0)