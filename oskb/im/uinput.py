import sys

if sys.platform.startswith("linux"):

    import evdev

    class UInput:
        def __init__(self):
            self.uinput = evdev.UInput(name="oskb")

        def receiveKeys(self, keycode, keyevent):
            self.uinput.write(evdev.ecodes.EV_KEY, keycode, keyevent)
            self.uinput.syn()
