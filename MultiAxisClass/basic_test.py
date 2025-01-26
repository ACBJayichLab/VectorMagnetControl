#Basic Check to make sure matlab can connect
#Important: Cannot query faster than 1 Hz 
import subprocess
import time
import sys
class MyClass:
    def __init__(self):
        self.multiSubProcess = None
        self.multiAxisConfig = None
    def queryField(self):
        self.multiSubProcess.stdin.write(b'FIELD?\n')
        self.multiSubProcess.stdin.flush()
        a=self.multiSubProcess.stdout.readline()
        print(a)
        return a
    def queryIDN(self):
        self.multiSubProcess.stdin.write(b'*IDN?\n')
        self.multiSubProcess.stdin.flush()
        a=self.multiSubProcess.stdout.readline()
        print(a)
        return a
    def initialize(self):
        programPathCom='C:\Program Files\American Magnetics, Inc\Multi-Axis Operation\Multi-Axis-Operation -p'
        self.multiAxisConfig=b'C:\Users\LTSPM3\Desktop\AMI Magnet Log\LTSPM3_1_24_25.sav'
        print("Opening Multi-Axis")
        self.multiSubProcess=subprocess.Popen(programPathCom, stdin=subprocess.PIPE, stdout=subprocess.PIPE)