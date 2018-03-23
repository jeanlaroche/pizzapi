import pigpio
from flask import Flask, render_template, request, jsonify, send_from_directory
from _433 import tx
import time, threading
from BaseClasses import baseServer
import logging
import datetime

TX_GPIO = 17
BUTTON_GPIO = 10
# Codes for our light remote. > 0 means turn on, < 0 means turn off
codesLivRoom = {1:5510451,-1:5510460,2:5510595,-2:5510604,3:5510915,-3:5510924,4:5512451,-4:5512460,5:5518595,-5:5518604}
codesBedRoom = {6:283955,-6:283964,7:284099,-7:284108,8:284419,-8:284428,9:285955,-9:285964,10:292099,-10:292108}
codesFamRoom = {11:4461875,-11:4461884,12:4462019,-12:4462028,13:4462339,-13:4462348,14:4463875,-14:4463884,15:4470019,-15:4470028}

codes = codesLivRoom
codes.update(codesBedRoom)
codes.update(codesFamRoom)
#codes = codesBedRoom

app = Flask(__name__)

class myTimer(object):
    
    def __init__(self):
        self.timedEvents = []
        self.getSunsetTime()
        
        def getST(): return self.getSunsetTime()
        self.addEvent(18,30,getST,[],"Sunset time")
        
    def addEvent(self,hour,min,func,params,name):
        if type(hour)==int:
            logging.info('Adding event %s at %d:%d',name,hour,min)
        else:
            logging.info('Adding event %s at %s:%d',name,hour,min)
        self.timedEvents.append({'hour':hour,'min':min,'func':func,'params':params,'done':0,'name':name})

    def getSunsetTime(self):
        import ephem  
        o=ephem.Observer()  
        o.lat='36.97'  
        o.long='-122.03'  
        s=ephem.Sun()  
        s.compute()
        logging.info( "Next sunrise: {}".format(ephem.localtime(o.next_rising(s))))
        logging.info( "Next sunset: {}".format(ephem.localtime(o.next_setting(s))))
        self.sunset = ephem.localtime(o.next_setting(s))        
        # import datetime
        # LT = LT+datetime.timedelta(minutes=self.onTimeOffsetMin)
        # return LT.hour,LT.minute,sunrise,sunset
        

    def start(self):
        def timerLoop():
            while 1:
                try:
                    locTime = time.localtime()
                    todo = []
                    # Make a list of events to trigger
                    for event in self.timedEvents:
                        hour,min,func,params,done = event['hour'],event['min'],event['func'],event['params'],event['done']
                        if hour == 'sunset':
                            sunset = self.sunset+datetime.timedelta(minutes=min)
                            hour,min = sunset.hour,sunset.minute
                            # logging.info('Sunset hour %d -- %d',hour,min)
                        if locTime.tm_hour == hour and locTime.tm_min == min:
                            if done==0:
                                todo.append(event)
                                event['done']=1
                        else:
                            event['done']=0
                    # Then trigger this!
                    for event in todo:
                        logging.info('Triggering %s at %d:%d',event['name'],locTime.tm_hour,locTime.tm_min)
                        event['func'](*event['params'])
                        
                    time.sleep(1)
                except Exception as e:
                    logging.error('Exception in timer: %s',e)        
        logging.info('Starting timer thread')
        self.timerThread = threading.Thread(target=timerLoop)
        self.timerThread.daemon = True
        self.timerThread.start()
    

class lightController(baseServer.Server):

    transmitter = None
    pi = None
    
    lightOffHour = 23
    lightOffMin = 0
    canTurnOff = 1
    pushCount = 10 # so the first callback does nothing. I'm not sure why I'm getting one anyway!
    pushDelayS = .7
    actionTimer = None
    
    def __init__(self):
        logging.info('Starting server')
        super(lightController,self).__init__("rfLights.log")
        logging.info('Starting pigpio')
        self.pi = pigpio.pi() # Connect to local Pi.
        self.transmitter = tx(self.pi,gpio = TX_GPIO, repeats=10)
        self.pi.set_mode(BUTTON_GPIO, pigpio.INPUT)
        self.pi.set_pull_up_down(BUTTON_GPIO, pigpio.PUD_DOWN)
        self.pi.set_glitch_filter(BUTTON_GPIO, 10e3)
        
        self.myTimer = myTimer()
        def turnOff():
            logging.info('Timer turn lights off')
            self.turnLigthOnOff(100,0)
            self.turnLigthOnOff(102,0)
        self.myTimer.addEvent(self.lightOffHour,self.lightOffMin,turnOff,[],'Turn lights off')
        self.myTimer.addEvent('sunset',30,self.turnLigthOnOff,[9,1],'Turn on gate light')
        self.myTimer.addEvent(2,0,self.turnLigthOnOff,[9,0],'Turn off gate light')
        self.myTimer.start()
        
        
        # Button callback
        def buttonCallback(GPIO, level, tick):
            self.onButton()
        self.pi.callback(BUTTON_GPIO, pigpio.RISING_EDGE, buttonCallback)

    def onButton(self):
        self.pushCount += 1
        logging.info('Button pressed, pushCount %d',self.pushCount)

        def takeAction():
            logging.info('Take action! %d',self.pushCount)
            pushCount,self.pushCount = self.pushCount,0
            if pushCount == 1: 
                self.turnLigthOnOff(100,1)
                self.turnLigthOnOff(102,1)
            if pushCount == 2: 
                self.turnLigthOnOff(100,0)
                self.turnLigthOnOff(102,0)
            if pushCount == 3: self.turnLigthOnOff(102,0)
            if pushCount == 4: self.turnLigthOnOff(100,0)
            
        try:
            self.actionTimer.cancel()
        except Exception as e:
            logging.warning('Couldnt cancel timer %s',e)
        self.actionTimer = threading.Timer(self.pushDelayS, takeAction, ())
        self.actionTimer.start()
        
    def Index(self):
        return super(lightController,self).Index("index.html")
        # return jsonify(imAlive="I am alive")
        
    def turnLigthOnOff(self, lightNum, onOff):
        if lightNum == 100:
            for ii in range(1,6):
                self.turnLigthOnOff(ii,onOff)
                time.sleep(0.01)
            return
        if lightNum == 101:
            for ii in range(6,11):
                self.turnLigthOnOff(ii,onOff)
                time.sleep(0.01)
            return
        if lightNum == 102:
            for ii in range(11,16):
                self.turnLigthOnOff(ii,onOff)
                time.sleep(0.01)
            return
        code = codes[lightNum] if onOff == 1 else codes[-lightNum]
        self.transmitter.send(code)
        logging.info('Turning light %d %d',lightNum,onOff)
        
    def getLog(self):
        with open("rfLights.log") as f:
            allLines = f.readlines()
        allLines.reverse()
        return (allLines[0:50])
        
@app.route('/favicon.ico')
def favicon():
    return lc.favicon()
            
@app.route("/reboot")
def reboot():
    return lc.reboot()

@app.route("/getLog")
def getLog():
    return jsonify(lc.getLog())

# return index page when IP address of RPi is typed in the browser
@app.route("/")
def Index():
    return lc.Index()

@app.route("/lightOnOff/<int:light_id>/<int:on_off>")
def lightOnOff(light_id,on_off):
    lc.turnLigthOnOff(light_id,on_off)
    return ('', 204)
    
lc = lightController()


if __name__ == "__main__":
    #app.run(host='127.0.0.1', port=8080, debug=True, threaded=False, use_reloader=False)
    app.run(host='0.0.0.0', port=8080, debug=True, threaded=False, use_reloader=False)
    
    while 1:
        a = raw_input('Command ->[]')
        a = int(a)
        lc.turnLigthOnOff(abs(a),a>0)
        
