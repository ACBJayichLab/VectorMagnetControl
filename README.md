# VectorMagnetControl

Setup:
Make sure that vectorMagnet.py is within the Matlab path
If so:
```
path_add = fileparts(which('vectorMagnet.py'));
if count(py.sys.path, path_add) == 0
    insert(py.sys.path, int64(0), path_add);
end
```
Will add the file to the python path.

For example, these lines of code start the Multi-Axis Software in LTSPM3:
```
% Start Vector Magnet Control
% See python methods by calling: methods(handles.vectorMagnet)

path_add = fileparts(which('vectorMagnet.py'));
if count(py.sys.path, path_add) == 0
    insert(py.sys.path, int64(0), path_add);
end

pyenv(ExecutionMode="OutOfProcess");
vectorMagnetModule=py.importlib.import_module('vectorMagnet');
handles.vectorMagnet = vectorMagnetModule.vectorMagnet();
handles.vectorMagnet.initialize_program()
disp("initialized waiting to connect")
pause(1)
stateValue = handles.vectorMagnet.connect();
if(stateValue ~= 3)
    disp("Connection not established to Multi-Axis")
end
```
