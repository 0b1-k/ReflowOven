#!/usr/bin/python
import platform as plat

class PlatformID(object):
    def __init__(self):
        if (plat.system() == 'Linux'):
            self.__IsLinux = True
        else:
            self.__IsLinux = False
        
        if (plat.machine()[:3] == 'arm'):
            self.__IsARM = True
        else:
            self.__IsARM = False
    
    def IsLinux(self):
        return self.__IsLinux
    
    def IsARM(self):
        return self.__IsARM
    
    
if __name__ == '__main__':
    plat = PlatformID()
    
    if (plat.IsLinux()):
        print("Linux")
    else:
        print("!Linux")
        
    if (plat.IsARM()):
        print("ARM")
    else:
        print("!ARM")