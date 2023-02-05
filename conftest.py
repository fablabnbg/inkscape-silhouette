# Configuration for extra --hardware flag, used for raising an Exception
# on real hardware when not specified.
# This is to avoid accidental plotter outputs within a py.test session

def pytest_addoption(parser):
    parser.addoption("--hardware", action="store_true", help="do HW tests")

def pytest_generate_tests(metafunc):
    if "do_hw" in metafunc.fixturenames:
        if metafunc.config.getoption("hardware"):
            hw = True
        else:
            hw = False
        metafunc.parametrize("do_hw", (hw, ))
