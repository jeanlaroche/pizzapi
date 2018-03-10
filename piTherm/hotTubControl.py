import displayControl as dc
import time, os
import pygame
import json
import urllib2
from threading import Thread
import logging

def readUrl(url):
    # Returns a dict from the URL.
    return json.loads(urllib2.urlopen(url).read())

class HotTubControl(object):
    
    targetTemp = 0
    hotTubTemp = 0
    hotTubOn = 'OFF'
    hotTubURL = 'http://hottub.mooo.com/'
    lightsURL = 'http://rfjl.mooo.com/'
    hc = None
    
    def __init__(self,display,hc):
        self.hc = hc
        self.display = hc.display
        self.doUpdate = 0
        
        def updateLoop():
            if self.doUpdate:
                self.getTubStatus()
                self.showStatus()
            time.sleep(1)
        
        self.updateLoopThread = Thread(target=updateLoop, args=(), group=None)
        self.updateLoopThread.daemon = True
        logging.info("Starting hottub update thread")
        self.updateLoopThread.start()
    
    def getTubStatus(self):
        try:
            # This is to allow controlling the temp!
            urllib2.urlopen(self.hotTubURL+'Pook').read()
            status = readUrl(self.hotTubURL+'_getTubStatus')
            self.targetTemp = status['targetTemperatureValue']
            self.hotTubTemp = status['temperatureValue']
            self.hotTubOn = status['heaterValueStr']
            logging.info('Tub status: target %d actual %d',self.targetTemp,self.hotTubTemp)
        except Exception as e:
            logging.error('Error reading tub status: %s',e)
        
    def draw(self,highlightButton=-1):
        logging.info('HotTubControl: draw!')
        self.display.screen.fill(dc.black)
        self.display.allButtons = []
        # Draw buttons:
        self.drawButtons(highlightButton)
        self.getTubStatus()
        self.showStatus()
        self.display.rectList = [[0,0,self.display.xSize,self.display.ySize]]
    
    def showStatus(self):
        # Show hot tub stuff
        startX=50
        startY=50
        height = 50
        gap = -10
        self.display.make_label("Target  {}F".format(self.targetTemp), startX, startY, height, dc.npeacock,fullLine=1)
        startY += height+gap
        self.display.make_label("Actual  {}F".format(self.hotTubTemp), startX, startY, height, dc.npeacock,fullLine=1)
        startY += height+gap
        thisColor = dc.red if self.hotTubOn == 'ON' else dc.ngreen
        self.display.make_label("Hot tub is {}".format(self.hotTubOn), startX, startY, height, dc.npeacock,fullLine=1)
        
    def drawButtons(self,highlightButton=-1):
        buttX=120
        buttY=50
        margin=10
        startX = margin
        colors = [dc.nocre]*5
        if highlightButton != -1: colors[highlightButton] = dc.nred
        self.display.make_button("UP",startX,self.display.ySize-2*buttY-2*margin, buttX, buttY, colors[0])
        startX += buttX+margin
        self.display.make_button("DOWN",startX,self.display.ySize-2*buttY-2*margin, buttX, buttY, colors[1])
        startX += buttX+margin
        startX = margin
        self.display.make_button("Done",startX,self.display.ySize-buttY-margin, buttX, buttY, colors[2])
        startX += buttX+margin
        self.display.make_button("Lights",startX,self.display.ySize-buttY-margin, buttX, buttY, colors[3])
        startX += buttX+margin
        
    def onButton(self,button):
        if button == 0:
            logging.info('Raise target')
            readUrl(self.hotTubURL+'_tempUp')
        if button == 1:
            logging.info('Decrease target')
            readUrl(self.hotTubURL+'_tempDown')
        if button == 2:
            logging.info('Return!')
            self.hc.showHotTub = 0
            self.doUpdate = 0
            self.hc.draw()
            return
        if button == 3:
            logging.info('Turn all lights off')
            urllib2.urlopen(self.lightsURL+'lightOnOff/100/0')
            urllib2.urlopen(self.lightsURL+'lightOnOff/102/0')
        self.getTubStatus()
        self.showStatus()
