#!/usr/bin/python
#
# Hardware-agnostic Reflow Oven Controller
# Python adaptation by Fabien Royer <fabien@nwazet.com>
#
# Based on the original Arduino code by 'Rocket Scream Electronics'
# https://github.com/rocketscream/Reflow-Oven-Controller
#
import argparse
from reflowctl import ReflowStateMachine
from thermocouple import *
from relayinterface import *
from lcd import LCD

def GetProfile(args):
    return args['profile'][0]

def GetTherm(args):
    return args['therm'][0]

def GetThermList(args):
    return args['thermlist']

def GetInterfaceList(args):
    return args['interfacelist']

def GetInterface(args):
    return args['interface'][0]

def PrintList(_list, title):
    print(title)
    for _type in _list:
        print(_type)
    
def ArgsToDict(args):
    kwargs = dict()
    for k in args:
        try:
            kwargs[k] = args[k][0]
        except TypeError:
            pass
        except IndexError:
            pass
    return kwargs

def OnCommand(args):   
    if GetThermList(args) is not None:
        factory = ThermocoupleFactory()
        PrintList(factory.ListTypes(), "Supported thermocouple types")
    elif GetInterfaceList(args) is not None:
        factory = RelayInterfaceFactory()
        PrintList(factory.ListTypes(), "Supported interface types")
    else:
        kwargs = ArgsToDict(args)
        tcf = ThermocoupleFactory()       
        rif = RelayInterfaceFactory()
        _relay = rif.GetInstance(GetInterface(args), kwargs)
        _lcd = LCD()
        reflowCtl = ReflowStateMachine(
            reflowProfile = GetProfile(args),
            thermocouple = tcf.GetInstance(GetTherm(args), kwargs),
            relay = _relay,
            lcd = _lcd)
        try:
            reflowCtl.Reflow()
        except KeyboardInterrupt:
            _relay.SwitchRelay(RelayInterface.OFF)
        _lcd.Cleanup()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Reflow Oven Controller", usage='%(prog)s [options] [parameter]')
    parser.add_argument('--profile', nargs=1, type=str, choices={'leaded', 'leadfree'}, help='lead-based or lead-free reflow profile')
    parser.add_argument('--therm', nargs=1, type=str, help='thermocouple type to be used')
    parser.add_argument('--thermlist', nargs='*', help='list thermocouple types')
    parser.add_argument('--interface', nargs=1, type=str, help='interface to the relay driving the reflow oven')
    parser.add_argument('--interfacelist', nargs='*', help='list relay interfaces')
    parser.add_argument('--pin', nargs=1, type=int, help='Pin # connected to the relay interface')
    parser.add_argument('--i2cbus', nargs=1, type=int, help='Relay interface I2C bus #')
    parser.add_argument('--i2caddr', nargs=1, type=int, help='Relay interface I2C address (decimal)')

    args = vars(parser.parse_args())
    if 'help' in args:
        parser.parse_args("--help")
        exit()
    else:
        OnCommand(args)
