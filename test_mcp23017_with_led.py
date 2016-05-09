#! /usr/bin/python
#
# Test Leds rgb with MCP23017 gpio extender (like a Nabaztag) with Raspberry
# 06.05.2016 carlo64
# 
import smbus
import time
import random

bus=smbus.SMBus(1) # check with: i2cdetect -y 1

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
"""
ledLeft1   = 0b00000001
ledLeft2   = 0b00000010
ledLeft3   = 0b00000100
ledMiddle1 = 0b00001000
ledMiddle2 = 0b00010000
ledMiddle3 = 0b00100000

ledRight1  = 0b00000001
ledRight2  = 0b00000010
ledRight3  = 0b00000100
ledTop1    = 0b00001000
ledTop2    = 0b00010000
ledTop3    = 0b00100000

ledAll1    = 0b00111111
ledAll2    = 0b00111111
"""
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

for i in range(1,7):   
    ledOn( i, 0, 0, 0, 0)   
    time.sleep(1)
    ledOn( 0, i, 0, 0, 0)   
    time.sleep(1)
    ledOn( 0, 0, i, 0, 0)   
    time.sleep(1)
    ledOn( 0, 0, 0, i, 0)   
    time.sleep(1)
    ledOn( 0, 0, 0, 0, i)   
    time.sleep(1)

a = random.randint(0,7)
b = random.randint(0,7)
c = random.randint(0,7)
d = random.randint(0,7)      
ledOn( a, b, c, d, 0)   
time.sleep(1)
a = random.randint(0,7)
b = random.randint(0,7)
c = random.randint(0,7)
d = random.randint(0,7)      
ledOn( a, b, c, d, 0)   
time.sleep(1)
a = random.randint(0,7)
b = random.randint(0,7)
c = random.randint(0,7)
d = random.randint(0,7)      
ledOn( a, b, c, d, 0)   
time.sleep(1)

i = random.randint(0,7)      
ledOn( 0, 0, 0, 0, i)   
time.sleep(1)
i = random.randint(0,7)      
ledOn( 0, 0, 0, 0, i)   
time.sleep(1)
i = random.randint(0,7)      
ledOn( 0, 0, 0, 0, i)   
time.sleep(1)

bus.write_byte_data(DEVICE,OLATA,0)
bus.write_byte_data(DEVICE,OLATB,0)

