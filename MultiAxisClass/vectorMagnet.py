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
    
    def __sendCommand(self, commandString:str):
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
        
    def formatNumericInput(self, input: int | float):
        output=f'{input:.10f}'.rstrip('0').rstrip('.').encode('ascii')
        return output

    def __sendQuery(self, commandString:str) -> (str):
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

    def getState(self) -> (int):
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

    def connect(self) -> (int):
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

    def getFieldSpherical(self) -> tuple[float, float, float]:
        """Returns field in spherical coordinates with currently active units.
        Format is: r, phi, theta
        """
        fieldString=self.__sendQuery(b'FIELD')
        print(fieldString)
        fieldList=[float(e) if e.isdecimal() else e for e in fieldString.split(',')]
        return fieldList[1],fieldList[2],fieldList[3]
    
    def getFieldCartesian(self) -> tuple[float, float, float]:
        """Returns Bx, By, & Bz in Cartesian coordinates with currently active units"""
        fieldString=self.__sendQuery(b'FIELD:CART')
        print(fieldString)
        fieldList=[float(e) if e.isdecimal() else e for e in fieldString.split(',')]
        return fieldList[1],fieldList[2],fieldList[3]
    
    def getIDN(self) -> (str):
        identifier=self.__sendQuery(b'*IDN')
        return identifier
    
    def loadSettings(self, filePath: str):
        """Loads all magnet parameters, sample alignment settings, and table contents"""
        self.__sendCommand(b'LOAD:SET '+filePath.encode('ascii'))
    
    def saveSettings(self, filePath: str):
        """Creates .Sav settings file at filepath. Includes all magnet settings, sample alignment settings, and table contents.
        Input type should be string"""
        self.__sendCommand(b'SAVE:SET '+filePath.encode('ascii'))

    def configureUnits(self, units: int):
        """Field units may only be changed when disconnected.
        Input type should be int.
        0: Kilogauss
        1: Tesla
        """
        self.__sendCommand(b'CONF:UNITS '+str(units).encode('ascii'))
    
    def getUnits(self) -> (int):
        """Returns current field units.
        0: Kilogauss
        1: Tesla
        """
        returnVal=self.__sendQuery(b'UNITS')
        return int(returnVal.strip())

    def setSampleAlignmentVector(self, vectorNumber:int, magnitude:float, azimuth:float, inclination:float):
        """Sets sample alignment vector 1 in spherical coordinates. Magnitude is in the present field units.
        vectorNumber should be 1 or 2.
        """
        if not(vectorNumber == 1 or vectorNumber == 2):
            raise Exception("Not a valid vector specification.")
        self.__sendCommand(b'CONF:ALIGN'+str(vectorNumber).encode('ascii')+b' '+self.formatNumericInput(magnitude)+b','+self.formatNumericInput(azimuth)+b','+self.formatNumericInput(inclination))

    def configureTargetToAlignmentVector(self, vectorNumber:int):
        """Sets the target field to the specified alignment vector and begins ramping. Vector number should be 1 or 2."""
        if not(vectorNumber == 1 or vectorNumber == 2):
            raise Exception("Not a valid vector specification.")
        self.__sendCommand(b'CONF:TARG:ALIGN'+str(vectorNumber).encode('ascii'))
    
    def setTargetFieldSpherical(self, magnitude:float, azimuth:float, inclination:float, dwellTime:float|None):
        """Sets target field in spherical coordinates, adds it to the vector table, and begins ramping. Magnitude is in the present field units.
        Dwell time is in seconds. If none, a zero entry is generated.
        """
        if dwellTime is None:
            self.__sendCommand(b'CONF:TARG:VEC '+self.formatNumericInput(magnitude)+b','+self.formatNumericInput(azimuth)+b','+self.formatNumericInput(inclination))
        else:
            self.__sendCommand(b'CONF:TARG:VEC '+self.formatNumericInput(magnitude)+b','+self.formatNumericInput(azimuth)+b','+self.formatNumericInput(inclination)+b','+self.formatNumericInput(dwellTime))

    def setTargetFieldCartesian(self, Bx:float, By:float, Bz:float, dwellTime:float|None):
        """Sets target field in Cartesian coordinates, adds it to the vector table, and begins ramping. Magnitude is in the present field units.
        Dwell time is in seconds. If none, a zero entry is generated.
        """
        if dwellTime is None:
            self.__sendCommand(b'CONF:TARG:VEC:CART '+self.formatNumericInput(Bx)+b','+self.formatNumericInput(By)+b','+self.formatNumericInput(Bz))
        else:
            self.__sendCommand(b'CONF:TARG:VEC:CART '+self.formatNumericInput(Bx)+b','+self.formatNumericInput(By)+b','+self.formatNumericInput(Bz)+b','+self.formatNumericInput(dwellTime))
        
    def setTargetToVectorTableRow(self, tableRow: int):
        """Sets the target field to the specified table row and begins ramping. Table row should be an int.
        """
        if (tableRow<1):
            raise Exception("Table row must be greater than 0.")

        self.__sendCommand(b'CONF:TARG:VEC:TABL '+str(tableRow).encode('ascii'))
    
    def setTargetToPolar(self, magnitude:float, angle:float, dwellTime:float|None):
        """Sets target field in polar coordinates, adds it to the polar table, and begins ramping. Magnitude is in the present field units.
        Dwell time is in seconds. If none, a zero entry is generated.
        """
        if dwellTime is None:
            self.__sendCommand(b'CONF:TARG:POL '+self.formatNumericInput(magnitude)+b','+self.formatNumericInput(angle))
        else:
            self.__sendCommand(b'CONF:TARG:POL '+self.formatNumericInput(magnitude)+b','+self.formatNumericInput(angle)+b','+self.formatNumericInput(dwellTime))
    
    def setTargetToPolarTableRow(self, tableRow: int):
        """Sets the target field to the specified table row and begins ramping. Table row should be an int.
        """
        if (tableRow<1):
            raise Exception("Table row must be greater than 0.")

        self.__sendCommand(b'CONF:TARG:POL:TABL '+str(tableRow).encode('ascii'))
    
    def enablePauseMode(self):
        """Pauses all connected devices at the present operating field."""
        self.__sendCommand(b'PAUSE')
    
    def enableRampMode(self):
        """Resumes ramping to the target field."""
        self.__sendCommand(b'RAMP')

    def enableZeroMode(self):
        """Sets the target field to zero and begins ramping."""
        self.__sendCommand(b'ZERO')

    def enablePersistentMode(self, persistentState:bool):
        """Sets the target field to zero and begins ramping."""
        self.__sendCommand(b'PERS '+str(int(persistentState)).encode('ascii'))

    def getPersistentMode(self) -> (bool):
        """Returns whether persistent mode is enabled."""
        returnVal=self.__sendQuery(b'PERS')
        return bool(int(returnVal.strip()))
    
    def getAlignmentVectorSpherical(self, vectorNumber:int) -> tuple[float, float, float]:
        """
        Returns the alignment vector in spherical coordinates.

        Parameters:
        vectorNumber (int): The vector number, should be either 1 or 2.

        Returns:
        tuple[float, float, float]: The alignment vector in spherical coordinates (r, phi, theta).

        Raises:
        Exception: If the vector number is not 1 or 2.
        """
        if not(vectorNumber == 1 or vectorNumber == 2):
            raise Exception("Not a valid vector specification.")
        vectorString = self.__sendQuery(b'ALIGN' + str(vectorNumber).encode('ascii'))
        vectorList = [float(e) if e.isdecimal() else e for e in vectorString.split(',')]
        return vectorList[1], vectorList[2], vectorList[3]
    
    def getAlignmentVectorCartesian(self, vectorNumber:int) -> tuple[float, float, float]:
        """
        Returns the alignment vector in Cartesian coordinates.

        Parameters:
        vectorNumber (int): The vector number, should be either 1 or 2.

        Returns:
        tuple[float, float, float]: The alignment vector in Cartesian coordinates (Bx, By, Bz).

        Raises:
        Exception: If the vector number is not 1 or 2.
        """
        if not(vectorNumber == 1 or vectorNumber == 2):
            raise Exception("Not a valid vector specification.")
        vectorString = self.__sendQuery(b'ALIGN:CART' + str(vectorNumber).encode('ascii'))
        vectorList = [float(e) if e.isdecimal() else e for e in vectorString.split(',')]
        return vectorList[1], vectorList[2], vectorList[3]

    def getAlignmentPlane(self) -> tuple[float, float, float]:
        """
        Returns the coefficients for the implicit plane equation made by the two sample alignment vectors.
        
        Returns (a, b, c) for the plane equation ax + by + cz = 0.
        """
        planeString = self.__sendQuery(b'PLANE')
        planeList = [float(e) if e.isdecimal() else e for e in planeString.split(',')]
        return planeList[1], planeList[2], planeList[3]
    
    def getTargetFieldSpherical(self) -> tuple[float, float, float]:
        """
        Returns the target field in spherical coordinates.

        Returns:
        tuple[float, float, float]: The target field in spherical coordinates (r, phi, theta).
        """
        fieldString = self.__sendQuery(b'TARG')
        fieldList = [float(e) if e.isdecimal() else e for e in fieldString.split(',')]
        return fieldList[1], fieldList[2], fieldList[3]
    
    def getTargetFieldCartesian(self) -> tuple[float, float, float]:
        """
        Returns the target field in Cartesian coordinates.

        Returns:
        tuple[float, float, float]: The target field in Cartesian coordinates (Bx, By, Bz).
        """
        fieldString = self.__sendQuery(b'TARG:CART')
        fieldList = [float(e) if e.isdecimal() else e for e in fieldString.split(',')]
        return fieldList[1], fieldList[2], fieldList[3]
    
    def getTimeToTarget(self) -> float:
        """
        Returns the estimated time to reach the target field in seconds.
        
        Returns:
        float: The estimated time to reach the target field in seconds.
        """
        timeString = self.__sendQuery(b'TARG:TIME')
        return float(timeString.strip())