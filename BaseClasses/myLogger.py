import logging
from logging.handlers import RotatingFileHandler
from logging import StreamHandler

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

# import logging
# from logging.handlers import RotatingFileHandler
# logger = logging.getLogger()
# logger.setLevel(logging.INFO)
# ch = RotatingFileHandler('foo.log',mode='a',maxBytes=1024*1024,backupCount=2)
# ch.setLevel(logging.INFO)
# formatter = logging.Formatter('%(asctime)s: %(message)s')
# # add formatter to ch
# ch.setFormatter(formatter)
# logger.addHandler(ch)


