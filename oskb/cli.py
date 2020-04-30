import argparse, sys, os, psutil, subprocess, re, signal
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QTimer
import pkg_resources

import oskb
from oskb import im

linux = sys.platform.startswith("linux")

if linux:
    import getpass
    from ewmh import EWMH, ewmh

    wm = EWMH()
    moved_windows = []


def command_line_arguments():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "keyboards",
        help="""Which keyboard(s) to load. These are either files or names of built-in keyboards. If
multiple keyboards are loaded, the user can switch between them with a menu key. If no keyboards are chosen
a full keyboard is shown if display is wider than 600 pixels, otherwise a phone-style keyboard is used. If
oskb comes with a keyboard for the presently set keyboard layout, that keyboard is used. Otherwise oskb
will show a US keyboard layout and switch the system keyboard layout to that.""",
        metavar="<kbd>",
        nargs="*",
    )
    ap.add_argument("--version", "-v", help="Print version number and exit.", action="store_true")
    ap.add_argument(
        "--start",
        metavar="<kbd>",
        help="""Normally the first keyboard specified is shown first. This allows you to specify one of the
loaded keyboards as the one to start with.""",
    )
    ap.add_argument(
        "--list", action="store_true", help="Lists all built-in keyboards that were shipped with oskb.",
    )
    ap.add_argument(
        "--dump",
        help="Keyboards are JSON files. This will write the contents of a built-in keyboard to stdout.",
        action="store_true",
    )
    ap.add_argument(
        "--nomap",
        help="""Prevent oskb from changing the system keyboard to the keymap specified with the keyboard.""",
        action="store_true",
    )
    ap.add_argument(
        "--toggle",
        help="""Will turn the keyboard off if one is already active, otherwise starts the keyboard. This
allows one shortcut to be used to turn the keyboard on and off.""",
        action="store_true",
    )
    ap.add_argument("--off", help="Turns off a running keyboard.", action="store_true")
    ap.add_argument(
        "--nopushaway",
        help="Do not attempt to push other windows out of the way when showing the keyboard.",
        action="store_true",
    )
    modmode = ap.add_mutually_exclusive_group()
    modmode.add_argument(
        "--flashmod",
        help="""Only press the modifier keys (Alt, Shift, etc) down briefly during each keypress. This is the
default when --float is specified.""",
        action="store_true",
    )
    modmode.add_argument(
        "--steadymod",
        help="""Modifier keys are pressed down as shown in interface. This is the default unless --float is
specified.""",
        action="store_true",
    )
    ap.add_argument("--justshow", help="Show keyboard, do not send keys to OS.", action="store_true")

    loc = ap.add_argument_group(title="Controlling position on screen")
    loc.add_argument("-x", help="Absolute position of left side of keyboard", metavar="<x>", type=int)
    loc.add_argument("-y", help="Absolute position of top of keyboard", metavar="<y>", type=int)
    loc.add_argument("--width",
        help="Keyboard width in pixels. The default is to use the full width of the primary display.",
        metavar="<width>",
        type=int,
    )
    loc.add_argument(
        "--height",
        help="Keyboard height in pixels. The default is a third of the height of the primary display.",
        metavar="<height>",
        type=int,
    )
    hpos = loc.add_mutually_exclusive_group()
    hpos.add_argument("--left", help="Keyboard docks to the left side of the screen.", action="store_true")
    hpos.add_argument(
        "--middle",
        "--center",
        help="Keyboard docks in the middle of the screen. This is the default.",
        action="store_true",
    )
    hpos.add_argument("--right", help="Keyboard docks to the right side of the screen.", action="store_true")
    vpos = loc.add_mutually_exclusive_group()
    vpos.add_argument(
        "--top", help="Keyboard docks to the top of the screen. This is the default.", action="store_true"
    )
    vpos.add_argument("--bottom", help="Keyboard docks to the bottom of the screen.", action="store_true")
    loc.add_argument(
        "--float", help="Floating keyboard window instead of fixed docked position.", action="store_true",
    )

    return ap


def main():
    global x, y, w, h

    #
    # Parse command line arguments
    #

    ap = command_line_arguments()
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
        if cmdline.left:
            x = screenleft
            mx = screenleft
        elif cmdline.right:
            x = screenleft + screenwidth - w
            mx = screenleft + screenwidth - mw
        else:
            x = int(screenleft + (screenwidth / 2) - (w / 2))
            mx = int(screenleft + (screenwidth / 2) - (mw / 2))

    # Set geometry accordingly
    keyboard.setMinimizer(mx, my, mw, mh)
    keyboard.setGeometry(x, y, w, h)

    #
    # Figure out default keyboard if nothing selected
    #

    # (Has to be done before plugging in virtual keyboard, bc that switches map to 'us')
    load_keyboards = cmdline.keyboards
    if load_keyboards == []:
        kbname = 'paddy' if screenwidth > 600 else 'phoney'
        tryfirst = kbname + "-" + querySystemKeymap("layout")
        if pkg_resources.resource_exists("oskb", "keyboards/" + tryfirst):
            load_keyboards = [tryfirst]
        else:
            load_keyboards = [kbname + "-us"]

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
                user = getpass.getuser()
                sys.stderr.write(
                    "Try 'sudo setfacl -m m::rw -m u:" + user + ":rw /dev/uinput /dev/input/*'\n"
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

    for k in load_keyboards:
        keyboard.readKeyboard(k)

    # Also works if no startup kbd is specified, because None will load first keyboard
    keyboard.setKeyboard(cmdline.start)

    #
    # Display the keyboard
    #

    keyboard.show()

    sys.exit(app.exec_())




def querySystemKeymap(key, default = None):
    try:
        output = subprocess.check_output(['setxkbmap', '-query']).decode("utf-8")
        match = re.search(key + ":\s+(\w+)", output)
        if match:
            return match.group(1)
        else:
            return default
    except:
        return default


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
                wm.setMoveResizeWindow(window, gravity=ewmh.X.SouthWestGravity, x=nx, y=ny, w=nw, h=nh)
                moved_windows.append((window, (fx, fy, fw - (fw - ww), fh - (fh - wh)), (nx, ny, nw, nh)))
    else:
        for w in moved_windows:
            window = w[0]
            (nx, ny, nw, nh) = w[1]
            wm.setMoveResizeWindow(window, gravity=ewmh.X.SouthWestGravity, x=nx, y=ny, w=nw, h=nh)
    wm.display.flush()
