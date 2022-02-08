from tkinter import *
from tkinter import messagebox
from functools import partial

class UI():
    def __init__(self,server):
        self.win = Tk()
        self.win.title("")
        self.height,self.width = 400,400
        self.win.minsize(self.height,self.width)
        self.server = server
        self.initPanelMain()

    def initPanelMain(self):
        # https://riptutorial.com/tkinter/example/29713/grid--
        # https://www.tutorialspoint.com/python/python_gui_programming.htm
        self.panel = LabelFrame(self.win,relief=GROOVE,height=self.height,width=self.width,text='MAIN')
        self.panel.pack(fill="both", expand="yes")
        parent = self.panel
        height = 3
        ### ROW1
        self.btn = Button(parent, text="Top Up", command=partial(self.incTemp,0,5),height=height)
        self.btn.grid(column=0,row=0,sticky="E W")
        self.btn = Button(parent, text="Top Down", command=partial(self.incTemp,0,-5),height=height)
        self.btn.grid(column=1,row=0,sticky="E W")
        self.targetTop = Text(parent,height=height,width=10)
        self.targetTop.grid(column=2,row=0,sticky="E W")
        ### ROW2
        self.btn = Button(parent, text="Bot Up", command=partial(self.incTemp,1,5),height=height)
        self.btn.grid(column=0,row=1,sticky="E W")
        self.btn = Button(parent, text="Bot Down", command=partial(self.incTemp,1,-5),height=height)
        self.btn.grid(column=1,row=1,sticky="E W")
        self.targetBot = Text(parent,height=height,width=10)
        self.targetBot.grid(column=2,row=1,sticky="E W")
        ### ROW3
        self.curTop = Text(parent,height=height,width=10)
        self.curTop.grid(column=0,row=2,columnspan =2,rowspan=2,sticky="E W")
        self.curBot = Text(parent,height=height,width=10)
        self.curBot.grid(column=0,row=4,columnspan =2,rowspan=2,sticky="E W")
        self.topPWM = Text(parent,height=height,width=10)
        self.topPWM.grid(column=2,row=2,columnspan =1,rowspan=2,sticky="E W")
        self.botPWM = Text(parent,height=height,width=10)
        self.botPWM.grid(column=2,row=4,columnspan =1,rowspan=2,sticky="E W")

        # POWER BUTTON:
        self.onOff = Button(parent, text="AAAA", command=lambda : self.server.onOff())
        self.onOff.grid(column=3, row=0, columnspan=1, rowspan=4, sticky="E W N S")
        self.onOff['fg'] = 'black'

    def setTargetTemps(self,topTemp,botTemp):
        self.targetTop.delete(1.0,END)
        self.targetBot.delete(1.0,END)
        self.targetTop.insert(END,f"Target {topTemp}")
        self.targetBot.insert(END,f"Target {botTemp}")

    def setCurTemps(self,topTemp,botTemp,topPWM,botPWM,isOnOff):
        self.curTop.delete(1.0,END)
        self.curBot.delete(1.0,END)
        self.curTop.insert(END,f"Current TOP {topTemp:.0f} C")
        self.curBot.insert(END,f"Current BOT {botTemp:.0f} C")
        self.topPWM.delete(1.0,END)
        self.botPWM.delete(1.0,END)
        self.topPWM.insert(END,f"PWM {topPWM:.2f}")
        self.botPWM.insert(END,f"PWM {botPWM:.2f}")
        self.onOff['text'] = "TURN POWER OFF" if isOnOff else "TURN POWER ON"
        self.onOff['fg'] = 'red' if isOnOff else "black"
        self.onOff['activeforeground'] = 'red' if isOnOff else "black"


    def incTemp(self,p1,p2):
        print(f"INCTEMP {p1} {p2}")
        self.server.incTemp(p1,p2)

    # find button callback
    def hello(self):
      messagebox.showinfo("Hello", "Callback worked!")

    def mainLoop(self):
        mainloop()

if __name__ == '__main__':
    ui = UI()
    ui.mainLoop()