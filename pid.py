#!/usr/bin/python
#
# Arduino PID Library v1.1.0
# by Brett Beauregard <br3ttb@gmail.com> brettbeauregard.com
# https://github.com/br3ttb/Arduino-PID-Library/
#
# Python adaptation by Fabien Royer <fabien@nwazet.com>
# Original comments in the C code have been preserved,
# along with the spirit of the original C interface to ease porting of applications using the
# Arduino PID library to Python.
#
# Detailed explanation of PID process control: http://playground.arduino.cc/Code/PIDLibrary
# This Library is licensed under the GPLv3 License: http://www.gnu.org/licenses/gpl-3.0.html
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see http://www.gnu.org/licenses/
#
from datetime import datetime, timedelta

class PIDContext(object):
    Input = 0
    Output = 1
    SetPoint = 2
    def __init__(self, _input, _output, _setpoint):
        self.Params = [_input, _output, _setpoint]


class PID(object):
    AUTOMATIC = 1
    MANUAL = 0
    DIRECT = 0
    REVERSE = 1
    DefaultPidSamplingTimeMs = 100.0
    """ Constructor
    links the PID to the Input, Output, and Setpoint. Initial tuning parameters are also set here.
    The parameters specified here are those for for which we can't set up reliable defaults, so we need to have the user set them.
    """
    def __init__(self, pidContext, Kp, Ki, Kd, direction):
        self.__context = pidContext
        self.__InAuto = False
        self.SetOutputLimits()
        self.__SampleTimeMs = PID.DefaultPidSamplingTimeMs
        self.SetControllerDirection(direction)
        self.SetTunings(Kp, Ki, Kd)
        self.__LastTime = datetime.now() - timedelta(milliseconds = self.__SampleTimeMs)
        

    """ Status Funcions
    Just because you set the Kp=-1 doesn't mean it actually happened.
    These functions query the internal state of the PID.
    They're here for display purposes. These are the functions the PID front-end uses, for example.
    """
    def GetKp(self):
        return self.__DispKp
    

    def GetKi(self):
        return self.__DispKi
    

    def GetKd(self):
        return self.__DispKd
    

    def GetMode(self):
        if (self.__InAuto == True):
            return PID.AUTOMATIC
        else:
            return PID.MANUAL


    def GetDirection(self):
       return self.__ControllerDirection


    """ SetTunings()
    This function allows the controller's dynamic performance to be adjusted. 
    It's called automatically from the constructor, but tunings can also be adjusted on the fly during normal operation.
    """
    def SetTunings(self, Kp, Ki, Kd):
        if (Kp<0.0 or Ki<0.0 or Kd<0.0):
            raise Exception("Kp, Ki, Kd must be >= 0.0")
        
        self.__DispKp = Kp
        self.__DispKi = Ki
        self.__DispKd = Kd
   
        _SampleTimeInSec = self.__SampleTimeMs/1000.0
        self.__kp = Kp
        self.__ki = Ki * _SampleTimeInSec
        self.__kd = Kd / _SampleTimeInSec
        
        if (self.GetDirection() == PID.REVERSE):
            self.__kp = (0.0 - self.__kp)
            self.__ki = (0.0 - self.__ki)
            self.__kd = (0.0 - self.__kd)


    """ SetSampleTime()
    Sets the period, in milliseconds, at which the calculation is performed.
    """
    def SetSampleTime(self, NewSampleTimeMs):
        if (NewSampleTimeMs > 0.0):
            _ratio  = NewSampleTimeMs / self.__SampleTimeMs
            self.__ki *= _ratio
            self.__kd /= _ratio
            self.__SampleTimeMs = NewSampleTimeMs
        else:
            raise Exception("Sample time <= 0!")


    """ SetOutputLimits()
    Clamps the output to a specific range.
    0-255 by default, but it's likely the user will want to change this depending on the application.
    While the input to the controller will generally be in the 0-1023 range (which is the default already), the output will be a little different.
    Maybe they'll be doing a time window and will need 0-8000 or something. Or maybe they'll want to clamp it from 0-125. Who knows. At any rate, that can all be done here.
    """
    def SetOutputLimits(self, Min=0.0, Max=255.0):
        if (Min >= Max):
            raise Exception("Min >= Max!")
        
        self.__OutMin = Min;
        self.__OutMax = Max;
 
        if (self.__InAuto == True):
            if (self.__context.Params[PIDContext.Output] > self.__OutMax):
                self.__context.Params[PIDContext.Output] = self.__OutMax
            elif (self.__context.Params[PIDContext.Output] < self.__OutMin):
                self.__context.Params[PIDContext.Output] = self.__OutMin

            if (self.__ITerm > self.__OutMax):
                self.__ITerm = self.__OutMax
            elif (self.__ITerm < self.__OutMin):
                self.__ITerm = self.__OutMin


    """ SetMode()
    Allows the controller Mode to be set to Manual (zero) or Automatic (non-zero).
    When the transition from manual to auto occurs, the controller is automatically initialized.
    """
    def SetMode(self, Mode):
        _newAuto = (Mode == PID.AUTOMATIC)
        if (_newAuto == (not self.__InAuto)):
            # we just went from manual to auto
            self.__Initialize()
        self.__InAuto = _newAuto
        

    """ Initialize()
    Does all the things that need to happen to ensure a bumpless transfer from manual to automatic mode.
    """
    def __Initialize(self):
        self.__ITerm = self.__context.Params[PIDContext.Output]
        self.__LastInput = self.__context.Params[PIDContext.Input]
        if (self.__ITerm > self.__OutMax):
            self.__ITerm = self.__OutMax
        elif (self.__ITerm < self.__OutMin):
            self.__ITerm = self.__OutMin


    """ SetControllerDirection()
    The PID will either be connected to a DIRECT acting process (+Output leads to +Input)
    or a REVERSE acting process(+Output leads to -Input). We need to know which one,
    because otherwise we may increase the output when we should be decreasing.
    This is called from the constructor.
    """
    def SetControllerDirection(self, Direction):
        if (self.__InAuto and Direction != self.__ControllerDirection):
            self.__kp = (0.0 - self.__kp)
            self.__ki = (0.0 - self.__ki)
            self.__kd = (0.0 - self.__kd)
        self.__ControllerDirection = Direction


    """ Compute()
    Performs the PID calculation.
    It should be called every time loop() cycles.
    ON/OFF and calculation frequency can be set using SetMode and SetSampleTime respectively.
    This, as they say, is where the magic happens. This function should be called
    every time "void loop()" executes. The function will decide for itself whether a new
    pid Output needs to be computed. Returns true when the output is computed, false when nothing has been done.
    """
    def Compute(self):
        if (self.__InAuto == False):
            return False
        _now = datetime.now()
        _timeChange = (_now - self.__LastTime)
        if (_timeChange >= timedelta(milliseconds=self.__SampleTimeMs)):
            # Compute all the working error variables
            _input = self.__context.Params[PIDContext.Input]
            _error = self.__context.Params[PIDContext.SetPoint] - _input
            self.__ITerm += (self.__ki * _error)
            if (self.__ITerm > self.__OutMax):
                self.__ITerm = self.__OutMax
            elif (self.__ITerm < self.__OutMin):
                self.__ITerm = self.__OutMin
            _dInput = (_input - self.__LastInput)

            # Compute PID Output
            _output = self.__kp * _error + self.__ITerm - self.__kd * _dInput
                      
            if (_output > self.__OutMax):
                _output = self.__OutMax
            elif (_output < self.__OutMin):
                _output = self.__OutMin
            self.__context.Params[PIDContext.Output] = _output

            # Remember some variables for next time
            self.__LastInput = _input
            self.__LastTime = _now
            return True
        else:
            return False
