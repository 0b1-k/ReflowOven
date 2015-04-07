#!/usr/bin/python
import os
import pickle
import argparse

class OneWire(object):
    def __init__(self, prefix = None, maxReadAttempts = 5):
        self.__devices = dict()
        self.__MaxReadAttempts = maxReadAttempts
        self.Prefix = prefix

    def EnumerateDevices(self):
        self.__devices.clear()
        for dirname, devices, filenames in os.walk('/sys/bus/w1/devices/'):
            for device in devices:
                if device.__contains__('-'):
                    self.__devices[device] = None
        return self.__devices


    def AssignAlias(self, deviceId, FriendlyName):
        if (self.__devices.__contains__(deviceId) == True):
            self.__devices[deviceId] = FriendlyName
        else:
            raise Exception("Unknown device name: " + deviceId)

    def SaveAliasConfig(self, filename):
        with open(filename, 'wb') as f:
            p = pickle.Pickler(f)
            p.dump(self.__devices)

    def LoadAliasConfig(self, filename):
        self.__devices.clear()
        try:
            with open(filename, 'rb') as f:
                up = pickle.Unpickler(f)
                self.__devices = up.load()
        except IOError:
            pass

    def GetDeviceAlias(self, devId):
        if (self.__devices.__contains__(devId) == True):
            return self.__devices[devId]
        else:
            return None

    def ResolveAlias(self, alias):
        for devId in self.__devices:
            if (self.__devices[devId] == alias):
                return devId
        return None

    def GetAliases(self):
        aliases = list()
        for devId in self.__devices:
            aliases.append(self.__devices[devId])
        return aliases

    def ValidateAliases(self):
        if (len(self.__devices) == 0):
            return False
        for devId in self.__devices:
            if self.__devices[devId] is None:
                return False
        return True

    def ReadRawData(self, deviceId):
        if (self.ContainsPrefix(deviceId) == False):
            raise Exception("Prefix " + self.GetPrefix() + " not found in device ID " + deviceId)
        with open("/sys/bus/w1/devices/" + deviceId + "/w1_slave") as dev:
            readAttempts = self.__MaxReadAttempts
            while readAttempts != 0:
                devData = dev.read()
                records = devData.split("\n")
                if records[0].find("YES") > 0:
                    hexData = records[1][:23].split(" ")
                    index = 0
                    for b in hexData:
                        hexData[index] = int(b, 16)
                        index += 1
                    return hexData
                else:
                    readAttempts -= 1
            raise Exception("Bad CRC reading " + deviceId)

    def ContainsPrefix(self, deviceId):
        if deviceId.__contains__(self.Prefix):
            return True
        return False
    
    def GetPrefix(self):
        return self.Prefix
    
    def RawDataToCelsius(self, raw):
        return float(raw/16.0)
    
    def RawDataToFahrenheit(self, raw):
        return (self.RawDataToCelsius(raw) * 1.8 + 32.0)

class DS18B20(OneWire):
    def __init__(self, kwargs):
        super(DS18B20, self).__init__(prefix = "28-")

    def GetDegreesCelsius(self, deviceId):
        data = self.ReadRawData(deviceId)
        # 12-bit temp resolution by default
        rawTemp = (data[1] << 8) | (data[0] & 0xF0)
        return self.RawDataToCelsius(rawTemp)


class MAX31850K(OneWire):
    def __init__(self, kwargs):
        super(MAX31850K, self).__init__(prefix = "3b-")

    def GetDegreesCelsius(self, deviceId):
        data= self.ReadRawData(deviceId)
        if (data[0] & 0x01):
            if (data[2] & 0x01):
                raise Exception("Thermocouple fault: open circuit!")
            elif (data[2] & 0x02):
                raise Exception("Thermocouple fault: short to GND!")
            elif (data[2] & 0x04):
                raise Exception("Thermocouple fault: short to VDD!")
        # 14-bit resolution by default
        rawTemp = (data[1] << 8) | (data[0] & 0xF8)
        return self.RawDataToCelsius(rawTemp)


class OneWireFactory(object):
    def __init__(self, AliasConfigFilename):
        self.__aliasConfigFilename = AliasConfigFilename
        self.__deviceClasses = self.__CreateDeviceClasses()
        
    def __CreateDeviceClasses(self):
        classes = dict()
        types = self.ListTypes()
        for _type in types:
            _class = self.GetInstance(_type, None)
            classes[_class.GetPrefix()] = _class
        return classes

    def __Identify(self, deviceList, aliasList, degreeCelsiusDiff=3.0):
        temps = dict()
        for devId in deviceList:
            _class = self.__GetInstanceByDeviceId(devId)
            temps[devId] = _class.GetDegreesCelsius(devId)
        namedSensorCount = 0
        for alias in aliasList:
            print("Warm up or cool down the '" + alias + "' sensor (" + str(len(deviceList) - namedSensorCount) + " devices remaining)")
            detectedDeviceId = None
            while detectedDeviceId is None:
                for devId in deviceList:
                    if deviceList[devId] is None:
                        _class = self.__GetInstanceByDeviceId(devId)
                        if abs(_class.GetDegreesCelsius(devId) - temps[devId]) >= degreeCelsiusDiff:
                            detectedDeviceId = devId
                            break
            deviceList[detectedDeviceId] = alias
            namedSensorCount += 1

    def __GetInstanceByDeviceId(self, deviceId):
        for k in self.__deviceClasses:
            if (deviceId.__contains__(k)):
                return self.__deviceClasses[k]
        raise Exception("No device class matches " + deviceId)
    
    def Setup(self, aliasList):
        oneWire = OneWire()
        self.__Identify(oneWire.EnumerateDevices(), aliasList)
        oneWire.SaveAliasConfig(self.__aliasConfigFilename)

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
        for _class in OneWire.__subclasses__():
            classInfo = str(_class).split('.')
            strippedClass = classInfo[1].strip('\'>')
            types.append(strippedClass)
        return types
    
    def Query(self):
        sensorValues = dict()
        oneWire = OneWire()
        oneWire.LoadAliasConfig(self.__aliasConfigFilename)
        aliases = oneWire.GetAliases()
        for alias in aliases:
            while True:
                try:
                    devId = oneWire.ResolveAlias(alias)
                    _class = self.__GetInstanceByDeviceId(devId)
                    sensorValues[alias] = _class.GetDegreesCelsius(devId)
                    break
                except Exception:
                    pass
        return sensorValues


def GetSetup(args):
    try:
        return args['setup']
    except:
        return None

def GetQuery(args):
    try:
        return args['query']
    except:
        return None

def GetAliasList(args):
    try:
        return args['aliases']
    except:
        return None
    
def GetConfigFile(args):
    try:
        return args['cfgfile'][0]
    except:
        return None

def OnCommand(args):
    cfgFile = GetConfigFile(args)
    if(cfgFile is not None):
        owf = OneWireFactory(cfgFile)
        if (GetSetup(args) is not None):
            owf.Setup(GetAliasList(args))
        elif (GetQuery(args) is not None):
            d = owf.Query()
            for k in d:
                print("Device '" + k + "' = " + str(d[k]))
    else:
        raise("Missing parameters")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OneWire Bus Helper", usage='%(prog)s [options] [parameter]')
    parser.add_argument('--setup', nargs='*', help='Discover and save alias configuration of 1-Wire devices to a file')
    parser.add_argument('--query', nargs='*', help='Query 1-Wire devices by alias using configuration file')
    parser.add_argument('--cfgfile', nargs=1, type=str, help='Name of the config file')
    parser.add_argument('--aliases', nargs='*', type=str, help='One or more aliases to assign to 1-Wire devices')

    args = vars(parser.parse_args())
    if 'help' in args:
        parser.parse_args("--help")
        exit()
    else:
        OnCommand(args)

