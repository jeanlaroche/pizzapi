from twilio.rest import Client
import threading

account = "AC61f8be00513231ed9b5301e3593d87eb"
token = "fee568ebe5a55fda904670a0fbcc60f1"


def repeatFunc(delayS,nRepeats=-1):
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


def sendText(body):
    # Sends a text to my phone number using twilio
    client = Client(account, token)
    client.messages.create(to="8312957882", from_="8317775381", body=body)

@repeatFunc(2,4)
def test():
    print("foo")
