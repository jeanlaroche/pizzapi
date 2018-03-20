import logging
from logging.handlers import RotatingFileHandler
from logging import StreamHandler
from threading import Thread
import time

defaultFormat = '%(asctime)s - %(filename)s / %(funcName)s- %(levelname)s - %(message)s'
defaultFormat = '%(asctime)s: %(message)s'
smallFormat = '%(message)s'
mstr = None
lastMessage = ''

def setLogger(fileName,mode='a',level=logging.INFO,format=defaultFormat):
    global mstr
    logger = logging.getLogger()
    logger.setLevel(level)
    ch = RotatingFileHandler(fileName,mode=mode,maxBytes=1024*1024,backupCount=2)
    ch.setLevel(level)
    formatter = logging.Formatter(format)
    # add formatter to ch
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    # This is so I can remember the last message
    mstr = myStream()
    ch2 = StreamHandler(mstr)
    ch2.setLevel(level)
    formatter2 = logging.Formatter(smallFormat)
    ch2.setFormatter(formatter2)
    logger.addHandler(ch2)

    
class myStream(object):
    def __init__(self):
        pass
    def write(self,thisString):
        global lastMessage
        lastMessage = thisString.strip()
    def flush(self):
        pass

def threadFunc(func,args=(),name = ''):
    loopThread = Thread(target=func, args=args, group=None)
    loopThread.daemon = True
    if name: logging.info("Starting %s thread",name)
    loopThread.start()
    return loopThread

def loopFunc(func,sleepS,args=(),name = ''):
    def auxFunc():
        while 1:
            func(*args)
            time.sleep(sleepS)
    loopThread = Thread(target=auxFunc, args=(), group=None)
    loopThread.daemon = True
    if name: logging.info("Starting %s thread",name)
    loopThread.start()
    return loopThread
    