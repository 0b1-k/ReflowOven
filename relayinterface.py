#!/usr/bin/python
from id import *

_plat = PlatformID()
if (_plat.IsLinux() and _plat.IsARM()):
    from mcp23008 import MCP23008, MCP23008PinState
    from i2c import I2CDevice
    import RPi.GPIO as GPIO


class RelayInterface(object):
    ON = 1
    OFF = 0
    def __init__(self, kwargs):
        self._plat = PlatformID()
        self._kwargs = kwargs
        self._pin = int(kwargs['pin'])
        
    def SwitchRelay(self, state):
        raise Exception('Not implemented')
    
    def Cleanup(self):
        raise Exception('Not implemented')


class RPI(RelayInterface):        
    def __init__(self, kwargs):
        super(RPI, self).__init__(kwargs)
        if (self._plat.IsLinux() and self._plat.IsARM()):
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self._kwargs['pin'], GPIO.OUT)

    def SwitchRelay(self, state):
        if (self._plat.IsLinux() and self._plat.IsARM()):
            GPIO.output(self._pin, state)
    
    def Cleanup(self):
        if (self._plat.IsLinux() and self._plat.IsARM()):
            GPIO.GPIO.cleanup()


class MCP23008IO(RelayInterface):
    def __init__(self, kwargs):
        self.__IO = None
        super(MCP23008IO, self).__init__(kwargs)
        if (self._plat.IsLinux() and self._plat.IsARM()):
            _i2c = I2CDevice(int(kwargs['i2cbus']), int(kwargs['i2caddr']))
            self.__IO = MCP23008(_i2c)
            self.__IO.PinMode(self._pin)
            self.__IO.SetOutputState(self._pin, MCP23008PinState.Low)
            
    def SwitchRelay(self, state):
        if (self._plat.IsLinux() and self._plat.IsARM()):
            if (state == RelayInterface.ON):
                self.__IO.SetOutputState(self._pin, MCP23008PinState.High)
            else:
                self.__IO.SetOutputState(self._pin, MCP23008PinState.Low)

    def Cleanup(self):
        if (self._plat.IsLinux() and self._plat.IsARM()):
            self.__IO.SetOutputState(self._pin, MCP23008PinState.Low)
    
    
class RelayInterfaceFactory(object):
    def __init__(self):
        pass

    def GetInstance(self, Type, kwargs):
        types = self.ListTypes()
        if types.__contains__(Type):
            module = __import__(__name__)
            _class = getattr(module, Type)
            return _class(kwargs)
        else:
            raise Exception("Unsupported relay interface")

    def ListTypes(self):
        types = list()
        for _class in RelayInterface.__subclasses__():
            classInfo = str(_class).split('.')
            strippedClass = classInfo[1].strip('\'>')
            types.append(strippedClass)
        return types


if __name__ == '__main__':
    import time
    factory = RelayInterfaceFactory()
    kwargs = dict()
    kwargs['pin'] = 0
    kwargs['i2cbus'] = 1
    kwargs['i2caddr'] = 0x20
    _class = factory.GetInstance('MCP23008IO', kwargs)
    try:
        state = 0
        while True:
            state = state ^ 1
            _class.SwitchRelay(state)
            print("Relay: " + str(state))
            time.sleep(1)
    except KeyboardInterrupt:
        _class.SwitchRelay(RelayInterface.OFF)
    _class.Cleanup()
