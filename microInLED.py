

import pyaudio
import time
import numpy as np
import threading

import RPi.GPIO as GPIO
import time

redLightsPin = 15
blueLightsPin = 13
greenLightsPin = 11
dgreenLightsPin = 7

red2LightsPin = 19
blue2LightsPin = 21
green2LightsPin = 23

allPins = [redLightsPin, blueLightsPin, greenLightsPin, dgreenLightsPin, red2LightsPin, blue2LightsPin, green2LightsPin]




def getFFT(data,rate):
    """Given some data and rate, returns FFTfreq and FFT (half)."""
    data=data*np.hamming(len(data))
    fft=np.fft.fft(data)
    fft=np.abs(fft)
    freq=np.fft.fftfreq(len(fft),1.0/rate)
    return freq[:int(len(freq)/2)],fft[:int(len(fft)/2)]

class microInLED():
    """
    The provides access to microphone input to LED output spectrum analyzer.
    use pyAudio and pyNum 
    Arguments:
        
    """

    def __init__(self,device=None,rate=None,updatesPerSecond=10):
        self.p=pyaudio.PyAudio()
        self.chunk=4096 
        self.updatesPerSecond=updatesPerSecond
        self.chunksRead=0
        self.device=device
        self.rate=rate

    ### SYSTEM TESTS

    def valid_low_rate(self,device):
        """set the rate to the lowest supported audio rate."""
        for testrate in [44100]:
            if self.valid_test(device,testrate):
                return testrate
        print("SOMETHING'S WRONG! I can't figure out how to use DEV",device)
        return None

    def valid_test(self,device,rate=44100):
        """given a device ID and a rate, return TRUE/False if it's valid."""
        try:
            self.info=self.p.get_device_info_by_index(device)
            if not self.info["maxInputChannels"]>0:
                return False
            stream=self.p.open(format=pyaudio.paInt16,channels=1,
               input_device_index=device,frames_per_buffer=self.chunk,
               rate=int(self.info["defaultSampleRate"]),input=True)
            stream.close()
            return True
        except:
            return False

    def valid_input_devices(self):
        """
        See which devices can be opened for microphone input.
        call this when no PyAudio object is loaded.
        """
        mics=[]
        for device in range(self.p.get_device_count()):
            if self.valid_test(device):
                mics.append(device)
        if len(mics)==0:
            print("no microphone devices found!")
        else:
            print("found %d microphone devices: %s"%(len(mics),mics))
        return mics

    ### SETUP AND SHUTDOWN

    def initiate(self):
        """run this after changing settings (like rate) before recording"""
        if self.device is None:
            self.device=self.valid_input_devices()[0] #pick the first one
        if self.rate is None:
            self.rate=self.valid_low_rate(self.device)
        self.chunk = int(self.rate/self.updatesPerSecond) # hold one tenth of a second in memory
        if not self.valid_test(self.device,self.rate):
            print("guessing a valid microphone device/rate...")
            self.device=self.valid_input_devices()[0] #pick the first one
            self.rate=self.valid_low_rate(self.device)
        self.datax=np.arange(self.chunk)/float(self.rate)
        msg='recording from "%s" '%self.info["name"]
        msg+='(device %d) '%self.device
        msg+='at %d Hz'%self.rate
        print(msg)

        GPIO.setmode(GPIO.BOARD)  # Numbers GPIOs by physical location
        for pin in allPins:
            GPIO.setup(pin, GPIO.OUT)  # Set all pins' mode is output
            GPIO.output(pin, GPIO.HIGH)  # Set all pins to high(+3.3V) to off led


    def close(self):
        """gently detach from things."""
        print(" -- sending stream termination command...")
        self.keepRecording=False #the threads should self-close
        while(self.t.isAlive()): #wait for all threads to close
            time.sleep(.1)
        self.stream.stop_stream()
        self.p.terminate()

    ### STREAM HANDLING

    def stream_readchunk(self):
        """reads some audio and re-launches itself"""
        try:
            self.data = np.fromstring(self.stream.read(self.chunk),dtype=np.int16)
            self.fftx, self.fft = getFFT(self.data,self.rate)

        except Exception as E:
            print(" -- exception! terminating...")
            print(E,"\n"*5)
            self.keepRecording=False

        max1 = 160000
        max2 = 80000
        max3 = 40000        
        max4 = 30000
        max5 = 2000
        max6 = 1000        
        b1 =  500
        b2 = 1000
        b3 = 1500
        b4 = 2000
        b5 = 2500
        b6 = 3000
        for i in range(len(self.fftx)): 
            # print("f=fft ",self.fftx[i],self.fft[i]);
            if ( i == 0 ) :
                GPIO.output(redLightsPin, GPIO.HIGH) # off    
            if ( i > 0 and i < b1 ) :
                if self.fft[i] > max1:
                    GPIO.output(redLightsPin, GPIO.LOW) # on

            if ( i == b1 ) :
                GPIO.output(blueLightsPin, GPIO.HIGH) # off    
            if ( i > b1 and i < b2 ) :
                if self.fft[i] > max2:
                    GPIO.output(blueLightsPin, GPIO.LOW) # on

            if ( i == b2 ) :
                GPIO.output(greenLightsPin, GPIO.HIGH) # off    
            if ( i > b2 and i < b3 ) :
                if self.fft[i] > max3:
                    GPIO.output(greenLightsPin, GPIO.LOW) # on

            if ( i == b3 ) :
                GPIO.output(red2LightsPin, GPIO.HIGH) # off    
            if ( i > b3 and i < b4 ) :
                if self.fft[i] > max4:
                    GPIO.output(red2LightsPin, GPIO.LOW) # on

            if ( i == b4 ) :
                GPIO.output(blue2LightsPin, GPIO.HIGH) # off    
            if ( i > b4 and i < b5 ) :
                if self.fft[i] > max2:
                    GPIO.output(blue2LightsPin, GPIO.LOW) # on

            if ( i == b5 ) :
                GPIO.output(green2LightsPin, GPIO.HIGH) # off    
            if ( i > b5 and i < b6 ) :
                if self.fft[i] > max3:
                    GPIO.output(green2LightsPin, GPIO.LOW) # on
            
        if self.keepRecording:
            self.stream_thread_new()
        else:
            self.stream.close()
            self.p.terminate()
            print(" -- stream STOPPED")
        self.chunksRead+=1

    def stream_thread_new(self):
        self.t=threading.Thread(target=self.stream_readchunk)
        self.t.start()

    def stream_start(self):
        """adds data to self.data until termination signal"""
        self.initiate()
        print(" -- starting stream")
        self.keepRecording=True # set this to False later to terminate stream
        self.data=None # will fill up with threaded recording data
        self.fft=None
        self.dataFiltered=None #same
        self.stream=self.p.open(format=pyaudio.paInt16,channels=1,
                      rate=self.rate,input=True,frames_per_buffer=self.chunk)
        self.stream_thread_new()

if __name__=="__main__":
    ear=SWHear(updatesPerSecond=10) # optinoally set sample rate here
    ear.stream_start() #goes forever
    lastRead=ear.chunksRead
    while True:
        while lastRead==ear.chunksRead:
            time.sleep(.01)
        print(ear.chunksRead,len(ear.data))
        lastRead=ear.chunksRead
    GPIO.output(redLightsPin, GPIO.HIGH) # off
    GPIO.output(blueLightsPin, GPIO.HIGH) # off
    GPIO.output(greenLightsPin, GPIO.HIGH) # off        
    GPIO.output(red2LightsPin, GPIO.HIGH) # off
    GPIO.output(blue2LightsPin, GPIO.HIGH) # off
    GPIO.output(green2LightsPin, GPIO.HIGH) # off        
    print("DONE")

