#! /usr/bin/python
#
# Test Led Rgb fade like a Nabaztag with Raspberry
# 06.05.2016 carlo64
# 
import time
import RPi.GPIO as GPIO

# LED pin mapping.
red = 11 
green = 13 
blue = 12 

def setColor(r,g,b):
  global red
  global green
  global blue
  GPIO.output(red, (r==1) )  
  GPIO.output(green, (g==1) )  
  GPIO.output(blue, (b==1) )    
#    
GPIO.setmode(GPIO.BOARD)

GPIO.setup(red, GPIO.OUT)
GPIO.setup(green, GPIO.OUT)
GPIO.setup(blue, GPIO.OUT)
print "red........"
setColor(1,0,0)
time.sleep(1)
print "green........."
setColor(0,1,0)
time.sleep(1)
print "blue......."
setColor(0,0,1)
time.sleep(1)
print "violet......."
setColor(1,0,1)
time.sleep(1)

## fade red... 
GPIO.output(red,False)
GPIO.output(green,False)
GPIO.output(blue,False)
# Use PWM to fade...
v = 99
i = True

redLed = GPIO.PWM(red, v)
redLed.start(0)

print "start fade....."
for c in range(0,1000):
    redLed.ChangeDutyCycle(v)
    if i:
        v += 1
    else:
        v -= 1
    if (v >= 100):
        i = False
    if (v <= 1):
        i = True
    time.sleep(0.01)

GPIO.cleanup()
