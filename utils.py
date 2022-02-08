import logging
import datetime
import time, threading
try:
    import pigpio
except:
    logging.info("No PIGPIO")

weekDays = {0:"Mon",1:"Tue",2:"Wed",3:"Thu",4:"Fri",5:"Sat",6:"Sun"}
allDays = ''.join(weekDays.values())

class myTimer(object):
    ''' Useful class for timing events'''
    
    def __init__(self):
        self.timedEvents = []
        self.vacation = 0
        self.hold = 0
        # Get the sunset times for today
        self.getSunsetTime()
        # Set an event for getting the sunset time every day.
        def getST(): return self.getSunsetTime()
        self.addEvent(3,0,getST,[],"Update sunset time")
        self.addEvent(0,1,lambda : logging.info('________________________________________'),[],"Newline!")
        
    def addEvent(self,hour,min,func,params,name,days=allDays):
        if type(hour)==int:
            logging.info('Adding event %s at %d:%d days: %s',name,hour,min,days)
        else:
            logging.info('Adding event %s at %s:%d days %s',name,hour,min,days)
        self.timedEvents.append({'hour':hour,'min':min,'func':func,'params':params,'done':0,'name':name,'remove':0,'days':days})
        
    def incEventTime(self,pattern,hour=0,min=0):
        found = 0
        for event in self.timedEvents:
            if pattern in event['name']: 
                event['hour']+=hour
                event['min']+=min
                while event['min']<0: 
                    event['hour'] -= 1
                    event['min'] += 60
                while event['min']>=60: 
                    event['hour'] += 1
                    event['min'] -= 60
                event['hour'] = (event['hour']+24)%24
                    
                logging.debug('Updating %s new hour %d new min %d',event['name'],event['hour'],event['min'])
                found = 1
        return found
    
    def findEvents(self,pattern):
        return [event for event in self.timedEvents if pattern in event['name']]
        
    def adjustEvent(self,pattern,newEventTimeS):
    # Set the time of all events that match pattern, and whose trigger day include the day in newEventTimeS to that of newEventTimeS
        now = time.localtime(newEventTimeS)
        eventList = [event for event in self.timedEvents if pattern in event['name'] and weekDays[now.tm_wday] in event['days']]
        for event in eventList:
            event['hour'] = now.tm_hour
            event['min'] = now.tm_min
            logging.debug('Updating %s new hour %d new min %d',event['name'],event['hour'],event['min'])
        
    def addDelayedEvent(self,delayM,func,params,name,days=allDays):
        logging.info('Adding delayed event %s, delay %.0f',name,delayM)
        import pdb
        #pdb.set_trace()
        eventTime = datetime.datetime.now()+datetime.timedelta(minutes=delayM)
        self.timedEvents.append({'hour':eventTime.hour,'min':eventTime.minute,'func':func,'params':params,'done':0,'name':name,'remove':1,'days':days})
        
    def removeEvents(self,pattern):
        found = 0
        for event in self.timedEvents:
            if pattern in event['name']: 
                logging.debug('Removing %s',event['name'])
                self.timedEvents.pop(self.timedEvents.index(event))
                found = 1
        return found

    def triggerEvents(self,pattern):
        found = 0
        todo = []
        for event in self.timedEvents:
            if pattern in event['name']: 
                todo.append(event)
                found = 1
        for event in todo:
            logging.info('Force Triggering %s',event['name'])
            event['func'](*event['params'])
            if event['remove']:
                try:
                    idx = self.timedEvents.index(event)
                    logging.debug('Removing event %s',event['name'])
                    self.timedEvents.pop(idx)
                except:
                    pass
        return found
                
    def redoLastEvent(self):
        logging.info('Redo last event')
        locTime = time.localtime()
        wday = locTime.tm_wday
        # If on vacation, set the local day to Sunday.
        if self.vacation: 
            logging.info('Vacation on, setting day to Sunday')
            wday = 6
        # Re-run the latest timed event in the past of now.
        _events = []
        nowMin = wday*24*60 + locTime.tm_hour*60 + locTime.tm_min
        for event in self.timedEvents:
            if 'Update sunset time' in event['name']: continue
            if 'Newline' in event['name']: continue
            days,hour,min = event['days'],event['hour'],event['min']
            # This should eventually be handled!
            if isinstance(hour,str): continue
            for ii in range(7):
                # Go back day by day, see if even triggers that, day, when it does and you're in the past of now, stop.
                thisDay = wday-ii
                # See if the even triggers this day
                if not weekDays[(7+thisDay)%7].lower() in days.lower(): continue
                # See if the even is in the past of the current time (it should be unless ii==0)
                tmin = thisDay*24*60 + hour*60 + min
                if tmin > nowMin: continue
                _events.append([tmin,event])
                break
            else:
                # This event appears to never trigger, this is fishy!
                print("Mmmm, no trigger of this guy?",event)
                
        # Sort event based on time.
        _events = sorted(_events)
        if len(_events):
            # Redo the last event.
            event = _events[-1][1]
            #print("Redoing {} {}:{} {}".format(event['name'],event['hour'],event['min'],event['days']))
            logging.info('Redoing %s at %d:%d',event['name'],event['hour'],event['min'])
            event['func'](*event['params'])       
        
    def getSunsetTime(self):
        try:
            import ephem  
            o=ephem.Observer()
            # Santa cruz! :)
            o.lat='36.97'  
            o.long='-122.03'  
            s=ephem.Sun()  
            s.compute()
            logging.info( "Next sunrise: {}".format(ephem.localtime(o.next_rising(s))))
            logging.info( "Next sunset: {}".format(ephem.localtime(o.next_setting(s))))
            self.sunset = ephem.localtime(o.next_setting(s))                
            self.sunrise = ephem.localtime(o.next_rising(s))
        except:
            logging.info("No Ephem module")

    def start(self):
        # Helper function for the timer loop
        def timerLoop():
            while 1:
                try:
                    locTime = time.localtime()
                    wday = locTime.tm_wday
                    if self.hold:
                        # If on hold, don't trigger anything.
                        time.sleep(1)
                        continue
                    # If on vacation, set the local day to Sunday.
                    if self.vacation: 
                        wday = 6
                    # Make a list of events to trigger. This way if one takes a long time to complete, the other will still run.
                    todo = []
                    for event in self.timedEvents:
                        hour,min,func,params,done,days = event['hour'],event['min'],event['func'],event['params'],event['done'],event['days']
                        # Special case for sunset.
                        if hour == 'sunset':
                            sunset = self.sunset+datetime.timedelta(minutes=min)
                            hour,min = sunset.hour,sunset.minute
                            # logging.info('Sunset hour %d -- %d',hour,min)
                        # Special case for sunrise.
                        if hour == 'sunrise':
                            sunrise = self.sunrise+datetime.timedelta(minutes=min)
                            hour,min = sunrise.hour,sunrise.minute
                            # logging.info('Sunrise hour %d -- %d',hour,min)
                        if locTime.tm_hour == hour and locTime.tm_min == min and weekDays[wday].lower() in days.lower():
                            if done==0:
                                todo.append(event)
                                event['done']=1
                        else:
                            # If the time does not match, then done is 0
                            event['done']=0
                    # Then trigger the events in the list
                    for event in todo:
                        logging.info('Triggering %s at %d:%d',event['name'],locTime.tm_hour,locTime.tm_min)
                        event['func'](*event['params'])
                        if event['remove']:
                            idx = self.timedEvents.index(event)
                            logging.debug('Removing event %s',event['name'])
                            self.timedEvents.pop(idx)
                        
                    time.sleep(1)
                except Exception as e:
                    logging.error('Exception in timer: %s',e)        
        logging.info('Starting timer thread')
        self.timerThread = threading.Thread(target=timerLoop)
        self.timerThread.daemon = False
        self.timerThread.start()
    
def printSeconds(nSecs):
    days,nSecs = divmod(nSecs,3600*24)
    hours,nSecs = divmod(nSecs,3600)
    minutes,nSecs = divmod(nSecs,60)
    str = ''
    if days: str += '{:.0f}d:'.format(days)
    if days or hours: str += '{:.0f}h:'.format(hours)
    if hours or minutes: str += '{:.0f}m:'.format(minutes)
    str += '{:.0f}s'.format(nSecs)
    return str
    
    
noBlinkOff=0
slowBlink=1
fastBlink=2
noBlinkOn=3
flashBlink=4
ffastBlink=5
fffastBlink=6
class blinker(object):
    blinkStat = noBlinkOff
    sampT = 0.010
    flashDurS = 0.050
    slowFreq = 1
    fastFreq = 4
    ffastFreq = 8
    fffastFreq = 16
    cycleS = 2
    exitBlink = 0
    prevOnOff = 0
    def  __init__(self,pi,blinkGPIO,checkFunc=None):
        '''
        blinkGPIO is the GPIO used for the blinking LED
        checkFunc is an optional function that's called around each loop and must return one of the available blinkStatus
        Note that the return does not affect self.blinkStatus. 
        '''
        self.blinkGPIO = blinkGPIO
        self.checkFunc = checkFunc
        self.pi = pi
        self.pi.set_mode(self.blinkGPIO, pigpio.OUTPUT)
        self.pi.set_PWM_frequency(self.blinkGPIO,256)
        self.cycleLen = int(self.cycleS/self.sampT)
        self.sleepTimeS = self.sampT
        self.nSlow = int(round(1./self.sampT/self.slowFreq))
        self.nFast = int(round(1./self.sampT/self.fastFreq))
        self.nFFast = int(round(1./self.sampT/self.ffastFreq))
        self.nFFFast = int(round(1./self.sampT/self.fffastFreq))
        #print self.cycleLen
        ##print self.nSlow
        #print self.nFast
        def doBlink():
            i = 0
            onSlow = [uu for uu in range(self.cycleLen) if uu%(self.nSlow)<self.nSlow/2]
            offSlow = [uu for uu in range(self.cycleLen) if uu%(self.nSlow)>=self.nSlow/2]
            onFast = [uu for uu in range(self.cycleLen) if uu%(self.nFast)<self.nFast/2]
            offFast = [uu for uu in range(self.cycleLen) if uu%(self.nFast)>=self.nFast/2]
            onFFast = [uu for uu in range(self.cycleLen) if uu%(self.nFFast)<self.nFFast/2]
            offFFast = [uu for uu in range(self.cycleLen) if uu%(self.nFFast)>=self.nFFast/2]
            onFFFast = [uu for uu in range(self.cycleLen) if uu%(self.nFFFast)<self.nFFFast/2]
            offFFFast = [uu for uu in range(self.cycleLen) if uu%(self.nFFFast)>=self.nFFFast/2]
            iFlash = int(self.flashDurS/self.sampT)
            while self.exitBlink == 0:
                if 1:
                    # Call the check function. 
                    blinkStat = self.blinkStat
                    if self.checkFunc: blinkStat = self.checkFunc()                        
                    i = (i + 1) % self.cycleLen
                    if blinkStat == slowBlink: on,off = onSlow,offSlow
                    elif blinkStat == fastBlink: on, off = onFast,offFast
                    elif blinkStat == ffastBlink: on, off = onFFast,offFFast
                    elif blinkStat == fffastBlink: on, off = onFFFast,offFFFast
                    elif blinkStat == noBlinkOn: on,off = range(self.cycleLen),[]
                    elif blinkStat == noBlinkOff: on,off = [],range(self.cycleLen)
                    elif blinkStat == flashBlink: on,off = range(0,iFlash),range(iFlash,self.cycleLen)
                    else: on,off = [],range(self.cycleLen)
                    # if i in on: self.pi.write(self.blinkGPIO,1)
                    # if i in off: self.pi.write(self.blinkGPIO,0)
                    if i in on: self.fade(1)
                    if i in off: self.fade(0)
                    time.sleep(self.sleepTimeS)
                else:
                    pass
        self.blinkStat = noBlinkOff
        t = threading.Thread(target=doBlink)
        t.start()    
    
    def fade(self,onOff):
        fadeSleepS = self.sleepTimeS/200.
#        def fadeLoop():
        if 1:
            # self.pi.write(self.blinkGPIO,onOff)
            # self.pi.set_PWM_dutycycle(self.blinkGPIO, onOff*16)
            # return
            #
            if onOff:
                if self.prevOnOff == 0:
                    for dutycycle in range(0,32,1):
                        self.pi.set_PWM_dutycycle(self.blinkGPIO, dutycycle)
                        time.sleep(fadeSleepS)
                
            else:
                if self.prevOnOff == 1:
                    for dutycycle in reversed(range(0,32,1)):
                        self.pi.set_PWM_dutycycle(self.blinkGPIO, dutycycle)
                        time.sleep(fadeSleepS)
            self.prevOnOff = onOff
        # fadeLoop()
        # t=threading.Thread(target=fadeLoop)
        # t.daemon = False
        # t.start()

        
        from threading import Timer

# Use this to run a function repeatedly every delayS seconds
# For example:
# @repeatFunc(2)
# def foo(x): print(x)
# Stop it with foo.stopNow = 1
def repeatFunc(delayS,nRepeats=0):
    def innerDec(some_function):
        def wrapper(*args):
            some_function(*args)
            wrapper.n += 1
            if wrapper.stopNow == 0 and (nRepeats == 0 or wrapper.n < nRepeats):
                threading.Timer(delayS,wrapper,args).start()
        wrapper.stopNow = 0
        wrapper.n=0
        return wrapper
    return innerDec
    
# Use this to run a function after a certain delay
# For example:
# @delayFunc(2)
# def foo(x): print(x)
# foo(33)
def delayFunc(delayS):
    def innerDec(some_function):
        def wrapper(*args):
            def foo(*args):
                some_function(*args)
            threading.Timer(delayS,foo,args).start()
        return wrapper
    return innerDec

def runDelayed(delayS,function,*args):
    threading.Timer(delayS,function,*args).start()

def runDelayedSingle(caller,delayS,function,*args):
    # This cancels the timer if it's still active before setting a new timer, so it can be
    # called repeatedly and the function will only be called at the very end.
    if hasattr(caller,'delay_thread'):
        caller.delay_thread.cancel()
    caller.delay_thread = threading.Timer(delayS,function,*args)
    caller.delay_thread.start()
        

def runThreaded(function,*args):
    t = threading.Thread(target=function,args=args)
    t.start()
    return t
    
def runThreadedSingle(caller,function,*args):
    # This is to call a function in threaded mode, but in a way that does not allow multiple
    # threads to be created if this is called over and over. This is good for displaying values
    # if the display function is slow, but the values can change rapidly. The redo mechanism ensures
    # that the last value is always displayed
    caller.redo = 0
    def helper():
        function(*args)
        if caller.redo:
            caller.redo = 0
            function(*args)
    if not hasattr(caller,'single_thread') or not caller.single_thread.is_alive():
        caller.single_thread = runThreaded(helper)
    else:
        # The thread is alive, don't start on, but ask it to re-run when done.
        caller.redo=1
    
    
def flashLED(pi,gpio,dur=0.100):
    # Use this to flash a LED but return immediately
    pi.write(gpio,1)
    def turnOff():
        pi.write(gpio,0)
    runDelayed(dur,turnOff)
    
def monitorButton(pi,caller,gpioPush,callback,between_click_ms=200,onOff=0):
    # Use this to monitor a button for long press, short press, double-clicks.
    # Pass an object as caller (any), callback will be called as callback(gpio,level,long_press,double_click)
    # If onOff is true, the callback only has gpio and level as inputs, and is called on both edges
    def pushCB(gpio,level,tick):
        # Remove the callback so we don't get called twice in case of a double-click
        caller.cb[gpio].cancel()
        # Wait for release, for some reason I'm not able to use wait_for_edge ...
        longPress = 0
        doubleClick = 0
        #print("FUCK GPIO {}".format(gpio))
        #print("SDF {} {} {}".format(pi.get_current_tick(),tick,pi.get_current_tick()-tick))
        while pi.read(gpio) == 0 and pi.get_current_tick() - tick < between_click_ms*1e3:
            time.sleep(.010)
        #print("SDF2 {} {} {} {}".format(pi.get_current_tick(),tick,pi.get_current_tick()-tick,pi.read(gpio)))
        if pi.read(gpio) == 0: longPress = 1
        tick = pi.get_current_tick()
        if not longPress:
            # check for a double-click
            while pi.read(gpio) == 1 and pi.get_current_tick() - tick < between_click_ms*1e3:
                time.sleep(.010)
            if pi.read(gpio) == 0:
                doubleClick = 1
        # restore the callback
        caller.cb[gpio]=pi.callback(gpio, pigpio.FALLING_EDGE, pushCB)
        # And call the supplied function
        #print("CCCCB {} {} {}".format(level,longPress,doubleClick))
        callback(gpio,level,longPress,doubleClick)
        
    def onOffCB(gpio,level,tick):
        callback(gpio,level)
        
    pi.set_mode(gpioPush, pigpio.INPUT)
    pi.set_glitch_filter(gpioPush, 100)
    pi.set_pull_up_down(gpioPush, pigpio.PUD_UP)
    if not hasattr(caller,'cb'): 
        #print("SET CB")
        caller.cb={}
    if not onOff:
        caller.cb[gpioPush]=pi.callback(gpioPush, pigpio.FALLING_EDGE, pushCB)
    else:
        caller.cb[gpioPush]=pi.callback(gpioPush, pigpio.EITHER_EDGE, onOffCB)

def writeJsonFile(fileName,data):
    import json
    with open(fileName,'w') as f:
        json.dump(data,f)

def readJsonFile(fileName):
    import json
    try:
        with open(fileName,'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Could not find {fileName}")
        data = {}
    return data

if __name__ == "__main__":
    mt = myTimer()
    mt.addEvent(19,25,None,None,"Turn On",days=allDays)
    mt.addEvent(19,25,None,None,"Turn On",days='Wed')
    mt.addEvent(19,25,None,None,"Turn On",days='Thu')
    import pdb
    pdb.set_trace()
    mt.adjustEvent('Turn',time.time())
    pass