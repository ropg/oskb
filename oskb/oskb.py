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

COLUMN_MARGIN = 0.1

# key detection timings in milliseconds
LONGPRESS_TIMEOUT = 350
DOUBLECLICK_TIMEOUT = 200

# The keyboard file format has its own version numbering
KEYBOARDFILE_VERSION = 1


class Keyboard(QWidget):
    def __init__(self):
        super().__init__()
        self._modifiers = {}
        self._flashmodifiers = True
        # This is all for the key-detection state-machine
        self._longpresswait = False
        self._longtimer = QTimer()
        self._stopsinglepress = False
        self._doublebutton = None
        self._doubletimer = QTimer()
        self._doubletimer.setSingleShot(True)
        self._doubletimer.timeout.connect(self._doubleTimeout)

        self._viewindex = None
        self._kbdname = None

        self._viewuntil = None
        self._thenview = None

        self._kbds = {}

        # Create the special 'chooser' keyboard that shows all the loaded keyboards
        self._kbds["_chooser"] = {
            "views": {"default": {"columns": [{"rows": []}]}},
        }

        # Create the special 'minimized' keyboard that shows one small button
        self._kbds["_minimized"] = {
            "style": "QWidget {background: transparent;}",
            "views": {
                "default": {
                    "columns": [
                        {"rows": [{"keys": [{"caption": "⌨", "single": {"keyboard": {"name": "back"}}}]}]}
                    ],
                }
            },
        }

        self._view = None
        self._viewname = "default"
        self._kbd = None
        self._sendkeys = None
        self._sendmapchanges = None
        self._sendscreenstate = None
        self._buttonhandler = self._oskbButtonHandler
        self._minimizerlocation = QRect(0, 0, 70, 70)

        self._kbdstack = QStackedLayout(self)

        self._stylesheet = pkg_resources.resource_string("oskb", "default.css").decode("utf-8")

    #
    # Reimplemented Qt methods
    #

    # Make sure show events also calculate proper sizes and first initialise if that hasn't happened yet.
    def showEvent(self, event):
        self.updateKeyboard()
        QWidget.showEvent(self, event)

    # Recalculate the fontsize and mrgaing and change the stylesheets when resizing
    def resizeEvent(self, event):
        QWidget.resizeEvent(self, event)
        if self._view and self.isVisible():
            self.updateKeyboard()

    # We just store the stylesheet, and then only do the super().setStyleSheet() when we've
    # recalculated values in updateKeyboard()
    def setStyleSheet(self, stylesheet):
        self._stylesheet = stylesheet

    #
    # Our own public
    #

    # specify callback that receives keymap information when user switches keyboards using _chooser
    def sendMapChanges(self, function):
        if callable(function):
            self._sendmapchanges = function
            return True
        return False

    def sendScreenState(self, function):
        if callable(function):
            self._sendscreenstate = function
            return True
        return False

    def sendKeys(self, function):
        if callable(function):
            self._sendkeys = function
            return True
        return False

    def setButtonHandler(self, handler=None):
        if not handler:
            handler = self._oskbButtonHandler
        self._buttonhandler = handler

    def setMinimizer(self, mx, my, mw, mh):
        self._minimizerlocation = QRect(mx, my, mw, mh)

    def setFlashModifiers(self, mode):
        self._flashmodifiers = mode

    def readKeyboard(self, kbdfile):
        kbd = None
        if os.access(kbdfile, os.R_OK):
            with open(kbdfile, "r", encoding="utf-8") as f:
                kbd = json.load(f)
        elif kbdfile == os.path.basename(kbdfile) and pkg_resources.resource_exists(
            "oskb", "keyboards/" + kbdfile
        ):
            kbd = json.loads(pkg_resources.resource_string("oskb", "keyboards/" + kbdfile))
        if not kbd:
            raise FileNotFoundError("Could not find " + kbdfile)
        if kbd.get("format") != "oskb keyboard":
            raise RuntimeError("Not an oskb keyboard file")
        if kbd.get("formatversion") > KEYBOARDFILE_VERSION:
            raise RuntimeError("oskb keyboard file for newer oskb version. You must upgrade.")
        kbdname = os.path.basename(kbdfile)
        self._kbds[kbdname] = kbd
        self._updateChooser()
        self.initKeyboards()
        return os.path.basename(kbdfile)

    def getView(self):
        return self._viewname

    def getViews(self):
        return self._kbd["views"].keys()

    def _updateChooser(self):
        if not self._kbds.get("_chooser"):
            return
        therows = self._kbds["_chooser"]["views"]["default"]["columns"][0]["rows"]
        therows.clear()
        for kbdname, kbd in self._kbds.items():
            if kbdname.startswith("_"):
                continue
            therows.append(
                {"keys": [{"caption": kbd.get("description"), "single": {"keyboard": {"name": kbdname}},}]}
            )

    def setKeyboard(self, kbdname=None):
        if self._sendscreenstate:
            self._sendscreenstate(kbdname != "_minimized")
        newgeometry = None
        if kbdname == "_minimized":
            newgeometry = self._minimizerlocation
        else:
            if kbdname == "back":
                kbdname = self._previouskeyboard
                if self._previousgeometry != self.geometry():
                    newgeometry = self._previousgeometry
        for n, k in self._kbds.items():
            if kbdname and kbdname != n:
                continue
            if not kbdname and n.startswith("_"):
                continue
            self._kbdname = n
            self._kbd = k
            # print("setKeybaord picked ", n)
            self._releaseModifiers()
            if self._sendmapchanges and k.get("keymap"):
                self._sendmapchanges(k.get("keymap"))
            if newgeometry:
                self.hide()
            if kbdname != "_minimized":
                self._previouskeyboard = n
            self._previousgeometry = self.geometry()
            self._kbdstack.setCurrentIndex(k.get("_stackindex", 0))
            if self._kbd["views"].get(self._viewname):
                self.setView(self._viewname, newgeometry)
            else:
                self.setView("default", newgeometry)
            return True
        return False

    def setView(self, viewname, newgeometry=None):
        # print ("setView", viewname)
        if self._kbd["views"].get(viewname):
            self._view = self._kbd["views"][viewname]
            self._viewname = viewname
            self._kbd["_QWidget"].layout().setCurrentIndex(self._view["_stackindex"])
            if newgeometry:
                self.setGeometry(newgeometry)
                self.show()
            else:
                self.updateKeyboard()
            return True
        return False

    def getRawKbds(self):
        return self._kbds

    #
    # initKeyboards sets up a QStackedLayout holding QWidgets for each keyboard, which in turn have a
    # QStackedlayout that holds a QWidget for each view within that keyboard. That has a QGridLayout with
    # QHboxLayouts in it that hold the individual key QPushButton widgets. It also sets the captions and
    # button actions for each key and figures out how many standard key widths and row vis there are in
    # all the views, which is used by updateKeyboard() to dynamically figure out how big the fonts, margins
    # and rounded corners need to be.
    #

    def initKeyboards(self):

        # Helper to return placeholder "empty row" widget
        def _makeEmptyRow(row):
            er = QPushButton(self)
            er.pressed.connect(partial(self._buttonhandler, er, PRESSED))
            er.released.connect(partial(self._buttonhandler, er, RELEASED))
            er.setMinimumSize(1, 1)
            er.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            er.setProperty("class", "emptyrow")
            row["_QWidget"] = er
            row["type"] = "emptyrow"
            er.data = row
            return er

        # Helper to return a QLayout to go in place of the QPushButton that contains it plus
        # any extra labels stacked on top
        def _makeCaptionLayout(k):
            extracaptions = k.data.get("extracaptions", None)
            if not extracaptions:
                return False
            # ecl = extra captions layout
            ecl = QStackedLayout()
            ecl.setStackingMode(QStackedLayout.StackAll)
            ecl.addWidget(k)
            for cssclass, txt in extracaptions.items():
                ql = QLabel(txt)
                ql.setProperty("class", cssclass)
                ql.setAttribute(Qt.WA_TransparentForMouseEvents)
                ecl.addWidget(ql)
            return ecl

        def _maxRowsInView(view):
            maxrows = 0
            for column in view.get("columns", []):
                maxrows = max(len(column.get("rows")), maxrows)
            return maxrows

        # This stores the width and height in standard key widths for each view.
        def _storeWidthsAndHeights(view):
            total_height = 0
            # Heights are only stored in first column
            column = view["columns"][0]
            for ri, row in enumerate(column.get("rows", [])):
                total_height += row.get("height", 1)
            total_width = 0
            for ci, column in enumerate(view.get("columns", [])):
                largest_width = 0
                for ri, row in reversed(list(enumerate(column.get("rows", [])))):
                    if len(row.get("keys", [])):
                        totalweight = 0
                        for keydata in row.get("keys", []):
                            w = keydata.get("width", 1)
                            totalweight += w
                        # Not counting frst row if there are widths already (reversed order)
                        if totalweight > largest_width and (ri != 0 or totalweight == 0):
                            largest_width = totalweight
                column["_widthInUnits"] = largest_width
                total_width += largest_width
            view["_widthInUnits"] = max(total_width, 1)
            view["_heightInUnits"] = max(total_height, 1)

        # Start of initKeyboards() itself

        if self._kbdstack.itemAt(0):
            self._clearLayout(self._kbdstack)
        ki = 0
        for kbdname, kbd in self._kbds.items():
            viewstack = QStackedLayout()
            vi = 0
            for viewname, view in kbd.get("views", {}).items():
                _storeWidthsAndHeights(view)
                grid = QGridLayout()
                grid.setSpacing(0)
                grid.setContentsMargins(0, 0, 0, 0)
                for ci, column in enumerate(view.get("columns", [])):
                    for ri in range(_maxRowsInView(view)):
                        if ri < len(column["rows"]):
                            row = column["rows"][ri]
                        else:
                            row = {"keys": []}
                            column["rows"].append(row)
                        keys = row.get("keys", [])
                        kl = QHBoxLayout()
                        kl.setContentsMargins(0, 0, 0, 0)
                        kl.setSpacing(0)
                        for keydata in keys:
                            stretch = keydata.get("width", 1) * 10
                            type = keydata.get("type", "key")
                            k = QPushButton(self)
                            k.setMinimumSize(1, 1)
                            keydata["_QWidget"] = k
                            keydata["_selected"] = False
                            k.data = keydata
                            k.pressed.connect(partial(self._buttonhandler, k, PRESSED))
                            k.released.connect(partial(self._buttonhandler, k, RELEASED))
                            k.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                            k.setMinimumSize(1, 1)
                            if type == "key":
                                k.setText(keydata.get("caption", ""))
                                # Multiple captions? Create a QStackedWidget overlays them all
                                ecl = _makeCaptionLayout(k)
                                if ecl:
                                    kl.addLayout(ecl, stretch)
                                else:
                                    kl.addWidget(k, stretch)
                            else:
                                kl.addWidget(k, stretch)
                        if not len(keys):
                            er = _makeEmptyRow(row)
                            kl.addWidget(er)
                        else:
                            row["_QWidget"] = None
                        grid.addLayout(kl, ri, ci * 2)
                        if ci == 0:
                            grid.setRowStretch(ri, row.get("height", 1) * 10)
                    grid.setColumnStretch(ci * 2, column.get("_widthInUnits", 1) * 10)
                    if ci > 0:
                        spacercolumn = QHBoxLayout()
                        spacercolumn.addWidget(QWidget(None))
                        grid.setColumnStretch((ci * 2) - 1, COLUMN_MARGIN * 10)
                        grid.addLayout(spacercolumn, 0, (ci * 2) - 1)
                # Create with self as parent, then reparent to prevent startup flicker
                view["_QWidget"] = QWidget(self)
                view["_QWidget"].setLayout(grid)
                viewstack.addWidget(view["_QWidget"])
                view["_stackindex"] = vi
                vi += 1
            kbd["_QWidget"] = QWidget(self)
            kbd["_stackindex"] = ki
            ki += 1
            kbd["_QWidget"].setLayout(viewstack)
            self._kbdstack.addWidget(kbd["_QWidget"])
        self.setKeyboard(self._kbdname)
        # Qt keeps coming up with minimum sizes that are way too wide
        # Some sane number will have to go in at some point, I guess
        self.setMaximumSize(16777215, 16777215)
        self.setMinimumSize(1, 1)

    def updateKeyboard(self):

        # Helper function to dynamically recalculate some sizes in stylesheets
        def fixStyle(stylesheet, fontsize, margin, radius):
            if stylesheet == "":
                return ""
            # Replace the main calculated values
            stylesheet = stylesheet.replace("_OSKB_FONTSIZE_", str(fontsize))
            stylesheet = stylesheet.replace("_OSKB_MARGIN_", str(margin))
            stylesheet = stylesheet.replace("_OSKB_RADIUS_", str(radius))
            # And then all the percentages based thereon (Qt5 doesn't do percentages in fontsizes)
            r = re.compile(r"font-size\s*:\s*(\d+)\%")
            i = r.finditer(stylesheet)
            for m in i:
                stylesheet = stylesheet.replace(
                    m.group(0), "font-size: " + str(int((fontsize / 100) * int(m.group(1)))) + "px",
                )
            return stylesheet

        if not self._view:
            return False
        # Calculate the font and margin sizes
        kw = self.width() / self._view["_widthInUnits"]
        kh = self.height() / self._view["_heightInUnits"]
        fontsize = min(max(int(min(kw / 1.5, kh / 2)), 5), 50)
        margin = int(fontsize / 15)
        radius = margin * 3
        # Dynamically change the default and keyboard stylesheets
        all_sheets = self._stylesheet + "\n\n" + self._kbd.get("style", "")
        super().setStyleSheet(fixStyle(all_sheets, fontsize, margin, radius))
        # Then adjust the stylesheets and class properties of all keys
        for ci, column in enumerate(self._view.get("columns", [])):
            for ri, row in enumerate(column.get("rows", [])):
                rowwidget = row.get("_QWidget")
                if rowwidget:
                    if row.get("_selected", False):
                        rowwidget.setProperty("class", "emptyrow selected")
                    else:
                        rowwidget.setProperty("class", "emptyrow")
                    # It needs .setStyleSheet(""), not .repaint() to show the changes
                    rowwidget.setStyleSheet("")
                else:
                    for keydata in row.get("keys", []):
                        k = keydata.get("_QWidget")
                        type = keydata.get("type", "key")
                        classes = [type]
                        classes.append(keydata.get("class", ""))
                        if keydata.get("single") and keydata["single"].get("modifier"):
                            modname = keydata["single"]["modifier"].get("name", "")
                            moddata = self._modifiers.get(modname, {})
                            modstate = moddata.get("state")
                            if modstate == 1:
                                classes.append("held")
                            elif modstate == 2:
                                classes.append("locked")
                            else:
                                classes.append("modifier")
                        if keydata.get("_selected", False):
                            classes.append("selected")
                        classes.append("view_" + self._viewname)
                        classes.append("row" + str(ri + 1))
                        classes.append("col" + str(ci + 1))
                        k.setProperty("class", " ".join(classes).strip())
                        keystyle = keydata.get("style", "")
                        k.setStyleSheet(fixStyle(keystyle, fontsize, margin, radius))


    #
    # The part here is the low-level button handling. It takes care of calling _doAction() with PRESSED and
    # RELEASED with pointers to either the "single", "double" or "long" sub-dictionaries for that button,
    # handling all the nitty-gritty. Bit involved.., Maybe only touch when wide awake and concentrated.
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
        self._stopsinglepress = True
        self._doAction(lng, PRESSED)
        self._doAction(lng, RELEASED)

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
        if not actiondict:
            return
        for cmd, argdict in actiondict.items():
            if not argdict:
                continue

            if cmd == "send":
                keycode = argdict.get("keycode", "")
                keycodeplus = keycode
                keyname = argdict.get("name", "")
                printable = argdict.get("printable", True)

                for modname, mod in self._modifiers.items():
                    if mod.get("state") > 0:
                        keyname = modname + " " + keyname
                        modkeycode = mod.get("keycode")
                        keycodeplus = modkeycode + "+" + keycode
                        if not mod.get("printable"):
                            printable = False
                        if direction == PRESSED and self._flashmodifiers:
                            self._injectKeys(modkeycode, PRESSED)
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
                m = self._modifiers.get(modifier)
                if modaction == "toggle":
                    if not m or m["state"] == 0:
                        self._modifiers[modifier] = {
                            "state": 1,
                            "keycode": keycode,
                            "printable": printable,
                        }
                        if not self._flashmodifiers:
                            self._injectKeys(keycode, PRESSED)
                    else:
                        self._modifiers[modifier] = {
                            "state": 0,
                            "keycode": keycode,
                            "printable": printable,
                        }
                        if not self._flashmodifiers:
                            self._injectKeys(keycode, RELEASED)
                if modaction == "lock":
                    if not m:
                        self._modifiers[modifier] = {}
                    s = self._modifiers[modifier].get("state", 0)
                    self._modifiers[modifier] = {
                        "state": 0 if s == 2 else 2,
                        "keycode": keycode,
                        "printable": printable,
                    }
                    if not self._flashmodifiers:
                        self._injectKeys(keycode, PRESSED if s == 0 else RELEASED)
                self.updateKeyboard()

            if cmd == "keyboard" and direction == RELEASED:
                kbdname = argdict.get("name", "")
                self.setKeyboard(kbdname)

    # This is where the strings with keycodes to be pressed or released get turned into actual keypress
    # events. There's two levels here: "42+2;57" (in the US layout) means we're first pressing and then
    # releasing shift 2 (an exclamation point) and then a space.

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
        if self._sendkeys:
            self._sendkeys(keycode, keyevent)

    def _releaseModifiers(self):
        if self._view:
            donestuff = False
            for modinfo in self._modifiers.values():
                if modinfo["state"] == 1:
                    donestuff = True
                    if not self._flashmodifiers:
                        self._injectKeys(modinfo["keycode"], RELEASED)
                    modinfo["state"] = 0
                if self._flashmodifiers:
                    self._injectKeys(modinfo["keycode"], RELEASED)
            if donestuff:
                self.updateKeyboard()

    # Helper

    def _clearLayout(self, layout):
        if layout != None:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget() is not None:
                    child.widget().deleteLater()
                elif child.layout() is not None:
                    self._clearLayout(child.layout())


# oskbCopy() copies an oskb data structure (a dict with sub-dicts and sub-lists). If you specify two
# variables it will move from one to the other without breaking the reference. If you specify just one,
# it will return a new copy.

def oskbCopy(f, t=None):
    if t == None:
        t = {}
    t.clear()
    if type(f) == dict:
        for fk, fv in f.items():
            if fv != {} and fv != "" and not fk.startswith("_"):
                if type(fv) == list or type(fv) == dict:
                    t[fk] = oskbCopy(fv)
                else:
                    t[fk] = fv
    elif type(f) == list:
        t = []
        for fi, fv in enumerate(f):
            t.append(oskbCopy(fv))
    return t


if __name__ == "__main__":
    main()
