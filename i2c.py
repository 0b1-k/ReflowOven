#!/usr/bin/python
import smbus


class I2CDevice:
    def __init__(self, I2CBus, I2CDeviceAddress):
        self.__I2CAddress = I2CDeviceAddress
        self.__I2CBus = smbus.SMBus(I2CBus)

    def WriteByte(self, byte):
        self.__I2CBus.write_byte(self.__I2CAddress, byte)

    def ReadByte(self):
        return self.__I2CBus.read_byte(self.__I2CAddress)
    
    def WriteRegisterByte(self, register, byte):
        return self.__I2CBus.write_byte_data(self.__I2CAddress, register, byte)

    def ReadRegisterByte(self, register):
        return self.__I2CBus.read_byte_data(self.__I2CAddress, register)

    def WriteRegisterWord(self, register, word):
        return self.__I2CBus.write_word_data(self.__I2CAddress, register, word)

    def ReadRegisterWord(self, register):
        return self.__I2CBus.read_word_data(self.__I2CAddress, register)
    
    def WriteBytes(self, register, dataBytes):
        self.__I2CBus.write_i2c_block_data(self.__I2CAddress, register, dataBytes)
        
    def ReadBytes(self, register, byteCount):
        return self.__I2CBus.read_i2c_block_data(self.__I2CAddress, register, byteCount)
