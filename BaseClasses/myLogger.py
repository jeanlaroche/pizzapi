import logging
from logging.handlers import RotatingFileHandler

defaultFormat = '%(asctime)s - %(filename)s / %(funcName)s- %(levelname)s - %(message)s'
defaultFormat = '%(asctime)s: %(message)s'

def setLogger(fileName,mode='a',level=logging.INFO,format=defaultFormat):
    logger = logging.getLogger()
    logger.setLevel(level)
    ch = RotatingFileHandler(fileName,mode=mode,maxBytes=1024*1024,backupCount=2)
    ch.setLevel(level)
    formatter = logging.Formatter(format)
    # add formatter to ch
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    # logger.removeHandler(logger.handlers[0])

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


