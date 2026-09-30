#Important: Cannot query faster than 1 Hz
#Parser commands for configuring the magnet parameters are not supported. This must be done via the GUI and then saved
#Only customizable lines are the two paths in __init__
import queue
import subprocess
import threading
import time

class vectorMagnet:
    """Controller object for AMI vector magnet Multi-Axis program. Written in python and intended for use via Matlab.
    Care should be taken as the Model 430's are fixed to one sample per second
    Potential exceptions are provided in class properties and should be handled.
    """
    def __init__(self):
        self.multiSubProcess = None
        self.multiAxisConfig = R'C:\Users\LTSPM3\Desktop\AMI Magnet Log\LTSPM3_1_28_25.sav'
        self.multiProgramPath = R'C:\Program Files\American Magnetics, Inc\Multi-Axis Operation\Multi-Axis-Operation'

        #Errors provided for try catch logic
        #This error shouldn't be raised but it is technically possible
        self.noError=Exception('0,"No error"')
        self.unrecognizedCommandError=Exception('-101,"Unrecognized command"')
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
        self.unrecognizedQueryError=Exception('-201,"Unrecognized query"')
        self.notConnectedError=Exception('-301,"Not connected"')
        self.connectionAttemptTimeout=Exception('Connection attempt exceeded time limit. Program in unknown state')
        self.switchTransitionError=Exception('-302,"Switch in transition"')
        self.quenchConditionError=Exception('-303,"Quench condition"')
        self.unitsConnectedError=Exception('-304,"No units change while connected"')
        self.cannotEnterPersistenceError=Exception('-305,"Cannot enter persistence"')
        self.persistentError=Exception('-306,"System is persistent"')
        self.noSwitchError=Exception('-307,"No switch installed"')
        self.loadConnectedError=Exception('-308,"Cannot LOAD while connected"')

        # Reply handling (see _startReader / _readline). Replies are read by a
        # background thread so a wedged Multi-Axis program raises
        # responseTimeoutError instead of blocking the caller (MATLAB) forever.
        self.responseTimeoutError=Exception('Timed out waiting for a reply from Multi-Axis')
        self.notRunningError=Exception('Multi-Axis program is not running')
        self.replyTimeout=5.0          # seconds; replies normally arrive within milliseconds
        self._replyQueue=None
        self._readerThread=None

    STATE_NAMES = {0: 'DISCONNECTED', 1: 'RAMPING', 2: 'HOLDING', 3: 'PAUSED',
                   4: 'ZEROING', 5: 'AT_ZERO', 6: 'QUENCH',
                   7: 'HEATING_SWITCHES', 8: 'COOLING_SWITCHES'}

    def initialize_program(self):
        programPathCom=self.multiProgramPath+' -p'
        print("Opening Multi-Axis")
        print(programPathCom)
        self.multiSubProcess=subprocess.Popen(programPathCom, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        self._startReader()

    def exit_program(self):
        """Disconnects from all system devices and gracefully exits Multi-Axis program"""
        self.__sendCommand(b'EXIT')

    # ----- reply plumbing ---------------------------------------------------
    def _startReader(self):
        """Start the thread that copies Multi-Axis stdout lines into a queue.
        Called by initialize_program; tests call it after injecting a fake process."""
        self._replyQueue=queue.Queue()
        proc=self.multiSubProcess
        q=self._replyQueue
        def loop():
            try:
                for line in iter(proc.stdout.readline, b''):
                    q.put(line)
            except Exception:
                pass
        self._readerThread=threading.Thread(target=loop, name='MultiAxisReader', daemon=True)
        self._readerThread.start()

    def _readline(self, timeout: float | None = None) -> bytes:
        """One reply line from Multi-Axis. Raises responseTimeoutError after
        `timeout` (default self.replyTimeout) seconds, or notRunningError if the
        program has exited."""
        if self._replyQueue is None:
            # reader not started (process attached without initialize_program)
            return self.multiSubProcess.stdout.readline()
        if timeout is None:
            timeout=self.replyTimeout
        try:
            return self._replyQueue.get(timeout=timeout)
        except queue.Empty:
            if not self.isAlive():
                raise self.notRunningError
            raise self.responseTimeoutError

    def _write(self, data: bytes):
        self.multiSubProcess.stdin.write(data)
        self.multiSubProcess.stdin.flush()

    def isAlive(self) -> bool:
        """True while the Multi-Axis program is running."""
        proc=self.multiSubProcess
        return proc is not None and proc.poll() is None
    
    def __sendCommand(self, commandString:str):
        """Takes in ascii encoded string."""
        #Command inputs should not have \n as that is added here
        self.multiSubProcess.stdin.write(commandString+b'\n')
        self.multiSubProcess.stdin.flush()

        errorCount= self.getErrorCount()
        if errorCount>0:
            time.sleep(1.001)
            errorString=self.getError()
            print("Error detected following command.")
            raise Exception(errorString)

    def _sendUnsafeCommand(self, commandString:str):
        """Sends command without error checking. Intended for tests."""
        self.multiSubProcess.stdin.write(commandString+b'\n')
        self.multiSubProcess.stdin.flush()
        
    def __formatNumericInput(self, input: int | float):
        output=f'{input:.10f}'.rstrip('0').rstrip('.').encode('ascii')
        return output

    def __sendQuery(self, commandString:str) -> (str):
        """Takes in ascii encoded string."""
        #Automatically includes ?\n at the end of the command
        self.multiSubProcess.stdin.write(commandString+b'?\n')
        self.multiSubProcess.stdin.flush()
        readBits=self._readline()
        decodedString=readBits.decode('ascii')
        decodedString=decodedString.rstrip()

        time.sleep(1.001)
        errorCount = self.getErrorCount()

        if errorCount>0:
            time.sleep(1.001)
            errorString=self.getError()
            print("Error detected following command.")
            raise Exception(errorString)

        return decodedString

    def _sendUnsafeQuery(self, commandString:str) -> (str):
        """Sends query without without error checking. Intended for tests."""
        #Automatically includes ?\n at the end of the command
        self.multiSubProcess.stdin.write(commandString+b'?\n')
        self.multiSubProcess.stdin.flush()
        readBits=self._readline()
        decodedString=readBits.decode('ascii')
        return decodedString

    def getError(self) -> str:
        """Returns last-in-first-out error string. See manual for decoding.
            If there is an error, it is then removed from the queue.
            If there are no errors the return will be:
            {0,"No error"}
        """
        self.multiSubProcess.stdin.write(b'SYST:ERR?\n')
        self.multiSubProcess.stdin.flush()
        readBits=self._readline()
        errorString=readBits.decode('ascii')
        errorString=errorString.rstrip()
        return errorString
    
    def getErrorCount(self) -> int:
        """Returns error count as int"""
        self.multiSubProcess.stdin.write(b'SYST:ERR:COUN?\n')
        self.multiSubProcess.stdin.flush()
        readBits=self._readline()
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
                        raise self.connectionAttemptTimeout
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

        # Handle potential invalid inputs
        fieldList = []
        for e in fieldString.split(','):
            fieldList.append(float(e))

        return fieldList[0],fieldList[1],fieldList[2]
    
    def getFieldCartesian(self) -> tuple[float, float, float]:
        """Returns Bx, By, & Bz in Cartesian coordinates with currently active units"""
        fieldString=self.__sendQuery(b'FIELD:CART')
        print(fieldString)
        
        # Handle potential invalid inputs
        fieldList = []
        for e in fieldString.split(','):
            fieldList.append(float(e))
        return fieldList[0], fieldList[1], fieldList[2]
    
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
        self.__sendCommand(b'CONF:ALIGN'+str(vectorNumber).encode('ascii')+b' '+self.__formatNumericInput(magnitude)+b','+self.__formatNumericInput(azimuth)+b','+self.__formatNumericInput(inclination))

    def configureTargetToAlignmentVector(self, vectorNumber:int):
        """Sets the target field to the specified alignment vector and begins ramping. Vector number should be 1 or 2."""
        if not(vectorNumber == 1 or vectorNumber == 2):
            raise Exception("Not a valid vector specification.")
        self.__sendCommand(b'CONF:TARG:ALIGN'+str(vectorNumber).encode('ascii'))
    
    def setTargetFieldSpherical(self, magnitude:float, azimuth:float, inclination:float, dwellTime:float|None = None):
        """Sets target field in spherical coordinates, adds it to the vector table, and begins ramping. Magnitude is in the present field units.
        Dwell time is in seconds. If none, a zero entry is generated.
        """
        if dwellTime is None:
            self.__sendCommand(b'CONF:TARG:VEC '+self.__formatNumericInput(magnitude)+b','+self.__formatNumericInput(azimuth)+b','+self.__formatNumericInput(inclination))
        else:
            self.__sendCommand(b'CONF:TARG:VEC '+self.__formatNumericInput(magnitude)+b','+self.__formatNumericInput(azimuth)+b','+self.__formatNumericInput(inclination)+b','+self.__formatNumericInput(dwellTime))

    def setTargetFieldCartesian(self, Bx:float, By:float, Bz:float, dwellTime:float|None = None):
        """Sets target field in Cartesian coordinates, adds it to the vector table, and begins ramping. Magnitude is in the present field units.
        Dwell time is in seconds. If none, a zero entry is generated.
        """
        if dwellTime is None:
            self.__sendCommand(b'CONF:TARG:VEC:CART '+self.__formatNumericInput(Bx)+b','+self.__formatNumericInput(By)+b','+self.__formatNumericInput(Bz))
        else:
            self.__sendCommand(b'CONF:TARG:VEC:CART '+self.__formatNumericInput(Bx)+b','+self.__formatNumericInput(By)+b','+self.__formatNumericInput(Bz)+b','+self.__formatNumericInput(dwellTime))
        
    def setTargetToVectorTableRow(self, tableRow: int):
        """Sets the target field to the specified table row and begins ramping. Table row should be an int.
        """
        if (tableRow<1):
            raise Exception("Table row must be greater than 0.")

        self.__sendCommand(b'CONF:TARG:VEC:TAB '+str(tableRow).encode('ascii'))
    
    def setTargetToPolar(self, magnitude:float, angle:float, dwellTime:float|None = None):
        """Sets target field in polar coordinates, adds it to the polar table, and begins ramping. Magnitude is in the present field units.
        Dwell time is in seconds. If none, a zero entry is generated.
        """
        if dwellTime is None:
            self.__sendCommand(b'CONF:TARG:POL '+self.__formatNumericInput(magnitude)+b','+self.__formatNumericInput(angle))
        else:
            self.__sendCommand(b'CONF:TARG:POL '+self.__formatNumericInput(magnitude)+b','+self.__formatNumericInput(angle)+b','+self.__formatNumericInput(dwellTime))
    
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
    
    def getSampleAlignmentVectorSpherical(self, vectorNumber:int) -> tuple[float, float, float]:
        """
        Returns the sample alignment vector in spherical coordinates.

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
        # Handle potential invalid inputs
        vectorList = []
        for e in vectorString.split(','):
            vectorList.append(float(e))
        return vectorList[0], vectorList[1], vectorList[2]
    
    def getSampleAlignmentVectorCartesian(self, vectorNumber:int) -> tuple[float, float, float]:
        """
        Returns the sample alignment vector in Cartesian coordinates.

        Parameters:
        vectorNumber (int): The vector number, should be either 1 or 2.

        Returns:
        tuple[float, float, float]: The alignment vector in Cartesian coordinates (Bx, By, Bz).

        Raises:
        Exception: If the vector number is not 1 or 2.
        """
        if not(vectorNumber == 1 or vectorNumber == 2):
            raise Exception("Not a valid vector specification.")
        vectorString = self.__sendQuery(b'ALIGN' + str(vectorNumber).encode('ascii')+b':CART')
        # Handle potential invalid inputs
        vectorList = []
        for e in vectorString.split(','):
            vectorList.append(float(e))
        return vectorList[0], vectorList[1], vectorList[2]

    def getSampleAlignmentPlane(self) -> tuple[float, float, float]:
        """
        Returns the coefficients for the implicit plane equation made by the two sample alignment vectors.
        
        Returns (a, b, c) for the plane equation ax + by + cz = 0.
        """
        planeString = self.__sendQuery(b'PLANE')
        planeList = [float(e) if e.isnumeric() else e for e in planeString.split(',')]
        return planeList[0], planeList[1], planeList[2]
    
    def getTargetFieldSpherical(self) -> tuple[float, float, float]:
        """
        Returns the target field in spherical coordinates.

        Returns:
        tuple[float, float, float]: The target field in spherical coordinates (r, phi, theta).
        """
        fieldString = self.__sendQuery(b'TARG')
        # Handle potential invalid inputs
        fieldList = []
        for e in fieldString.split(','):
            fieldList.append(float(e))
        return fieldList[0], fieldList[1], fieldList[2]
    
    def getTargetFieldCartesian(self) -> tuple[float, float, float]:
        """
        Returns the target field in Cartesian coordinates.

        Returns:
        tuple[float, float, float]: The target field in Cartesian coordinates (Bx, By, Bz).
        """
        fieldString = self.__sendQuery(b'TARG:CART')
        # Handle potential invalid inputs
        fieldList = []
        for e in fieldString.split(','):
            fieldList.append(float(e))
        return fieldList[0], fieldList[1], fieldList[2]
    
    def getTimeToTarget(self) -> float:
        """
        Returns the estimated time to reach the target field in seconds.
        
        Returns:
        float: The estimated time to reach the target field in seconds.
        """
        timeString = self.__sendQuery(b'TARG:TIME')
        return float(timeString.strip())

    # ----- snapshots for data files -----------------------------------------
    @staticmethod
    def _parseTriple(line: bytes) -> tuple[float, float, float]:
        parts = line.decode('ascii').strip().split(',')
        if len(parts) != 3:
            raise ValueError(f'expected 3 comma-separated values, got {line!r}')
        return float(parts[0]), float(parts[1]), float(parts[2])

    def getStateSnapshot(self, mode: str = 'batched') -> dict:
        """Read-only snapshot of the magnet for stamping into data files.

        Returns a flat dict of float / int / bool / str values (never None or
        tuples) so MATLAB's struct() converts it directly:
          r, phi, theta                    measured field (present units; degrees; ISO, theta from +z)
          rTarget, phiTarget, thetaTarget  setpoint
          state                            see getState (-1 if unknown)
          persistent                       persistent-switch mode
          tRead                            time.time() at the read
          snapshotMode                     'batched' | 'sequential'
          errorString                      instrument error popped during the read, else ''

        'batched' (default): STATE? first, then FIELD?, TARG?, PERS? written
        back-to-back and their replies read, followed by one error-count check
        with no sleep. The per-query 1 s sleep in __sendQuery exists so a
        *command's* error has registered before the count is checked; these
        queries are read-only, their replies are validated by parsing, and any
        late error is caught by the next command's own check. STATE? goes first
        so nothing is asked while disconnected (0) or quenched (6).
        'sequential': the individual getters, about 1.1 s each.
        """
        nan = float('nan')
        snap = {'r': nan, 'phi': nan, 'theta': nan,
                'rTarget': nan, 'phiTarget': nan, 'thetaTarget': nan,
                'state': -1, 'persistent': False, 'tRead': time.time(),
                'snapshotMode': str(mode), 'errorString': ''}

        if mode == 'sequential':
            snap['state'] = int(self.getState())
            if snap['state'] not in (0, 6):
                r, p, t = self.getFieldSpherical()
                snap['r'], snap['phi'], snap['theta'] = float(r), float(p), float(t)
                r, p, t = self.getTargetFieldSpherical()
                snap['rTarget'], snap['phiTarget'], snap['thetaTarget'] = float(r), float(p), float(t)
                snap['persistent'] = bool(self.getPersistentMode())
            return snap
        if mode != 'batched':
            raise ValueError(f"unknown snapshot mode '{mode}'")

        self._write(b'STATE?\n')
        snap['state'] = int(self._readline().decode('ascii').strip())
        if snap['state'] in (0, 6):
            return snap

        self._write(b'FIELD?\nTARG?\nPERS?\n')
        field = self._parseTriple(self._readline())
        target = self._parseTriple(self._readline())
        persistent = bool(int(self._readline().decode('ascii').strip()))
        snap['r'], snap['phi'], snap['theta'] = field
        snap['rTarget'], snap['phiTarget'], snap['thetaTarget'] = target
        snap['persistent'] = persistent

        if self.getErrorCount() > 0:
            snap['errorString'] = self.getError()
            for key in ('r', 'phi', 'theta', 'rTarget', 'phiTarget', 'thetaTarget'):
                snap[key] = nan
        return snap

    def getSessionInfo(self) -> dict:
        """Things that do not change while connected, for one read per session:
        idn, units (0 kG / 1 T), unitsName, configPath (the .sav this driver
        points at), align1_r/phi/theta, align2_r/phi/theta, errorString.
        Uses the individual getters (about 1.1 s each). Failures leave NaN / ''
        and are listed in errorString rather than raised."""
        nan = float('nan')
        info = {'idn': '', 'units': -1, 'unitsName': '',
                'configPath': str(self.multiAxisConfig),
                'align1_r': nan, 'align1_phi': nan, 'align1_theta': nan,
                'align2_r': nan, 'align2_phi': nan, 'align2_theta': nan,
                'errorString': ''}
        errors = []
        try:
            info['idn'] = str(self.getIDN())
        except Exception as e:
            errors.append(f'idn: {e}')
        try:
            units = int(self.getUnits())
            info['units'] = units
            info['unitsName'] = {0: 'kG', 1: 'T'}.get(units, '')
        except Exception as e:
            errors.append(f'units: {e}')
        for n in (1, 2):
            try:
                r, p, t = self.getSampleAlignmentVectorSpherical(n)
                info[f'align{n}_r'], info[f'align{n}_phi'], info[f'align{n}_theta'] = float(r), float(p), float(t)
            except Exception as e:
                errors.append(f'align{n}: {e}')
        info['errorString'] = '; '.join(errors)
        return info