import PySimpleGUI as sg

sg.theme("Python")
fontName = "Helvetica"
import os, tkinter
import matplotlib.pyplot as pl
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg,NavigationToolbar2Tk
import matplotlib.dates as mdates
import time
import re

def scaleSize(a,b):
    factorW = 1.1
    factorH = 1.8
    return (int(a*factorW),int(b*factorH))

class UI():
    def __init__(self,server):
        self.height,self.width = 600,1024
        self.server = server
        self.useC = 1
        self.processLoop = None
        self.drawD = 0
        self.maxPlotLength = 400
        self.lastPlotLenTemps = 0


    def finishInit(self,no_titlebar=1):
        fontParams = {'font':(fontName, 34)}
        self.no_titlebar = no_titlebar
        self.tabMain = self.initPanelMain()
        self.tabPWM = self.initPanelPWM()
        self.tabStatus = self.iniPanelStatus()
        self.tabPID = self.initPanelPID()
        self.tabPlotTemp = self.initPanelPlotTemps()
        self.tabPlotPID = self.initPanelPlotPID()
        self.tabGroup = sg.TabGroup([[sg.Tab('Main', self.tabMain), sg.Tab('Max PWM', self.tabPWM), sg.Tab('PID', self.tabPID), 
                                      sg.Tab('Temp Plot', self.tabPlotTemp), sg.Tab('PID Plot', self.tabPlotPID), 
                                      sg.Tab('Status', self.tabStatus)]],**fontParams)
        self.layout = [[self.tabGroup]]
        self.window = sg.Window('PIZZA CONTROL', self.layout, default_element_size=scaleSize(44, 10),default_button_element_size=scaleSize(60,3),element_padding=5,finalize=1,size=(self.width,self.height),no_titlebar = no_titlebar,disable_close=1)
        if no_titlebar: self.window.set_cursor("none")
        class NavigationToolbar(NavigationToolbar2Tk):
            # only display the buttons we need
            toolitems = [t for t in NavigationToolbar2Tk.toolitems if
                         t[0] in ('Home', 'Pan', 'Zoom')]

        plotSize = (11,4.2)
        self.figTemps = pl.figure('temps',dpi=100.,figsize=plotSize)
        self.tkcanvasTemps = FigureCanvasTkAgg(self.figTemps, master=self.canvasTemps.TKCanvas)
        self.tkcanvasTemps.get_tk_widget().pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=1)
        toolbar = NavigationToolbar(self.tkcanvasTemps, self.canvasTemps.TKCanvas)
        toolbar.update()
        self.tkcanvasTemps.get_tk_widget().pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=1)

        self.figPIDs = pl.figure('pids',dpi=100.,figsize=plotSize)
        self.tkcanvasPID = FigureCanvasTkAgg(self.figPIDs, master=self.canvasPID.TKCanvas)
        self.tkcanvasPID.get_tk_widget().pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=1)
        toolbar = NavigationToolbar(self.tkcanvasPID, self.canvasPID.TKCanvas)
        toolbar.update()
        self.tkcanvasPID.get_tk_widget().pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=1)

    def initPanelMain(self):
        fontParams = {'font':(fontName, 16)}
        params = {'size':scaleSize(10,1),'font':(fontName, 28)}
        self.topTarget = sg.T(self.cvTemp(self.server.topPID.targetTemp),font=(fontName,28),size=scaleSize(5,1))
        self.botTarget = sg.T(self.cvTemp(self.server.botPID.targetTemp),font=(fontName,28),size=scaleSize(5,1))
        self.topTemp = sg.T("Temp",**params)
        self.botTemp = sg.T("Temp",**params)
        self.topPWM = sg.T("PWM",**params)
        self.botPWM = sg.T("PWM",**params)
        self.onTime = sg.T("OnTime",**params)
        self.topTimeToTarget = sg.T("Time to target Top",**params)
        self.botTimeToTarget = sg.T("Time to target Bot",**params)
        self.power = sg.Button("Power",size=scaleSize(10,3),font=(fontName, 25),expand_y=1)#,image_filename="/home/pi/piPizza/power.png")
        paramsSilders = {'range':(20,600),'orientation':'h','enable_events':1,'resolution':5,'disable_number_display':1,'size':scaleSize(25,30)}
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

        #Col = sg.Column([[B,self.power],[C]])
        Col = sg.Column([[A], [B]])
        self.tabMain = [ [Col,self.power], [C,D]]
        # self.tabMain = [ [A], [B,self.power], [C,D]]
        #self.tabMain = [ [A], [Col,sg.Column([[self.power],[D]])]]
        return self.tabMain

    def initPanelPWM(self):
        fontParams = {'font':(fontName, 16)}
        params = {'size':scaleSize(15,1)}
        params.update(fontParams)
        paramsSilders = {'range':(0,1),'resolution':0.05,'orientation':'h','font':(fontName, 20),
                         'enable_events':1,'size':scaleSize(30,30)}
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
        fontParams = {'font':(fontName, 15)}
        params = {'size':scaleSize(15,1)}
        params.update(fontParams)
        paramsSilders = {'range':(0,4),'resolution':0.01,'orientation':'h','font':(fontName, 15),
                         'enable_events':1,'size':scaleSize(20,30)}
        self.topKP = sg.Slider(default_value=self.server.topPID.kP, **paramsSilders, key='TP')
        self.topKD = sg.Slider(default_value=self.server.topPID.kD, **paramsSilders, key='TD')
        self.topKI = sg.Slider(default_value=self.server.topPID.kI, **paramsSilders, key='TI')
        self.botKP = sg.Slider(default_value=self.server.botPID.kP, **paramsSilders, key='BP')
        self.botKD = sg.Slider(default_value=self.server.botPID.kD, **paramsSilders, key='BD')
        self.botKI = sg.Slider(default_value=self.server.botPID.kI, **paramsSilders, key='BI')
        paramsSilders['range']=(0,0.2)
        self.topKF = sg.Slider(default_value=1-self.server.topPID.iForget, **paramsSilders, key='TF')
        self.botKF = sg.Slider(default_value=1-self.server.topPID.iForget, **paramsSilders, key='BF')

        tabParams=fontParams
        tabParams['pad'] = (10,2)
        butParams={'size':scaleSize(18,1),'font':(fontName, 21),'pad':(5,10)}
        stp = [sg.Button(f'Save preset {i}',key=f'save{i}',**butParams) for i in [1,2]]
        rfp = [sg.Button(f'Load preset {i}',key=f'load{i}',**butParams) for i in [1,2]]
        S = [[stp[0]],[rfp[0]],[stp[1]],[rfp[1]]]
        C1 = sg.Column([[sg.Button('Reset to default',key='resetPID',**butParams)]] + S,expand_y=1)
        A= sg.Column([
            [sg.Frame('Top kP',[[self.topKP]],**tabParams),
            sg.Frame('Bot kP',[[self.botKP]],**tabParams),
            ],
            [
            sg.Frame('Top kD',[[self.topKD]],**tabParams),
            sg.Frame('Bot kD',[[self.botKD]],**tabParams),
            ],
            [
            sg.Frame('Top kI',[[self.topKI]],**tabParams),
            sg.Frame('Bot kI',[[self.botKI]],**tabParams),
            ],
            [
            sg.Frame('Top forget', [[self.topKF]], **tabParams),
            sg.Frame('Bot forget', [[self.botKF]], **tabParams),
            ]
        ])
        self.tabPID = [[A,C1]]
        return self.tabPID

    def setPID(self):
        self.topKP.update(value=self.server.topPID.kP)
        self.topKI.update(value=self.server.topPID.kI)
        self.topKD.update(value=self.server.topPID.kD)
        self.topKF.update(value=1-self.server.topPID.iForget)

        self.botKP.update(value=self.server.botPID.kP)
        self.botKI.update(value=self.server.botPID.kI)
        self.botKD.update(value=self.server.botPID.kD)
        self.botKF.update(value=1-self.server.botPID.iForget)

    def initPanelPlotTemps(self):
        params = {'size':scaleSize(10,1),'font':(fontName, 16)}
        self.canvasTemps = sg.Canvas()
        self.drawDelta = sg.Checkbox("draw delta",self.drawD,**params,key='drawDelta',enable_events=1)
        self.zoomTemps = sg.Checkbox("zoom",1,**params,key='zoomTemps',enable_events=1)
        self.tabPlotTemp = [[self.canvasTemps],[sg.Button("clear",**params),self.drawDelta,self.zoomTemps]]
        return self.tabPlotTemp

    def initPanelPlotPID(self):
        params = {'size':scaleSize(10,1),'font':(fontName, 16)}
        self.canvasPID = sg.Canvas()
        self.plotBot = sg.Checkbox("plot bottom",0,**params,key='plotBotPID',enable_events=1)
        self.tabPlotPID = [[self.canvasPID],[self.plotBot]]
        return self.tabPlotPID

    def iniPanelStatus(self):
        params = {'size':scaleSize(14,1),'font':(fontName, 28)}
        ipAddress = sg.T(self.server.ip,**params)
        self.C = sg.Radio("Celcius",0,default=self.useC,enable_events=1,key='cel',**params)
        self.F = sg.Radio("Fahrenheit",0,default=not self.useC,enable_events=1,key='fah',**params)
        self.ambientTemp = sg.T("Ambient",**params)
        self.turnoffTimer = sg.Combo([f"Off after {i}h" for i in range(1,6)],default_value=f"Off after {self.server.turnoffAfterH}h",**params,
                                     key='turnoff',readonly=1,enable_events=1)
        A = sg.Frame("Ambient Temp",[[self.ambientTemp]],expand_y=1)
        B = sg.Frame("Turnoff timer",[[self.turnoffTimer]],expand_y=1)
        self.tabStatus = [
            [sg.Frame("IP address",[[ipAddress]]),sg.Frame("Version",[[sg.T(self.server.version,**params)]])],
            [sg.Frame("Units",[[self.C],[self.F]],expand_y=1),A],
            [B,],
#            [sg.T("Ambient temp",font=(fontName, 28)),self.ambientTemp],
            [sg.Button("Show PI Desktop" if self.no_titlebar else "Hide PI Desktop",**params,key="maximize"),
             sg.Button("Update / Restart",**params,key="update")],
            [sg.Button("Shutdown", **params, key="shutdown")],
            ]
        return self.tabStatus

    def cvTemp(self,temp):
        return f" {temp:.0f} C" if self.useC else f" {temp*1.8+32:.0f} F"

    def setTargetTemps(self,setSliders = 1):
        topTemp = self.server.topPID.targetTemp
        botTemp = self.server.botPID.targetTemp
        self.topTarget.update(value=self.cvTemp(topTemp))
        self.botTarget.update(value=self.cvTemp(botTemp))
        if setSliders:
            self.topTargetSlider.update(value=topTemp)
            self.botTargetSlider.update(value=botTemp)

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


    def plotPIDs(self,topPids,botPids,legend):
        self.topPids = topPids
        self.botPids = botPids
        self.pidLegend = legend
        if self.tabGroup.get() == "PID Plot":
            self.drawPIDs()

    def drawPIDs(self):
        try:
            print("DRAW PID")
            pids = self.botPids if self.plotBot.get() else self.topPids
            if not len(pids) >= 2 or not len(pids[0]): return
            pl.figure("pids")
            pl.clf()
            for ii in range(0,len(pids[0])):
                pl.plot([t[ii] for t in pids])
            pl.legend(self.pidLegend)
            pl.grid(1)
            self.tkcanvasPID.draw()
        except Exception as e:
            print(e)
            pass

    def plotTemps(self,times,temps,legend):
        self.times = times
        self.temps = temps
        self.legend = legend
        if len(self.times) >= 2 and self.tabGroup.get() == "Temp Plot" and self.lastPlotLenTemps != len(times):
            self.drawTemps()
            self.lastPlotLenTemps = len(times)

    def drawTemps(self):
        try:
            print("DRAW TEMPS")
            pl.figure("temps")
            pl.clf()
            X = mdates.datestr2num(self.times)
            t0=time.time()
            # Downsample the plot data, this is a round.
            inc = max(1,int(len(X) / self.maxPlotLength + .5))
            if self.zoomTemps.get():
                X=X[-100*inc:]
            if inc > 1:
                X = X[0::inc]
            temps = self.temps
            for ii in range(len(self.temps)):
                if self.zoomTemps.get():
                    temps[ii] = temps[ii][-100*inc:]
                if inc > 1:
                    temps[ii] = temps[ii][0::inc]
                if self.drawDelta.get():
                    tTemp = self.server.topPID.targetTemp if ii == 0 else self.server.botPID.targetTemp
                    temps[ii] = [t - tTemp for t in temps[ii]]
                if not self.useC:
                    temps[ii] = [1.8 * t + 32 for t in temps[ii]]
                pl.plot(X, temps[ii])
            #locator = mdates.MinuteLocator(interval=10)
            locator = mdates.AutoDateLocator(interval_multiples=True,maxticks=5,minticks=2)
            #locator = mdates.MinuteLocator()
            pl.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            pl.gca().xaxis.set_major_locator(locator)
            pl.legend(self.legend)
            pl.grid(1)
            print(f"Plot t0 {time.time()-t0}, inc: {inc}")
            t0=time.time()
            self.tkcanvasTemps.draw()
            print(f"Plot t1 {time.time()-t0}")
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
            if event == "Power":
                self.server.onOff()
            if event in ["cel","fah"]:
                self.useC = event == "cel"
                self.server.dirty = 1
                self.setTargetTemps(setSliders=0)
            if event in ['TP','TD','BP','BD','TI','BI','TF','BF']:
                self.server.setPID([values[i] for i in ['TP','TD','TI','BP','BD','BI','TF','BF']])
            if event in ['TMS','BMS']:
                self.server.setMaxPWM((values[i] for i in ['TMS','BMS']))
            if event in ['TTS','BTS']:
                self.server.setTemps((values[i] for i in ['TTS','BTS']))
                self.setTargetTemps(setSliders=0)
            if event == "maximize":
                self.window.close()
                self.finishInit(no_titlebar=1-self.no_titlebar)
            if event == "turnoff":
                R = re.findall('(\d)h',values['turnoff'])
                if R:
                    self.server.turnoffAfterH = int(R[0])
                    self.server.dirty = 1
            if event == "update":
                ret = sg.popup_ok_cancel("Update software?",font=(fontName,50),keep_on_top=1)
                if ret == "OK":
                    ret,code = self.server.runUpdate()
                    sg.popup_ok(ret, font=(fontName, 40), keep_on_top=1)
                    if code == 1: self.server.runUpdate(1)
            if event == "shutdown":
                ret = sg.popup_ok_cancel("Shutdown now?",font=(fontName,50),keep_on_top=1)
                if ret == "OK":
                    os.system('sudo shutdown -h now')
            if event == "clear":
                self.server.clearHist()
                pl.clf()
                self.drawTemps()
            if event in ["drawDelta","zoomTemps"]:
                self.drawD = self.drawDelta.get()
                self.server.dirty = 1
                self.drawTemps()
            if event in ["save1","save2"]:
                ret = sg.popup_ok_cancel("You sure?",font=(fontName,50),keep_on_top=1)
                if ret == "OK":
                    self.server.savePreset(1 if event == "save1" else 2)
            if event in ["load1","load2"]:
                self.server.loadPreset(1 if event == "load1" else 2)
            if event == "resetPID":
                self.server.loadPreset(0)
            if event == sg.WIN_CLOSED:  # always,  always give a way out!
                break


if __name__ == '__main__':
    class P:
        kP=0
        kD=1
        kI=0
        iForget=.9
        targetTemp = 50
    class S:
        topPID = P()
        botPID = P()
        topMaxPWM=1
        botMaxPWM=.5
        ip='192.168.1.110'
        version='ah ah ah'
        turnoffAfterH=1
        pass
        def __init__(self):
            self.ui = UI(self)
            pass

        def setTemps(self,a):
            b=list(a)
            self.topPID.targetTemp=b[0]
            self.botPID.targetTemp=b[1]
            pass
    S0 = S()
    S0.ui.finishInit()
    S0.ui.mainLoop()
