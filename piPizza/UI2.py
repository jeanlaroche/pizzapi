import PySimpleGUI as sg

from tkinter import *
from tkinter import messagebox, ttk, font
from functools import partial

class UI():
    def __init__(self,server):
        self.tabMain = self.initPanelMain()
        self.tabAux1 = [[sg.T('Aux1')],[sg.In(key='in')]]
        self.layout = [[sg.TabGroup([[sg.Tab('Tab 1', self.tabMain, tooltip='tip'), sg.Tab('Tab 2', self.tabAux1)]],
                               tooltip='TIP2')], [sg.Button('Read')]]
        self.window = sg.Window('PIZZA CONTROL', self.layout, default_element_size=(44, 10),default_button_element_size=(60,3),element_padding=5)
        self.height,self.width = 480,800
        self.server = server

    def initPanelMain(self):
        params = {'size':(15,1),'font':("Helvetica", 35)}
        self.topTarget = sg.T("Target",**params)
        self.botTarget = sg.T("Target",**params)
        self.topTemp = sg.T("Temp",**params)
        self.botTemp = sg.T("Temp",**params)
        self.topPWM = sg.T("PWM",**params)
        self.botPWM = sg.T("PWM",**params)
        self.power = sg.Button("Power",**params)
        self.tabMain = [[sg.Frame('targets',layout=[
            [sg.Button('Top up',**params),sg.Button('Top down',**params),self.topTarget],
            [sg.Button('Bot up',**params), sg.Button('Bot down',**params), self.botTarget]
            ])],
            [sg.Frame('current',layout=[
            [self.topTemp, self.topPWM],
            [self.botTemp, self.botPWM]])],
            [self.power]
        ]
        return self.tabMain
        # POWER BUTTON:
        self.onOff = Button(parent, text="AAAA", command=lambda : self.server.onOff())
        self.onOff.grid(column=0, row=5, columnspan=2, rowspan=1,**padding)
        self.onOff['fg'] = 'black'

    def initPanelAux1(self):
        # https://riptutorial.com/tkinter/example/29713/grid--
        # https://www.tutorialspoint.com/python/python_gui_programming.htm
        parent = self.tabAux1
        height = 3
        ### ROW1
        self.btn = Button(parent, text="A",height=height)
        self.btn.grid(column=0,row=0,sticky="E W")
        self.btn = Button(parent, text="B",height=height)
        self.btn.grid(column=1,row=0,sticky="E W")

    def setTargetTemps(self,topTemp,botTemp):
        self.topTarget.update(value=f"Target {topTemp} C")
        self.botTarget.update(value=f"Target {botTemp} C")

    def setCurTemps(self,topTemp,botTemp,topPWM,botPWM,isOnOff):
        self.topTemp.update(value=f"TOP Current {topTemp:.0f} C")
        self.botTemp.update(value=f"BOT Current {botTemp:.0f} C")
        self.topPWM.update(value=f"PWM {topPWM:.2f}")
        self.botPWM.update(value=f"PWM {botPWM:.2f}")
        self.power.update(text = "TURN POWER OFF" if isOnOff else "TURN POWER ON")
        self.power.update(button_color = ('red',None) if isOnOff else ('black',None))


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
            if event == "Read": self.setTargetTemps(35,56)
            if event == "Read": self.setCurTemps(20,25,.8,.9,1)
            if event == sg.WIN_CLOSED:  # always,  always give a way out!
                break


if __name__ == '__main__':
    ui = UI(None)
    ui.mainLoop()
