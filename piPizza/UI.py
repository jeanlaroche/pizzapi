import PySimpleGUI as sg

sg.theme("Python")
fontName = "Helvetica"
import os, tkinter
import matplotlib.pyplot as pl
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg,NavigationToolbar2Tk
import matplotlib.dates as mdates
class UI():
    def __init__(self,server):
        self.height,self.width = 480,800
        self.server = server
        self.useC = 1
        self.lastPlotLen = 0
        self.canDraw = 0
        self.processLoop = None


    def finishInit(self,no_titlebar=0):
        fontParams = {'font':(fontName, 14)}
        self.no_titlebar = no_titlebar
        self.tabMain = self.initPanelMain()
        self.tabPWM = self.initPanelPWM()
        self.tabStatus = self.iniPanelStatus()
        self.tabPID = self.initPanelPID()
        self.tabPlot = self.initPanelPlot()
        self.layout = [[sg.TabGroup([[sg.Tab('Main', self.tabMain), sg.Tab('Max PWM', self.tabPWM), sg.Tab('PID', self.tabPID), sg.Tab('PLOT', self.tabPlot), sg.Tab('Status', self.tabStatus)]],**fontParams)]]
        self.window = sg.Window('PIZZA CONTROL', self.layout, default_element_size=(44, 10),default_button_element_size=(60,3),element_padding=5,finalize=1,size=(self.width,self.height),no_titlebar = no_titlebar,disable_close=1)
        # self.window.set_cursor("none")
        self.fig = pl.figure(dpi=100.,figsize=(7,3.5))
        self.tkcanvas = FigureCanvasTkAgg(self.fig, master=self.canvas.TKCanvas)
        self.tkcanvas.get_tk_widget().pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=1)
        toolbar = NavigationToolbar2Tk(self.tkcanvas, self.canvas.TKCanvas)
        toolbar.update()
        self.tkcanvas.get_tk_widget().pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=1)
        # Force an update from the server.
        #self.server.dirty = 1

    def initPanelMain(self):
        fontParams = {'font':(fontName, 16)}
        params = {'size':(10,1),'font':(fontName, 28)}
        self.topTarget = sg.T(self.cvTemp(self.server.topPID.targetTemp),**params)
        self.botTarget = sg.T(self.cvTemp(self.server.botPID.targetTemp),**params)
        self.topTemp = sg.T("Temp",**params)
        self.botTemp = sg.T("Temp",**params)
        self.topPWM = sg.T("PWM",**params)
        self.botPWM = sg.T("PWM",**params)
        self.onTime = sg.T("OnTime",**params)
        self.topTimeToTarget = sg.T("Time to target Top",**params)
        self.botTimeToTarget = sg.T("Time to target Bot",**params)
        self.power = sg.Button("Power",size=(10,3),font=(fontName, 25))#,image_filename="/home/pi/piPizza/power.png")
        paramsSilders = {'range':(20,400),'orientation':'h','enable_events':1,'resolution':5,'disable_number_display':1,'size':(25,30)}
        paramsSilders.update(fontParams)
        self.topTargetSlider = sg.Slider(**paramsSilders, default_value=self.server.topPID.targetTemp, key='TTS')
        self.botTargetSlider = sg.Slider(**paramsSilders,default_value=self.server.botPID.targetTemp,key='BTS')
        A = sg.Frame('Target temps',layout=[
            [self.topTargetSlider,self.topTarget],
            [self.botTargetSlider, self.botTarget]
            ],**fontParams,expand_x=1)
        B = sg.Frame('Current temps',layout=[
            [self.topTemp, self.topPWM],
            [self.botTemp, self.botPWM]],**fontParams,expand_x=1)
        C = sg.Frame('Time to target',layout=[
            [self.topTimeToTarget,self.botTimeToTarget]],**fontParams,expand_x=1)
        D = sg.Frame('Time since last on',layout=[[self.onTime]],**fontParams,expand_x=1)

        Col = sg.Column([[B],[C]])
        #self.tabMain = [ [A], [B,self.power], [C]]
        self.tabMain = [ [A], [Col,sg.Column([[self.power],[D]])]]
        return self.tabMain

    def initPanelPWM(self):
        fontParams = {'font':(fontName, 16)}
        params = {'size':(15,1)}
        params.update(fontParams)
        paramsSilders = {'range':(0,1),'resolution':0.05,'orientation':'h','font':(fontName, 20),
                         'enable_events':1,'size':(30,30)}
        self.topMaxPWM = sg.T("Top Max PWM",**params)
        self.botMaxPWM = sg.T("Top Max PWM",**params)
        A = sg.Frame('Top Max PWM',
                     [
                      [sg.Slider(**paramsSilders,key='TMS',default_value  = self.server.topMaxPWM)],
                     ],**fontParams)
        B = sg.Frame('Bot Max PWM',
                     [
                      [sg.Slider(**paramsSilders,key='BMS',default_value  = self.server.botMaxPWM)]
                     ],**fontParams)
        self.tabPWM = [[A],[B]]
        return self.tabPWM

    def initPanelPID(self):
        fontParams = {'font':(fontName, 16)}
        params = {'size':(15,1)}
        params.update(fontParams)
        paramsSilders = {'range':(0,10),'resolution':0.01,'orientation':'h','font':(fontName, 20),
                         'enable_events':1,'size':(20,30)}
        topKP = sg.Slider(default_value=self.server.topPID.kP, **paramsSilders, key='TP')
        topKD = sg.Slider(default_value=self.server.topPID.kD, **paramsSilders, key='TD')
        topKI = sg.Slider(default_value=self.server.topPID.kI, **paramsSilders, key='TI')
        botKP = sg.Slider(default_value=self.server.botPID.kP, **paramsSilders, key='BP')
        botKD = sg.Slider(default_value=self.server.botPID.kD, **paramsSilders, key='BD')
        botKI = sg.Slider(default_value=self.server.botPID.kI, **paramsSilders, key='BI')
        # A= [
        #     [sg.Frame('Top kP',[[topKP]],**fontParams),
        #     sg.Frame('Top kD',[[topKD]],**fontParams),
        #     sg.Frame('Top kI',[[topKI]],**fontParams)
        #     ],
        #     [
        #     sg.Frame('Bot kP',[[botKP]],**fontParams),
        #     sg.Frame('Bot kD',[[botKD]],**fontParams),
        #     sg.Frame('Bot kI',[[botKI]],**fontParams)
        #      ]
        # ]
        A= [
            [sg.Frame('Top kP',[[topKP]],**fontParams),
            sg.Frame('Bot kP',[[botKP]],**fontParams),
             ],
            [
            sg.Frame('Top kD',[[topKD]],**fontParams),
            sg.Frame('Bot kD',[[botKD]],**fontParams),
            ],
            [
            sg.Frame('Top kI',[[topKI]],**fontParams),
            sg.Frame('Bot kI',[[botKI]],**fontParams),
            ]
        ]
        self.tabPID = A
        return self.tabPID

    def initPanelPlot(self):
        params = {'size':(5,1),'font':(fontName, 16)}
        self.canvas = sg.Canvas()
        self.tabPlot = [[self.canvas],[sg.Button("clear",**params)]]
        return self.tabPlot

    def iniPanelStatus(self):
        params = {'size':(14,1),'font':(fontName, 28)}
        ipAddress = sg.T(self.server.ip,**params)
        self.C = sg.Radio("Celcius",0,default=self.useC,enable_events=1,key='cel',**params)
        self.F = sg.Radio("Fahrenheit",0,default=not self.useC,enable_events=1,key='fah',**params)
        self.ambientTemp = sg.T("Ambient",**params)
        self.tabStatus = [
            [sg.Frame("IP address",[[ipAddress]]),sg.Frame("Version",[[sg.T(self.server.version,**params)]])],
            [sg.Frame("Units",[[self.C],[self.F]])],
            [sg.T("Ambient temp",font=(fontName, 28)),self.ambientTemp],
            [sg.Button("Show PI Desktop" if self.no_titlebar else "Hide PI Desktop",**params,key="maximize"),
             sg.Button("Update / Restart",**params,key="update")],
            [sg.Button("Reboot", **params, key="reboot")],
            ]
        return self.tabStatus

    def cvTemp(self,temp):
        return f" {temp:.0f} C" if self.useC else f" {temp*1.8+32:.0f} F"

    def setTargetTemps(self,topTemp,botTemp):
        self.topTarget.update(value=self.cvTemp(topTemp))
        self.botTarget.update(value=self.cvTemp(botTemp))
        self.topTargetSlider.update(value=topTemp)
        self.botTargetSlider.update(value=botTemp)

    def setMaxPWM(self,topMaxPWM,botMaxPWM):
        pass

    def setCurTemps(self,topTemp,botTemp,topPWM,botPWM,isOnOff,ambientTemp,topTimeToTarget,botTimeToTarget,onTime):
        self.topTemp.update(value=f"TOP " + self.cvTemp(topTemp))
        self.botTemp.update(value=f"BOT " + self.cvTemp(botTemp))
        self.topPWM.update(value=f"PWM {topPWM:.2f}")
        self.botPWM.update(value=f"PWM {botPWM:.2f}")
        self.power.update(text = "TURN POWER OFF" if isOnOff else "TURN POWER ON")
        self.power.update(button_color = ('red',None) if isOnOff else ('black',None))
        self.ambientTemp.update(value = self.cvTemp(ambientTemp))
        self.topTimeToTarget.update(value=topTimeToTarget)
        self.botTimeToTarget.update(value=botTimeToTarget)
        self.onTime.update(value=onTime)

    def plotTemps(self,times,temps,legend):
        if len(times) == self.lastPlotLen: return
        self.lastPlotLen = len(times)
        self.times = times
        self.temps = temps
        self.legend = legend
        if len(self.times) >= 2: self.draw()

    def draw(self):
        try:
            pl.clf()
            X = mdates.datestr2num(self.times)
            for ii in range(len(self.temps)):
                temps = self.temps
                if not self.useC:
                    temps[ii] = [1.8 * t + 32 for t in temps[ii]]
                pl.plot(X, temps[ii])
            #locator = mdates.MinuteLocator(interval=10)
            locator = mdates.AutoDateLocator(interval_multiples=True,maxticks=5,minticks=2)
            #locator = mdates.MinuteLocator()
            pl.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            pl.gca().xaxis.set_major_locator(locator)
            pl.legend(self.legend)
            pl.grid()
            self.tkcanvas.draw()
        except Exception as e:
            print(e)
            pass

    def mainLoop(self):
        while True:
            event, values = self.window.read(timeout = 100,timeout_key=None)
            if event is None:
                if self.processLoop is not None: self.processLoop()
                continue
            print(event, values)
            if event == "TTU": self.server.incTemp(0,5)
            if event == "TTD": self.server.incTemp(0,-5)
            if event == "BTU": self.server.incTemp(1,5)
            if event == "BTD": self.server.incTemp(1,-5)
            if event == "TUM": self.server.incMaxPWM(0,.05)
            if event == "TDM": self.server.incMaxPWM(0,-.05)
            if event == "BUM": self.server.incMaxPWM(1,.05)
            if event == "BDM": self.server.incMaxPWM(1,-.05)
            if event == "Power":
                self.server.onOff()
            if event == "cel": self.useC = 1
            if event == "fah": self.useC = 0
            if event == "cel" or event == 'fah':
                self.server.dirty = 1
            if event in ['TP','TD','BP','BD','TI','BI']:
                self.server.setPID((values[i] for i in ['TP','TD','TI','BP','BD','BI']))
            if event in ['TMS','BMS']:
                self.server.setMaxPWM((values[i] for i in ['TMS','BMS']))
            if event in ['TTS','BTS']:
                self.server.setTemps((values[i] for i in ['TTS','BTS']))
            if event == "maximize":
                self.window.close()
                self.finishInit(no_titlebar=1-self.no_titlebar)
            if event == "update":
                ret = sg.popup_ok_cancel("Update software?",font=(fontName,30),keep_on_top=1)
                if ret == "OK":
                    ret,code = self.server.runUpdate()
                    sg.popup_ok(ret, font=(fontName, 30), keep_on_top=1)
                    if code == 1: self.server.runUpdate(1)
            if event == "reboot":
                ret = sg.popup_ok_cancel("Reboot now?",font=(fontName,30),keep_on_top=1)
                if ret == "OK":
                    os.system('sudo reboot now')
            if event == "clear":
                self.server.clearHist()
                self.canDraw = 0
                pl.clf()
                self.tkcanvas.draw()
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
        ip='192.168.1.110'
        version='ah ah ah'
        pass
    ui = UI(S)
    ui.finishInit()
    ui.mainLoop()
