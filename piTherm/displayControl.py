import sys, pygame
from pygame.locals import *
import time
import subprocess
import os
from subprocess import *
os.environ["SDL_FBDEV"] = "/dev/fb1"


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
        # While loop to manage touch self.screen inputs
        while 1:
            try:
                for event in pygame.event.get():
                    print event.type
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        print "self.screen pressed" #for debugging purposes
                        pos = (pygame.mouse.get_pos() [1], pygame.mouse.get_pos() [0])
                        print pos #for checking
                        pygame.draw.circle(self.screen, white, pos, 2, 0) #for debugging purposes - adds a small dot where the self.screen is pressed
                        #on_click()
                        self.on_touch()
                time.sleep(0.01)
                pygame.display.update()
            except:
                pygame.quit()
                break
        
if __name__ == '__main__':
    dc = displayControl()
    dc.draw()
    dc.eventLoop()