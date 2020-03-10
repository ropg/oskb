import argparse, sys, os, psutil, subprocess, re, signal
import logging, logging.handlers
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QTimer
import pkg_resources

import oskb
from oskb import im

linux = sys.platform.startswith("linux")

if linux:
    from ewmh import EWMH, ewmh
    wm = EWMH()
    moved_windows = []

def main():
    global x, y, w, h

    #
    # Parse command line arguments
    #

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "keyboards",
        help="one or more keyboard files, either actual files or names of built-in keyboards",
        metavar="<kbd>",
        nargs="*",
        default=["phoney-us"],
    )
    ap.add_argument("--start", help="start with keyboard", metavar="<kbdname>")
    ap.add_argument("--list", help="list built-in keyboards", action="store_true")
    ap.add_argument("--dump", help="dumps built-in keyboard to stdout", action="store_true")
    ap.add_argument("--nomap", help="do not remap systemkeyboard", action="store_true")
    ap.add_argument("-x", help="window absolute position x", metavar="<x>", type=int)
    ap.add_argument("-y", help="window absolute position y", metavar="<y>", type=int)
    ap.add_argument("--width", help="window width", metavar="<width>", type=int)
    ap.add_argument("--height", help="window height", metavar="<height>", type=int)
    hpos = ap.add_mutually_exclusive_group()
    hpos.add_argument("--left", help="oksb docks to the left", action="store_true")
    hpos.add_argument("--middle", "--center", help="oksb docks in the middle", action="store_true")
    hpos.add_argument("--right", help="oksb docks to the right", action="store_true")
    vpos = ap.add_mutually_exclusive_group()
    vpos.add_argument("--top", help="oksb docks to the top", action="store_true")
    vpos.add_argument("--bottom", help="oksb docks to the top", action="store_true")
    ap.add_argument("--toggle", help="toggles oskb on and off", action="store_true")
    ap.add_argument("--off", help="turns oskb off", action="store_true")
    ap.add_argument(
        "--float", help="floating window instead of docking to top or bottom", action="store_true",
    )
    ap.add_argument("--nopushaway", help="do not push other windows out of the way", action="store_true")
    modmode = ap.add_mutually_exclusive_group()
    modmode.add_argument("--flashmod", help="modifiers down briefly during keypress", action="store_true")
    modmode.add_argument("--steadymod", help="modifiers down as shown in interface", action="store_true")
    ap.add_argument("--justshow", help="show keyboard, do not send keys to OS", action="store_true")
    ap.add_argument("--version", "-v", help="print version number and exit", action="store_true")
    cmdline = ap.parse_args()

    if cmdline.version:
        print(pkg_resources.get_distribution("oskb").version)
        sys.exit(0)

    if cmdline.list:
        for k in pkg_resources.resource_listdir("oskb", "keyboards"):
            if not k.startswith("_"):
                print(k)
        sys.exit(0)

    if cmdline.dump:
        if len(cmdline.keyboards) != 1:
            sys.stderr.write("Must specify exactly one built-in keyboard to dump.\n")
            sys.exit(-1)
        if not pkg_resources.resource_exists("oskb", "keyboards/" + cmdline.keyboards[0]):
            sys.stderr.write("Built-in keyboard '" + cmdline.keyboards[0] + "' not found.\n")
            sys.exit(-1)
        print(pkg_resources.resource_string("oskb", "keyboards/" + cmdline.keyboards[0]).decode("utf-8"))
        sys.exit(0)

    #
    # Kill any existing keyboard instances. If we did end up killing existing keyboards
    # only start up if '--toggle' wasn't specified. It allows the same command line to
    # be used to turn the keyboard on and off. '--off' just kills keyboard processes.
    #

    ikilled = False
    mypid = os.getpid()
    myparent = os.getppid()
    myname = "oskb"
    for proc in psutil.process_iter(attrs=(["pid"])):
        try:
            if not proc.pid == mypid and not proc.pid == myparent:
                itsname = os.path.basename(proc.name())
                if re.match("^[Pp]ython\d*$", itsname) and len(proc.cmdline()) > 1:
                    itsname = os.path.basename(proc.cmdline()[1])
                if itsname == myname:
                    proc.send_signal(9)
                    ikilled = True
        except:
            pass
    if (ikilled and cmdline.toggle) or cmdline.off:
        sys.exit()

    #
    # Start the Qt context
    #

    app = QApplication([])

    #
    # Make sure Ctrl-C can interrupt oskb
    #

    def sigint_handler(*args):
        sys.stderr.write("\r")
        QApplication.quit()

    signal.signal(signal.SIGINT, sigint_handler)
    timer = QTimer()
    timer.start(250)
    timer.timeout.connect(lambda: None)

    #
    # Get our keyboard widget instance
    #

    keyboard = oskb.Keyboard()
    if cmdline.float:
        keyboard.setWindowTitle("On-Screen Keyboard")
        keyboard.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus)
        if not cmdline.steadymod:
            keyboard.setFlashModifiers(True)
    else:
        if linux and not cmdline.nopushaway:
            keyboard.sendScreenState(receiveScreenState)
        if not cmdline.flashmod:
            keyboard.setFlashModifiers(False)
        # quickly make sure X doesn't make a window frame etc.
        keyboard.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.X11BypassWindowManagerHint)
        # Qt.X11BypassWindowManagerHint means no WM border or title, no application focus, not in taskbar

        # also works but creates taskbar entry that will application focus to oskb if pressed
        # ( Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus | Qt.FramelessWindowHint)

    #
    # Figure out where and how big we're going to be on the screen
    #

    # First take the screen dimensions
    desktop = app.desktop()
    screen = desktop.screenGeometry()
    screenleft = 0
    screentop = 0
    screenwidth = screen.width()
    screenheight = screen.height()
    # On Linux see if we can improve on that by asking windowmanager for workarea (minus taskbar etc).
    if linux:
        try:
            screenleft, screentop, screenwidth, screenheight = list(wm.getWorkArea()[0:4])
        except:
            pass
    # set width and height from arguments, defaulting to screen width and quarter of screen height resp.
    w = cmdline.width if cmdline.width else screenwidth
    h = cmdline.height if cmdline.height else max(250, int(screenheight / 3))
    mw, mh = 70, 70  # Size of minimized keyboard button
    # Vertical position
    if cmdline.y:
        y = cmdline.y
    else:
        if cmdline.top:
            y = screentop
            my = screentop
        else:
            y = screentop + screenheight - h
            my = screentop + screenheight - mh
    # Horizontal position
    if cmdline.x:
        x = cmdline.x
    else:
        if cmdline.middle:
            x = int(screenleft + (screenwidth / 2) - (w / 2))
            mx = int(screenleft + (screenwidth / 2) - (mw / 2))
        elif cmdline.left:
            x = screenleft
            mx = screenleft
        else:
            x = screenleft + screenwidth - w
            mx = screenleft + screenwidth - mw
    # Set geometry accordingly
    keyboard.setMinimizer(mx, my, mw, mh)
    keyboard.setGeometry(x, y, w, h)

    #
    # Tell keyboard to send the keypresses to the default handler for OS
    #

    if not cmdline.justshow:
        plugged = False
        try:
            plugged = keyboard.sendKeys(im.default().receiveKeys)
        except:
            sys.stderr.write("Could not set up the virtual keyboard.\n")

        if not plugged:
            if linux:
                import getpass

                user = getpass.getuser()
                sys.stderr.write(
                    "Try 'sudo setfacl -m m::rw -m u:" + user + ":rw /dev/uinput'\n"
                    "See the oskb documentation for more information.\n"
                )
            else:
                sys.stderr.write(
                    "Your platform is not yet supported by oskd. Try --justshow if\n"
                    "you just want to see how pretty oskb is.\n"
                )
            sys.exit(-1)

    #
    # Tell oskb where to send keymap changes, so we can call setxkbmap to switch as well
    #

    if not cmdline.nomap:
        keyboard.sendMapChanges(receiveMapChanges)

    #
    # Load the keyboard files
    #

    for k in cmdline.keyboards:
        keyboard.readKeyboard(k)

    # Also works if no startup kbd is specified, because None will load first keyboard
    keyboard.setKeyboard(cmdline.start)

    #
    # Display the keyboard
    #

    keyboard.show()

    sys.exit(app.exec_())


def receiveMapChanges(keymap):
    try:
        subprocess.run(["setxkbmap"] + keymap.split(" "))
    except:
        pass


def receiveScreenState(maximize):

    def get_geometry(window):
        g = window.get_geometry()
        return g.x, g.y, g.width, g.height

    def frame(window):
        frame = window
        while frame.query_tree().parent != wm.root:
            frame = frame.query_tree().parent
        return frame

    global moved_windows
    if maximize:
        moved_windows = []
        for window in wm.getClientList():
            wn = wm.getWmName(window).decode("utf-8")
            wx, wy, ww, wh = get_geometry(window)
            fx, fy, fw, fh = get_geometry(frame(window))
            bottom = fy + fh
            if bottom > y and bottom < y + h and fy < y + h:
                need = bottom - y + (fh - wh)
                moveby = min(fy, need)
                shrinkby = need - moveby
                nx, nw = fx, fw
                ny = fy - moveby
                nh = bottom - fy - shrinkby
                wm.setMoveResizeWindow(
                    window,
                    gravity=ewmh.X.SouthWestGravity,
                    x=nx,
                    y=ny,
                    w=nw,
                    h=nh
                )
                moved_windows.append( (window, (fx, fy, fw - (fw - ww), fh - (fh - wh)), (nx, ny, nw, nh)) )
    else:
        for w in moved_windows:
            window = w[0]
            (nx, ny, nw, nh) = w[1]
            wm.setMoveResizeWindow(
                window,
                gravity=ewmh.X.SouthWestGravity,
                x=nx,
                y=ny,
                w=nw,
                h=nh
            )
    wm.display.flush()



