from MultiAxisClass.vectorMagnet import vectorMagnet
import time
multiAxisControl = vectorMagnet()

multiAxisControl.initialize_program()
time.sleep(1)
multiAxisControl.connect()
time.sleep(1)
a=multiAxisControl.getError()
# vectorMagnet.time.sleep(1.01)
# errorCount=multiAxisControl.getErrorCount()
# if(errorCount==0):
#     print("Math is working correctly")
# print(str(errorCount))
# vectorMagnet.time.sleep(1.01)
# # multiAxisControl.queryField() 