import sys, pygame
from pygame.locals import *
import time
import subprocess
import os
from subprocess import *
os.environ["SDL_FBDEV"] = "/dev/fb1"
os.environ["SDL_MOUSEDRV"] = "TSLIBa"
os.environ["SDL_MOUSEDEV"] = "/dev/input/event2"
os.environ["TSLIB_CALIBFILE"] = "/etc/pointercal"
os.environ["TSLIB_CONFFILE"] = "/etc/ts.conf"

#colors     R    G    B
white   = (255, 255, 255)
red     = (255,   0,   0)
green   = (  0, 255,   0)
blue    = (  0,   0, 255)
black   = (  0,   0,   0)
cyan    = ( 50, 255, 255)
magenta = (255,   0, 255)
yellow  = (255, 255,   0)
orange  = (255, 127,   0)

from ctypes import *


class tsdev(Structure):
	pass

class timeval(Structure):
	_fields_ = [("tv_sec", c_long),
		("tv_usec", c_long)]

class ts_sample(Structure):
	_fields_ = [("x", c_int),
		("y", c_int),
		("pressure", c_uint),
		("tv", timeval)]

def initTsLib():
    tslib = cdll.LoadLibrary("libts-0.0.so.0")
    ts_read = tslib.ts_read
    ts_read.restype = c_int
    ts_read.argtypes = [POINTER(tsdev), POINTER(ts_sample), c_int]

    ts_open = tslib.ts_open
    ts_open.restype = POINTER(tsdev)
    ts_open.argtypes = [c_char_p, c_int]

    ts_close = tslib.ts_close
    ts_close.restype = c_int
    ts_close.argtypes = [POINTER(tsdev)]

    ts_config = tslib.ts_config
    ts_config.restype = c_int
    ts_config.argtype = [POINTER(tsdev)]


    ts = ts_open("/dev/input/event2", 0)
    if ts == 0:
        exit("ts_open failed")

    if ts_config(ts):
        exit("ts_config failed")
    return ts,ts_read,ts_close


class displayControl(object):

    xSize = 480
    ySize = 320
    fontSize = 80

    def __init__(self):
        # Initialize pygame and hide mouse
        pygame.init()
        size = width, height = self.xSize, self.ySize
        self.screen = pygame.display.set_mode(size)
        pygame.mouse.set_visible(0)
        self.ts, self.ts_read, self.ts_close = initTsLib()

    def getTSEvent(self,):
        s = ts_sample()
        if self.ts_read(self.ts, byref(s), 1) < 0:
            exit("ts_read_raw failed")
        # if s.pressure != 0:
        #     print s.x, s.y
        return s

    # define function for printing text in a specific place with a specific width and height with a specific colour and border
    def make_button(self, text, xpo, ypo, height, width, colour):
        font=pygame.font.Font(None,42)
        label=font.render(str(text), 1, (colour))
        self.screen.blit(label,(xpo,ypo))
        pygame.draw.rect(self.screen, blue, (xpo-10,ypo-10,width,height),3)

    # define function for printing text in a specific place with a specific colour
    def make_label(self, text, xpo, ypo, fontSize, colour):
        font=pygame.font.Font(None,fontSize)
        label=font.render(str(text), 1, (colour))
        self.screen.blit(label,(xpo,ypo))

    # define function that checks for touch location
    def on_touch(self,):
        # get the position that was touched
        touch_pos = (pygame.mouse.get_pos() [0], pygame.mouse.get_pos() [1])
        print touch_pos

    def draw(self):
        # Set up the base menu you can customize your menu with the colors above
        # Background Color
        self.screen.fill(black)
        
        # Outer Border
        pygame.draw.rect(self.screen, blue, (0,0,self.xSize,self.ySize),10)
        
        # Buttons and labels
        # First Row
        self.make_label("Room Temp: 70F", 20, 20, self.fontSize, red)
        self.make_button("Menu Item 1", 30, self.ySize-80, 55, 210, blue)

    def eventLoop(self):
        import pdb
        # While loop to manage touch self.screen inputs
        while 1:
            try:
                s = self.getTSEvent()
                print s.x,s.y
                # for event in pygame.event.get():
                #     print event.type
                #     if event.type == pygame.MOUSEBUTTONDOWN:
                #         #pdb.set_trace()
                #         print "self.screen pressed" #for debugging purposes
                #         pos1 = (pygame.mouse.get_pos() [0], pygame.mouse.get_pos() [1])
                #         pos = event.pos
                #         #pos = (pos[1],pos[0])
                #         print pos #for checking
                #         print pos1 #for checking
                #         pygame.draw.circle(self.screen, white, pos, 2, 0) #for debugging purposes - adds a small dot where the self.screen is pressed
                #         #on_click()
                #         #self.on_touch()
                # time.sleep(0.01)
                pygame.display.update()
            except:
                pygame.quit()
                break
        
if __name__ == '__main__':
    dc = displayControl()
    dc.draw()
    dc.eventLoop()