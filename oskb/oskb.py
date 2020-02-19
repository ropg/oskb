import os, sys, re, json, subprocess
from functools import partial
import pkg_resources

from PyQt5.QtCore import QTimer, QRect, QSysInfo, QEvent, QSize, Qt
from PyQt5.QtWidgets import (
    QWidget,
    QPushButton,
    QMainWindow,
    QGridLayout,
    QHBoxLayout,
    QSizePolicy,
    QLayout,
    QStackedLayout,
    QLabel,
)


RELEASED = 0
PRESSED = 1

# key detection timings in milliseconds
LONGPRESS_TIMEOUT = 350
DOUBLECLICK_TIMEOUT = 200


class Keyboard(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("On-Screen Keyboard")

        self._modifiers = {}

        # This is all for the key-detection state-machine
        self._longpresswait = False
        self._longtimer = QTimer()
        self._stopsinglepress = False
        self._doublebutton = None
        self._doubletimer = QTimer()
        self._doubletimer.setSingleShot(True)
        self._doubletimer.timeout.connect(self._doubleTimeout)

        self._viewuntil = None
        self._thenview = None

        self._kbds = []
        self._view = None
        self._kbd = None
        self._sendkeysobject = None
        self._buttonhandler = self._oskbButtonHandler
        self._minimizerlocation = QRect(0, 0, 70, 70)

    def sendKeys(self, object):
        if getattr(object, "receiveKeys", None) and callable(object.receiveKeys):
            self._sendkeysobject = object
            return True
        return False

    def setButtonHandler(self, handler=None):
        if not handler:
            handler = self._oskbButtonHandler
        self._buttonhandler = handler

    def setMinimizer(self, mx, my, mw, mh):
        self._minimizerlocation = QRect(mx, my, mw, mh)

    def readKeyboards(self, kbdfiles):
        for kbdfile in kbdfiles:
            kbd = None
            if os.access(kbdfile, os.R_OK):
                with open(kbdfile, "r", encoding="utf-8") as f:
                    kbd = json.load(f)
            elif kbdfile == os.path.basename(kbdfile) and pkg_resources.resource_exists(
                "oskb", "keyboards/" + kbdfile
            ):
                kbd = json.loads(
                    pkg_resources.resource_string("oskb", "keyboards/" + kbdfile)
                )
            if kbd:
                kbd["_name"] = os.path.basename(kbdfile)
                self._kbds.append(kbd)
            else:
                raise FileNotFoundError("Could not find " + kbdfile)

        if len(self._kbds) > 1:
            chooser = {
                "_name": "chooser",
                "views": [{"name": "default", "columns": [{"rows": []}]}],
            }
            for k in self._kbds:
                rows = chooser["views"][0]["columns"][0].get("rows")
                rows.append(
                    {
                        "keys": [
                            {
                                "caption": k.get("description"),
                                "single": {"keyboard": {"name": k.get("name")}},
                            }
                        ]
                    }
                )
            self._kbds.append(chooser)

        minimized = {
            "_name": "minimized",
            "style": "QWidget {background: transparent;}",
            "views": [
                {
                    "name": "default",
                    "columns": [
                        {
                            "rows": [
                                {
                                    "keys": [
                                        {
                                            "caption": "⌨",
                                            "single": {"keyboard": {"name": "back"}},
                                        }
                                    ]
                                }
                            ]
                        }
                    ],
                }
            ],
        }
        self._kbds.append(minimized)

        self._initKeyboards()

    def setKeyboard(self, kbdname=None):
        newgeometry = None
        if not kbdname:
            kbdname = self._kbds[0]["_name"]
        if kbdname == "minimized":
            newgeometry = self._minimizerlocation
            if not self._view:
                self._previouskeyboard = self._kbds[0]["_name"]
        else:
            if kbdname == "back":
                kbdname = self._previouskeyboard
                if self._previousgeometry != self.geometry():
                    newgeometry = self._previousgeometry
        for ki, k in enumerate(self._kbds):
            if k.get("_name") == kbdname:
                self._releaseModifiers()
                self._kbd = k
                if sys.platform.startswith("linux") and k.get("setxkbmap"):
                    cmd = ["setxkbmap"] + k["setxkbmap"].split(" ")
                    try:
                        subprocess.check_output(cmd)
                    except:
                        pass
                if newgeometry:
                    self.hide()
                if kbdname != "minimized":
                    self._previouskeyboard = kbdname
                self._previousgeometry = self.geometry()
                self.layout().setCurrentIndex(ki)
                self.setView("default", newgeometry)

    def setView(self, viewname, newgeometry=None):
        for vi, view in enumerate(self._kbd.get("views")):
            if view.get("name") == viewname:
                self._view = view
                self._kbd["_QWidget"].layout().setCurrentIndex(vi)
                if newgeometry:
                    self.setGeometry(newgeometry)
                    self.show()
                else:
                    self.updateKeyboard()

    #
    # Make sure show events also calculate proper sizes and first initialise if that hasn't happened yet.
    #

    def showEvent(self, event):
        if not self._view:
            self.setKeyboard()  # includes another show event with self._view set
        else:
            self.updateKeyboard()
            QWidget.showEvent(self, event)

    #
    # Recalculate the fontsize and mrgaing and change the stylesheets when resizing
    #

    def resizeEvent(self, event):
        QWidget.resizeEvent(self, event)
        if self._view and self.isVisible():
            self.updateKeyboard()

    def updateKeyboard(self):
        if not self._view:
            return False
        #
        # Calculate the font and margin sizes
        kw = self.width() / self._view["widthInUnits"]
        kh = self.height() / self._view["heightInUnits"]
        fontsize = min(max(int(min(kw / 1.5, kh / 2)), 5), 50)
        margin = int(fontsize / 10)
        #
        # Dynamically change the default, per-keyboard and per-view stylesheets
        all_sheets = (
            pkg_resources.resource_string("oskb", "default.css").decode("utf-8")
            + " .key { font-size: "
            + str(fontsize)
            + "px; "
            + "margin: "
            + str(margin)
            + "px; "
            + "border-radius: "
            + str(margin * 3)
            + "px } "
            + self._kbd.get("style", "")
            + " "
            + self._view.get("style", "")
            + " "
        )
        self.setStyleSheet(self._fixStyleSheet(all_sheets, fontsize))
        #
        # Then adjust the stylesheets and class properties of all keys
        for ci, column in enumerate(self._view.get("columns", [])):
            for ri, row in enumerate(column.get("rows", [])):
                for keydata in row.get("keys", []):
                    k = keydata.get("_QWidget")
                    if k:
                        addclass = ""
                        if keydata.get("single") and keydata["single"].get("modifier"):
                            modname = keydata["single"]["modifier"].get("name", "")
                            moddata = self._modifiers.get(modname, {})
                            modstate = moddata.get("state")
                            if modstate == 1:
                                addclass = " held"
                            elif modstate == 2:
                                addclass = " locked"
                        k.setProperty(
                            "class",
                            "key row"
                            + str(ri + 1)
                            + " col"
                            + str(ci + 1)
                            + " "
                            + keydata.get("class", "")
                            + addclass,
                        )
                        k.setStyleSheet(
                            self._fixStyleSheet(keydata.get("style", ""), fontsize)
                        )

    #
    # _initKeyboards sets up a QStackedLayout holding QWidgets for each keyboard, which in turn have a QStackedlayout
    # that holds a QWidget for each view within that keyboard. That has a QGridLayout with QHboxLayouts in it that
    # hold the individual key QPushButton widgets. It also sets the captions and button actions for each key
    # and figures out how many standard key widths and row heights there are in all the views, which is used by
    # updateKeyboard() to dynamically figure out how big the fonts, margins and rounded corners need to be.
    #

    def _initKeyboards(self):
        kbdstack = QStackedLayout()
        self.setMaximumSize(self.width(), self.height())
        kbdstack.setSizeConstraint(QLayout.SetMaximumSize)
        for ki, kbd in enumerate(self._kbds):
            viewstack = QStackedLayout()
            for vi, view in enumerate(kbd.get("views", [])):
                #
                # This stores the width and height in standard key widths for each view.
                total_height = 0
                total_width = 0
                for ci, column in enumerate(view.get("columns", [])):
                    largest_width = 0
                    for ri, row in enumerate(column.get("rows", [])):
                        if len(row.get("keys", [])) and not row.get("ignoreKeyWidths"):
                            totalweight = 0
                            for keydata in row.get("keys", []):
                                w = keydata.get("width", "1")
                                totalweight += float(w)
                            if totalweight > largest_width:
                                largest_width = totalweight
                        total_height += float(row.get("height", "1"))
                    total_width += largest_width
                view["widthInUnits"] = total_width
                view["heightInUnits"] = total_height
                #
                # This is the part where everything is created
                grid = QGridLayout()
                grid.setSpacing(0)
                grid.setContentsMargins(0, 0, 0, 0)
                for ci, column in enumerate(view.get("columns", [])):
                    for ri, row in enumerate(column.get("rows", [])):
                        keys = row.get("keys", [])
                        if not len(keys):
                            continue
                        kl = QHBoxLayout()
                        kl.setContentsMargins(0, 0, 0, 0)
                        kl.setSpacing(0)
                        for keydata in keys:
                            stretch = int(float(keydata.get("width", 1)) * 10)
                            #
                            # This handles creation of the QPushButton for the key
                            if keydata.get("type", "key") == "key":
                                k = QPushButton()
                                k.setSizePolicy(
                                    QSizePolicy.Expanding, QSizePolicy.Expanding
                                )
                                k.setText(keydata.get("caption", ""))
                                k.data = keydata
                                k.pressed.connect(
                                    partial(self._buttonhandler, k, PRESSED)
                                )
                                k.released.connect(
                                    partial(self._buttonhandler, k, RELEASED)
                                )
                                keydata["_QWidget"] = k
                                #
                                # Is there are multiple captions, create a QStackedWidget that overlays them all
                                ec = keydata.get("extracaptions", {})
                                if len(ec):
                                    # ecl = extra captions layout
                                    ecl = QStackedLayout()
                                    ecl.setStackingMode(QStackedLayout.StackAll)
                                    ecl.addWidget(k)
                                    for cssclass, txt in ec.items():
                                        ql = QLabel(txt)
                                        ql.setProperty("class", cssclass)
                                        ql.setAttribute(Qt.WA_TransparentForMouseEvents)
                                        ecl.addWidget(ql)
                                        kl.addLayout(ecl, stretch)
                                else:
                                    kl.addWidget(k, stretch)
                            #
                            # Oh... It's only a spacer....
                            if keydata.get("type", "key") == "spacer":
                                kl.addStretch(stretch)
                        grid.addLayout(kl, ri, ci)
                view["_QWidget"] = QWidget(
                    self
                )  # Create with self as parent, then reparent to prevent startup flicker
                view["_QWidget"].setLayout(grid)
                viewstack.addWidget(view["_QWidget"])
            kbd["_QWidget"] = QWidget(self)
            kbd["_QWidget"].setLayout(viewstack)
            kbdstack.addWidget(kbd["_QWidget"])
        # Apply layout to our root QWidget
        self.setLayout(kbdstack)

    def _releaseModifiers(self):
        if self._view:
            donestuff = False
            for modinfo in self._modifiers.values():
                if modinfo["state"] == 1:
                    donestuff = True
                    self._injectKeys(modinfo["keycode"], 0)
                    modinfo["state"] = 0
            if donestuff:
                self.updateKeyboard()

    def _fixStyleSheet(self, stylesheet, fontsize):
        if stylesheet == "":
            return stylesheet
        r = re.compile(r"font-size\s*:\s*(\d+)\%")
        i = r.finditer(stylesheet)
        for m in i:
            stylesheet = stylesheet.replace(
                m.group(0),
                "font-size: " + str(int((fontsize / 100) * int(m.group(1)))) + "px",
            )
        return stylesheet

    #
    # The part here is the low-level button handling. It takes care of calling _doAction() with PRESSED and RELEASED
    # with pointers to either the "single", "double" or "long" sub-dictionaries for that button, handling all the
    # nitty-gritty. Somewhat complex state-machine, maybe only touch when wide awake and concentrated.
    #

    def _oskbButtonHandler(self, button, direction):
        sng = button.data.get("single")
        dbl = button.data.get("double")
        lng = button.data.get("long")
        if direction == PRESSED:
            if self._doublebutton and self._doublebutton != button:
                # Another key was pressed within the doubleclick timeout, so we must
                # first process the previous key that was held back
                self._doAction(self._doublebutton.data.get("single"), PRESSED)
                self._doAction(self._doublebutton.data.get("single"), RELEASED)
                self._doublebutton = None
                self._doubletimer.stop()
            self._stopsinglepress = False
            if lng or dbl:
                if lng:
                    self._longtimer = QTimer()
                    self._longtimer.setSingleShot(True)
                    self._longtimer.timeout.connect(partial(self._longPress, lng))
                    self._longtimer.start(LONGPRESS_TIMEOUT)
                if dbl:
                    self._stopsinglepress = True
                    if self._doubletimer.isActive():
                        self._doubletimer.stop()
                        self._doAction(dbl, PRESSED)
                        self._doAction(dbl, RELEASED)
                        self._doublebutton = None
                    else:
                        self._doublebutton = button
                        self._doubletimer.start(DOUBLECLICK_TIMEOUT)
            else:
                self._doAction(sng, PRESSED)
        else:
            if not self._stopsinglepress:
                if self._longtimer.isActive():
                    self._longtimer.stop()
                    self._doAction(sng, PRESSED)
                    self._doAction(sng, RELEASED)
                else:
                    self._doAction(sng, RELEASED)
            self._stopsinglepress = False
            self._longtimer.stop()

    def _longPress(self, lng):
        self._doAction(lng, PRESSED)
        self._doAction(lng, RELEASED)
        self._stopsinglepress = True

    def _doubleTimeout(self):
        if not self._stopsinglepress:
            actiondict = self._doublebutton.data.get("single")
            self._doAction(actiondict, PRESSED)
            self._doAction(actiondict, RELEASED)
        self._doublebutton = None

    #
    # Higher level button handling: parses the actions from the action dictionary
    #

    def _doAction(self, actiondict, direction):
        for cmd, argdict in actiondict.items():

            if cmd == "send":
                keycode = argdict.get("keycode", "")
                keycodeplus = keycode
                keyname = argdict.get("name", "")
                printable = argdict.get("printable", True)

                for modname, mod in self._modifiers.items():
                    if mod.get("state") > 0:
                        keyname = modname + " " + keyname
                        keycodeplus = mod.get("keycode") + "+" + keycode
                        if not mod.get("printable"):
                            printable = False
                self._injectKeys(keycode, direction)
                if direction == RELEASED:
                    self._releaseModifiers()
                    if self._viewuntil and re.fullmatch(self._viewuntil, keyname):
                        self.setView(self._thenview)
                        self.viewuntil, self._thenview = None, None

            if cmd == "view" and direction == RELEASED:
                viewname = argdict.get("name", "default")
                self._viewuntil = argdict.get("until")
                self._thenview = argdict.get("thenview")
                self.setView(viewname)
                addclass = "oneview" if self._viewuntil else "view"
                self.setProperty("class", self._view.get("class", "") + addclass)
                self.updateKeyboard()

            if cmd == "modifier" and direction == RELEASED:
                keycode = argdict.get("keycode", "")
                modifier = argdict.get("name", "")
                printable = argdict.get("printable", True)
                modaction = argdict.get("action", "toggle")
                if modaction == "toggle":
                    m = self._modifiers.get(modifier)
                    if not m or m["state"] == 0:
                        self._modifiers[modifier] = {
                            "state": 1,
                            "keycode": keycode,
                            "printable": printable,
                        }
                        self._injectKeys(keycode, PRESSED)
                    else:
                        self._modifiers[modifier] = {
                            "state": 0,
                            "keycode": keycode,
                            "printable": printable,
                        }
                        self._injectKeys(keycode, RELEASED)
                if modaction == "lock":
                    self._modifiers[modifier] = {
                        "state": 2,
                        "keycode": keycode,
                        "printable": printable,
                    }
                    self._injectKeys(keycode, PRESSED)
                self.updateKeyboard()

            if cmd == "keyboard" and direction == RELEASED:
                kbdname = argdict.get("name", "")
                self.setKeyboard(kbdname)

    #
    # This is where the strings with keycodes to be pressed or released get turned into actual keypress
    # events. There's two levels here: "42+2;57" (in the US layout) means we're first pressing and then
    # releasing shift 2 (an exclamation point) and then a space.
    #

    def _injectKeys(self, keystr, direction):
        keylist = keystr.split(";")

        # If PRESSED, press and release all the ;-separated keycodes, releasing all but the last
        if direction == PRESSED:
            for keycodes in keylist:
                keycodelist = keycodes.split("+")
                for keycode in keycodelist:
                    self._sendKey(int(keycode), PRESSED)
                    if keycodes != keylist[-1]:
                        self._sendKey(int(keycode), RELEASED)

        # If RELEASED, only need to release the last (set of) keys
        if direction == RELEASED:
            keycodelist = keylist[-1].split("+")
            for keycode in reversed(keycodelist):
                self._sendKey(int(keycode), RELEASED)

    def _sendKey(self, keycode, keyevent):
        if self._sendkeysobject:
            self._sendkeysobject.receiveKeys(keycode, keyevent)


if __name__ == "__main__":
    main()
