from tkinter import *
from tkinter import messagebox, ttk, font
from functools import partial

class UI():
    def __init__(self,server):
        self.win = Tk()
        self.win.title("")
        self.height,self.width = 480,800
        self.win.minsize(self.width,self.height)
        self.server = server
        self.frame = ttk.Notebook(self.win)
        self.tabMain = Frame(self.frame)
        self.tabAux1 = Frame(self.frame)
        self.tabAux2 = Frame(self.frame)
        self.frame.add(self.tabMain, text="Main")
        self.frame.add(self.tabAux1, text="Aux1")
        self.frame.add(self.tabAux2, text="Aux2")
        self.frame.pack(expand=1, fill='both')
        self.defaultFont = font.nametofont("TkDefaultFont")
        self.defaultFont.configure(size=30,)
        self.win.option_add("*Font", self.defaultFont)
        self.initPanelMain()
        self.initPanelAux1()

    def initPanelMain(self):
        # https://riptutorial.com/tkinter/example/29713/grid--
        # https://www.tutorialspoint.com/python/python_gui_programming.htm
        parent = self.tabMain
        height = 1
        padding = {'padx': '1m', 'pady': '1m','sticky':"E W N S"}
        ### ROW1
        self.btn = Button(parent, text="Top Up", command=partial(self.incTemp,0,5),height=height)
        self.btn.grid(column=0,row=0,**padding)
        self.btn = Button(parent, text="Top Down", command=partial(self.incTemp,0,-5),height=height)
        self.btn.grid(column=1,row=0,**padding)
        self.targetTop = Text(parent,height=height,width=10)
        self.targetTop.grid(column=2,row=0,**padding)
        ### ROW2
        self.btn = Button(parent, text="Bot Up", command=partial(self.incTemp,1,5),height=height)
        self.btn.grid(column=0,row=1,**padding)
        self.btn = Button(parent, text="Bot Down", command=partial(self.incTemp,1,-5),height=height)
        self.btn.grid(column=1,row=1,**padding)
        self.targetBot = Text(parent,height=height,width=10)
        self.targetBot.grid(column=2,row=1,**padding)
        ### ROW3
        self.curTop = Text(parent,height=height,width=10)
        self.curTop.grid(column=0,row=2,columnspan =2,rowspan=2,**padding)
        self.curBot = Text(parent,height=height,width=10)
        self.curBot.grid(column=0,row=4,columnspan =2,rowspan=2,**padding)
        self.topPWM = Text(parent,height=height,width=10)
        self.topPWM.grid(column=2,row=2,columnspan =1,rowspan=2,**padding)
        self.botPWM = Text(parent,height=height,width=10)
        self.botPWM.grid(column=2,row=4,columnspan =1,rowspan=2,**padding)

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