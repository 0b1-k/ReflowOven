#!/usr/bin/python
from i2c import I2CDevice
from datetime import datetime
import time


I2CBus = 1
MCP23008_I2C_Base_Address = 0x20


class MCP23008Register(object):
    IODIR = 0x00
    IPOL = 0x01
    GPINTEN = 0x02
    DEFVAL = 0x03
    INTCON = 0x04
    IOCON = 0x05
    GPPU = 0x06
    INTF = 0x07
    INTCAP = 0x08
    GPIO = 0x09
    OLAT = 0x0A


class MCP23008IOConRegisterBits(object):
    INTPOL = 1
    ODR = 2
    DISSLW = 4
    SEQOP = 5


class MCP23008PinDirection(object):
    Output = 0
    Input = 1


class MCP23008Polarity(object):
    SameLogicState = 0
    OppositeLogicState = 1


class MCP23008PinState(object):
    Low = 0
    High = 1
    

class MCP23008Pullup(object):
    Disabled = 0
    Enabled = 1


class MCP23008SequentialOperation(object):
    Enabled = 0
    Disabled = 1

# MCP23008 I/O Expander driver
# Datasheet: http://ww1.microchip.com/downloads/en/DeviceDoc/21919e.pdf
# To do: implement interrupt handling
class MCP23008(object):
    def __init__(self, I2CDevice):
        self.__i2cDevice = I2CDevice
        self.__IODIR = 0xFF
        self.__GPPU = 0x00
        self.__OLAT = 0x00
        self.__GPPU = 0x00
        self.__IPOL = 0x00

    def PinMode(self, pin, direction = MCP23008PinDirection.Output):
        self.__IODIR = self.__SetBitState(self.__IODIR, pin, direction)
        self.__i2cDevice.WriteRegisterByte(MCP23008Register.IODIR, self.__IODIR)
        
    def SetOutputState(self, pin, state = MCP23008PinState.High):
        self._RaiseNotOutputException(pin)
        self.__OLAT = self.__SetBitState(self.__OLAT, pin, state)
        self.__i2cDevice.WriteRegisterByte(MCP23008Register.GPIO, self.__OLAT)
        
    def SetInputPullUp(self, pin, state = MCP23008Pullup.Enabled):
        self._RaiseNotInputException(pin)
        self.__GPPU = self.__SetBitState(self.__GPPU, pin, state)
        self.__i2cDevice.WriteRegisterByte(MCP23008Register.GPPU, self.__GPPU)
        
    def SetInputPolarity(self, pin, polarity = MCP23008Polarity.OppositeLogicState):
        self._RaiseNotInputException(pin)
        self.__IPOL = self.__SetBitState(self.__IPOL, pin, polarity)
        self.__i2cDevice.WriteRegisterByte(MCP23008Register.IPOL, self.__IPOL)

    def GetInputState(self, pin):
        self._RaiseNotInputException(pin)
        portState = self.__i2cDevice.ReadRegisterByte(MCP23008Register.GPIO)
        return portState & (1 << pin)
    
    def GetGPIOPortState(self):
        return self.__i2cDevice.ReadRegisterByte(MCP23008Register.GPIO)
    
    def SetSequentialOperationState(self, state = MCP23008SequentialOperation.Disabled):
        iocon = self.__i2cDevice.ReadRegisterByte(MCP23008Register.IOCON)
        iocon = self.__SetBitState(iocon, MCP23008IOConRegisterBits.SEQOP, state)
        self.__i2cDevice.WriteRegisterByte(MCP23008Register.IOCON, iocon)
    
    def SetStreamRegister(self, register = MCP23008Register.GPIO):
        self.SetSequentialOperationState()
        return self.__i2cDevice.ReadRegisterByte(register)
    
    def StreamRegisterData(self):
        return self.__i2cDevice.ReadByte()
    
    def __SetBitState(self, value, bit, state):
        if state is 0:
            return value & ~(1 << bit)
        else:
            return value | (1 << bit)
    
    def _RaiseNotInputException(self, pin):
        if (self.__IODIR & (1 << pin)) == 0:
            raise Exception("Pin " + str(pin) + " is not an input")

    def _RaiseNotOutputException(self, pin):
        if (self.__IODIR & (1 << pin)) != 0:
            raise Exception("Pin " + str(pin) + " is not an output")

def InputTest(mcp = None):    
    print("InputTest(): all pins as inputs with pullups enabled, waiting for a change on pin 0")
    for pin in range(0,8):
        mcp.PinMode(pin, MCP23008PinDirection.Input)
        mcp.SetInputPullUp(pin)
    currentState = mcp.GetInputState(0)
    print("Pin 0 state: " + str(currentState))
    while True:
        try:
            state = mcp.GetInputState(0)
            if state != currentState:
                print("Pin 0 new state: " + str(state))
                break
        except IOError:
            pass

def OutputTest(mcp = None):
    iterations = 0
    print("OutputTest(): use LEDs for best results")
    try:
        for pin in range(0,8):
            mcp.PinMode(pin)
        while True:
            iterations+=1
            for pin in range(0,8):     
                mcp.SetOutputState(pin, MCP23008PinState.High)
                time.sleep(.01)
                mcp.SetOutputState(pin, MCP23008PinState.Low)
                time.sleep(.01)
    except IOError as Oops:
        print(Oops.__str__())
        return iterations
            
if __name__ == '__main__':
    i2c = I2CDevice(I2CBus, MCP23008_I2C_Base_Address)
    mcp = MCP23008(i2c)
    while True:
        print("OutputTest iterations completed: " + str(OutputTest(mcp)))
