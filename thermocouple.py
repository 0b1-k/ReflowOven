#!/usr/bin/python

from onewire import OneWireFactory

class Thermocouple(object):
    def __init__(self, kwargs):
        self._kwargs = kwargs
  
    def ReadCelsius(self):
        raise Exception("Not implemented")
    

class Max31850(Thermocouple):
    def __init__(self, kwargs):
        super(Max31850, self).__init__(kwargs)
        self.__OneWireFactory = OneWireFactory('reflow.cfg')
    
    def ReadCelsius(self):
        temps = self.__OneWireFactory.Query()
        return temps['oven']


class ThermocoupleFactory(object):
    def __init__(self):
        pass

    def GetInstance(self, Type, kwargs):
        types = self.ListTypes()
        if types.__contains__(Type):
            module = __import__(__name__)
            _class = getattr(module, Type)
            return _class(kwargs)
        else:
            raise Exception("Unsupported thermocouple type")

    def ListTypes(self):
        types = list()
        for _class in Thermocouple.__subclasses__():
            classInfo = str(_class).split('.')
            strippedClass = classInfo[1].strip('\'>')
            types.append(strippedClass)
        return types


if __name__ == '__main__':
    factory = ThermocoupleFactory()
    _class = factory.GetInstance('Max31850', None)
    tempC = _class.ReadCelsius()
    print(str(tempC) + "C")
