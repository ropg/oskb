import sys, os, json, re, pkg_resources, argparse
from functools import partial
from PyQt5.QtCore import (
    QTimer,
    QRect,
    QSysInfo,
    QEvent,
    QSize,
    Qt,
    QMetaObject,
)
from PyQt5.QtGui import (
    QIcon,
    QFont,
    QGuiApplication,
)
from PyQt5.QtWidgets import (
    QAction,
    QActionGroup,
    QApplication,
    QCheckBox,
    QComboBox,
    QDesktopWidget,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLayout,
    QLineEdit,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedLayout,
    QStyle,
    QStyleFactory,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
import oskb
from oskb.ui_keywizard import Ui_KeyWizard
from oskb.ui_editkey import Ui_EditKey
from oskb.ui_keyactions import Ui_KeyActions
from oskb.ui_editcss import Ui_EditCSS
from oskb.ui_valueedit import Ui_ValueEdit

if sys.platform.startswith("linux"):
    import getpass, evdev

DOUBLECLICK_TIMEOUT = 350
MAX_UNDO = 10


def main():
    # A few things are global because the alternative is passing them around
    global g_cmdline, g_kbdinput, g_oskbwidget
    # Parse the command line arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", "-i", help="input device for key wizard", metavar="<dev>")
    ap.add_argument("--inputlist", help="list input devices and exit", action="store_true")
    ap.add_argument("keyboard", help="a keyboard file", metavar="<kbd>", nargs="?")
    g_cmdline = ap.parse_args()
    # Handle --inputlist and create g_kbdinput InputDevice if --input is specified
    g_kbdinput = None
    if g_cmdline.inputlist or g_cmdline.input:
        if sys.platform.startswith("linux"):
            worked = True
            if g_cmdline.inputlist:
                devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
                if devices != []:
                    for device in devices:
                        print(device.path + ":", device.name, device.phys)
                    sys.exit(0)
                else:
                    worked = False
            elif g_cmdline.input:
                try:
                    g_kbdinput = evdev.InputDevice(g_cmdline.input)
                except:
                    worked = False

            if not worked:
                user = getpass.getuser()
                sys.stderr.write(
                    "Do you have permission to read the input devices?\n\n"
                    "Try 'sudo setfacl -m m::rw -m u:" + user + ":rw /dev/input/*'\n"
                    "See the oskb documentation for more information.\n"
                )
                sys.exit(-1)
        else:
            sys.stderr.write("You cannot use the key wizard on this OS, that is Linux-only")
            sys.exit(-1)
    # Start the Qt magic
    app = QApplication([])
    window = OskbEdit()
    sys.exit(app.exec_())


class OskbEdit(QWidget):
    def __init__(self):
        super().__init__()
        # Some variables need initialising
        self._doubletimer = QTimer()
        self._doubletimer.setSingleShot(True)
        self._mode = "edit"
        self._changed = False
        self._lastclicked = None
        self._copypaste = []
        # Size window at half width and third of height of screen, positioned in the middle
        av_height = QDesktopWidget().availableGeometry(self).size().height()
        av_width = QDesktopWidget().availableGeometry(self).size().width()
        self.setGeometry(
            QStyle.alignedRect(
                Qt.LeftToRight,
                Qt.AlignCenter,
                QSize(int(av_width / 2), int(av_height / 3)),
                QDesktopWidget().availableGeometry(self),
            )
        )
        # Get a keyboard widget instance and set it up a tiny bit
        global g_oskbwidget
        g_oskbwidget = oskb.Keyboard()
        g_oskbwidget.setButtonHandler(self._buttonHandler)
        g_oskbwidget.setStyleSheet(pkg_resources.resource_string("oskb", "oskbedit.css").decode("utf-8"))
        # Set up elements on the screen, must be done before _loadFile()
        layout = QVBoxLayout(self)
        frame = QWidget()
        self._kbdlayout = QHBoxLayout()
        frame.setLayout(self._kbdlayout)
        self._kbdlayout.addWidget(g_oskbwidget)
        layout.addWidget(frame)
        self.setWindowTitle("oskbedit")
        layout.addWidget(frame)
        self._menu = QMenuBar()
        self._menu.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.layout().setMenuBar(self._menu)
        self.show()
        # Load the file from the command line, or the blank keyboard if none specified
        if g_cmdline.keyboard:
            if not self._loadFile(g_cmdline.keyboard):
                sys.exit(-1)
        else:
            self._loadFile("_new")

    def _fixMenu(self):
        self._menu.clear()
        self._menu_file()
        self._menu_edit()
        self._menu_insert()
        self._menu_view()

    #
    # "File" menu
    #

    def _menu_file(self):
        filemenu = self._menu.addMenu("&File")
        newitem = filemenu.addAction("&New")
        newitem.setShortcut("Ctrl+N")
        newitem.triggered.connect(partial(self._loadFile, "_new"))
        loaditem = filemenu.addAction("&Open file")
        loaditem.triggered.connect(self._file_open)
        loaditem.setShortcut("Ctrl+O")
        builtinmenu = filemenu.addMenu("open &Builtin")
        for k in pkg_resources.resource_listdir("oskb", "keyboards"):
            if not k.startswith("_"):
                builtinitem = QAction(k, self)
                builtinitem.triggered.connect(partial(self._loadFile, k))
                builtinmenu.addAction(builtinitem)
        saveitem = filemenu.addAction("&Save")
        if not self._savefilename or not self._changed:
            saveitem.setEnabled(False)
        else:
            saveitem.triggered.connect(partial(self._saveFile, self._savefilename))
            saveitem.setShortcut("Ctrl+S")
        saveasitem = filemenu.addAction("Save &As")
        if self._changed:
            saveasitem.triggered.connect(self._file_save_as)
            if not self._savefilename:
                saveasitem.setShortcut("Ctrl+S")
        else:
            saveasitem.setEnabled(False)
        filemenu.addSeparator()
        exitButton = QAction("&Quit", self)
        exitButton.setShortcut("Ctrl+Q")
        exitButton.setStatusTip("Exit application")
        exitButton.triggered.connect(self.close)
        filemenu.addAction(exitButton)

    def _file_open(self):
        if self._changed and not self._areyousure():
            return
        self._changed = False
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setViewMode(QFileDialog.Detail)
        if dialog.exec_():
            self._loadFile(*dialog.selectedFiles())

    def _loadFile(self, f):
        if self._changed and not self._areyousure():
            return False
        if os.path.isfile(f):
            self._savefilename = f
        else:
            self._savefilename = None
        try:
            self._kbdname = g_oskbwidget.readKeyboard(f)
        except:
            QMessageBox.warning(
                self,
                "read failed",
                "File read failed: " + str(sys.exc_info()[1]),
                QMessageBox.Ok,
                QMessageBox.Ok,
            )
            return False
        g_oskbwidget.setKeyboard(self._kbdname)
        self._changed = False
        self._kbds = g_oskbwidget.getRawKbds()
        try:
            del self._kbds["_minimized"]
            del self._kbds["_chooser"]
        except:
            pass
        self._kbd = self._kbds[self._kbdname]
        self._viewname = g_oskbwidget.getView()
        self._view = self._kbd["views"][self._viewname]
        g_oskbwidget.updateKeyboard()
        g_oskbwidget.show()
        self._undo = []
        self._redo = []
        self._previouskbd = oskb.oskbCopy(self._kbd)
        self._stir()
        return True

    def _areyousure(self):
        if (
            QMessageBox.warning(
                self,
                "Almost losing changes",
                "You have made changes, are you sure you want to do this? Hit 'No' and save if not.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            == QMessageBox.Yes
        ):
            return True
        else:
            return False

    def _file_save_as(self):
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setViewMode(QFileDialog.Detail)
        if dialog.exec_():
            filenames = dialog.selectedFiles()
            self._saveFile(*filenames)

    def _saveFile(self, f):
        savecopy = oskb.oskbCopy(self._kbd)
        with open(f, "w") as outfile:
            json.dump(savecopy, outfile, ensure_ascii=False, indent=4)
        self._changed = False

    def closeEvent(self, event):
        if self._changed and not self._areyousure():
            event.ignore()
            return
        event.accept()

    #
    # "Edit" menu
    #

    def _menu_edit(self):
        selrows, selkeys = self._surveySelected()
        sel = selrows + selkeys
        editmenu = self._menu.addMenu("&Edit")
        if len(self._undo):
            undoitem = QAction("&Undo " + self._undo[0][0], self)
            undoitem.triggered.connect(self._edit_undo)
        else:
            undoitem = QAction("&Undo", self)
            undoitem.setEnabled(False)
        undoitem.setShortcut("Ctrl+Z")
        editmenu.addAction(undoitem)
        if len(self._redo):
            redoitem = QAction("&Redo " + self._redo[0][0], self)
            redoitem.triggered.connect(self._edit_redo)
        else:
            redoitem = QAction("Redo", self)
            redoitem.setEnabled(False)
        redoitem.setShortcut("Shift+Ctrl+Z")
        editmenu.addAction(redoitem)
        editmenu.addSeparator()
        cutitem = QAction("Cut", self)
        cutitem.setShortcut("Ctrl+X")
        cutitem.triggered.connect(self._edit_cut)
        cutitem.setEnabled(selkeys > 0 and selrows == 0)
        editmenu.addAction(cutitem)
        copyitem = QAction("Copy", self)
        copyitem.setShortcut("Ctrl+C")
        copyitem.triggered.connect(self._edit_copy)
        copyitem.setEnabled(selkeys > 0 and selrows == 0)
        editmenu.addAction(copyitem)
        pasteafteritem = QAction("&Paste", self)
        pasteafteritem.setShortcut("Ctrl+V")
        if not self._copypaste or sel == 0 or (selrows > 0 and selkeys > 0) or selrows > 1:
            pasteafteritem.setEnabled(False)
        else:
            if selkeys > 0:
                pasteafteritem.triggered.connect(partial(self._edit_paste, self._lastSelKey(), 1))
                editmenu.addAction(pasteafteritem)

                pastebeforeitem = QAction("Paste &Before Selected", self)
                pastebeforeitem.triggered.connect(partial(self._edit_paste, self._firstSelKey()))
                editmenu.addAction(pastebeforeitem)
            elif selrows == 1:
                pasteafteritem.triggered.connect(partial(self._edit_paste, self._firstSelRow()))
        editmenu.addAction(pasteafteritem)
        deleteitem = QAction("&Delete", self)
        deleteitem.setShortcut("Del")
        deleteitem.triggered.connect(self._edit_delete)
        deleteitem.setEnabled(sel > 0)
        editmenu.addAction(deleteitem)
        deleterowitem = QAction("Delete &Row", self)
        deleterowitem.triggered.connect(partial(self._edit_delete_row, self._firstSel()))
        deleterowitem.setEnabled(sel == 1)
        editmenu.addAction(deleterowitem)
        deletecolumnitem = QAction("Delete &Column", self)
        deletecolumnitem.triggered.connect(partial(self._edit_delete_column, self._firstSel()))
        deletecolumnitem.setEnabled(sel == 1)
        editmenu.addAction(deletecolumnitem)
        editmenu.addSeparator()
        editkeyitem = QAction("Edit &Key/Spacer", self)
        if sel != 1 or selrows > 0:
            editkeyitem.setEnabled(False)
        else:
            w = self._firstSelWidget()
            if w.data.get("type", "key") == "key":
                editkeyitem.triggered.connect(partial(self._edit_key, w))
            elif w.data.get("type", "key") == "spacer":
                editkeyitem.triggered.connect(partial(self._edit_spacer, w))
        editmenu.addAction(editkeyitem)
        editrowitem = QAction("Edit &Row", self)
        if sel != 1:
            editrowitem.setEnabled(False)
        else:
            if selkeys == 1:
                _, ri, _ = self._firstSelKey()
            else:
                _, ri, _ = self._firstSelRow()
            # heights are only stored in first column
            editrowitem.triggered.connect(partial(self._edit_row, ri))
        editmenu.addAction(editrowitem)
        cssitem = QAction("&Edit Keyboard CSS", self)
        cssitem.triggered.connect(self._edit_css)
        editmenu.addAction(cssitem)

    def _edit_undo(self):
        actionname, actionview, kbd = self._undo.pop(0)
        self._redo.insert(0, (actionname, self._viewname, oskb.oskbCopy(self._kbd)))
        oskb.oskbCopy(kbd, self._kbd)
        self._stir()

    def _edit_redo(self):
        actionname, actionview, kbd = self._redo.pop(0)
        self._undo.insert(0, (actionname, self._viewname, oskb.oskbCopy(self._kbd)))
        oskb.oskbCopy(kbd, self._kbd)
        self._stir()

    def _edit_delete(self):
        self._copyCut(True)
        self._stir("Delete")

    def _edit_delete_row(self, tuple):
        if len(self._view["columns"][0]["rows"]) == 1:
            QMessageBox.warning(self, "Delete", "You cannot delete the last row", QMessageBox.Ok)
            return
        _, ri, _ = tuple
        for ci, column in enumerate(self._view.get("columns", [])):
            column["rows"].pop(ri)
        self._stir("Delete Row")

    def _edit_delete_column(self, tuple):
        if len(self._view["columns"]) == 1:
            QMessageBox.warning(self, "Delete", "You cannot delete the last column", QMessageBox.Ok)
            return
        ci, _, _ = tuple
        self._view["columns"].pop(ci)
        self._stir("Delete Column")

    def _edit_copy(self):
        self._copypaste = self._copyCut(False)

    def _edit_cut(self):
        self._copypaste = self._copyCut(True)
        self._stir("Cut")

    def _edit_paste(self, tuple, after=0):
        ci, ri, ki = tuple
        for ins in self._copypaste:
            self._view["columns"][ci]["rows"][ri]["keys"].insert(ki + after, oskb.oskbCopy(ins))
        self._stir("Paste")

    def _copyCut(self, cut=False):
        buffer = []
        for ci, ri, ki, keydata in self._reverseIterateKeys():
            if keydata.get("_selected", False):
                buffer.append(oskb.oskbCopy(keydata))
                if cut:
                    del self._view["columns"][ci]["rows"][ri]["keys"][ki]
        return buffer

    def _edit_css(self):
        if EditCSS(self._kbd).exec():
            self._stir("Edit CSS")

    def _edit_spacer(self, widget):
        if ValueEdit(widget.data, "width", 0.5).exec():
            self._stir("Edit Spacer")

    def _edit_row(self, ri):
        dict = self._view["columns"][0]["rows"][ri]
        if ValueEdit(dict, "height").exec():
            self._stir("Edit Row")

    def _edit_key(self, widget):
        if EditKey(widget).exec():
            self._stir("Edit Key")

    #
    # "Insert" menu
    #

    def _menu_insert(self):
        selrows, selkeys = self._surveySelected()
        sel = selrows + selkeys
        keymenu = self._menu.addMenu("&Insert")
        insertkmenu = keymenu.addMenu("&Key")
        insertsmenu = keymenu.addMenu("&Spacer")
        if sel == 0 or (selrows > 0 and selkeys > 0) or selrows > 1:
            insertkmenu.setEnabled(False)
            insertsmenu.setEnabled(False)
        elif selkeys > 0:
            addkbefore = QAction("&Before Selected", self)
            addkbefore.triggered.connect(partial(self._insert_key, self._firstSelKey()))
            insertkmenu.addAction(addkbefore)
            addkafter = QAction("&After Selected", self)
            addkafter.triggered.connect(partial(self._insert_key, self._lastSelKey(), 1))
            addkafter.setShortcut("Ctrl+K")
            insertkmenu.addAction(addkafter)
            addsbefore = QAction("&Before Selected", self)
            addsbefore.triggered.connect(partial(self._insert_spacer, self._firstSelKey()))
            insertsmenu.addAction(addsbefore)
            addsafter = QAction("&After Selected", self)
            addsafter.triggered.connect(partial(self._insert_spacer, self._lastSelKey(), 1))
            insertsmenu.addAction(addsafter)
        elif selrows == 1:
            addkon = QAction("&On Selected Row", self)
            addkon.triggered.connect(partial(self._insert_key, self._firstSelRow()))
            addkon.setShortcut("Ctrl+K")
            insertkmenu.addAction(addkon)
            addson = QAction("&On Selected Row", self)
            addson.triggered.connect(partial(self._insert_spacer, self._firstSelRow()))
            insertsmenu.addAction(addson)
        insertrmenu = keymenu.addMenu("&Row")
        insertcmenu = keymenu.addMenu("&Column")
        if sel != 1:
            insertrmenu.setEnabled(False)
            insertcmenu.setEnabled(False)
        else:
            curpos = self._firstSel()
            addrbefore = QAction("&Before Selected", self)
            addrbefore.triggered.connect(partial(self._insert_row, curpos))
            insertrmenu.addAction(addrbefore)
            addrafter = QAction("&After Selected", self)
            addrafter.triggered.connect(partial(self._insert_row, curpos, 1))
            insertrmenu.addAction(addrafter)
            addcbefore = QAction("&Before Selected", self)
            addcbefore.triggered.connect(partial(self._insert_column, curpos))
            insertcmenu.addAction(addcbefore)
            addcafter = QAction("&After Selected", self)
            addcafter.triggered.connect(partial(self._insert_column, curpos, 1))
            insertcmenu.addAction(addcafter)

    def _insert_key(self, tuple, after=0):
        ci, ri, ki = tuple
        k = {"type": "key"}
        rowkeys = self._view["columns"][ci]["rows"][ri]["keys"]
        rowkeys.insert(ki + after, k)
        wiz = None
        if g_kbdinput:
            wiz = KeyWizard()
            if wiz.exec():
                k["caption"] = wiz.caption
                k["single"] = {"send": {}}
                k["single"]["send"]["name"] = wiz.keyname
                k["single"]["send"]["keycode"] = wiz.keycode
                if not wiz.printable:
                    k["single"]["send"]["printable"] = False
            else:
                wiz = None
        if not wiz:
            g_oskbwidget.initKeyboards()
            self._edit_key(rowkeys[ki + after]["_QWidget"])
        self._stir("Insert Key")
        self._selectState(False)
        self._selectState(True, rowkeys[ki + after]["_QWidget"])
        g_oskbwidget.updateKeyboard()
        self._fixMenu()

    def _insert_spacer(self, tuple, after=0):
        ci, ri, ki = tuple
        rowkeys = self._view["columns"][ci]["rows"][ri]["keys"]
        rowkeys.insert(ki + after, {"type": "spacer", "width": 0.5})
        self._stir("Insert Spacer")
        self._selectState(False)
        self._selectState(True, rowkeys[ki + after]["_QWidget"])
        g_oskbwidget.updateKeyboard()
        self._fixMenu()

    def _insert_row(self, tuple, after=0):
        _, ri, _ = tuple
        for ci, column in enumerate(self._view.get("columns", [])):
            column["rows"].insert(ri + after, {"keys": []})
        self._stir("Insert Row")

    def _insert_column(self, tuple, after=0):
        ci, _, _ = tuple
        self._view["columns"].insert(ci + after, {"rows": [{"keys": []}]})
        self._stir("Insert Column")

    #
    # "View" menu
    #

    def _menu_view(self):
        viewmenu = self._menu.addMenu("&View")
        mag = QActionGroup(self)
        editmodeitem = QAction("&Edit mode", self)
        editmodeitem.triggered.connect(self._view_editmode)
        editmodeitem.setCheckable(True)
        editmodeitem.setChecked(self._mode == "edit")
        editmodeitem.setShortcut("Ctrl+E")
        viewmenu.addAction(editmodeitem)
        mag.addAction(editmodeitem)
        testmodeitem = QAction("&Test mode", self)
        testmodeitem.triggered.connect(self._view_testmode)
        testmodeitem.setCheckable(True)
        testmodeitem.setChecked(self._mode == "test")
        testmodeitem.setShortcut("Ctrl+T")
        viewmenu.addAction(testmodeitem)
        mag.addAction(testmodeitem)
        if self._mode == "edit":
            viewmenu.addSeparator()
            vag = QActionGroup(self)
            for vn, v in self._kbd["views"].items():
                va = QAction(vn, vag)
                va.setCheckable(True)
                if v == self._view:
                    va.setChecked(True)
                va.triggered.connect(partial(self._view_switch, vn))
                viewmenu.addAction(va)
            viewmenu.addSeparator()
        addviewitem = QAction("&Add New View", self)
        addviewitem.triggered.connect(self._view_add)
        viewmenu.addAction(addviewitem)
        delviewitem = QAction("&Delete Current View", self)
        delviewitem.triggered.connect(self._view_delete)
        viewmenu.addAction(delviewitem)

    def _view_editmode(self):
        self._mode = "edit"
        self._view_switch(g_oskbwidget.getView())
        g_oskbwidget.setButtonHandler(self._buttonHandler)
        self._stir()

    def _view_testmode(self):
        self._mode = "test"
        self._selectState(False)
        g_oskbwidget.setButtonHandler()
        self._stir()

    def _view_switch(self, viewname):
        g_oskbwidget.setView(viewname)
        self._view = self._kbd["views"][viewname]
        self._viewname = viewname
        self._fixMenu()

    def _view_delete(self):
        delview = g_oskbwidget.getView()
        if delview == "default":
            QMessageBox.warning(self, "New View", "Cannot delete 'default' view", QMessageBox.Ok)
            return
        self._view_switch("default")
        del self._kbd["views"][delview]
        self._stir("Delete View")

    def _view_add(self):
        while True:
            viewname, result = QInputDialog.getText(self, "New View", "Name:")
            if not result:
                break
            if not re.fullmatch("[a-z_]+", viewname):
                QMessageBox.warning(
                    self,
                    "New View",
                    "View name can only contain lower case letters and underscores",
                    QMessageBox.Ok,
                )
                continue
            if self._kbd["views"].get(viewname):
                QMessageBox.warning(self, "New View", "View " + viewname + " already exists", QMessageBox.Ok)
                continue
            self._kbd["views"][viewname] = {"columns": [{"rows": [{"keys": []}]}]}
            self._stir("Add View")
            self._view_switch(viewname)
            self._fixMenu()
            break

    #
    # Button Handler
    #

    def _buttonHandler(self, widget, direction):
        if direction == oskb.PRESSED:
            # Read only once, is not state now but of last click event
            mod = QGuiApplication.keyboardModifiers()
            if mod & Qt.ControlModifier:
                self._selectState(not widget.data.get("_selected", False), widget)
            elif mod & Qt.ShiftModifier:
                if self._lastclicked:
                    if widget.data.get("type") == "emptyrow":
                        return
                    selecting = False
                    for ci, ri, ki, keydata in self._iterateKeys():
                        thisone = keydata["_QWidget"]
                        if thisone == self._lastclicked:
                            selecting = not selecting
                        if thisone == widget:
                            selecting = not selecting
                        if selecting or thisone == widget:
                            self._selectState(True, thisone)
            else:
                if self._doubletimer.isActive():
                    self._doubleClick(widget)
                else:
                    self._doubletimer.start(DOUBLECLICK_TIMEOUT)
                    self._selectState(False)
                    self._selectState(True, widget)
        if widget.data.get("type") == "emptyrow":
            self._lastclicked = None
        else:
            self._lastclicked = widget
        g_oskbwidget.updateKeyboard()
        self._fixMenu()

    def _doubleClick(self, widget):
        if widget.data.get("type") == "spacer":
            self._edit_spacer(widget)
        elif widget.data.get("type", "key") == "key":
            self._edit_key(widget)

    #
    # Various functions
    #

    # Redoes the keyboard. When called with an actionname string, it will store an undo state.
    def _stir(self, actionname=None):
        if actionname:
            self._changed = True
            self._undo.insert(0, (actionname, self._viewname[:], oskb.oskbCopy(self._previouskbd)))
            self._previouskbd = oskb.oskbCopy(self._kbd)
            while len(self._undo) > MAX_UNDO:
                self._undo.pop(len(self._undo) - 1)
            self._redo = []
        g_oskbwidget.initKeyboards()
        # g_oskbwidget.updateKeyboard()
        self._view_switch(g_oskbwidget.getView())
        self._fixMenu()

    def _listViews(self):
        viewlist = []
        for view in self._kbd["views"]:
            viewlist.append(view["name"])
        return viewlist

    # Calling without widget selects or deselects everything
    def _selectState(self, newstate, widget=None):
        for _, _, row in self._iterateRows():
            if row.get("_QWidget"):
                if not widget or row.get("_QWidget") == widget:
                    row["_selected"] = newstate
        for _, _, _, keydata in self._iterateKeys():
            if not widget or widget == keydata.get("_QWidget"):
                keydata["_selected"] = newstate

    def _surveySelected(self):
        selrows, selkeys = 0, 0
        for _, _, row in self._iterateRows():
            if row.get("_QWidget") and row.get("_selected"):
                selrows += 1
        for _, _, _, keydata in self._iterateKeys():
            if keydata.get("_selected"):
                selkeys += 1
        return selrows, selkeys

    def _firstSelWidget(self):
        for ci, ri, ki, keydata in self._iterateKeys():
            if keydata.get("_selected"):
                return keydata.get("_QWidget")

    def _firstSelKey(self):
        for ci, ri, ki, keydata in self._iterateKeys():
            if keydata.get("_selected"):
                return (ci, ri, ki)

    def _lastSelKey(self):
        for ci, ri, ki, keydata in self._reverseIterateKeys():
            if keydata.get("_selected"):
                return (ci, ri, ki)

    def _firstSelRow(self):
        for ci, ri, row in self._iterateRows():
            if row.get("_QWidget") and row.get("_selected"):
                return (ci, ri, 0)

    def _firstSel(self):
        p = self._firstSelKey()
        if p:
            return p
        return self._firstSelRow()

    def _iterateKeys(self):
        for ci, column in enumerate(self._view.get("columns", [])):
            for ri, row in enumerate(column.get("rows", [])):
                for ki, keydata in enumerate(row.get("keys", [])):
                    yield ci, ri, ki, keydata

    def _reverseIterateKeys(self):
        for ci, column in reversed(list(enumerate(self._view.get("columns", [])))):
            for ri, row in reversed(list(enumerate(column.get("rows", [])))):
                for ki, keydata in reversed(list(enumerate(row.get("keys", [])))):
                    yield ci, ri, ki, keydata

    def _iterateRows(self):
        for ci, column in enumerate(self._view.get("columns", [])):
            for ri, row in enumerate(column.get("rows", [])):
                yield ci, ri, row


#
# Other windows and widgets.
#


class KeyWizard(QDialog):
    def __init__(self):
        super().__init__()
        self.ui = Ui_KeyWizard()
        self.ui.setupUi(self)
        self.ui.lineEdit.setFocus()
        self.show()
        QTimer.singleShot(20, self.get_key)

    def get_key(self):
        # Wait for all keys to be released, and then a key to be pressed
        while g_kbdinput.active_keys() != []:
            pass
        while g_kbdinput.active_keys() == []:
            pass
        pressed = []
        while True:
            active = g_kbdinput.active_keys()
            if active == []:
                break
            for k in active:
                if not k in pressed:
                    pressed.append(k)
        result = ""
        for k in pressed:
            result += "+" + str(k)
        self.keycode = result[1:]
        QTimer.singleShot(20, partial(self.got_key, pressed))

    def got_key(self, pressed):
        caption = self.ui.lineEdit.text()
        if caption == "":
            captions = []
            for k in pressed:
                if type(k) == "list":
                    c = evdev.ecodes.KEY[k][0]
                else:
                    c = evdev.ecodes.KEY[k]
                c = c.replace("KEY_", "")
                c = c[4:] if c.startswith("LEFT") and len(c) > 4 else c
                c = c.lower()

                captions.append(c)
            self.keyname = "+".join(captions)
            self.printable = False
        else:
            self.printable = True
            self.keyname = caption
        self.caption = caption
        self.accept()


class EditCSS(QDialog):
    def __init__(self, kbd):
        super().__init__()
        self.ui = Ui_EditCSS()
        self.ui.setupUi(self)
        self._kbd = kbd
        self.ui.defaultcss.setPlainText(pkg_resources.resource_string("oskb", "default.css").decode("utf-8"))
        self.ui.keyboardcss.setPlainText(self._kbd.get("style", ""))

    def accept(self):
        self._kbd["style"] = self.ui.keyboardcss.toPlainText()
        super().accept()


class ValueEdit(QDialog):
    def __init__(self, dict, valkey, default=1):
        super().__init__()
        self.ui = Ui_ValueEdit()
        self.ui.setupUi(self)
        self._dict = dict
        self._valkey = valkey
        self._backup = dict.get(valkey, default)
        self.ui.doubleSpinBox.setProperty("value", self._backup)
        self.ui.label.setText(valkey.capitalize() + ":")
        self.ui.doubleSpinBox.valueChanged.connect(self._tryItOut)
        self.setStyleSheet("QDoubleSpinBox { border: 1px solid #bcbebf; }")

    def _tryItOut(self):
        self._dict[self._valkey] = round(self.ui.doubleSpinBox.value(), 1)
        g_oskbwidget.initKeyboards()
        g_oskbwidget.updateKeyboard()

    def reject(self):
        self._dict[self._valkey] = self._backup
        g_oskbwidget.initKeyboards()
        g_oskbwidget.updateKeyboard()
        super().reject()


class EditKey(QDialog):
    def __init__(self, widget):
        super().__init__()
        self._backup = oskb.oskbCopy(widget.data)
        self._d = widget.data
        self.ui = Ui_EditKey()
        self.ui.setupUi(self)
        self.setStyleSheet(
            "QLineEdit, QDoubleSpinBox { border: 1px solid #bcbebf; } QComboBox { padding-left: 5px; }"
        )
        # Put in the KeyAction widgets for the three types of keypress
        self.ui.keyactionwidgets = [None, None, None]
        for idx, act in enumerate(["single", "double", "long"]):
            if not widget.data.get(act):
                widget.data[act] = {}
            self.ui.keyactionwidgets[idx] = KeyActions(widget.data[act])
            self.ui.keyactionwidgets[idx].setParent(eval("self.ui." + act))
            # self.ui.keyactionwidgets[idx].setGeometry(10, 10, 560, 290)
        # Stick in the values from the key dictionary
        self.ui.width.setProperty("value", self._d.get("width", 1.0))
        self.ui.width.valueChanged.connect(self._tryItOut)
        self.ui.caption.setText(self._d.get("caption", "").replace("\n", "\\n"))
        self.ui.caption.editingFinished.connect(self._tryItOut)
        self.ui.cssclass.setText(self._d.get("class", ""))
        self.ui.cssclass.editingFinished.connect(self._tryItOut)
        self.ui.style.setPlainText(self._d.get("style", ""))
        self.ui.addcaption.clicked.connect(self._addcaption)
        self.ui.deletecaption.clicked.connect(self._deletecaption)
        for c, t in self._d.get("extracaptions", {}).items():
            rows = self.ui.extracaptions.rowCount()
            self.ui.extracaptions.setRowCount(rows + 1)
            item = QTableWidgetItem()
            item.setText(c)
            self.ui.extracaptions.setItem(rows, 0, item)
            item = QTableWidgetItem()
            item.setText(t.replace("\n", "\\n"))
            self.ui.extracaptions.setItem(rows, 1, item)

    def _stickBack(self):
        # Appearance
        self._d["width"] = self.ui.width.value()
        self._d["caption"] = self.ui.caption.text().replace("\\n", "\n")
        self._d["class"] = self.ui.cssclass.text()
        self._d["style"] = self.ui.style.toPlainText()
        self._d["extracaptions"] = {}
        for n in range(self.ui.extracaptions.rowCount()):
            cssclass = self.ui.extracaptions.item(n, 0).text()
            caption = self.ui.extracaptions.item(n, 1).text()
            if caption and cssclass:
                caption = caption.replace("\\n", "\n")
                self._d["extracaptions"][cssclass] = caption

    def _addcaption(self):
        rows = self.ui.extracaptions.rowCount()
        self.ui.extracaptions.setRowCount(rows + 1)

    def _deletecaption(self):
        row = self.ui.extracaptions.currentRow()
        self.ui.extracaptions.removeRow(row)

    def _tryItOut(self):
        self._stickBack()
        g_oskbwidget.initKeyboards()
        g_oskbwidget.updateKeyboard()

    def reject(self):
        super().reject()
        oskb.oskbCopy(self._backup, self._d)
        g_oskbwidget.initKeyboards()
        g_oskbwidget.updateKeyboard()

    def accept(self):
        self._stickBack()
        # Tell KeyAction widgets to save their stuff as well
        for idx, act in enumerate(["single", "double", "long"]):
            self.ui.keyactionwidgets[idx].stickBack()
        super().accept()


class KeyActions(QWidget):
    def __init__(self, a):
        super().__init__()
        self._a = a
        self.ui = Ui_KeyActions()
        self.ui.setupUi(self)
        self.setStyleSheet("QLineEdit, QDoubleSpinBox { border: 1px solid #bcbebf; }")
        if not g_kbdinput:
            self.ui.send_wiz.setEnabled(False)
            self.ui.modifier_wiz.setEnabled(False)
        else:
            self.ui.send_wiz.clicked.connect(
                partial(self._wiz, self.ui.send_keycode, self.ui.send_name, self.ui.send_printable)
            )
            self.ui.modifier_wiz.clicked.connect(
                partial(
                    self._wiz, self.ui.modifier_keycode, self.ui.modifier_name, self.ui.modifier_printable
                )
            )
        if a.get("send", {}):
            self.ui.send.setChecked(True)
            self.ui.send_keycode.setText(a["send"].get("keycode", ""))
            self.ui.send_name.setText(a["send"].get("name", ""))
            self.ui.send_printable.setChecked(a["send"].get("printable", True))
        for v in g_oskbwidget.getViews():
            self.ui.view_name.addItem(v)
            self.ui.view_thenview.addItem(v)
        if a.get("view", {}):
            self.ui.view.setChecked(True)
            self.ui.view_name.setCurrentText(a["view"].get("name", ""))
            if a["view"].get("thenview"):
                self.ui.view_until_checkbox.setChecked(True)
                self.ui.view_thenview.setCurrentText(a["view"].get("thenview", ""))
                self.ui.view_until.setText(a["view"].get("until", ""))
        if a.get("modifier", {}):
            self.ui.modifier.setChecked(True)
            self.ui.modifier_keycode.setText(a["modifier"].get("keycode", ""))
            self.ui.modifier_name.setText(a["modifier"].get("name", ""))
            self.ui.modifier_action.setCurrentText(a["modifier"].get("action", "toggle"))
            self.ui.modifier_printable.setChecked(a["modifier"].get("printable", True))
        if a.get("keyboard", {}):
            self.ui.keyboard.setChecked(True)
            self.ui.keyboard_name.setText(a["keyboard"].get("name", ""))

    def _wiz(self, keycode_lineedit, name_lineedit, printable_checkbox):
        wiz = KeyWizard()
        if not wiz.exec():
            return
        name_lineedit.setText(wiz.keyname)
        keycode_lineedit.setText(wiz.keycode)
        printable_checkbox.setChecked(wiz.printable)

    # Called from EditKey.accept()
    def stickBack(self):
        a = self._a
        a["send"] = {}
        if self.ui.send.isChecked():
            a["send"]["keycode"] = self.ui.send_keycode.text()
            a["send"]["name"] = self.ui.send_name.text()
            a["send"]["printable"] = self.ui.send_printable.isChecked()
        a["view"] = {}
        if self.ui.view.isChecked():
            a["view"]["name"] = self.ui.view_name.currentText()
            if self.ui.view_until_checkbox.isChecked():
                a["view"]["thenview"] = self.ui.view_thenview.currentText()
                a["view"]["until"] = self.ui.view_until.text()
        a["modifier"] = {}
        if self.ui.modifier.isChecked():
            a["modifier"]["keycode"] = self.ui.modifier_keycode.text()
            a["modifier"]["name"] = self.ui.modifier_name.text()
            a["modifier"]["action"] = self.ui.modifier_action.currentText()
            a["modifier"]["printable"] = self.ui.modifier_printable.isChecked()
        a["keyboard"] = {}
        if self.ui.keyboard.isChecked():
            a["keyboard"]["name"] = self.ui.keyboard_name.text()


if __name__ == "__main__":
    main()
