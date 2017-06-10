#! /usr/bin/python
#
# Nabaztag emulator for Raspberry by Carlo64 :-P
# 2016 v 001 002 003 004
# RGB led 
#
# 
from threading import Thread
import RPi.GPIO as GPIO
import smbus

import random
import string
import md5
import subprocess
import os.path
import socket    
import sys
import struct
import time
import base64
import re

RFIDSTAMP=''

bus=smbus.SMBus(1) # check with: i2cdetect -y 1

#################### RFID
R_PARAM = 0x00 #Parameter Register
R_FRAME = 0x01 #Input/Output Frame Register
R_AUTH  = 0x02 #Authenticate Register
R_SLOT  = 0x03 #slot Marker Register
RFID    = 0x50 #address
cmdInitiate  = [0x02,0x06,0x00]
cmdSelectTag = [0x02,0x0E,0x00]
cmdGetTagUid = [0x01,0x0B]
zero = []

###################### LED 1 2 3 4 

DEVICE =0x20
IODIRA =0x00
IODIRB =0x01
OLATA  =0x14
OLATB  =0x15
GPIOA  =0x12
GPIOB  =0x13

bus.write_byte_data(DEVICE,IODIRA,0x00) # all output
bus.write_byte_data(DEVICE,IODIRB,0x00)

bus.write_byte_data(DEVICE,OLATA,0) # all off
bus.write_byte_data(DEVICE,OLATB,0)

def ledOn(colorLeft,colorMiddle,colorRight,colorTop,colorAll):
   global bus
   global DEVICE
   global OLATA
   global OLATB
##      000    001  010   011  100 101    110    111
#       none   blue green cyan red violet yellow white
#       0      1    2     3    4   5      6      7
   tableColor=[0b000,0b001,0b010,0b011,0b100,0b101,0b110,0b111]
   outputA = 0
   outputB = 0
   if colorLeft:
      outputA = outputA | tableColor[colorLeft]
   if colorMiddle:
      outputA = outputA | tableColor[colorMiddle]*8
   if colorRight:
      outputB = outputB | tableColor[colorRight]
   if colorTop:
      outputB = outputB | tableColor[colorTop]*8
   if colorAll:
      outputA = 0
      outputB = 0   
      outputA = outputA | tableColor[colorAll]   
      outputA = outputA | tableColor[colorAll]*8
      outputB = outputB | tableColor[colorAll]
      outputB = outputB | tableColor[colorAll]*8
      
   bus.write_byte_data(DEVICE,OLATA,outputA)
   bus.write_byte_data(DEVICE,OLATB,outputB)

ledOn(0,0,0,0,2)
time.sleep(1)
ledOn(3,0,0,0,0)
time.sleep(1)
ledOn(0,0,0,0,0)
#####################################
#
resetEar=0 # if 1 do reset
newPosLeft=0 # 0 - 17
newPosRight=0 # 0 - 17
motorLeftOn=0 #1 se acceso
motorRightOn=0
fakeLeft=0 # 0 - 17
fakeRight=0 # 0 - 17   
#
def motorLeft(s,dir):
  #dir = 0 clockwise - 1 counterclockwise (0 forward - 1 back)
  ##global pwm
  global fakeLeft # 0 - 15
  global motorLeftOn
  global resetEar # if 1 do reset
  global newPosLeft # 0 - 15
  if s=='start':
    if motorLeftOn==0:
      print "motorLeft START! ", s, " pos now:", fakeLeft, " next step ",newPosLeft      
      if dir==0:
        GPIO.output(motorLeftA,GPIO.HIGH)
        GPIO.output(motorLeftB,GPIO.LOW)
      else:
        GPIO.output(motorLeftA,GPIO.LOW)
        GPIO.output(motorLeftB,GPIO.HIGH)
      GPIO.output(motorLeftE,GPIO.HIGH)
      ##pwm = GPIO.PWM(motorLeftE,50)   ## pwm de la pin 22 a une frequence de 50 Hz
      ##pwm.start(40)   ## on commemnce avec un rapport cyclique de 100%
    motorLeftOn=1
  else:
    if motorLeftOn==1:
      print "motorLeft STOP! ", s
      GPIO.output(motorLeftE,GPIO.LOW)
      ##GPIO.output(motorLeftE,GPIO.LOW)
      ##pwm.stop()
    motorLeftOn=0  

def motorRight(s,dir):
  #dir = 0 clockwise - 1 counterclockwise (0 forward - 1 back)
  global fakeRight # 0 - 15
  global motorRightOn
  global resetEar # if 1 do reset
  global newPosRight # 0 - 15
  if s=='start':
    if motorRightOn==0:
      print "motorRight START! ", s, " pos now:", fakeRight, " next step ",newPosRight      
      if dir==0:
        GPIO.output(motorRightA,GPIO.HIGH)
        GPIO.output(motorRightB,GPIO.LOW)      
      else:
        GPIO.output(motorRightA,GPIO.LOW)
        GPIO.output(motorRightB,GPIO.HIGH)            
      GPIO.output(motorRightE,GPIO.HIGH)
    motorRightOn=1
  else:
    if motorRightOn==1:
      print "motorRight STOP! ", s
      GPIO.output(motorRightE,GPIO.LOW)
    motorRightOn=0  





#
# variables
#
errorSOCK=0
later=0.8 #delay between send and receive
logSW=1 # value: 0 nothing, 1 write file log.txt (warning no size control), 2 console
sleep=0
infoTaichi=0
loopTry=50 ### CHANGE if you want
midiList=["midi_1noteA4","midi_1noteB5","midi_1noteBb4","midi_1noteC5",
"midi_1noteE4","midi_1noteF4","midi_1noteF5","midi_1noteG5","midi_2notesC6C4",
"midi_2notesC6F5","midi_2notesD4A5","midi_2notesD4G4","midi_2notesD5G4",
"midi_2notesE5A5","midi_2notesE5C6","midi_2notesE5E4","midi_3notesA4G5G5",
"midi_3notesB5A5F5","midi_3notesB5D5C6","midi_3notesD4E4G4","midi_3notesE5A5C6",
"midi_3notesE5C6D5","midi_3notesE5D5A5","midi_3notesF5C6G5"]
defaultLedColor=1
bootVer="18673"
pathBase='/home/pi/extra/'
pathAudio=pathBase+'A'
pathAudioFile=pathBase+'audio.wav'
pathLocate=pathBase+'locate.txt'
pathUser =pathBase+'user.txt'
pathRfid=pathBase+'R'
rfidtxt=pathBase+'rfid.txt'


script=pathBase+'script.sh'
logFile=pathBase+'log.txt'


##  --------------------------------------------------
##
## LED breath pin GPIO BOARD red 11, green 13, blue 12
## MOTORS pin GPIO BOARD left(36,38,40) right(33,35,37)
## SENSORS left(15) right()
##
##  --------------------------------------------------

GPIO.setmode(GPIO.BOARD)
#GPIO.setwarnings(False)

buttonPin = 18

sensorPinLeft = 15
sensorPinRight = 16

ledRed = 11
ledGreen = 13
ledBlue = 12

motorLeftA = 36
motorLeftB = 38
motorLeftE = 40

motorRightA = 33
motorRightB = 35
motorRightE = 37

#
# MOTORS
#
GPIO.setup(motorLeftA,GPIO.OUT)
GPIO.setup(motorLeftB,GPIO.OUT)
GPIO.setup(motorLeftE,GPIO.OUT)
GPIO.setup(motorRightA,GPIO.OUT)
GPIO.setup(motorRightB,GPIO.OUT)
GPIO.setup(motorRightE,GPIO.OUT)

GPIO.output(motorLeftA,GPIO.HIGH)
GPIO.output(motorLeftB,GPIO.LOW)
GPIO.output(motorLeftE,GPIO.LOW) #off
GPIO.output(motorRightA,GPIO.HIGH)
GPIO.output(motorRightB,GPIO.LOW)
GPIO.output(motorRightE,GPIO.LOW) #off
#
# LED
#
GPIO.setup(ledRed, GPIO.OUT)
GPIO.setup(ledGreen, GPIO.OUT)
GPIO.setup(ledBlue, GPIO.OUT)

GPIO.output(ledRed,False) #off
GPIO.output(ledGreen,False) #off
GPIO.output(ledBlue,False) #off
# Use PWM to fade..........
fadeRed = GPIO.PWM(ledRed, 100)
fadeRed.start(0)
fadeGreen = GPIO.PWM(ledGreen, 100)
fadeGreen.start(0)
fadeBlue = GPIO.PWM(ledBlue, 100)
fadeBlue.start(0)

#
# SENSORS
#
GPIO.setup(sensorPinLeft,GPIO.IN)  #left
GPIO.setup(sensorPinRight,GPIO.IN)  #right

#
# BUTTON
#
GPIO.setup(buttonPin,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)

laterRfid=0.05
#
# RFID ....
#
class ThreadingRfid:
    def __init__(self, interval=1):
        self.interval = interval
        self._running = True
        self._pause = True
    def terminate(self):
        self._running = False
    def pause(self):
        self._pause = False
        time.sleep(0.2)
    def resume(self):
        self._pause = True
    def run(self):
        global RFIDSTAMP
        global pathRfid
        global pathBase
        global laterRfid
        while self._running: 
            if self._pause:
                bus.write_quick(RFID)
                bus.write_byte_data(RFID,R_PARAM,0x00) #off rfid! test, if read must be 00
                bus.write_byte_data(RFID,R_PARAM,0x10) #on rfid! test, if read must be 10
                ###time.sleep(laterRfid)

                bus.write_i2c_block_data(RFID,R_FRAME,cmdInitiate)
                time.sleep(laterRfid)
                
                r = bus.read_i2c_block_data(RFID,R_FRAME)
                #####time.sleep(laterRfid)
                
                ###############print "wait for rfid ...",r[0]
                if r[0]<>0x00:
                  bus.write_i2c_block_data(RFID,R_SLOT,zero) #Turn on detected sequence of tags
                  time.sleep(laterRfid)
                  
                  bus.write_i2c_block_data(RFID,R_FRAME,zero) 
                  
                  tableChip=bus.read_i2c_block_data(RFID,R_FRAME) 
                  
                  find = (tableChip[2] << 8) + tableChip[1];
                  if find>0:
                    print "found, now test chip: "  ,tableChip    

                    countTag=0        
                    wordBitIdx = (tableChip[2]<<8) + tableChip[1]
                    print "wordBitIdx: ",wordBitIdx
                    for idxTmp in range( 0,16):
                      if (wordBitIdx & 0x0001):
                        print "CHIP ",tableChip[idxTmp+3]
                        
                        cmdSelectTag[2]=tableChip[idxTmp+3]
                        bus.write_i2c_block_data(RFID,R_FRAME,cmdSelectTag)  #select chip 
                        time.sleep(laterRfid) 
                        
                        bus.write_i2c_block_data(RFID,R_FRAME,zero) 
                        time.sleep(laterRfid)
                                    
                        rr=bus.read_i2c_block_data(RFID,R_FRAME)  # 
                        # test response != null && response.Length == 2 && response[1] == tag.ChipId;
                        
                        bus.write_i2c_block_data(RFID,R_FRAME,cmdGetTagUid) #get id  
                        time.sleep(laterRfid) 
                        
                        bus.write_i2c_block_data(RFID,R_FRAME,zero) 
                        ###time.sleep(laterRfid)
                                    
                        uid=bus.read_i2c_block_data(RFID,R_FRAME)  # read id

                        print "getuid :", countTag, " len + udi (8 byte) ",uid
                        u=''.join(hex(a )[2:].zfill(2) for a in reversed(uid[1:9]))
                        print "your TAG is: ", u
                        #ricordati minuscolo !!! rfid=rfid.lower()
                        #d00218c1090b9f90   d0 02 18 c1 09 0b 9f 90
                        #d00218c109163e94   d0 02 18 c1 09 16 3e 94
                        # save rifd
                        pathRfid=pathBase+'R'
                        text_file = open(pathRfid, "w")
                        text_file.write(u)
                        text_file.close()
                        # or
                        RFIDSTAMP = u
                        
                        countTag+=1
                      wordBitIdx>>=1
                      
            time.sleep(0.1)
            
cRfid = ThreadingRfid()
tRfid = Thread(target=cRfid.run) ###, args=(10,))
tRfid.daemon = True
###### ** tRfid.start() 
#
# END RFID
#


#
# PULSE ....
#
class ThreadingBreath:
    def __init__(self, interval=1):
        self.interval = interval
        self._running = True
        self._pause = True
        self._color = 4
        self.setColor( 4 ) #red at boot time       
    def terminate(self):
        self._running = False
    def pause(self):
        self._pause = False
        time.sleep(0.2)
        self.setColor(self._color)        
    def resume(self):
        self._pause = True
    def setColor(self, c):
        self._color = c
        if c == 0:
          self._vred = 0
          self._vgreen = 0
          self._vblue = 0
        elif c == 1:
          self._vred = 0
          self._vgreen = 0
          self._vblue = 99
        elif c == 2:
          self._vred = 0
          self._vgreen = 99
          self._vblue = 0
        elif  c == 3:
          self._vred = 0
          self._vgreen = 99
          self._vblue = 99
        elif  c == 4:
          self._vred = 99
          self._vgreen = 0
          self._vblue = 0
        elif  c == 5:
          self._vred = 99
          self._vgreen = 0
          self._vblue = 99
        elif  c == 6:
          self._vred = 99
          self._vgreen = 99
          self._vblue = 0
        elif  c == 7:
          self._vred = 99
          self._vgreen = 99
          self._vblue = 99
        self._red = (self._vred>0)
        self._green = (self._vgreen>0)
        self._blue = (self._vblue>0)                     
    def run(self):
        global fadeRed
        global fadeGreen
        global fadeBlue
        updownFade = True
        incFade = 1
        while self._running: 
            if self._pause:
                fadeRed.ChangeDutyCycle(self._vred)
                fadeGreen.ChangeDutyCycle(self._vgreen)
                fadeBlue.ChangeDutyCycle(self._vblue)
                if updownFade:
                    if self._red: 
                      self._vred += incFade
                    if self._green: 
                      self._vgreen += incFade
                    if self._blue: 
                      self._vblue += incFade
                    time.sleep(0.002)
                else:
                    if self._red: 
                      self._vred -= incFade
                    if self._green: 
                      self._vgreen -= incFade
                    if self._blue: 
                      self._vblue -= incFade
                    time.sleep(0.002)

                if (self._vred >= 100) and self._red:
                    updownFade = False
                if (self._vgreen >= 100) and self._green:
                    updownFade = False
                if (self._vblue >= 100) and self._blue:
                    updownFade = False

                if (self._vred <= 2) and self._red:
                    updownFade = True
                if (self._vgreen <= 2) and self._green:
                    updownFade = True
                if (self._vblue <= 2) and self._blue:
                    updownFade = True

            time.sleep(0.03)
            ###time.sleep(self.interval)
            
cBreath = ThreadingBreath()
breath = Thread(target=cBreath.run) ###, args=(10,))
breath.daemon = True
####### ** breath.start() 
#
# END PULSE
#




## -----------------------------------------------
# sensori
"""
reset 
avvia motore
set tempo
se delta e' zero
 su up e dw salva delta
se delta e' valorizzato
 su up e dw controlla delta
 se in range non e' posizione zero
 se 


if stato==UP and rangeTime()
if up:
  sup=True
  sdw=False
  stato=UP
if dw:
  sdw=True
  sup=False
  stato=DOWN
## -----------------------------------------------



"""

# 
# SENSORS
# event on change state
#
sLeftU=False
sLeftD=False
def eventSensorLeft(channel):
    #global sensorPinLeft
    global sLeftU #evento up
    global sLeftD #evento down
    global newPosLeft # 0 - 17
    global fakeLeft
##    print "Evento # : GPIO", GPIO.input(channel), fakeLeft
    GPIO.remove_event_detect(channel)
    if GPIO.input(channel):
        sLeftU=True
        sLeftD=False
        if newPosLeft==fakeLeft:
          motorLeft('stop',0)    
        else:
          fakeLeft +=1
        ####print "RISING Triggered "
        if fakeLeft>15:
           fakeLeft=0   
           newPosLeft=0            
    else:
        sLeftU=False
        sLeftD=True
        ####print "FALLING Triggered "
    GPIO.add_event_detect(channel, GPIO.BOTH, callback=eventSensorLeft)
#GPIO.wait_for_edge(i, GPIO.RISING)  #in salita oppure gpio.FALLING)
GPIO.add_event_detect(sensorPinLeft, GPIO.BOTH, callback=eventSensorLeft)#, bouncetime=200)

sRightU=False
sRightD=False
def eventSensorRight(channel):
    #global sensorPinRight
    global sRightU #evento up
    global sRightD #evento down
    global newPosRight # 0 - 17
    global fakeRight
###    print "Evento # : GPIO", GPIO.input(channel), fakeRight
    GPIO.remove_event_detect(channel)
    if GPIO.input(channel):
        sRightU=True
        sRightD=False
        if newPosRight==fakeRight:
          motorRight('stop',0)    
        else:
          fakeRight +=1
        #####print "RISING Triggered "
        if fakeRight>15:
           fakeRight=0   
           newPosRight=0            
    else:
        sRightU=False
        sRightD=True
        ####print "FALLING Triggered "
    GPIO.add_event_detect(channel, GPIO.BOTH, callback=eventSensorRight)
#GPIO.wait_for_edge(i, GPIO.RISING)  #in salita oppure gpio.FALLING)
GPIO.add_event_detect(sensorPinRight, GPIO.BOTH, callback=eventSensorRight)#, bouncetime=200)




#
# find reset position !?!?
#
class ThreadingSensorLeft:
    def __init__(self, interval=0.3):
        self.interval = interval
        self._running = True
        self._pause = True
    def pause(self):
        self._pause = False
    def resume(self):
        self._pause = True
    def terminate(self):
        self._running = False
    def run(self):
        global fakeLeft
	global newPosLeft
        global sLeftU #evento up
        global sLeftD #evento down
        conta=0
        while self._running: 
            if self._pause:
                if sLeftD:
                  conta+=1
                  print "left conta",conta
                if sLeftU:
                  conta-=1
                if conta>1 or conta<0:
                   print "position zero"
                   fakeLeft=0   
                   newPosLeft=1
                   self._pause=False #stop
            time.sleep(self.interval)
class ThreadingSensorRight:
    def __init__(self, interval=0.3):
        self.interval = interval
        self._running = True
        self._pause = True
    def pause(self):
        self._pause = False
    def resume(self):
        self._pause = True
    def terminate(self):
        self._running = False
    def run(self):
	global newPosRight # 0 - 17
        global fakeRight
        global sRightU #evento up
        global sRightD #evento down
        conta=0
        while self._running: 
            if self._pause:
                if sRightD:
                  conta+=1
                  print "right conta",conta
                if sRightU:
                  conta-=1
                if conta>1 or conta<0:
                   print "position zero"
                   fakeRight=0   
                   newPosRight=1
                   self._pause=False #stop
            time.sleep(self.interval)

cSensorLeft = ThreadingSensorLeft()
sensorL = Thread(target=cSensorLeft.run)
sensorL.daemon=True
cSensorRight = ThreadingSensorRight()
sensorR = Thread(target=cSensorRight.run)
sensorR.daemon=True

#
# TAICHI ....
#
class ThreadingTaichi:
    def __init__(self, interval=1):
        self.interval = interval
        self._running = True
        self._pause = True
        self._taichi = 0
    def setTaichi(self,x):
        self._taichi = x
    def terminate(self):
        self._running = False
    def pause(self):
        self._pause = False
        time.sleep(0.2)
    def resume(self):
        self._pause = True
    def run(self):
        global fakeLeft
        global fakeRight
        global motorLeftOn
        global motorRightOn
        global newPosLeft
        global newPosRight
        while self._running: 
            if self._pause:
               if self._taichi>0:
                  # viaaaaaaaa
                  if self._taichi==1:
                    #generator...
                    ne = random.randint(1,8) # numero elementi
                    pl=0
                    pr=0
                    tabellaTaichi=[]
                    for i in range(0, ne):
                      plm=pl+3
                      if plm>16:
                       plm=16
                      prm=pr+3
                      if prm>16:
                       prm=16
                    #  print "maxl=",plm," maxr=",prm
                      ml = random.randint(pl,plm)
                      mr = random.randint(pr,prm)
                      print "ml=",ml," mr=",mr
                      tabellaTaichi.insert(99,ml)
                      tabellaTaichi.insert(99,mr)
                      pl = ml+1
                      pr = mr+1
                      if pl>15:
                        pl=0
                      if pr>15:
                        pr=0                    
                                        
                    ##tabellaTaichi=[4,4,8,8,12,12,16,16,3,3,7,7,12,12,0,0]
                    indexTaichi = len(tabellaTaichi)
                    for idx in range(0,indexTaichi,2):
                      sxi = tabellaTaichi[idx]
                      dxi = tabellaTaichi[idx+1]
                      if sxi<=0:
                        sxi=16+sxi
                      if dxi<0:
                        dxi=16+dxi
                      if fakeLeft<sxi:
                        newPosLeft=sxi
                        motorLeft('start',0)                 
                      if fakeRight<dxi:
                        newPosRight=dxi
                        motorRight('start',0)     
                      while motorLeftOn==1 or motorRightOn==1:
                         time.sleep(0.1)
                    self._taichi = 0
           
              
            time.sleep(0.05)
            ###time.sleep(self.interval)
            
cTaichi = ThreadingTaichi()
tTaichi = Thread(target=cTaichi.run) ###, args=(10,))
tTaichi.daemon = True
#### ** tTaichi.start() 
###cTaichi.setTaichi(1) #test
#
# END TAICHI
#
#
# TAICHI led....
#
class ThreadingTaichiLed:
    def __init__(self, interval=1):
        self.interval = interval
        self._running = True
        self._pause = True
        self._taichi = 0
    def setTaichi(self,x):
        self._taichi = x
    def terminate(self):
        self._running = False
    def pause(self):
        self._pause = False
        time.sleep(0.2)
    def resume(self):
        self._pause = True
    def run(self):
        global fakeLeft
        global fakeRight
        global motorLeftOn
        global motorRightOn
        global newPosLeft
        global newPosRight
        while self._running: 
            if self._pause:
               if self._taichi>0:
                  # ok
                  if self._taichi==1:
                    #one
                    #led
                    ne = random.randint(1,16) # numero elementi
                    tabellaTaichi=[]
                    for i in range(0, ne):
                      a = random.randint(0,7)
                      b = random.randint(0,7)
                      c = random.randint(0,7)
                      d = random.randint(0,7)       
#                      print a,b,c,d
                      tabellaTaichi.insert(99,a)
                      tabellaTaichi.insert(99,b)
                      tabellaTaichi.insert(99,c)
                      tabellaTaichi.insert(99,d)
                      tabellaTaichi.insert(99,0)
                    indexTaichi = len(tabellaTaichi)
                    for idx in range(0,indexTaichi,5):
                      a = tabellaTaichi[idx]
                      b = tabellaTaichi[idx+1]
                      c = tabellaTaichi[idx+2]
                      d = tabellaTaichi[idx+3]
                      e = tabellaTaichi[idx+4]
  
                      ledOn( a, b, c, d, e)   
                      time.sleep(0.2)
                    self._taichi = 0
                    ledOn( 0, 0, 0, 0, 0)   
           
              
            time.sleep(0.05)
            ###time.sleep(self.interval)
            
lTaichi = ThreadingTaichiLed()
tlTaichi = Thread(target=lTaichi.run) ###, args=(10,))
tlTaichi.daemon = True
##### ** tlTaichi.start() 
##lTaichi.setTaichi(1) #test
#
# END TAICHI
#


# reset position
fakeLeft = 0   
newPosLeft = 16
# reset position
fakeRight = 0   
newPosRight = 16

# start motors
motorLeft('start',0)                 
####sensorL.start()
motorRight('start',0)                 
###sensorR.start()
# wait
print "wait... ears"
for zz in range(1,12):
  print "right ", fakeRight, " left ", fakeLeft
  time.sleep(1)


# 
# Button int
#
bCount=0
bWait=0
def eventButton(channel):
    global bCount
    print "Evento bottone# : GPIO", GPIO.input(channel)
    GPIO.remove_event_detect(channel)
    if GPIO.input(channel):
        bCount+=1
        print "RISING Triggered ", bCount
    else:
        ##bCount=0
        print "FALLING Triggered "
    GPIO.add_event_detect(channel, GPIO.BOTH, callback=eventButton)
#GPIO.wait_for_edge(i, GPIO.RISING)  #in salita oppure gpio.FALLING) BOTH
GPIO.add_event_detect(buttonPin, GPIO.BOTH, callback=eventButton)#, bouncetime=200)
  
# 

def pollButton():    
    global RFIDSTAMP
    global bCount
    global bWait
    print "pollButton.."
    if  os.path.exists(pathAudio):
      subprocess.call(["/bin/rm", pathAudio])
      subprocess.call(["/bin/rm", pathAudioFile])
      tt = "/usr/bin/ffmpeg -f oss -i /dev/dsp "+pathAudioFile+" -t 00:00:03"
      subprocess.call( tt, shell=True )      
      audio = 'http://'+h+httpPort+'/vl/record.jsp?sn='+mac+'&v='+bootVer+'&h=4&m=0'
      tt = "/usr/bin/curl -0 --header 'Content-Type:application/octet-stream' --data-binary @"+pathAudioFile+" '"+audio+"'"
#      subprocess.call( tt, shell=True )      
      subprocess.Popen( tt, shell=True )  # dont wait    
      debugLog( 'rcord audio file: ' )
      
    # or
    if RFIDSTAMP<>'':
      rfid=RFIDSTAMP.lower()
      RFIDSTAMP = ''
      rfidSend='http://'+h+httpPort+'/vl/rfid.jsp?sn='+mac+'&v='+bootVer+'&h=4&t='+rfid ###+''
      subprocess.Popen( "/usr/bin/curl -0 -A MTL --header 'Accept: ' --header 'Pragma: no-cache' --header 'Icy-MetaData: 0' --header 'Host: "+ping+"' '"+rfidSend+"' >"+rfidtxt, shell=True )   # dont wait
      debugLog( 'rfid: ' + rfid )    
    """
    if  os.path.exists(pathRfid):
      rfid = open(pathRfid).read().replace('\n','') 
      rfid=rfid.lower()
      subprocess.call(["/bin/rm", pathRfid])
      rfidSend='http://'+h+httpPort+'/vl/rfid.jsp?sn='+mac+'&v='+bootVer+'&h=4&t='+rfid ###+''
#      subprocess.call( "/usr/bin/curl -0 -A MTL --header 'Accept: ' --header 'Pragma: no-cache' --header 'Icy-MetaData: 0' --header 'Host: "+ping+"' '"+rfidSend+"' >"+rfidtxt, shell=True )      
      subprocess.Popen( "/usr/bin/curl -0 -A MTL --header 'Accept: ' --header 'Pragma: no-cache' --header 'Icy-MetaData: 0' --header 'Host: "+ping+"' '"+rfidSend+"' >"+rfidtxt, shell=True )   # dont wait
      debugLog( 'rfid: ' + rfid )
    """
    if  bCount>0:
      # bwait wait for double press
      bWait+=1
      if bWait>0:
         print "click numbers ",bCount
         if bCount==1:
            print "single click"
            m='<message from=\''+mac+'@'+h+'/idle\' to=\''+h+'\' id=\'26\'><button xmlns="violet:nabaztag:button"><clic>1</clic></button></message>'
            sendmsg(s,m)
            debugLog( 'one button click: ' + m )
         elif bCount==2:
            print "double click"
            m='<message from=\''+mac+'@'+h+'/idle\' to=\''+h+'\' id=\'26\'><button xmlns="violet:nabaztag:button"><clic>2</clic></button></message>'
            sendmsg(s,m)
            debugLog( 'two button click: ' + m )  
         elif bCount==3:
            print "triple click"
         bWait=0
         bCount=0

############################
# FUNCTION write debug log 
############################
def debugLog( txt ): #v4
    n = "( " + time.strftime("%c") + " ) "
    if logSW==1:
       subprocess.call( 'echo "'+n+txt+'" >> '+logFile, shell=True )  
    if logSW==2:
       print n, txt
    return
############################
# FUNCTION restore/set led
############################
def restoreLed( defaultLedColor ):
    global cBreath
    cBreath.pause()  
    cBreath.setColor(color)
    cBreath.resume()     
    return
############################
# FUNCTION taichi
############################
#// 
#// donc si x=30, (x*R)>>7 => 15  45 mn
#// donc si x=40, (x*R)>>7 => 20  61 mn
#// donc si x=80, (x*R)>>7 => 40  122 mn
#    R=60*((rand&127)+64)) => 64  196 mn
#// donc si x=216, (x*R)>>7 => 108  330 mn
#// donc si x=255, (x*R)>>7 => 127  390 mn, soit 2  6,5h
#openjabnab.fr 
#<option value="10" selected >Ultra</option> 0x0a
#<option value="30"  >Beaucoup</option> 0x1e
#<option value="60"  >Souvent</option> 0x3c
#<option value="120"  >Un peu</option> 0x78
#<option value="0"  >Pas de TaiChi</option>
# base source
#<option value="50" <?php if ($frequency==50) echo 'selected'; ?> >Un peu...</option> 0x32
#<option value="125" <?php if ($frequency==125) echo 'selected'; ?>>Beaucoup...</option> 0x7d
#<option value="250" <?php if ($frequency==250) echo 'selected'; ?>>A la folie...</option> 0xfa
#<option value="0" <?php if ($frequency==0) echo 'selected'; ?>>Pas du tout!</option>
# fr      # it      # base 
# 10(0a)  # 255(ff) # 250(fa)   a la folie
# 30(1e)  # 125(7d) # 125(7d)   beaucoup
# 60(3c)  # --      # ---   souvent ###########
# 120(78) # 50(32)  # 50(32)    un peu
# 0       # 0       # 0     pas du tout
def taichi(infoTaichi):
    nextTaichi=0
    if infoTaichi!='00':
        if infoTaichi=="ff" or infoTaichi=="fa" or infoTaichi=="0a":
          nextTaichi = random.randint(15,45) #a la folie
        if infoTaichi=="7d" or infoTaichi=="1e":
          nextTaichi = random.randint(20,61) #beaucoup
        if infoTaichi=="3c":
          nextTaichi = random.randint(40,122) #souvent
        if infoTaichi=="32" or infoTaichi=="78":
          nextTaichi = random.randint(64,196) #un peu
    #    if infoTaichi==216:
    #      nextTaichi = random.randint(108,330)
    #    if infoTaichi==255:
    #      nextTaichi = random.randint(127,390)
    nextTaichi=nextTaichi*60 #second
    ##else: #-v4
        ##nextTaichi=0 #-v4
    ##print "next taichi after ....",nextTaichi," seconds..."
    return nextTaichi    
############################
# FUNCTION sleep/wakeup
############################
def go(w):
    global newPosLeft
    global newPosRight
    if w==0:  
      # sleep
      newPosLeft=7 #13
      motorLeft('start',0)                 
      newPosRight=7 #13
      motorRight('start',0)                     
    if w==1:
      # wakeup
      newPosLeft=16 #3
      motorLeft('start',0)                 
      newPosRight=16 #3
      motorRight('start',0)                     
    
############################
# FUNCTION move ears 04 e 05 type in packet not used for now
############################
def moveEars( dx, sx ):
    rst='1'
    if (dx=='00') and (sx=='00'):
        rst='0' #do reset
    subprocess.call([script,"ears",str(int(sx,16)),str(int(dx,16)),rst])    
############################
# FUNCTION decode msg packet
############################
def decodeString( orig ):
    currentChar = 35
    x=''
    for i in range(1,len(orig)-2,2):
      code = int(orig[i+1:i+3],16)
      currentChar = ((code -47)*(1+2*currentChar))%256
      x=x+chr(currentChar)
    return x
############################
# FUNCTION socket send data
############################
def sendmsg(s,m):
    global later    
    global errorSOCK
    try :
      s.sendall(m)
    except socket.error, e:
        debugLog( 'SENDMSG: sendmsg' )               
        #sys.exit()
        errorSOCK=1
    time.sleep( later )
    return
############################
# FUNCTION socket send and receive data
############################
def sendANDreceive( s, m ):
    d=''
    global later
    global errorSOCK
    try :
      s.sendall(m)
    except socket.error, e:
      debugLog( 'SENDANDRECEIVE: sendall' )
      #sys.exit()
      errorSOCK=1
    time.sleep( later )
    try:
      d = s.recv(1024)      
    except socket.timeout:
      print("timeout error")
    except socket.error:
 ##print("socket error occured: ")     
    ##except socket.error, e:
      debugLog( 'SENDANDRECEIVE: recv' )               
      #sys.exit() 
      errorSOCK=1      
#    d = recv_timeout(s)
    debugLog( 'send: ' + m )
    debugLog( 'receive: ' + d )
    return d
########################
# MAIN 
########################
#h = 'ojn.raspberry.pi'
#h = 'openjabnab.nappey.org'

h = 'openznab.it' 
##h = 'openjabnab.fr'   ################# CHANGE HERE
typePing=0 ## 
httpPort= ':80' #':20081' #':80' ## :80 or empty for default
port = 5222 # 5222 default
#mac      = "" ################ CHANGE HERE
##mac = open('/sys/class/net/wlan0/address').readline().replace('\n', '').replace(':','') #automac (pixel :) )
mac='000e8e2d053f'

password = "123456789012"  ################ CHANGE HERE if you want. (12 numbers)
##password = ''.join(random.choice(string.digits) for _ in range(12))
passwordX=''.join(hex( int(a,16) ^ int(b,16) )[2:] for a,b in zip(mac, password))

rgb=['000000','0000ff','00ff00','00ffff','ff0000','ff00ff','ffff00','ffffff']
##      000    001    010    011    100    101    110    111
#       none   blue   green  cyan   red    violet yellow white

if  os.path.exists(pathLocate):
  subprocess.call(["/bin/rm", pathLocate])
if  os.path.exists(logFile):
  subprocess.call(["/bin/rm", logFile])
  
# get file locate... 
ping=h  
locate='http://'+h+httpPort+'/vl/locate.jsp?sn='+mac+'&h=4&v='+bootVer#####+'18673'
subprocess.call( "/usr/bin/curl -0 -A MTL '"+locate+"' >"+pathLocate, shell=True )

f=open(pathLocate, "r")
try:
  for line in f:
    mm=re.search('ping.*:(.*)',line)
    if mm:
      httpPort=':'+mm.group(1)
      mm=re.search('ping (.*):.*',line)
      ping=mm.group(1)
    zz=re.search('xmpp_domain.*:(.*)',line)
    if zz:
      port=int(zz.group(1),10)
      zz=re.search('xmpp_domain (.*):.*',line)
      h=zz.group(1)      
    #  break
finally:
    f.close()
    
debugLog( ' locate file ' + locate )
debugLog( ' ping server ' + ping )
debugLog( ' http port ping server ' + httpPort )
debugLog( ' server xmpp ' + h )
debugLog( ' port xmpp ' + str(port) )

debugLog( ' start breath Thread' )
breath.start()     
debugLog( ' start rfid Thread' )
tRfid.start() 
debugLog( ' start taichi motor Thread' )
tTaichi.start() 
debugLog( ' start taichi led Thread' )
tlTaichi.start() 

######
#
# Hey Ho, Lets Go!
#
######
while loopTry>0:
    ##  
    if  os.path.exists(pathAudio):
      subprocess.call(["/bin/rm", pathAudio])
      subprocess.call(["/bin/rm", pathAudioFile])
    if  os.path.exists(pathRfid):
      subprocess.call(["/bin/rm", pathRfid])
    sleep=0
    infoTaichi='00'
    loopTry=loopTry-1
    errorSOCK=0
    
##    createSock
    try:
        ip = socket.gethostbyname( h )
    except socket.error, e:
        debugLog( 'CREATESOCK: ' ) ##+ e.strerror )
        errorSOCK=1
        ##sys.exit()
    ##
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip , port))
        s.setblocking(1)
        s.settimeout(2.0) # 20
    except socket.error, e:
        debugLog( 'CREATESOCK: ' ) ##+ e.strerror )
        errorSOCK=1
        ##sys.exit()
    print 'Yeee! Socket Connected to ' + h + ' on ip ' + ip
    
    m = "<?xml version='1.0' encoding='UTF-8'?><stream:stream to='"+h+"' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>"
    d = sendANDreceive(s,m)
    ### 1 # test if already register (file user.txt with mac address)
    already=''
    if os.path.exists(pathUser):
        already = open(pathUser).read().replace('\n','') 
    if already!=mac:
        m = "<iq type='get' id='1'><query xmlns='violet:iq:register'/></iq>"
        d = sendANDreceive(s,m)
        m="<iq to='"+h+"' type='set' id='2'><query xmlns=\"violet:iq:register\"><username>"+mac+"</username><password>"+passwordX+"</password></query></iq>"
        d = sendANDreceive(s,m)

    m = "<auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl' mechanism='DIGEST-MD5'/>"
    d = sendANDreceive(s,m)
    ### 2
    a= repr(d)
    mm = re.search('>(.+)</challenge>', a)
    if mm:
      #b=mm.group(0)
      c=mm.group(1)
      d=base64.b64decode(c)
      mm = re.search('nonce=\"(.+)\",qop', d)
      #b=mm.group(0)
      c=mm.group(1)
    else:
      debugLog('INIT: Error fase 2 nonce not found :(')
      errorSOCK=1
      ##sys.exit()   
      
    debugLog( 'AUTH base64decode: ' + d )      
    nc="00000001"
    nonce = c
    #         1234567890123
    #cnonce = '4840560059474'+chr(0)
    cnonce = ''.join(random.choice(string.digits) for _ in range(13))
    cnonce = cnonce + chr(0)
    digest_uri="xmpp/"+h

    # crypt crypt
    c1=md5.new()
    c1.update(mac + "::" + password)
    c2=md5.new()
    c2.update(c1.digest() + ":" + nonce + ":" + cnonce)
    HA1 = c2.hexdigest()
    c3=md5.new()

    mode="AUTHENTICATE"
    c3.update(mode + ":" + digest_uri)
    HA2=c3.hexdigest()
    c4=md5.new()
    c4.update(HA1 + ":" + nonce + ":" + nc + ":" + cnonce + ":auth:" + HA2)
    response=c4.hexdigest()
    other = ',nc='+nc+',qop=auth,digest-uri="'+digest_uri+'",response='+response+',charset=utf-8'
    stringa = 'username="'+mac+'",nonce="'+nonce+'",cnonce="'+cnonce+'"'+other
    a=base64.b64encode(stringa)

    debugLog( 'AUTH pre-base64encode: usename=' + mac )    
    debugLog( 'AUTH pre-base64encode: nonce=' + nonce )    
    debugLog( 'AUTH pre-base64encode: cnonce=' + cnonce[:-1] )    
    debugLog( 'AUTH pre-base64encode: nc=' + nc )    
    debugLog( 'AUTH pre-base64encode: digest_uri=' + digest_uri )    
    debugLog( 'AUTH pre-base64encode: response=' + response )    
    debugLog( 'AUTH pre-base64encode: charset=utf-8' )    
    
    m = '<response xmlns="urn:ietf:params:xml:ns:xmpp-sasl">'+a+'</response>'
    d = sendANDreceive(s,m)
    #riceive ok register <challenge xmlns='urn:ietf:params:xml:ns:xmpp-sasl'>cnNwYXV0aD1iNTk4NDM1NjY2OWJhM2JkNWZhMTU1Nzg4YjgyNDJjZg==</challenge>
    mm = re.search('<challenge[^>]*>([^<]*)</challenge>', d)
    if mm:
       text_file = open(pathUser, "w")
       text_file.write(mac)
       text_file.close()
       m="<response xmlns='urn:ietf:params:xml:ns:xmpp-sasl'/>"
       d = sendANDreceive(s,m)

    ### 3
    m = "<?xml version='1.0' encoding='UTF-8'?><stream:stream to='"+h+"' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>"
    d = sendANDreceive(s,m)
    ### 4
    m='<iq from="'+mac+'@'+h+'/" to="'+h+'" type=\'set\' id=\'1\'><bind xmlns=\'urn:ietf:params:xml:ns:xmpp-bind\'><resource>Boot</resource></bind></iq>'
    d = sendANDreceive(s,m)
    ### 5
    m='<iq from="'+mac+'@'+h+'/boot" to="'+h+'" type=\'set\' id=\'2\'><session xmlns=\'urn:ietf:params:xml:ns:xmpp-session\'/></iq>'
    d = sendANDreceive(s,m)
    ### 6
    m='<iq from=\''+mac+'@'+h+'/boot\' to=\'net.violet.platform@'+h+'/sources\' type=\'get\' id=\'3\'><query xmlns="violet:iq:sources"><packet xmlns="violet:packet" format="1.0"/></query></iq>'
    d = sendANDreceive(s,m)
    bootPacket=re.search('<iq[^>]*><query[^>]*><packet[^>]*>([^<]*)</packet></query></iq>',d) #v4
    ### 7  v4.1
    m='<iq from=\''+mac+'@'+h+'/boot\' to="'+h+'" type=\'set\' id=\'4\'><bind xmlns=\'urn:ietf:params:xml:ns:xmpp-bind\'><resource>idle</resource></bind></iq>'
    d = sendANDreceive(s,m)
    ### 8
    m='<iq from=\''+mac+'@'+h+'/idle\' to=\''+h+'\' type=\'set\' id=\'5\'><session xmlns=\'urn:ietf:params:xml:ns:xmpp-session\'/></iq>'
    d = sendANDreceive(s,m)
    ### 9
    m='<presence from=\''+mac+'@'+h+'/idle\' id=\'6\'></presence>'
    d = sendANDreceive(s,m)
    ### 10
    m='<iq from=\''+mac+'@'+h+'/boot\' to=\''+h+'\' type=\'set\' id=\'7\'><unbind xmlns=\'urn:ietf:params:xml:ns:xmpp-bind\'><resource>boot</resource></unbind></iq>'
    d = sendANDreceive(s,m)
    ### 11
    msgExtra=re.findall('<message[^>]*><packet[^>]*>(?:[^<]*)</packet></message>',d)
    ####
    # 
    # End authentication..
    #
    # boot packet v4 #
    times=int(time.time()) # default  no boot packet
    nextTaichi = taichi(infoTaichi) # default  no boot packet
    if bootPacket:
       c=bootPacket.group(1)
       debugLog( 'boot packet: ' + c )       
       a=base64.b64decode(c)
       b=''
       c=b.join(x.encode('hex') for x in a)
       debugLog( 'boot packet: ' + c )       
       #ears
       dx = c[20:22] #ear 04 e 05
       sx = c[24:26]       
       rst='1'
       if (dx=='00') and (sx=='00'):
           rst='0' #do reset
       ##subprocess.call([script,"ears",str(int(sx,16)),str(int(dx,16)),rst])
       ##moveEars(dx, sx)
       nose = c[28:30] #nose 08
       ###color = rgb[ int(c[32:34],16) ]   #breath 09    
       color = int(c[32:34],16)  
       ##subprocess.call([script,"leds",color])
       defaultLedColor = color
       infoTaichi = c[36:38] ## taichi 0e or 23
       times=int(time.time())          #fix v3.6
       nextTaichi = taichi(infoTaichi) #fix v3.6
       if c[38:50]=='0b00000100ff':
            debugLog( 'boot ears: ' + dx + sx + ' nose: ' + nose + ' color breath: ' + c[32:34] + ' taichi: ' + infoTaichi + ' wakeup!')                   
            sleep=0
            subprocess.call([script,"wakeup"])
            go(1) # wakeup
       restoreLed( defaultLedColor )            
       if c[38:50]=='0b00000101ff':
            sleep=1
            debugLog( 'boot ears: ' + dx + sx + ' nose: ' + nose + ' breath: ' + c[32:34] + ' taichi: ' + infoTaichi + ' sleep!')                   
            subprocess.call([script, "sleep"])
            go(0) #sleep
    debugLog( 'Authentication complete....' )                   
    print 'Now wait.... (press ^C to exit)...'
     
    #msgExtra=re.findall('<message[^>]*><packet[^>]*>(?:[^<]*)</packet></message>',d)
    l1=len(msgExtra)
    l2=0
    debugLog( 'found ' +str(l1) + ' message extra..' )                   

    ##ntestPing()
    idPing=0
    countSec=0
    while 1:
        if infoTaichi!='00':
          now=int(time.time())
          if now>(times+nextTaichi) and sleep==0:
              debugLog( 'start taichi..' )
              choiceMidi = random.randint(0,len(midiList)-1)
              tt = 'echo "'+pathBase+'mid/_'+midiList[ choiceMidi ]+'.mp3" >/tmp/tlist.txt'
              ##tt = 'echo "/usr/openkarotz/Extra/mid/_'+midiList[ choiceMidi ]+'.mp3" >/tmp/tlist.txt'
              stringTmp = ''
              stringTmp = tt + '\n'
              tt = '/bin/killall mplayer >> /dev/null 2>> /dev/null' #x
              stringTmp = stringTmp + tt +'\n'              
              tt = '/usr/bin/mplayer -quiet -playlist /tmp/tlist.txt' #x
              stringTmp = stringTmp + tt +'\n'                            
              #tt = '/usr/openkarotz/Extra/mid/_'+midiList[ choiceMidi ]+".mp3"              
              #subprocess.call( 'echo "'+tt+'" >/tmp/tlist.txt', shell=True )
              #subprocess.call( '/bin/killall mplayer >> /dev/null 2>> /dev/null', shell=True )              
              #subprocess.call( '/usr/bin/mplayer -quiet -playlist /tmp/tlist.txt', shell=True )
              #
              # attiva il threadtaichi con il parametro
              #
              z = random.randint(0,31)
              name=pathBase+'chor/tmp'+str(z)+'.sh'
              #subprocess.call( name, shell=True )
              #subprocess.call( '/usr/bin/mplayer -quiet -playlist /tmp/tlist.txt', shell=True )
              stringTmp = stringTmp + name +'\n'
              tt = '/usr/bin/mplayer -quiet -playlist /tmp/tlist.txt' #x              
              stringTmp = stringTmp + tt +'\n'
            
              #tt = script +' leds ' + defaultLedColor
              #stringTmp = stringTmp + tt +'\n'
              
              subprocess.call( 'echo "'+stringTmp+'" >'+pathBase+'taichi.sh', shell=True ) #x              
              subprocess.call( '/bin/chmod +x '+pathBase+'taichi.sh', shell=True ) #x     
              # run the file
              name=pathBase+'taichi.sh &'
              subprocess.call( name, shell=True )
              #
              times=times+nextTaichi
              nextTaichi = taichi(infoTaichi)              
              #restoreLed( defaultLedColor )
              debugLog( 'end taichi.. I used: ' + midiList[ choiceMidi ] + ', tmp' + str(z) + ' next taichi after ' +str(nextTaichi))              
    ########################################           
        da=''
        if l1>0:
            da=msgExtra[l2]
            l2=l2+1
            l1=l1-1
        else:
##            try:
            if countSec>20: #10*timeout = 20sec
                cTaichi.setTaichi(1) #test           
                lTaichi.setTaichi(1) #test
                print "TEST TAICHI"
                countSec=0

                idPing=idPing+1
                if idPing>1000:
                   idPing=1
                m='<presence from=\''+mac+'@'+h+'/idle\' id=\''+str(idPing)+'\'></presence>'
                if typePing==1:
                  m="<iq from='"+mac+'@'+h+"/' to='"+h+"' id='"+str(idPing)+"' type='get'><ping xmlns='urn:xmpp:ping'/></iq>"
                print "o" ###,m,status
                d = sendANDreceive(s,m)
                if errorSOCK==1:
                  debugLog( 'ERROR: exit loop while, try reconnect.. try n.ro '+str(loopTry)) ## +e.strerror )                
                  break
                mm=re.search('<message[^>]*><packet[^>]*>([^<]*)</packet></message>',d)
                if mm: #found message in ping packet
                  da = d
                else:
                  da = '' #s.recv(1024)
            else:
                countSec=countSec+1
                pollButton()
                try: 
                  da = s.recv(1024)
                  #timeout 2 sec                                    
##            except socket.timeout, e: #v4            
                  #print "t"
                  #debugLog( 'loop while 1 timeout') ## +e.strerror )
                except socket.error, e: #v4            
                  print "."
                #  debugLog( 'ERROR: loop while sock, try reconnect.. try n.ro '+str(loopTry)) ## +e.strerror )   
                #  break
        ##debugLog( 'rcv data=> ' + da )        
        if len(da)>0:
          debugLog( 'rcv data=> ' + da )                
          a= repr(da)                
          mm=re.search('<message[^>]*><packet[^>]*>([^<]*)</packet></message>',a)
          if mm:
            c=mm.group(1)
            a=base64.b64decode(c)
            b=''
            c=b.join(x.encode('hex') for x in a)            
          debugLog( 'received packet: ' + c )

    ######################## sleep
          if c[0:14]=='7f0b00000101ff':
            sleep=1
            subprocess.call([script, "sleep"])
            go(0) #sleep
            m='<iq from=\''+mac+'@'+h+'/idle\' to=\''+h+'\' type=\'set\' id=\'16\'><bind xmlns=\'urn:ietf:params:xml:ns:xmpp-bind\'><resource>asleep</resource></bind></iq>'
            d = sendANDreceive(s,m)
            #
            msgExtra=re.findall('<message[^>]*><packet[^>]*>(?:[^<]*)</packet></message>',d)
            l1=len(msgExtra)
            l2=0            
            #                        
            m='<iq from=\''+mac+'@'+h+'/asleep\' to=\''+h+'\' type=\'set\' id=\'17\'><session xmlns=\'urn:ietf:params:xml:ns:xmpp-session\'/></iq>'
            d = sendANDreceive(s,m)
            m='<presence from=\''+mac+'@'+h+'/asleep\' id=\'18\'></presence>'
            d = sendANDreceive(s,m)
            m='<iq from=\''+mac+'@'+h+'/idle\' to=\''+h+'\' type=\'set\' id=\'19\'><unbind xmlns=\'urn:ietf:params:xml:ns:xmpp-bind\'><resource>idle</resource></unbind></iq>'
            d = sendANDreceive(s,m)
            debugLog( 'going to sleep... ' )
            debugLog( 'found ' +str(l1) + ' message extra in sleep..' )                   
    ######################## wakeup
          if c[0:14]=='7f0b00000100ff':
            times=int(time.time())          #fix v3.6
            nextTaichi = taichi(infoTaichi) #fix v3.6
            sleep=0
            subprocess.call([script,"wakeup"])
            go(1) #wakeup
            m='<iq from=\''+mac+'@'+h+'/asleep\' to=\''+h+'\' type=\'set\' id=\'20\'><bind xmlns=\'urn:ietf:params:xml:ns:xmpp-bind\'><resource>idle</resource></bind></iq>'
            d = sendANDreceive(s,m)
            #
            msgExtra=re.findall('<message[^>]*><packet[^>]*>(?:[^<]*)</packet></message>',d)
            l1=len(msgExtra)
            l2=0            
            #
            m='<iq from=\''+mac+'@'+h+'/asleep\' to=\''+h+'\' type=\'set\' id=\'21\'><session xmlns=\'urn:ietf:params:xml:ns:xmpp-session\'/></iq>'
            d = sendANDreceive(s,m)
            m='<presence from=\''+mac+'@'+h+'/idle\' id=\'22\'></presence>'
            d = sendANDreceive(s,m)
            m='<iq from=\''+mac+'@'+h+'/asleep\' to=\''+h+'\' type=\'set\' id=\'19\'><unbind xmlns=\'urn:ietf:params:xml:ns:xmpp-bind\'><resource>asleep</resource></unbind></iq>'
            d = sendANDreceive(s,m)
            debugLog( 'I am wake up... ' )
            debugLog( 'found ' +str(l1) + ' message extra in wake up..' )                               
            restoreLed( defaultLedColor )
          if c[0:12]=='7f09000000ff':
            # reboot
            subprocess.call([script,"reboot"])
    ########################
    #
    # KAROTZ dedicated :)
    #
    ######################## 
          ###if sleep==0:
          if c[0:12]=='7fcc000001ff':
            # karotz 000001
            subprocess.call([script,"k000001"])
          if c[0:12]=='7fcc000002ff':
            # karotz 000002
            subprocess.call([script,"k000002"])
          if c[0:12]=='7fcc000003ff':
            # karotz 000003
            subprocess.call([script,"k000003"])
    ########################
    #
    #
    ######################## 
          if c[0:4]=='7f04':
            dx=False
            sx=False        
            #c#print 'msg type 04 Ambient block'
            l = int(c[8:10],16)  
            #c#print ' len: ', l
            l = l*2 + 18 - 8
            # len not used...
            #c#print 'dati:', c[18:l]
            type = c[18:20]
    #### move ears        
            if type=='04': #ear dx must 04xx05xx
              #c#print 'type ears', type
              dx = c[20:22]
              sx = c[24:26]
              rst='1'
              if (dx=='00') and (sx=='00'):
                 rst='0' #do reset
              subprocess.call([script,"ears",str(int(sx,16)),str(int(dx,16)),rst])
              debugLog( 'packet type 04 ears move: ' + dx + '  ' + sx)
            ## 
              sxi = int(c[24:26],16)
              dxi = int(c[20:22],16)
              if fakeLeft<sxi:
                newPosLeft=sxi
                motorLeft('start',0)                 
              if fakeRight<dxi:
                newPosRight=dxi
                motorRight('start',0)                 
            ##  
    ### others (to do)
            if type=='00': #disable
              debugLog( 'packet disable ' + type + '  ' + c[20:22])
            if type=='01': #meteo
              debugLog( 'packet meteo ' + type + '  ' + c[20:22])
            if type=='02': #borse
              debugLog( 'packet borse ' + type + '  ' + c[20:22])
            if type=='03': #traffic
              debugLog( 'packet traffic ' + type + '  ' + c[20:22])
            if type=='06': #mail
              debugLog( 'packet mail ' + type + '  ' + c[20:22])
            if type=='07': #air
              debugLog( 'packet air ' + type + '  ' + c[20:22])
            if type=='08': #blinknose
              debugLog( 'packet blinknose ' + type + '  ' + c[20:22])
    ### color breath    
            if type=='09': #ledbreath           
              color = int(c[20:22],16)
              defaultLedColor = color
              restoreLed( defaultLedColor )              
              debugLog( 'packet ledbreath ' + type + '  ' + c[20:22] )
    #openjabnab.fr !!!!
            if type=='21': #ledbreath
              color = int(c[20:22],16)
              defaultLedColor = color
              restoreLed( defaultLedColor )
              debugLog( 'OPENJABNAB.FR packet ledbreath ' + type + '  ' + c[20:22] ) 
            if type=='22': #set volume
              debugLog( 'OPENJABNAB.FR packet volume ' + type + '  ' + c[20:22] )                            
            if type=='23': #set taichi
              infoTaichi = c[20:22]
              debugLog( 'OPENJABNAB.FR packet taichi ' + type + '  ' + c[20:22] )                            
     
    ### others..
            if type=='0e': #taichi
              debugLog( 'packet taichi ' + type + '  ' + c[20:22] )                            
              infoTaichi = c[20:22]
    ### block crypt message....
          if c[0:4]=='7f0a':
            ##print 'msg type 0a message block'
            l = int(c[8:10],16)
            hb = int(c[6:8],16)
            ##print ' len ', l, hb
            l = l*2 + 10 - 2 + hb*256                        
            debugLog( 'packet messageblock 0a, len ' + str(l) )
            debugLog( 'packet messageblock:  ' + c )                                        
            # len not used...
            #l = len(c) -10
            ##print ' dati ', c[10:l]
            #decode
            P=c[10:] #l
            sound = decodeString( P )
            debugLog( 'packet messageblock: ' + sound )                            
            listn=re.split('[\n]+',sound) #create list by newline
            newlistn=[]     
            for elink in listn:
                repStr = 'http://'+h
                el=re.sub('broadcast',repStr,elink) #
                mw = re.search('^MW([^.]*)', el) # excludes MW
                si = re.search('^SI([^.]*)', el) # excludes SI
                se = re.search('^SE([^.]*)', el) # excludes SE
                pl = re.search('^PL([^.]*)', el) # excludes PL
    #add type for openjabnab.fr !!!
                rb = re.search('^RB([^.]*)', el) # excludes RB (reset bunny??)
                gv = re.search('^GV([^.]*)', el) # volume ?!
                if not mw and not si and not se and not pl and not rb and not gv:
                  newlistn.append(el)     
            tt=''
            #commandLen=len(newlistn)
            for el in newlistn:
                sound=''  
                mm = re.search('MU (.+)', el) #mp3
                if mm:
                  sound=mm.group(1)             
                mm = re.search('^ST (.+)', el)  #stream
                if mm:
                  sound=mm.group(1)
                tt=tt+sound+'\n'
            #if sleep==0:
            subprocess.call( 'echo "'+tt+'" >/tmp/list.txt', shell=True )
            subprocess.call( '/bin/killall mplayer >> /dev/null 2>> /dev/null', shell=True )
            subprocess.call( '/usr/bin/mplayer -quiet -playlist /tmp/list.txt &', shell=True )
            #else:
            #  debugLog( 'I would rather sleep than talk!' )                                      
    # endwhile 1       
    #Close the socket
    s.close()
# end :-(



