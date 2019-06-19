
#!/usr/bin/env python

import pigpio

class decoder:

    """Class to decode mechanical rotary encoder pulses."""

    def __init__(self, pi, gpioA, gpioB, callback):

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

        self.pi.set_pull_up_down(gpioA, pigpio.PUD_UP)
        self.pi.set_pull_up_down(gpioB, pigpio.PUD_UP)
        # THis is quite crucial with the shitty encoders.
        self.pi.set_glitch_filter(gpioA, 1000)
        self.pi.set_glitch_filter(gpioA, 1000)
        # RISING_EDGE (default), or FALLING_EDGE, EITHER_EDGE
        self.cbA = self.pi.callback(gpioA, pigpio.EITHER_EDGE, self._pulse)
        self.cbB = self.pi.callback(gpioB, pigpio.EITHER_EDGE, self._pulse)
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
            if gpio == self.gpioA and level == 1:
                if self.levB==1: self.callback(1)
            elif gpio == self.gpioB and level == 1:
                if self.levA == 1: self.callback(-1)

               
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
        pi.set_mode(18, pigpio.OUTPUT)
        pi.set_mode(17, pigpio.INPUT)
        pi.set_mode(27, pigpio.INPUT)
        pi.write(18,0)
        pi.set_pull_up_down(17, pigpio.PUD_UP)
        pi.set_pull_up_down(27, pigpio.PUD_UP)
        cnt = -1
        while 0:
            a = pi.read(17)
            b = pi.read(27)
            print "{} {}".format(a,b)
        while 1:
            cnt = -1
            while 1:
                a = pi.read(17)
                b = pi.read(27)
                if a==0 or b==0 or cnt > 0:
                     print "{} {} {}".format(a,b,cnt)
                if a==0 or b==0:
                     cnt = 10
                if a and b : cnt -= 1
                if cnt == 0: break
        exit()

    decoder = rotary.decoder(pi, 27, 17, callback)
    while 0:
        print("pos={}".format(decoder.pos))
        time.sleep(0.1)
        
    time.sleep(300)

    decoder.cancel()

    pi.stop()

