
#!/usr/bin/env python

import pigpio

class decoder:

    """Class to decode mechanical rotary encoder pulses."""

    def __init__(self, pi, gpioA, gpioB, callback, UAStyle=0,gpioPush=None):

        """
        Instantiate the class with the pi and gpios connected to
        rotary encoder contacts A and B.  The common contact
        should be connected to ground.  The callback is
        called when the rotary encoder is turned.  It takes
        one parameter which is +1 for clockwise and -1 for
        counterclockwise.

        EXAMPLE

        import time
        import pigpio

        import rotary_encoder

        pos = 0

        def callback(way):

            global pos

            pos += way

            print("pos={}".format(pos))

        pi = pigpio.pi()

        decoder = rotary_encoder.decoder(pi, 7, 8, callback)

        time.sleep(300)

        decoder.cancel()

        pi.stop()

        """

        self.pi = pi
        self.gpioA = gpioA
        self.gpioB = gpioB
        self.callback = callback

        self.levA = 0
        self.levB = 0

        self.lastGpio = None

        self.pi.set_mode(gpioA, pigpio.INPUT)
        self.pi.set_mode(gpioB, pigpio.INPUT)
        if gpioPush is not None:
            def pushCB(gpio,level,tick):
                callback(0,push=1)
            self.pi.set_mode(gpioPush, pigpio.INPUT)
            self.pi.set_pull_up_down(gpioPush, pigpio.PUD_UP)
            self.pi.set_glitch_filter(gpioPush, 100)
            self.pi.callback(gpioPush, pigpio.FALLING_EDGE, pushCB)

        self.pi.set_pull_up_down(gpioA, pigpio.PUD_UP)
        self.pi.set_pull_up_down(gpioB, pigpio.PUD_UP)
        # THis is quite crucial with the shitty encoders.
        self.pi.set_glitch_filter(gpioA, 1000)
        self.pi.set_glitch_filter(gpioA, 1000)
        # RISING_EDGE (default), or FALLING_EDGE, EITHER_EDGE
        self.cbA = self.pi.callback(gpioA, pigpio.EITHER_EDGE, self._pulseUA if UAStyle else self._pulse)
        self.cbB = self.pi.callback(gpioB, pigpio.EITHER_EDGE, self._pulseUA if UAStyle else self._pulse)
        self.pos = 0

    def _pulse(self, gpio, level, tick):

        """
        Decode the rotary encoder pulse.

                         +---------+            +---------+        0
                         |            |            |            |
            A            |            |            |            |
                         |            |            |            |
            +---------+            +---------+            +----- 1

                 +---------+            +---------+                0
                 |            |            |            |
            B    |            |            |            |
                 |            |            |            |
            ----+            +---------+            +---------+  1
        """

        if gpio == self.gpioA:
            self.levA = level
        else:
            self.levB = level
        
        #return
        # print "GPIO {} level {}".format(gpio,level)
        
        if gpio != self.lastGpio: # debounce
            #print("{} {}".format(self.levA,self.levB))
            self.lastGpio = gpio
            try:
                if gpio == self.gpioA and level == 1:
                    if self.levB==1: self.callback(1)
                elif gpio == self.gpioB and level == 1:
                    if self.levA == 1: self.callback(-1)
            except Exception as e:
                pass

    def _pulseUA(self, gpio, level, tick):
        # Decoding specific for the UA encoders.
        if gpio == self.gpioA:
            self.levA = level
        else:
            self.levB = level
        
        if gpio != self.lastGpio:
            #print("{} {}".format(self.levA,self.levB))
            self.lastGpio = gpio
            try:
                if gpio == self.gpioA and level != self.levB:
                    self.callback(1)
                elif gpio == self.gpioB and level != self.levA:
                    self.callback(-1)
            except Exception as e:
                pass
                
    def cancel(self):

        """
        Cancel the rotary encoder decoder.
        """

        self.cbA.cancel()
        self.cbB.cancel()

if __name__ == "__main__":

    import time
    import pigpio

    import rotary

    pos = 0

    def callback(way):
        global pos
        pos += way
        print("pos={}".format(pos))

    pi = pigpio.pi()
    if 0:
        #pi.set_mode(18, pigpio.OUTPUT)
        pi.set_mode(17, pigpio.INPUT)
        pi.set_mode(27, pigpio.INPUT)
        #pi.write(18,0)
        pi.set_pull_up_down(20, pigpio.PUD_UP)
        pi.set_pull_up_down(21, pigpio.PUD_UP)
        cnt = -1
        t1 = time.time()
        while time.time()-t1 < 10:
            a = pi.read(20)
            b = pi.read(21)
            print "{} {}".format(a,b)
        exit()
        while 1:
            cnt = -1
            while 1:
                a = pi.read(20)
                b = pi.read(21)
                if a==0 or b==0 or cnt > 0:
                     print "{} {} {}".format(a,b,cnt)
                if a==0 or b==0:
                     cnt = 10
                if a and b : cnt -= 1
                if cnt == 0: break
        exit()

    decoder = rotary.decoder(pi, 20, 21, callback,UAStyle=1)
    while 0:
        print("pos={}".format(decoder.pos))
        time.sleep(0.1)
        
    time.sleep(300)

    decoder.cancel()

    pi.stop()

