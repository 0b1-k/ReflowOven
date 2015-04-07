#!/usr/bin/python
#
# Hardware-agnostic Reflow Oven Controller
# Python adaptation by Fabien Royer
#
# Based on the original Arduino code by 'Rocket Scream Electronics'
# https://github.com/rocketscream/Reflow-Oven-Controller
#
from datetime import datetime, timedelta
from pid import PID, PIDContext
from thermocouple import *
from relayinterface import *
from lcd import LCD

class ReflowLeadFreeProfile(object):
    # PID PARAMETERS
    # PRE-HEAT STAGE
    PID_KP_PREHEAT = 100
    PID_KI_PREHEAT = 0.025
    PID_KD_PREHEAT = 20
    # SOAKING STAGE
    PID_KP_SOAK = 300
    PID_KI_SOAK = 0.05
    PID_KD_SOAK = 250
    # REFLOW STAGE
    PID_KP_REFLOW = 300
    PID_KI_REFLOW = 0.05
    PID_KD_REFLOW = 350
    PID_SAMPLE_TIME = 1000
    # Temperature profile
    TEMPERATURE_SOAK_MIN = 150
    TEMPERATURE_SOAK_MAX = 200
    TEMPERATURE_REFLOW_MAX = 250
    TEMPERATURE_COOL_MIN = 100

class ReflowLeadedProfile(object):
    # PID PARAMETERS
    # PRE-HEAT STAGE
    PID_KP_PREHEAT = 300
    PID_KI_PREHEAT = 0.05
    PID_KD_PREHEAT = 350
    # SOAKING STAGE
    PID_KP_SOAK = 300
    PID_KI_SOAK = 0.05
    PID_KD_SOAK = 350
    # REFLOW STAGE
    PID_KP_REFLOW = 300
    PID_KI_REFLOW = 0.05
    PID_KD_REFLOW = 350
    PID_SAMPLE_TIME = 1000
    # Temperature profile
    TEMPERATURE_SOAK_MIN = 150
    TEMPERATURE_SOAK_MAX = 180
    TEMPERATURE_REFLOW_MAX = 220
    TEMPERATURE_COOL_MIN = 100

class ReflowState(object):
    REFLOW_STATE_IDLE = 0
    REFLOW_STATE_PREHEAT = 1
    REFLOW_STATE_SOAK = 2
    REFLOW_STATE_REFLOW = 3
    REFLOW_STATE_COOL = 4
    REFLOW_STATE_COMPLETE = 5
    REFLOW_STATE_TOO_HOT = 6
    REFLOW_STATE_ERROR = 7

    Messages = [
        "Ready to reflow",
        "Pre-heating phase",
        "Soaking phase",
        "Reflow phase",
        "Cooling phase",
        "Reflow cycle complete",
        "Please Wait, still too hot",
        "Error"]


class ReflowStatus(object):
    REFLOW_STATUS_OFF = 0
    REFLOW_STATUS_ON = 1


class ReflowStateMachine(object):
    # Reflow profiles
    LEADED_PROFILE = 'leaded'
    LEAD_FREE_PROFILE = 'leadfree'
    
    # Constants
    TEMPERATURE_ROOM = 50
    SENSOR_SAMPLING_TIME = 1000
    SOAK_TEMPERATURE_STEP = 5
    SOAK_MICRO_PERIOD = 9000

    def __init__(self, reflowProfile, thermocouple = None, relay = None, lcd = None):
        self.__reflowProfile = None
        
        if (reflowProfile == self.LEAD_FREE_PROFILE):
            self.__reflowProfile = ReflowLeadFreeProfile()
        else:
            self.__reflowProfile = ReflowLeadedProfile()
            
        self.__reflowOvenPidContext = PIDContext(_input=0.0, _output=0.0, _setpoint=0.0)
        self.__reflowOvenPid = PID(self.__reflowOvenPidContext,
                                   Kp=self.__reflowProfile.PID_KP_PREHEAT,
                                   Ki=self.__reflowProfile.PID_KI_PREHEAT,
                                   Kd=self.__reflowProfile.PID_KD_PREHEAT,
                                   direction=PID.DIRECT)
        
        self.__thermocouple = thermocouple
        self.__relay = relay
        self.__lcd = lcd
        self.__windowSize = 2000
        self.__windowStartTime = datetime.now()
        self.__nextCheck = datetime.now()
        self.__nextRead = datetime.now()
        self.__timerSoak = 0.0
        self.__reflowState = ReflowState.REFLOW_STATE_IDLE
        self.__reflowStatus = ReflowStatus.REFLOW_STATUS_OFF
        self.__timerSeconds = 0.0


    def Reflow(self):
        reflowCycleComplete = False
        now = datetime.now()
        while (reflowCycleComplete == False):
            # Time to read the thermocouple?
            if (datetime.now() > self.__nextRead):
                # Read thermocouple next sampling period
                self.__nextRead += timedelta(milliseconds=self.SENSOR_SAMPLING_TIME)
                # Read current temperature
                try:
                    self.__reflowOvenPidContext.Params[PIDContext.Input] = self.__thermocouple.ReadCelsius()
                except Exception as e:
                    # Thermocouple error
                    self.__reflowState = ReflowState.REFLOW_STATE_ERROR
                    self.__reflowStatus = ReflowStatus.REFLOW_STATUS_OFF
            
            if (datetime.now() > self.__nextCheck):
                # Check the Input within the next second
                self.__nextCheck += timedelta(milliseconds=1000)
                # If reflow process is ongoing
                if (self.__reflowStatus == ReflowStatus.REFLOW_STATUS_ON):
                    self.__timerSeconds += 1
                    
                if (self.__lcd is not None):
                    self.__lcd.Clear()
                    self.__lcd.Print(ReflowState.Messages[self.__reflowState])
                    self.__lcd.SetCursor(0, 1)
                    
                    if (self.__reflowState == ReflowState.REFLOW_STATE_ERROR):
                        self.__lcd.Print("No thermocouple connected!")
                    else:
                        self.__lcd.Print(str(self.__reflowOvenPidContext.Params[PIDContext.Input]) + "C ")

            # Reflow oven controller state machine
            if (self.__reflowState == ReflowState.REFLOW_STATE_IDLE):
                if (self.__reflowOvenPidContext.Params[PIDContext.Input] >= self.TEMPERATURE_ROOM):
                    self.__reflowState = ReflowState.REFLOW_STATE_TOO_HOT
                else:
                    # Intialize seconds timer for serial debug information
                    self.__timerSeconds = 0
                    # Initialize PID control window starting time
                    self.__windowStartTime = datetime.now()
                    # Ramp up to minimum soaking temperature
                    self.__reflowOvenPidContext.Params[PIDContext.SetPoint] = self.__reflowProfile.TEMPERATURE_SOAK_MIN
                    # Tell the PID to range between 0 and the full window size
                    self.__reflowOvenPid.SetOutputLimits(0.0, self.__windowSize)
                    self.__reflowOvenPid.SetSampleTime(self.__reflowProfile.PID_SAMPLE_TIME)
                    # Turn the PID on
                    self.__reflowOvenPid.SetMode(PID.AUTOMATIC)
                    # Proceed to preheat stage
                    self.__reflowState = ReflowState.REFLOW_STATE_PREHEAT
                    
            elif (self.__reflowState == ReflowState.REFLOW_STATE_PREHEAT):
                self.__reflowStatus = ReflowStatus.REFLOW_STATUS_ON
                # If minimum soak temperature is achieved
                if (self.__reflowOvenPidContext.Params[PIDContext.Input] >= self.__reflowProfile.TEMPERATURE_SOAK_MIN):
                    # Chop soaking period into smaller sub-periods
                    self.__timerSoak = datetime.now() + timedelta(milliseconds=self.SOAK_MICRO_PERIOD)
                    # Set less agressive PID parameters for soaking ramp
                    self.__reflowOvenPid.SetTunings(
                        Kp=self.__reflowProfile.PID_KP_SOAK,
                        Ki=self.__reflowProfile.PID_KI_SOAK,
                        Kd=self.__reflowProfile.PID_KD_SOAK)
                    # Ramp up to first section of soaking temperature
                    self.__reflowOvenPidContext.Params[PIDContext.SetPoint] = self.__reflowProfile.TEMPERATURE_SOAK_MIN + self.SOAK_TEMPERATURE_STEP
                    # Proceed to soaking state
                    self.__reflowState = ReflowState.REFLOW_STATE_SOAK
                    
            elif (self.__reflowState == ReflowState.REFLOW_STATE_SOAK):
                # If micro soak temperature is achieved
                if (datetime.now() > self.__timerSoak):
                    self.__timerSoak = (datetime.now() + timedelta(milliseconds=self.SOAK_MICRO_PERIOD))
                    # Increment micro setpoint
                    self.__reflowOvenPidContext.Params[PIDContext.SetPoint] += self.SOAK_TEMPERATURE_STEP
                    if (self.__reflowOvenPidContext.Params[PIDContext.SetPoint] > self.__reflowProfile.TEMPERATURE_SOAK_MAX):
                        # Set agressive PID parameters for reflow ramp
                        self.__reflowOvenPid.SetTunings(
                            Kp=self.__reflowProfile.PID_KP_REFLOW,
                            Ki=self.__reflowProfile.PID_KI_REFLOW,
                            Kd=self.__reflowProfile.PID_KD_REFLOW)
                        # Ramp up to first section of reflow temperature
                        self.__reflowOvenPidContext.Params[PIDContext.SetPoint] = self.__reflowProfile.TEMPERATURE_REFLOW_MAX
                        # Proceed to reflowing state
                        self.__reflowState = ReflowState.REFLOW_STATE_REFLOW
                        
            elif (self.__reflowState == ReflowState.REFLOW_STATE_REFLOW):
                # We need to avoid hovering at peak temperature for too long
                # Crude method that works like a charm and safe for the components
                if (self.__reflowOvenPidContext.Params[PIDContext.Input] >= (self.__reflowProfile.TEMPERATURE_REFLOW_MAX - 5)):
                    # Set PID parameters for cooling ramp
                    self.__reflowOvenPid.SetTunings(
                            Kp=self.__reflowProfile.PID_KP_REFLOW,
                            Ki=self.__reflowProfile.PID_KI_REFLOW,
                            Kd=self.__reflowProfile.PID_KD_REFLOW)
                    # Ramp down to minimum cooling temperature
                    self.__reflowOvenPidContext.Params[PIDContext.SetPoint] = self.__reflowProfile.TEMPERATURE_COOL_MIN
                    # Proceed to cooling state
                    self.__reflowState = ReflowState.REFLOW_STATE_COOL
                    
            elif (self.__reflowState == ReflowState.REFLOW_STATE_COOL):
                # If minimum cool temperature is achieved
                if (self.__reflowOvenPidContext.Params[PIDContext.Input] <= self.__reflowProfile.TEMPERATURE_COOL_MIN):
                    # Turn off reflow process
                    self.__reflowStatus = ReflowStatus.REFLOW_STATUS_OFF
                    # Proceed to reflow Completion state
                    self.__reflowState = ReflowState.REFLOW_STATE_COMPLETE
            
            elif (self.__reflowState == ReflowState.REFLOW_STATE_COMPLETE):
                # Reflow process ended
                self.__reflowState = ReflowState.REFLOW_STATE_IDLE
                # Exit the state machine loop
                reflowCycleComplete = True
                
            elif (self.__reflowState == ReflowState.REFLOW_STATE_TOO_HOT):
                # If oven temperature drops below room temperature
                if (self.__reflowOvenPidContext.Params[PIDContext.Input] < self.TEMPERATURE_ROOM):
                    # Ready to reflow
                    self.__reflowState = ReflowState.REFLOW_STATE_IDLE
            
            elif (self.__reflowState == ReflowState.REFLOW_STATE_ERROR):
                # Exit the state machine loop
                reflowCycleComplete = True
            
            # PID computation and relay control
            if (self.__reflowStatus == ReflowStatus.REFLOW_STATUS_ON):
                now = datetime.now()
                self.__reflowOvenPid.Compute()
                if ((now - self.__windowStartTime) > timedelta(milliseconds=self.__windowSize)):
                    # Time to shift the Relay Window
                    self.__windowStartTime += timedelta(milliseconds=self.__windowSize)
                if (timedelta(milliseconds=self.__reflowOvenPidContext.Params[PIDContext.Output]) > (now - self.__windowStartTime)):
                    self.__relay.SwitchRelay(RelayInterface.ON)
                else:
                    self.__relay.SwitchRelay(RelayInterface.OFF)
            else:
                self.__relay.SwitchRelay(RelayInterface.OFF)
