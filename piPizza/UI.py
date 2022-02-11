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


    def finishInit(self,no_titlebar=1):
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
        Col = sg.Column([[B],[C]])
        #self.tabMain = [ [A], [B,self.power], [C]]
        self.tabMain = [ [A], [Col,self.power]]
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
        A= [[sg.Frame('Top P',[[sg.Slider(default_value  = self.server.topPID.p, **paramsSilders, key='TP')]],**fontParams),
                       sg.Frame('Top D',[[sg.Slider(default_value  = self.server.topPID.d, **paramsSilders, key='TD')]],**fontParams)
                       ],
                     [
                       sg.Frame('Bot P',[[sg.Slider(default_value  = self.server.botPID.p, **paramsSilders, key='BP')]],**fontParams),
                       sg.Frame('Bot D',[[sg.Slider(default_value  = self.server.botPID.d, **paramsSilders, key='BD')]],**fontParams)
                     ]]
        self.tabPID = A
        return self.tabPID

    def initPanelPlot(self):
        self.canvas = sg.Canvas()
        self.tabPlot = [[self.canvas]]
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

    def setCurTemps(self,topTemp,botTemp,topPWM,botPWM,isOnOff,ambientTemp,topTimeToTarget,botTimeToTarget):
        self.topTemp.update(value=f"TOP " + self.cvTemp(topTemp))
        self.botTemp.update(value=f"BOT " + self.cvTemp(botTemp))
        self.topPWM.update(value=f"PWM {topPWM:.2f}")
        self.botPWM.update(value=f"PWM {botPWM:.2f}")
        self.power.update(text = "TURN POWER OFF" if isOnOff else "TURN POWER ON")
        self.power.update(button_color = ('red',None) if isOnOff else ('black',None))
        self.ambientTemp.update(value = self.cvTemp(ambientTemp))
        self.topTimeToTarget.update(value=topTimeToTarget)
        self.botTimeToTarget.update(value=botTimeToTarget)

    def plotTemps(self,times,topTemps,botTemps):
        if len(times) == self.lastPlotLen: return
        self.lastPlotLen = len(times)
        print("PLOT1",len(times))
        if len(times) < 4: return
        self.canDraw = 0
        pl.clf()
        X = mdates.datestr2num(times)
        if not self.useC:
            topTemps = [1.8*t+32 for t in topTemps]
            botTemps = [1.8*t+32 for t in botTemps]
        pl.plot(X, topTemps)
        pl.plot(X, botTemps)
        locator = mdates.MinuteLocator(interval=10)
        pl.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        #pl.gca().xaxis.set_major_formatter(mdates.AutoDateFormatter(locator))
        pl.gca().xaxis.set_major_locator(locator)
        # pl.gca().xaxis.set_major_locator(mdates.DayLocator())
        pl.legend(['Top','Bottom'])
        pl.grid()
        self.canDraw = 1

    def draw(self):
        if not self.canDraw: return
        try:
            self.tkcanvas.draw()
            self.canDraw = 0
        except Exception as e:
            pass

    def mainLoop(self):
        while True:
            event, values = self.window.read(timeout = 1000,timeout_key=None)
            if event is None:
                self.draw()
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
                #self.tkcanvas.draw()
                #self.plotTemps(["2022-02-10T15:30:30.317823","2022-02-10T15:40:36.317823","2022-02-10T15:50:36.317823"],[20,21,22],[24,25,26])
                self.server.onOff()
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
                self.server.stopUI = 1
                self.window.close()
                self.finishInit(no_titlebar=1-self.no_titlebar)
                self.server.stopUI = 0
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
