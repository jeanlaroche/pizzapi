import PySimpleGUI as sg

from tkinter import *
from tkinter import messagebox, ttk, font
from functools import partial

sg.theme("Python")

class UI():
    def __init__(self,server):
        self.height,self.width = 480,800
        self.server = server
        self.useC = 1
        self.tabMain = self.initPanelMain()
        self.tabAux1 = self.initPanelAux1()
        self.layout = [[sg.TabGroup([[sg.Tab('Tab 1', self.tabMain), sg.Tab('Tab 2', self.tabAux1)]])], [sg.Button('Read')]]
        self.window = sg.Window('PIZZA CONTROL', self.layout, default_element_size=(44, 10),default_button_element_size=(60,3),element_padding=5,finalize=1)

    def initPanelMain(self):
        params = {'size':(15,1),'font':("Helvetica", 25)}
        self.topTarget = sg.T("Target",**params)
        self.botTarget = sg.T("Target",**params)
        self.topTemp = sg.T("Temp",**params)
        self.botTemp = sg.T("Temp",**params)
        self.topPWM = sg.T("PWM",**params)
        self.botPWM = sg.T("PWM",**params)
        self.power = sg.Button("Power",**params)
        self.ambientTemp = sg.T("Ambient",**params)
        self.tabMain = [[sg.Frame('targets',layout=[
            [sg.Button('Top up',**params),sg.Button('Top down',**params),self.topTarget],
            [sg.Button('Bot up',**params), sg.Button('Bot down',**params), self.botTarget]
            ])],
            [sg.Frame('current',layout=[
            [self.topTemp, self.topPWM],
            [self.botTemp, self.botPWM]])],
            [self.ambientTemp],
            [self.power]
        ]
        return self.tabMain

    def initPanelAux1(self):
        params = {'size':(35,1),'font':("Helvetica", 25)}
        self.ipAddress = sg.T("IP",**params)
        self.C = sg.Radio("Celcius",0,default=self.useC,enable_events=1,key='cel',**params)
        self.F = sg.Radio("Fahrenheit",0,default=not self.useC,enable_events=1,key='fah',**params)
        #self.C = sg.Radio("Celcius",0,default=self.useC,key='cel',**params)
        #self.F = sg.Radio("Fahrenheit",0,default=not self.useC,key='fah',**params)
        self.tabAux1 = [[sg.Frame("",[[self.ipAddress]])],[sg.Frame("",[[self.C],[self.F]])]]
        return self.tabAux1

    def cvTemp(self,temp):
        return f" {temp:.0f} C" if self.useC else f" {temp*1.8+32:.0f} F"

    def setTargetTemps(self,topTemp,botTemp):
        self.topTarget.update(value=f"Target" + self.cvTemp(topTemp))
        self.botTarget.update(value=f"Target" + self.cvTemp(botTemp))

    def setCurTemps(self,topTemp,botTemp,topPWM,botPWM,isOnOff,ambientTemp):
        self.topTemp.update(value=f"TOP Current" + self.cvTemp(topTemp))
        self.botTemp.update(value=f"BOT Current" + self.cvTemp(botTemp))
        self.topPWM.update(value=f"PWM {topPWM:.2f}")
        self.botPWM.update(value=f"PWM {botPWM:.2f}")
        self.power.update(text = "TURN POWER OFF" if isOnOff else "TURN POWER ON")
        self.power.update(button_color = ('red',None) if isOnOff else ('black',None))
        self.ambientTemp.update(value = "Ambient temp" + self.cvTemp(ambientTemp))

    def setIPAddress(self,ipAdd):
        self.ipAddress.update(value=f"IP Address: {ipAdd}")


    def incTemp(self,p1,p2):
        print(f"INCTEMP {p1} {p2}")
        self.server.incTemp(p1,p2)

    # find button callback
    def hello(self):
      messagebox.showinfo("Hello", "Callback worked!")

    def mainLoop(self):
        while True:
            event, values = self.window.read()
            print(event, values)
            if event == "Top up": self.incTemp(0,5)
            if event == "Top down": self.incTemp(0,-5)
            if event == "Bot up": self.incTemp(1,5)
            if event == "Bot down": self.incTemp(1,-5)
            if event == "Power": self.server.onOff()
            if event == "cel": self.useC = 1
            if event == "fah": self.useC = 0
            if event == "Read": self.setTargetTemps(35,56)
            if event == "Read": self.setCurTemps(20,25,.8,.9,1)
            if event == "Read": self.setIPAddress("192.168.1.100")
            if event == sg.WIN_CLOSED:  # always,  always give a way out!
                break


if __name__ == '__main__':
    ui = UI(None)
    ui.mainLoop()
