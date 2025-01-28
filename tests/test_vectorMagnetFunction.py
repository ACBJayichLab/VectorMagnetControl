import pytest
import time
from MultiAxisClass.vectorMagnet import vectorMagnet
#Run pytest in the top of the project

@pytest.fixture(scope="module")
def magnet():
    magnet=vectorMagnet()
    magnet.initialize_program()
    time.sleep(2)
    magnet.loadSettings(magnet.multiAxisConfig)
    time.sleep(2)
    magnet.connect()
    time.sleep(1)

    yield magnet

    time.sleep(1)
    magnet.exit_program()



def test_error(magnet):
    magnet.clearErrorQueue()
    time.sleep(0.1)

    errorCount = magnet.getErrorCount()
    assert errorCount == 0
    time.sleep(1)

    errorString=magnet.getError()
    assert type(Exception(errorString)) == type(magnet.noError)
    assert errorString == str(magnet.noError)

def test_testErrorFunctionality(magnet):
    magnet.clearErrorQueue()
    time.sleep(0.1)
    magnet._sendUnsafeCommand(b'LOAD:SET '+magnet.multiAxisConfig.encode('ascii'))
    time.sleep(0.1)
    magnet._sendUnsafeCommand(b'LOAD:SET '+magnet.multiAxisConfig.encode('ascii'))
    time.sleep(0.1)
    errorCount=magnet.getErrorCount()
    assert errorCount==2
    time.sleep(1)
    magnet._sendUnsafeCommand(b'LOAD:SET '+magnet.multiAxisConfig.encode('ascii'))
    time.sleep(0.1)
    errorCount=magnet.getErrorCount()
    assert errorCount==3
    
    time.sleep(0.1)
    assert errorCount == 3
    magnet.clearErrorQueue()
    time.sleep(0.1)
    errorCount = magnet.getErrorCount()
    assert errorCount == 0


def test_getState(magnet):
    magnet.enablePauseMode()
    time.sleep(0.1)
    state=magnet.getState()
    time.sleep(1)
    assert state == 3

def test_getFieldSpherical(magnet):
    #Need to customize this to whatever field you are at.
    r,phi,theta = magnet.getFieldSpherical()
    assert round(r, 4) == 0.09
    assert round(phi, 2) == -6.5
    assert round(theta, 2) == 56.5

def test_getFieldCartesian(magnet):
    Bx, By, Bz = magnet.getFieldCartesian()
    assert round(Bx, 4) == 0.0746
    assert round(By, 4) == -0.0085
    assert round(Bz, 4) == 0.0497

def test_loadSettings(magnet):
    with pytest.raises(Exception, match=str(magnet.loadConnectedError)) as exc_info:
        magnet.loadSettings(magnet.multiAxisConfig)
    time.sleep(1)
    magnet.disconnect()
    time.sleep(1)
    magnet.loadSettings(magnet.multiAxisConfig)
    
def test_Units(magnet):
    
    magnet.disconnect()
    time.sleep(0.1)
    magnet.configureUnits(0)
    time.sleep(0.1)
    units=magnet.getUnits()
    assert units == 0
    time.sleep(1)
    magnet.configureUnits(1)
    time.sleep(0.1)
    units=magnet.getUnits()
    assert units == 1
    time.sleep(1)
    magnet.connect()
    time.sleep(1)
    with pytest.raises(Exception, match=str(magnet.unitsConnectedError)) as exc_info:
        magnet.configureUnits(0)

def test_sampleAlignmentVector(magnet):
    r, phi, theta = magnet.getFieldSpherical()
    magnet.setSampleAlignmentVector(1,r*1.01, phi, theta)
    time.sleep(6)
    r1, phi1, theta1 = magnet.getFieldSpherical()
    time.sleep(1)
    r2, phi2, theta2 = magnet.getSampleAlignmentVectorSpherical(1)
    
    assert round(r1, 3) == round(r * 1.01, 3)
    assert round(phi1, 2) == round(phi, 2)
    assert round(theta1, 2) == round(theta, 2)
    assert round(r2, 3) == round(r * 1.01, 3)
    assert round(phi2, 2) == round(phi, 2)
    assert round(theta2, 2) == round(theta, 2)
    
    time.sleep(1)
    magnet.setSampleAlignmentVector(1, r, phi, theta)
    time.sleep(6)
    Bx, By, Bz = magnet.getSampleAlignmentVectorCartesian(1)
    
    assert round(Bx, 3) == 0.0746
    assert round(By, 3) == -0.0085
    assert round(Bz, 3) == 0.0497

def test_setTargetFieldSpherical(magnet):
    r, phi, theta = magnet.getFieldSpherical()
    time.sleep(1)

    magnet.setTargetFieldSpherical(r, phi, theta)
    
    time.sleep(3)
    
    magnet.setTargetFieldSpherical(r*1.01, phi, theta)
    
    time.sleep(8)
    
    state = magnet.getState()
    assert state == 2
    time.sleep(1)
    r1, phi1, theta1 = magnet.getFieldSpherical()
    assert round(r1, 3) == round(r * 1.01, 3)
    assert round(phi1, 2) == round(phi, 2)
    assert round(theta1, 2) == round(theta, 2)
    
    magnet.setTargetFieldSpherical(r, phi, theta)
    time.sleep(8)
    r2, phi2, theta2 = magnet.getFieldSpherical()
    assert round(r2, 3) == round(r, 3)
    assert round(phi2, 2) == round(phi, 2)
    assert round(theta2, 2) == round(theta, 2)
    
    magnet.enablePauseMode()
    time.sleep(0.1)

    state = magnet.getState()
    assert state == 3
    time.sleep(3)

def test_setTargetToVectorTableRow(magnet):
    magnet.setTargetToVectorTableRow(1)
    time.sleep(3)
    r, phi, theta = magnet.getTargetFieldSpherical()
    
    assert round(r, 3) == 0.09
    assert round(phi, 2) == -6.5
    assert round(theta, 2) == 56.5

# def test_setTargetToPolar(magnet):
#     pass

# def test_setTargetToPolarTableRow(magnet):
#     pass

# def test_enablePauseMode(magnet):
#     pass

# def test_enableRampMode(magnet):
#     pass

# def test_enableZeroMode(magnet):
#     pass

# def test_enablePersistentMode(magnet):
#     pass

# def test_getPersistentMode(magnet):
#     pass

# def test_getAlignmentVectorSpherical(magnet):
#     pass

# def test_getAlignmentVectorCartesian(magnet):
#     pass

# def test_getAlignmentPlane(magnet):
#     pass

# def test_getTargetFieldSpherical(magnet):
#     pass

# def test_getTargetFieldCartesian(magnet):
#     pass

# def test_getTimeToTarget(magnet):
#     pass