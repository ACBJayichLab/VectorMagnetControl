%Basic test of creating a Multi-Axis instance and connecting to the magnet
pyenv(ExecutionMode="OutOfProcess")
terminate(pyenv);
pyenv
my_module=py.importlib.import_module('basic_test')
obj=my_module.MyClass();
obj.initialize()
pause(3)
obj.queryIDN()
%Prints the response and returns it as a bit array