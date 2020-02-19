import argparse, sys, os, psutil, subprocess, re, signal
import logging, logging.handlers
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QTimer
import pkg_resources

import oskb
from oskb import im


def main():

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
    ap.add_argument("-x", help="window absolute position x", metavar="<x>", type=int)
    ap.add_argument("-y", help="window absolute position y", metavar="<y>", type=int)
    ap.add_argument("--width", help="window width", metavar="<width>", type=int)
    ap.add_argument("--height", help="window height", metavar="<height>", type=int)
    hpos = ap.add_mutually_exclusive_group()
    hpos.add_argument("--left", help="oksb docks to the left", action="store_true")
    hpos.add_argument(
        "--middle", "--center", help="oksb docks in the middle", action="store_true"
    )
    hpos.add_argument("--right", help="oksb docks to the right", action="store_true")
    vpos = ap.add_mutually_exclusive_group()
    vpos.add_argument("--top", help="oksb docks to the top", action="store_true")
    vpos.add_argument("--bottom", help="oksb docks to the top", action="store_true")
    ap.add_argument("--toggle", help="toggles oskb on and off", action="store_true")
    ap.add_argument("--off", help="turns oskb off", action="store_true")
    ap.add_argument(
        "--float",
        help="floating window instead of docking to top or bottom",
        action="store_true",
    )
    ap.add_argument(
        "--justshow", help="show keyboard, do not send keys to OS", action="store_true"
    )
    ap.add_argument(
        "--version", "-v", help="print version number and exit", action="store_true"
    )
    cmdline = ap.parse_args()

    if cmdline.version:
        print(pkg_resources.get_distribution("oskb").version)
        sys.exit(0)

    if cmdline.list:
        for k in pkg_resources.resource_listdir("oskb", "keyboards"):
            print(k)
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
    # Get our keyboard instance
    #

    keyboard = oskb.Keyboard()

    if cmdline.float:
        keyboard.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus)
    else:
        # quickly make sure X doesn't make a window frame etc.
        keyboard.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.X11BypassWindowManagerHint)
        # Qt.X11BypassWindowManagerHint means no WM border or title, no application focus, not in taskbar

        # This alternative also works but creates taskbar entry that will give app focus to oskb if pressed
        # keyboard.setWindowFlags( Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus | Qt.FramelessWindowHint)

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
    # On Linux see if we can improve on that with xprop, giving us the workarea minus taskbar and such.
    if sys.platform.startswith("linux"):
        try:
            # See if xprop will give us the workarea minus taskbar and such.
            out = subprocess.check_output(["xprop", "-root", "_NET_WORKAREA"])
            workarea = re.split("=|,", out.decode())
            screenleft = int(workarea[1])
            screentop = int(workarea[2])
            screenwidth = int(workarea[3])
            screenheight = int(workarea[4])
        except:
            pass
    # set width and height from arguments, defaulting to screen width and quarter of screen height resp.
    w = cmdline.width if cmdline.width else screenwidth
    h = cmdline.height if cmdline.height else max(250, int(screenheight / 4))
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
            plugged = keyboard.sendKeys(im.default())
        except:
            sys.stderr.write("Could not set up the virtual keyboard.\n")

        if not plugged:
            if sys.platform.startswith("linux"):
                sys.stderr.write(
                    "Try 'sudo setfacl -m m::rw -m u:<username>:rw /dev/uinput'\n"
                    "(replacing <username> with your username).\n"
                    "See the oskb documentation for more information.\n"
                )
            else:
                sys.stderr.write(
                    "Your platform is not yet supported by oskd. Try --justshow if\n"
                    "you just want to see how pretty oskb is.\n"
                )
            sys.exit(-1)

    #
    # Load the keyboard files
    #

    keyboard.readKeyboards(cmdline.keyboards)

    if cmdline.start:
        keyboard.setKeyboard(cmdline.start)

    #
    # Display the keyboard
    #

    keyboard.show()

    sys.exit(app.exec_())
