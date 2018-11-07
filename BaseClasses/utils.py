import logging
import datetime
import time, threading

class myTimer(object):
    ''' Useful class for timing events'''
    
    def __init__(self):
        self.timedEvents = []
        # Get the sunset times for today
        self.getSunsetTime()
        # Set an event for getting the sunset time every day.
        def getST(): return self.getSunsetTime()
        self.addEvent(3,0,getST,[],"Update sunset time")
        
    def addEvent(self,hour,min,func,params,name):
        if type(hour)==int:
            logging.info('Adding event %s at %d:%d',name,hour,min)
        else:
            logging.info('Adding event %s at %s:%d',name,hour,min)
        self.timedEvents.append({'hour':hour,'min':min,'func':func,'params':params,'done':0,'name':name,'remove':0})
        
    def addDelayedEvent(self,delayM,func,params,name):
        logging.info('Adding delayed event %s, delay %.0f',name,delayM)
        import pdb
        #pdb.set_trace()
        eventTime = datetime.datetime.now()+datetime.timedelta(minutes=delayM)
        self.timedEvents.append({'hour':eventTime.hour,'min':eventTime.minute,'func':func,'params':params,'done':0,'name':name,'remove':1})

    def getSunsetTime(self):
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

    def start(self):
        # Helper function for the timer loop
        def timerLoop():
            while 1:
                try:
                    locTime = time.localtime()
                    # Make a list of events to trigger. This way if one takes a long time to complete, the other will still run.
                    todo = []
                    for event in self.timedEvents:
                        hour,min,func,params,done = event['hour'],event['min'],event['func'],event['params'],event['done']
                        # Special case for sunset.
                        if hour == 'sunset':
                            sunset = self.sunset+datetime.timedelta(minutes=min)
                            hour,min = sunset.hour,sunset.minute
                            # logging.info('Sunset hour %d -- %d',hour,min)
                        if locTime.tm_hour == hour and locTime.tm_min == min:
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
                            logging.info('Removing event %s',event['name'])
                            self.timedEvents.pop(idx)
                        
                    time.sleep(1)
                except Exception as e:
                    logging.error('Exception in timer: %s',e)        
        logging.info('Starting timer thread')
        self.timerThread = threading.Thread(target=timerLoop)
        self.timerThread.daemon = True
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
    
    