import pytest
import time
from MultiAxisClass.vectorMagnet import vectorMagnet

@pytest.fixture(scope="module")
def magnet():
    magnet = vectorMagnet()
    magnet.initialize_program()
    time.sleep(2)
    yield magnet

    time.sleep(1)

    magnet.exit_program()

def test_connect(magnet:vectorMagnet):
    magnet.connect()
    time.sleep(1)
    currentState=magnet.getState()
    time.sleep(1)
    assert currentState != 0

def test_disconnect(magnet:vectorMagnet):
    #Assumes it is connected based on test order
    magnet.disconnect()
    time.sleep(0.1)
    currentState=magnet.getState()
    assert currentState == 0
