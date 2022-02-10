import PySimpleGUI as sg

from tkinter import *
from tkinter import messagebox, ttk, font
from functools import partial

sg.theme("Python")

fontName = "Helvetica"

class UI():
    def __init__(self,server):
        self.height,self.width = 480,800
        self.server = server
        self.useC = 1

    def finishInit(self,no_titlebar=1):
        fontParams = {'font':(fontName, 14)}
        self.no_titlebar = no_titlebar
        self.tabMain = self.initPanelMain()
        self.tabAux1 = self.initPanelAux1()
        self.tabAux2 = self.initPanelAux2()
        self.layout = [[sg.TabGroup([[sg.Tab('Main', self.tabMain), sg.Tab('PWM and PID', self.tabAux1), sg.Tab('Status', self.tabAux2)]],**fontParams)]]
        self.window = sg.Window('PIZZA CONTROL', self.layout, default_element_size=(44, 10),default_button_element_size=(60,3),element_padding=5,finalize=1,size=(self.width,self.height),no_titlebar = no_titlebar)

    def initPanelMain(self):
        fontParams = {'font':(fontName, 16)}
        params = {'size':(10,1),'font':(fontName, 28)}
        paramsButs = {'size':(9,1),'font':(fontName, 28)}
        self.topTarget = sg.T("Target",**params)
        self.botTarget = sg.T("Target",**params)
        self.topTemp = sg.T("Temp",**params)
        self.botTemp = sg.T("Temp",**params)
        self.topPWM = sg.T("PWM",**params)
        self.botPWM = sg.T("PWM",**params)
        self.power = sg.Button("Power",size=(10,3),font=(fontName, 25))
        paramsSilders = {'range':(0,400),'orientation':'h','enable_events':1}
        paramsSilders.update(fontParams)
        self.tabMain = [
            [sg.Frame('Target temps',layout=[
            # [sg.Button('Top +',**paramsButs,key='TTU'),sg.Button('Top -',**paramsButs,key='TTD'),self.topTarget],
            # [sg.Button('Bot +',**paramsButs,key='BTU'), sg.Button('Bot -',**paramsButs,key='BTD'), self.botTarget]
            [sg.Slider(**paramsSilders,default_value=self.server.topPID.targetTemp,key='TTS'),self.topTarget],
            [sg.Slider(**paramsSilders,default_value=self.server.botPID.targetTemp,key='BTS'), self.botTarget]
            ],**fontParams)],
            [sg.Frame('Current temps',layout=[
            [self.topTemp, self.topPWM],
            [self.botTemp, self.botPWM]],**fontParams),self.power],
#            [self.power]
        ]
        return self.tabMain

    def initPanelAux1(self):
        fontParams = {'font':(fontName, 16)}
        params = {'size':(15,1)}
        params.update(fontParams)
        paramsSilders = {'range':(0,1),'resolution':0.01,'orientation':'h','font':(fontName, 20),
                         'enable_events':1}
        self.topMaxPWM = sg.T("Top Max PWM",**params)
        self.botMaxPWM = sg.T("Top Max PWM",**params)
        A = sg.Frame('MAX PWM',
                     [
                      # [sg.Button('Top +',**params,key='TUM'),sg.Button('Top -',**params,key='TDM'),self.topMaxPWM],
                      # [sg.Button('Bot +',**params,key='BUM'),sg.Button('Bot -',**params,key='BDM'),self.botMaxPWM]
                      [sg.Slider(**paramsSilders,key='TMS',default_value  = self.server.topMaxPWM),self.topMaxPWM],
                      [sg.Slider(**paramsSilders,key='BMS',default_value  = self.server.botMaxPWM),self.botMaxPWM]
                     ],**fontParams)
        paramsSilders['range'] = (0,10)
        B = sg.Frame('PID',
                     [[sg.Frame('Top P',[[sg.Slider(default_value  = self.server.topPID.p, **paramsSilders, key='TP')]]),
                       sg.Frame('Top D',[[sg.Slider(default_value  = self.server.topPID.d, **paramsSilders, key='TD')]])
                       ],
                     [
                       sg.Frame('Bot P',[[sg.Slider(default_value  = self.server.botPID.p, **paramsSilders, key='BP')]]),
                       sg.Frame('Bot D',[[sg.Slider(default_value  = self.server.botPID.d, **paramsSilders, key='BD')]])
                     ]],**fontParams)
        self.tabAux1 = [[A],[B]]
        return self.tabAux1

    def initPanelAux2(self):
        params = {'size':(12,1),'font':(fontName, 28)}
        self.ipAddress = sg.T("IP",**params)
        self.C = sg.Radio("Celcius",0,default=self.useC,enable_events=1,key='cel',**params)
        self.F = sg.Radio("Fahrenheit",0,default=not self.useC,enable_events=1,key='fah',**params)
        #self.C = sg.Radio("Celcius",0,default=self.useC,key='cel',**params)
        #self.F = sg.Radio("Fahrenheit",0,default=not self.useC,key='fah',**params)
        self.ambientTemp = sg.T("Ambient",**params)
        self.tabAux2 = [
            [sg.Frame("",[[self.ipAddress]])],
            [sg.Frame("",[[self.C],[self.F]])],
            [sg.T("Ambient temp",font=(fontName, 28)),self.ambientTemp],
            [sg.Button("Show Desktop" if self.no_titlebar else "Maximize",**params,key="maximize")]
            ]
        return self.tabAux2

    def cvTemp(self,temp):
        return f" {temp:.0f} C" if self.useC else f" {temp*1.8+32:.0f} F"

    def setTargetTemps(self,topTemp,botTemp):
        self.topTarget.update(value=f"Target" + self.cvTemp(topTemp))
        self.botTarget.update(value=f"Target" + self.cvTemp(botTemp))

    def setMaxPWM(self,topMaxPWM,botMaxPWM):
        self.topMaxPWM.update(value=f" {topMaxPWM:.2f}")
        self.botMaxPWM.update(value=f" {botMaxPWM:.2f}")

    def setCurTemps(self,topTemp,botTemp,topPWM,botPWM,isOnOff,ambientTemp):
        self.topTemp.update(value=f"TOP " + self.cvTemp(topTemp))
        self.botTemp.update(value=f"BOT " + self.cvTemp(botTemp))
        self.topPWM.update(value=f"PWM {topPWM:.2f}")
        self.botPWM.update(value=f"PWM {botPWM:.2f}")
        self.power.update(text = "TURN POWER OFF" if isOnOff else "TURN POWER ON")
        self.power.update(button_color = ('red',None) if isOnOff else ('black',None))
        self.ambientTemp.update(value = self.cvTemp(ambientTemp))

    def setIPAddress(self,ipAdd):
        self.ipAddress.update(value=f"IP Address: {ipAdd}")

    # find button callback
    def hello(self):
      messagebox.showinfo("Hello", "Callback worked!")

    def mainLoop(self):
        while True:
            event, values = self.window.read()
            print(event, values)
            if event == "TTU": self.server.incTemp(0,5)
            if event == "TTD": self.server.incTemp(0,-5)
            if event == "BTU": self.server.incTemp(1,5)
            if event == "BTD": self.server.incTemp(1,-5)
            if event == "TUM": self.server.incMaxPWM(0,.05)
            if event == "TDM": self.server.incMaxPWM(0,-.05)
            if event == "BUM": self.server.incMaxPWM(1,.05)
            if event == "BDM": self.server.incMaxPWM(1,-.05)
            if event == "Power": self.server.onOff()
            if event == "cel": self.useC = 1
            if event == "fah": self.useC = 0
            if event == "cel" or event == 'fah':
                self.server.dirty = 1
            if event in ['TP','TD','BP','BD']:
                self.server.setPID((values[i] for i in ['TP','TD','BP','BD']))
            if event in ['TMS','BMS']:
                self.server.setMaxPWM((values[i] for i in ['TMS','BMS']))
            if event in ['TTS','BTS']:
                self.server.setTemps((values[i] for i in ['TTS','BTS']))
            if event == "maximize":
                self.window.close()
                self.finishInit(no_titlebar=1-self.no_titlebar)
            # if event == "Read": self.setTargetTemps(35,56)
            # if event == "Read": self.setCurTemps(20,25,.8,.9,1)
            # if event == "Read": self.setIPAddress("192.168.1.100")
            if event == sg.WIN_CLOSED:  # always,  always give a way out!
                break


if __name__ == '__main__':
    class P:
        p=0
        d=1
        targetTemp = 50
    class S:
        topPID = P()
        botPID = P()
        topMaxPWM=1
        botMaxPWM=.5
        pass
    ui = UI(S)
    ui.finishInit()
    ui.mainLoop()
