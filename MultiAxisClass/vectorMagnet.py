#Important: Cannot query faster than 1 Hz
#Parser commands for configuring the magnet parameters are not supported. This must be done via the GUI and then saved
#Only customizable lines are the two paths in __init__
import subprocess
import time
import sys
class vectorMagnet:
    """Controller object for AMI vector magnet Multi-Axis program. Written in python and intended for use via Matlab.
    Care should be taken as the Model 430's are fixed to one sample per second
    Potential exceptions are provided in class properties and should be handled.
    """
    def __init__(self):
        self.multiSubProcess = None
        self.multiAxisConfig = b'C:\Users\LTSPM3\Desktop\AMI Magnet Log\LTSPM3_1_24_25.sav'
        self.multiProgramPath = 'C:\Program Files\American Magnetics, Inc\Multi-Axis Operation\Multi-Axis-Operation'

        #Errors provided for try catch logic
        #This error shouldn't be raised but it is technically possible
        self.noError=Exception('0,"No error"')
        self.unrecongizedCommandError=Exception('-101,"Unrecognized command"')
        self.invalidArgumentError=Exception('-102,"Invalid argument"')
        self.nonBooleanArgumentError=Exception('-103,"Non-boolean argument"')
        self.missingParameterError=Exception('-104,"Missing parameter"')
        self.valueRangeError=Exception('-105,"Value out of range"')
        self.nonNumericalEntryError=Exception('-151,"Non-numerical entry"')
        self.magnitudeLimitError=Exception('-152,"Magnitude exceeds limit"')
        self.negativeMagnitudeError=Exception('-153,"Negative magnitude"')
        self.inclinationRangeError=Exception('-154,"Inclination out of range"')
        self.xCoilLimitError=Exception('-155,"Field exceeds x-coil limit"')
        self.xCoilMissingError=Exception('-156,"Field requires x-coil"')
        self.yCoilLimitError=Exception('-157,"Field exceeds y-coil limit"')
        self.yCoilMissingError=Exception('-158,"Field requires y-coil"')
        self.zCoilLimitError=Exception('-159,"Field exceeds z-coil limit"')
        self.zCoilMissingError=Exception('-160,"Field requires z-coil"')
        self.unrecongizedQueryError=Exception('-201,"Unrecognized query"')
        self.notConnectedError=Exception('-301,"Not connected"')
        self.connectionAttemptTimeout=Exception('Connection attempt exceeded time limit. Program in unknown state')
        self.switchTransitionError=Exception('-302,"Switch in transition"')
        self.quenchConditionError=Exception('-303,"Quench condition"')
        self.unitsConnectedError=Exception('-304,"No units change while connected"')
        self.cannotEnterPersistenceError=Exception('-305,"Cannot enter persistence"')
        self.persistentError=Exception('-306,"System is persistent"')
        self.noSwitchError=Exception('-307,"No switch installed"')
        self.loadConnectedError=Exception('-308,"Cannot LOAD while connected"')


    def initialize_program(self):
        programPathCom=self.multiProgramPath+' -p'
        print("Opening Multi-Axis")
        print(programPathCom)
        self.multiSubProcess=subprocess.Popen(programPathCom, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def exit_program(self):
        """Disconnects from all system devices and gracefully exits Multi-Axis program"""
        self.__sendCommand(b'EXIT')
    
    def __sendCommand(self, commandString):
        #Command inputs should not have \n as that is added here
        self.multiSubProcess.stdin.write(commandString+b'\n')
        self.multiSubProcess.stdin.flush()

        errorCount= self.getErrorCount()
        if errorCount>0:
            time.sleep(1.001)
            errorString=self.getError()
            print("Error detected following command.")
            raise Exception(errorString)

    def public_sendCommand(self, commandString):
        """Delete later"""
        self.__sendCommand(commandString)
        
    def __sendQuery(self, commandString) -> (str | None):
        #Automatically includes ?\n at the end of the command
        self.multiSubProcess.stdin.write(commandString+b'?\n')
        self.multiSubProcess.stdin.flush()
        readBits=self.multiSubProcess.stdout.readline()
        decodedString=readBits.decode('ascii')

        time.sleep(1.001)
        errorCount = self.getErrorCount()

        if errorCount>0:
            time.sleep(1.001)
            errorString=self.getError()
            print("Error detected following command.")
            raise Exception(errorString)

        return decodedString

    def getError(self) -> str:
        """Returns last-in-first-out error string. See manual for decoding.
            If there is an error, it is then removed from the queue.
            If there are no errors the return will be:
            {0,"No error"}
        """
        self.multiSubProcess.stdin.write(b'SYST:ERR?\n')
        self.multiSubProcess.stdin.flush()
        readBits=self.multiSubProcess.stdout.readline()
        errorString=readBits.decode('ascii')
        return errorString
    
    def getErrorCount(self) -> int:
        """Returns error count as int"""
        self.multiSubProcess.stdin.write(b'SYST:ERR:COUN?\n')
        self.multiSubProcess.stdin.flush()
        readBits=self.multiSubProcess.stdout.readline()
        decodedString=readBits.decode('ascii')
        errorCount=int(decodedString.strip())
        return errorCount
    
    def clearErrorQueue(self):
        self.__sendCommand(b'*CLS')    

    def getState(self) -> int:
        """Return Values
        0: DISCONNECTED
        1: RAMPING
        2: HOLDING
        3: PAUSED
        4: ZEROING IN PROGRESS
        5: AT ZERO FIELD
        6: QUENCH DETECTED
        7: HEATING PERSISTENT SWITCHES
        8: COOLING PERSISTENT SWITCHES
        """
        returnVal=self.__sendQuery(b'STATE')
        stateVal=int(returnVal.strip())
        return stateVal

    def connect(self) -> (int | None):
        """Connects to Model 430's. Returns current state.
        System settings should be loaded prior."""
        self.__sendCommand(b'SYST:CONN')
        print("Waiting for CONNECT", end='')
        stateVal = 0
        startTime = time.time()
        timeOutCheckTime = 5
        timeoutErrorTime = 15
        # checking for a connected state
        time.sleep(1.01)
        while not stateVal:
            stateVal = self.getState()
            if not stateVal:
                print('.', end='')
                currentTime=time.time()
                elapsedTime=currentTime-startTime
                time.sleep(1.01)
                if(elapsedTime>timeOutCheckTime):
                    errorCount=self.getErrorCount()
                    time.sleep(1.01)
                    if(errorCount>0):
                        print("Unable to Connect. There is an active error")
                        currentError=self.getError()
                        raise Exception(currentError)
                    elif(elapsedTime>timeoutErrorTime):
                        print("Connection was not established and program timed out. Program state unknown.")
                        raise self.connectionAttemptTimeout()
            else:
                print("STATE = " + str(stateVal))
                return stateVal
                
    def disconnect(self):
        """Disconnects from all system devices"""
        self.__sendCommand(b'SYST:DISC')

    def getFieldSpherical(self) -> tuple[int, int, int]:
        """Returns field in spherical coordinates with currently active units.
        Format is: r, phi, theta
        """
        fieldString=self.__sendQuery(b'FIELD')
        print(fieldString)
        fieldList=[int(e) if e.isdigit() else e for e in fieldString.split(',')]
        return fieldList[1],fieldList[2],fieldList[3]
    
    def getFieldCartesian(self) -> tuple[int, int, int]:
        """Returns Bx, By, & Bz in Cartesian coordinates with currently active units"""
        fieldString=self.__sendQuery(b'FIELD:CART')
        print(fieldString)
        fieldList=[int(e) if e.isdigit() else e for e in fieldString.split(',')]
        return fieldList[1],fieldList[2],fieldList[3]
    
    def getIDN(self) -> str:
        identifier=self.__sendQuery(b'*IDN')
        return identifier
    
    def loadSettings(self, filePath):
        """Loads all magnet parameters, sample alignment settings, and table contents"""
        self.__sendCommand(b'LOAD:SET')
