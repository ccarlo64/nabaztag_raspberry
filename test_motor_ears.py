#! /usr/bin/python
#
# Test Nabaztag ears motors with Raspberry and L293D
# 06.05.2016 carlo64
#

import RPi.GPIO as GPIO
from time import sleep

GPIO.setmode(GPIO.BOARD)

motor1A = 36
motor1B = 38
motor1E = 40
motor2A = 33
motor2B = 35
motor2E = 37

GPIO.setup(motor1A,GPIO.OUT)
GPIO.setup(motor1B,GPIO.OUT)
GPIO.setup(motor1E,GPIO.OUT)
GPIO.setup(motor2A,GPIO.OUT)
GPIO.setup(motor2B,GPIO.OUT)
GPIO.setup(motor2E,GPIO.OUT)

print "clockwise rotation"
#m1
GPIO.output(motor1A,GPIO.HIGH)
GPIO.output(motor1B,GPIO.LOW)
GPIO.output(motor1E,GPIO.HIGH)
#m2
GPIO.output(motor2A,GPIO.HIGH)
GPIO.output(motor2B,GPIO.LOW)
GPIO.output(motor2E,GPIO.HIGH)
sleep(2) 
print "counterclockwise rotation"
#m1
GPIO.output(motor1A,GPIO.LOW)
GPIO.output(motor1B,GPIO.HIGH)
#m2
GPIO.output(motor2A,GPIO.LOW)
GPIO.output(motor2B,GPIO.HIGH)
sleep(2)

print "STOP!"
GPIO.output(motor1E,GPIO.LOW)
GPIO.output(motor2E,GPIO.LOW)

GPIO.cleanup()



