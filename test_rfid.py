#! /usr/bin/python
#
# Test Nabaztag RFID with Raspberry
# 06.05.2016 carlo64
# 
import smbus
import time

bus=smbus.SMBus(1)

R_PARAM = 0x00 #Parameter Register
R_FRAME = 0x01 #Input/Output Frame Register
R_AUTH  = 0x02 #Authenticate Register
R_SLOT  = 0x03 #slot Marker Register
RFID    = 0x50 #address
cmdInitiate  = [0x02,0x06,0x00]
cmdSelectTag = [0x02,0x0E,0x00]
cmdGetTagUid = [0x01,0x0B]
cmdOn  = 0x10
cmdOff = 0x00
zero = []
laterRfid = 0.05

bus.write_quick(RFID)
bus.write_byte_data(RFID,R_PARAM,cmdOff) #off rfid! 
bus.write_byte_data(RFID,R_PARAM,cmdOn) #on rfid! 
time.sleep(laterRfid)

while 1:
    bus.write_i2c_block_data(RFID,R_FRAME,cmdInitiate)
    time.sleep(laterRfid)
    
    r = bus.read_i2c_block_data(RFID,R_FRAME)
    time.sleep(laterRfid)
    
    print "wait for rfid ...",r[0]
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
            time.sleep(laterRfid)
                        
            uid=bus.read_i2c_block_data(RFID,R_FRAME)  # read id

            print "getuid :", countTag, " len + udi (8 byte) ",uid
            print "your TAG is: ", ''.join(hex(a )[2:].zfill(2) for a in reversed(uid[1:9]))

            #d00218c1......   d0 02 18 c1 .. .. .. ..
            
            countTag+=1
          wordBitIdx>>=1
          
    #print "loop..."
    time.sleep(0.5)
