#!/usr/bin/python
from pid import PID, PIDContext
from datetime import datetime, timedelta

SetPoint = 260.0
Input = 1.0
Output = 0.0
WindowSize = 3000.0
WindowSizeTimeDelta = timedelta(milliseconds=WindowSize)
WindowStartTime = datetime.now()

pidContext = PIDContext(Input, Output, SetPoint)
pid = PID(pidContext, 0.2, 0.5, 0.1, PID.DIRECT)
pid.SetOutputLimits(0.0, WindowSize)
pid.SetMode(PID.AUTOMATIC)

while pidContext.Params[PIDContext.Input] < SetPoint:
    now = datetime.now()
    pid.Compute()
    
    print(pidContext.Params.__str__())
    
    output = pidContext.Params[PIDContext.Output]
    
    if (now - WindowStartTime > WindowSizeTimeDelta):
        WindowStartTime += WindowSizeTimeDelta
        
    pidContext.Params[PIDContext.Input] += 1
    
    if (timedelta(milliseconds=output) > now - WindowStartTime):
        print("Relay ON")
    else:
        print("Relay OFF")

print("Setpoint reached")
print("Relay OFF")
