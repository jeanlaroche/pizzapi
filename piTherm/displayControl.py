import sys, pygame
from pygame.locals import *
import time, signal
from signal import alarm, signal, SIGALRM, SIGKILL
import subprocess
import os
from subprocess import *
from threading import Timer, Thread
import numpy as np
import exifread

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

nblue = (31, 155, 186) # blue
ngreen = (36, 173, 82) # (green) 
nred = (255, 96, 38) #(red) 
nteal = (29, 71, 224) # blue 
nocre = (154, 193, 25) # (moutarde?). 
npeacock = (51,161,201)  # peacock
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
    rectList = []
    bckColor = black
    hc = None

    def __init__(self,touchCallback = None,heatercontrol=None):
        # Initialize pygame and hide mouse
        self.hc = heatercontrol
        print "Initpygame"
        size = width, height = self.xSize, self.ySize
        print "set mode"
        class Alarm(Exception):
            pass
        def alarm_handler(signum, frame):
            raise Alarm
        signal(SIGALRM, alarm_handler)
        alarm(5)
        try:
            pygame.init()
            self.screen = pygame.display.set_mode(size) 
            alarm(0)
        except Alarm:
            raise KeyboardInterrupt
        print "Mouse"
        pygame.mouse.set_visible(0)
        print "tslib"
        self.ts, self.ts_read, self.ts_close = initTsLib()
        self.touchCallback = touchCallback
        print "Done"

    def close(self):
        print "Closing display"
        self.stopNow=1
        self.ts_close(self.ts)
        pygame.quit()

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
        R = [xpo-10,ypo-10,width,height]
        self.screen.fill(self.bckColor,R)
        font=pygame.font.Font(None,42)
        label=font.render(str(text), 1, (colour))
        self.screen.blit(label,(xpo,ypo))
        pygame.draw.rect(self.screen, ngreen, R,3)
        button = {'x':xpo,'y':ypo,'dx':width,'dy':height}
        self.allButtons.append(button)
        self.rectList.append(R)

    def findHit(self,s):
        x,y=s.x,s.y
        for ii,but in enumerate(self.allButtons):
            if x>but['x'] and x < but['x']+but['dx'] and y>but['y'] and y < but['y']+but['dy']:
                return ii
        else: return -1

    # define function for printing text in a specific place with a specific colour
    def make_label(self, text, xpo, ypo, fontSize, colour, fullLine = 0,noBack=0):
        font=pygame.font.Font(None,fontSize)
        if fullLine: text += ' '*300
        label=font.render(str(text), 1, (colour))
        if not noBack: self.screen.fill(self.bckColor,label.get_rect().move(xpo,ypo))
        self.rectList.append(self.screen.blit(label,(xpo,ypo)))

    def make_circle(self,text,xpo,ypo,radius,colour):
        R = [xpo-radius,ypo-radius,2*radius,2*radius]
        self.screen.fill(self.bckColor,R)
        self.make_label(text,xpo-78,ypo-54,120,ngreen)
        pygame.draw.circle(self.screen,nred,(xpo,ypo),100,10)
        self.rectList.append(R)
    
    def make_disk(self,xpo,ypo,radius,colour):
        R = [xpo-radius,ypo-radius,2*radius,2*radius]
        self.screen.fill(self.bckColor,R)
        pygame.draw.circle(self.screen,colour,(xpo,ypo),radius,0)
        self.rectList.append(R)

    def displayJPEG(self,imagePath,finalCheckFun):
        import pdb
        if not imagePath: return
        # pdb.set_trace()
        dateTaken = ''
        try:
            with open(imagePath, 'rb') as fh:
                tags = exifread.process_file(fh, stop_tag="EXIF DateTimeOriginal")
                dateTaken = tags["EXIF DateTimeOriginal"]
                dateTaken = str(dateTaken).split()[0]
            print "{} : {}".format(imagePath,dateTaken)
            img=pygame.image.load(imagePath)
            # Rescale by the larger of the two x/y factors.
            #fact = np.max(np.array(img.get_size())/np.array([self.xSize,self.ySize]))
            fact = np.max([1.*self.xSize/img.get_size()[0],1.*self.ySize/img.get_size()[1]])
            newSize = [int(fact*img.get_size()[0]),int(fact*img.get_size()[1])]
            imgsc = pygame.transform.smoothscale(img, newSize)
            # Now, if imgsc.get_size() is a lot more vertical than the screen, let's scroll
            vOffset = int((imgsc.get_size()[1]-self.ySize)*.3)
            # This is a kludge
            if finalCheckFun():
                self.screen.blit(imgsc,(0,0),area=[0,vOffset,self.xSize,self.ySize])
                self.make_label(dateTaken,10,self.ySize-40,30,nred,noBack = 1)
                self.rectList.append([0,0,self.xSize,self.ySize])
            # JEAN: THIS SHOULD NOT BE CALLED HERE< I DON"T THINK.
            #pygame.display.update()
        except:
            pass
        
    def draw(self):
        # Set up the base menu you can customize your menu with the colors above
        # Background Color
        self.screen.fill(self.bckColor)
        
        # Outer Border
        pygame.draw.rect(self.screen, ngreen, (0,0,self.xSize,self.ySize),10)
        
        # Buttons and labels
        # First Row
        self.make_circle("76",self.xSize/2,self.ySize/2,100,nred)
        self.make_label("Room Temp: 70F", 20, 20, self.fontSize, nred)
        self.make_button("Foo", 30, self.ySize-80, 55, 65, ngreen)
        # self.make_label("Room Temp: 70F", 20, 20, self.fontSize, red)
        # self.make_button("Menu Item 1", 30, self.ySize-80, 55, 210, green)

    def update(self):
        if len(self.rectList): 
            pygame.display.update(self.rectList)
            #print self.rectList
        self.rectList = []
        
    def startLoop(self,hc):
        # Start two loops in two different threads.
        def _eventLoop():
            self.eventLoop()
        self.touchThread = Thread(target=_eventLoop, args=(), group=None)
        self.touchThread.daemon = True
        hc.mprint("Starting touch thread")
        self.touchThread.start()
        def _displayLoop():
            while self.stopNow == 0:
                self.update()
                time.sleep(0.1)
                
        self.displayThread = Thread(target=_displayLoop, args=(), group=None)
        self.displayThread.daemon = True
        hc.mprint("Starting display thread")
        self.displayThread.start()
        hc.mprint("DisplayControl starting done")

    def eventLoop(self):
        import pdb
        # While loop to manage touch self.screen inputs
        self.stopNow = 0
        prevPress = 0
        lastT = 0
        off = ts_sample()
        timeThresh = 0.100
        self.down = 0
        A = [[]]*10
        while 1:
            try:
                s=None
                # I don't know that this is needed!
                s = self.getTSEvent()
                # for ii in range(2):
                    # a = self.getTSEvent()
                    # if a: s=a
                    # else: break
                if s and s.x >= 0 and s.y >= 0:
                    #print s.x, s.y, s.pressure
                    if self.down == 0:
                        self.firstDownPos = (s.x,s.y)
                        #print "FIRST {}".format(s.y)
                    self.down = 1
                    self.onTouch(s)
                    lastT = time.time()
                elif time.time()-lastT > timeThresh and self.down == 1:
                    self.down = 0
                    self.onTouch(off)
                    print "UP"
                # print "{} {} ".format(lastT,time.time())

                if self.stopNow: break
                time.sleep(0.001)
            except:
                self.hc.mprint("ERROR IN TOUCH LOOP")
                pass
                
if __name__ == '__main__':
    dc = displayControl()
    import time
    tic = time.time()
    N = 500
    import pdb
    dc.draw()
    dc.update()
    for ii in range(N):
        #pdb.set_trace()
        dc.screen.fill(dd.bckColor)
        dc.make_circle("{}".format(ii),100,100,30,30)
        #dc.make_button("Menu Item 1", 30, dc.ySize-80, 55, 65, ngreen)
        #dc.draw()
        pygame.display.update(dc.rectList)
        dc.rectList = []
    toc = time.time()
    print "Elapsed: {:.2f}s {:.0f} per second".format(toc-tic,N*1./(toc-tic))
    # dc.eventLoop()
