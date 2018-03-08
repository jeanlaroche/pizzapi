import logging
from logging.handlers import RotatingFileHandler

defaultFormat = '%(asctime)s - %(filename)s / %(funcName)s- %(levelname)s - %(message)s'
defaultFormat = '%(asctime)s: %(message)s'

class myLogger():
    """"""

    def __init__(self,fileName,mode='a',level=logging.INFO,format=defaultFormat):
        """Constructor for myLogger"""

        self.format = format
        self.level=level

        # create logger
        self.logger = logging.getLogger('myLogger')
        self.logger.setLevel(level)

        # create console handler and set level to debug
        self.ch = RotatingFileHandler(fileName,mode=mode,maxBytes=1024*1024,backupCount=2)
        self.ch.setLevel(level)

        # create formatter
        self.formatter = logging.Formatter(format)

        # add formatter to ch
        self.ch.setFormatter(self.formatter)

        # add ch to logger
        self.logger.addHandler(self.ch)

        # 'application' code
        # logger.debug('debug message')
        # logger.info('info message')
        # logger.warn('warn message')
        # logger.error('error message')
        # logger.critical('critical message')

    def getLogger(self):
        return self.logger


if __name__ == '__main__':
    LL = myLogger('foo.log')
    log = LL.getLogger()

    for ii in range(100000):
        log.debug('My message %d',ii)


