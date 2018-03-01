from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.uix.boxlayout import BoxLayout
import cv2
import perspective_correction as pc
import puck_tracker as pt

class Camera(Image):
    def __init__(self, capture, fps, **kwargs):
        super(Camera, self).__init__(allow_stretch = True,**kwargs)
        self.capture = capture
	self.fiducials = pc.retrieve_fiducials()
	self.puckLowerHSV, self.puckUpperHSV = pt.retrieve_puck_color()
        Clock.schedule_interval(self.update, 1.0 / fps)

    def update(self, dt):
        ret, frame = self.capture.read()
	frame = pc.perspective_correction(frame, self.fiducials)
	frame, puckCenter = pt.track_puck(frame, self.puckLowerHSV, self.puckUpperHSV)
        if ret:
            # convert it to texture
            frameRGB = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            buf1 = cv2.flip(frameRGB, 0)
            buf = buf1.tostring()
            image_texture = Texture.create(
                size=(frame.shape[1], frame.shape[0]), colorfmt='rgb')
            image_texture.blit_buffer(buf, colorfmt='rgb', bufferfmt='ubyte')
            # display image from the texture
            self.texture = image_texture

class UiApp(App):
    def build(self):
        self.capture = cv2.VideoCapture(0)
	success = pc.find_fiducials(self.capture)
        camera = Camera(capture=self.capture, fps=120)
        root = BoxLayout(orientation='horizontal')
        root.add_widget(Button(text="<-", size_hint=(0.1,1)))
        root.add_widget(camera)
        root.add_widget(Button(text="->", size_hint=(0.1,1)))
        return root

if __name__ == '__main__':
    UiApp().run()
