import sys, pygame
from pygame.locals import *
import time
import subprocess
import os
from subprocess import *

inputDev = "/dev/input/event0"
os.environ["SDL_FBDEV"] = "/dev/fb1"
os.environ["SDL_MOUSEDRV"] = "TSLIB"
os.environ["SDL_MOUSEDEV"] = inputDev
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

    ts_read_raw = tslib.ts_read_raw
    ts_read_raw.restype = c_int
    ts_read_raw.argtypes = [POINTER(tsdev), POINTER(ts_sample), c_int]

    ts_open = tslib.ts_open
    ts_open.restype = POINTER(tsdev)
    ts_open.argtypes = [c_char_p, c_int]

    ts_close = tslib.ts_close
    ts_close.restype = c_int
    ts_close.argtypes = [POINTER(tsdev)]

    ts_config = tslib.ts_config
    ts_config.restype = c_int
    ts_config.argtype = [POINTER(tsdev)]

    doNotBlock = 1
    ts = ts_open(inputDev, doNotBlock)
    if ts == 0:
        exit("ts_open failed")

    if ts_config(ts):
        exit("ts_config failed")
    return ts,ts_read,ts_close


class displayControl(object):

    xSize = 480
    ySize = 320
    fontSize = 80
    stopNow = 0
    allButtons = []
    firstDownPos = [0,0]
    down = 0

    def __init__(self,touchCallback = None):
        # Initialize pygame and hide mouse
        pygame.init()
        size = width, height = self.xSize, self.ySize
        self.screen = pygame.display.set_mode(size)
        pygame.mouse.set_visible(0)
        self.ts, self.ts_read, self.ts_close = initTsLib()
        self.touchCallback = touchCallback

    def close(self):
        print "Closing display"
        self.stopNow=1
        self.ts_close(self.ts)

    def getTSEvent(self,):
        s = ts_sample()
        if self.ts_read(self.ts, byref(s), 1):
            return s
        else:
            return None

    def onTouch(self,s):
        if self.touchCallback: self.touchCallback(s,self.down)

    # define function for printing text in a specific place with a specific width and height with a specific colour and border
    def make_button(self, text, xpo, ypo, width, height, colour):
        font=pygame.font.Font(None,42)
        label=font.render(str(text), 1, (colour))
        self.screen.blit(label,(xpo,ypo))
        pygame.draw.rect(self.screen, green, (xpo-10,ypo-10,width,height),3)
        button = {'x':xpo,'y':ypo,'dx':width,'dy':height}
        self.allButtons.append(button)

    def findHit(self,s):
        x,y=s.x,s.y
        for ii,but in enumerate(self.allButtons):
            if x>but['x'] and x < but['x']+but['dx'] and y>but['y'] and y < but['y']+but['dy']:
                return ii
        else: return -1

    # define function for printing text in a specific place with a specific colour
    def make_label(self, text, xpo, ypo, fontSize, colour):
        font=pygame.font.Font(None,fontSize)
        label=font.render(str(text), 1, (colour))
        self.screen.blit(label,(xpo,ypo))

    def make_circle(self,text,xpo,ypo,radius,colour):
        self.make_label(text,xpo-45,ypo-45,120,green)
        pygame.draw.circle(self.screen,red,(xpo,ypo),100,10)


    def draw(self):
        # Set up the base menu you can customize your menu with the colors above
        # Background Color
        self.screen.fill(black)
        
        # Outer Border
        pygame.draw.rect(self.screen, green, (0,0,self.xSize,self.ySize),10)
        
        # Buttons and labels
        # First Row
        self.make_circle("76",self.xSize/2,self.ySize/2,100,red)
        # self.make_label("Room Temp: 70F", 20, 20, self.fontSize, red)
        # self.make_button("Menu Item 1", 30, self.ySize-80, 55, 210, green)
        # self.make_label("Room Temp: 70F", 20, 20, self.fontSize, red)
        # self.make_button("Menu Item 1", 30, self.ySize-80, 55, 210, green)

    def update(self):
        pygame.display.update()

    def eventLoop(self):
        import pdb
        # While loop to manage touch self.screen inputs
        self.stopNow = 0
        prevPress = 0
        lastT = 0
        off = ts_sample()
        timeThresh = 0.100
        self.down = 0
        skip = 0
        toSkip = 3
        A = [[]]*10
        while 1:
            try:
                pygame.display.update()
                for ii in range(4):
                    A[ii] = self.getTSEvent()
                    #print A[ii]
                s = A[0]
                if s:
                    skip += 1
                    #print s.x, s.y, s.pressure
                    if self.down == 0:
                        skip = 0
                    if skip == toSkip:
                        self.firstDownPos = (s.x,s.y)
                        print "FIRST {}".format(s.y)
                    self.down = 1
                    if skip >= toSkip:
                        self.onTouch(s)
                    lastT = time.time()
                elif time.time()-lastT > timeThresh and self.down == 1:
                    self.down = 0
                    self.onTouch(off)
                # print "{} {} ".format(lastT,time.time())

                if self.stopNow: break
            except:
                pygame.quit()
                break
        
if __name__ == '__main__':
    dc = displayControl()
    dc.draw()
    dc.eventLoop()