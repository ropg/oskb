import sys, os, json, re
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
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
import pkg_resources, argparse
import oskb

DOUBLECLICK_TIMEOUT = 200
MAX_UNDO = 10

def main():
    app = QApplication(sys.argv)
    ex = OskbEdit()

    sys.exit(app.exec_())


class OskbEdit(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self._doubletimer = QTimer()
        self._doubletimer.setSingleShot(True)

        ap = argparse.ArgumentParser()
        ap.add_argument("keyboard", help="a keyboard file", metavar="<kbd>", nargs="?")
        self._cmdline = ap.parse_args()

        self._changed = False

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

        self._copypaste = []

        self._oskb = oskb.Keyboard()
        self._oskb.setButtonHandler(self._buttonHandler)
        self._oskb.setStyleSheet(pkg_resources.resource_string("oskb", "oskbedit.css").decode("utf-8"))

        self._mode = "edit"

        layout = QVBoxLayout(self)

        frame = QWidget()

        self._kbdlayout = QHBoxLayout()
        frame.setLayout(self._kbdlayout)
        self._kbdlayout.addWidget(self._oskb)

        layout.addLayout(self._kbdlayout)
        self.setWindowTitle("oskbedit")

        layout.addWidget(frame)

        self._menu = QMenuBar()
        self._menu.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.layout().setMenuBar(self._menu)

        if self._cmdline.keyboard:
            if not self._loadFile(self._cmdline.keyboard):
                sys.exit(-1)
        else:
            self._loadFile("_new")

        self.show()

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
        newitem.triggered.connect(partial(self._loadFile,"_new"))
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
        dialog.setViewMode(QFileDialog.Detail);
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
            self._kbdname = self._oskb.readKeyboard(f)
        except:
            QMessageBox.warning(self, "read failed",
                "File read failed: " + str(sys.exc_info()[1]), QMessageBox.Ok, QMessageBox.Ok)
            return False
        self._oskb.setKeyboard(self._kbdname)
        self._changed = False
        self._kbds = self._oskb.getRawKbds()
        try:
            del self._kbds["_minimized"]
            del self._kbds["_chooser"]
        except:
            pass
        self._kbd = self._kbds[self._kbdname]
        self._viewname = self._oskb.getView()
        self._view = self._kbd["views"][self._viewname]
        self._oskb.updateKeyboard()
        self._oskb.show()
        self._undo = []
        self._redo = []
        self._previouskbd = oskb.oskbCopy(self._kbd)
        self._stir()
        return True

    def _areyousure(self):
        if QMessageBox.warning(self, "Almost losing changes",
            "You have made changes, are you sure you want to do this? Hit 'No' and save if not.",
             QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
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
        with open(f, 'w') as outfile:
            json.dump(savecopy, outfile)
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
        deleteitem.setEnabled(True if sel > 0 else False)
        editmenu.addAction(deleteitem)

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

        cssitem = QAction("&Edit Keyboard CSS", self)
        cssitem.triggered.connect(self._edit_css)
        editmenu.addAction(cssitem)

    def _edit_undo(self):
        actionname, actionview, kbd = self._undo.pop(0)
        self._redo.insert(0, (actionname, self._viewname, oskb.oskbCopy(self._kbd)))
        oskb.oskbCopy(kbd, self._kbd)
        if actionview != self._viewname:
            self._view_switch(actionview)
        self._stir()

    def _edit_redo(self):
        actionname, actionview, kbd = self._redo.pop(0)
        self._undo.insert(0, (actionname, self._viewname, oskb.oskbCopy(self._kbd)))
        oskb.oskbCopy(kbd, self._kbd)
        if actionview != self._viewname:
            self._view_switch(actionview)
        self._stir()

    def _edit_delete(self):
        self._copyCut(True)
        self._stir("Delete")

    def _edit_copy(self):
        self._copypaste = self._copyCut(False)

    def _edit_cut(self):
        self._copypaste = self._copyCut(True)
        self._stir("Cut")

    def _edit_paste(self, tuple, after = 0):
        ci, ri, ki = (tuple)
        for ins in self._copypaste:
            self._view["columns"][ci]["rows"][ri]["keys"].insert(ki + after, oskb.oskbCopy(ins))
        self._stir("Paste")

    def _copyCut(self, cut = False):
        buffer = []
        for ci, ri, ki, keydata in self._reverseIterateKeys():
            if keydata.get("_selected", False):
                buffer.append(oskb.oskbCopy(keydata))
                if cut:
                    del self._view["columns"][ci]["rows"][ri]["keys"][ki]
        for ci, ri, row in self._iterateRows():
            if row.get("_selected"):
                if len(self._view["columns"][ci].get("rows", [])) > 1:
                    del self._view["columns"][ci]["rows"][ri]
                else:
                    QMessageBox.warning(self, "Deleting objects",
                        "You cannot delete the last row", QMessageBox.Ok, QMessageBox.Ok)
        return buffer

    def _edit_css(self):
        if EditCSS(self._kbd).exec():
            self._stir("Edit CSS")

    def _edit_spacer(self, widget):
        if EditSpacer(widget, self._oskb).exec():
            self._stir("Edit Spacer")

    def _edit_key(self, widget):
        if Editkey(widget, self._oskb, self._kbd).exec():
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
            addkbefore.triggered.connect(partial(self._insertKey, self._firstSelKey()))
            insertkmenu.addAction(addkbefore)
            addkafter = QAction("&After Selected", self)
            addkafter.triggered.connect(partial(self._insertKey, self._lastSelKey(), 1))
            addkafter.setShortcut("Ctrl+K")
            insertkmenu.addAction(addkafter)
            addsbefore = QAction("&Before Selected", self)
            addsbefore.triggered.connect(partial(self._insertSpacer, self._firstSelKey()))
            insertsmenu.addAction(addsbefore)
            addsafter = QAction("&After Selected", self)
            addsafter.triggered.connect(partial(self._insertSpacer, self._lastSelKey(), 1))
            insertsmenu.addAction(addsafter)
        elif selrows == 1:
            addkon = QAction("&On Selected Row", self)
            addkon.triggered.connect(partial(self._insertKey, self._firstSelRow()))
            addkon.setShortcut("Ctrl+K")
            insertkmenu.addAction(addkon)
            addson = QAction("&On Selected Row", self)
            addson.triggered.connect(partial(self._insertSpacer, self._firstSelRow()))
            insertkmenu.addAction(addkon)

    def _insertKey(self, tuple, after = 0):
        ci, ri, ki = (tuple)
        rowkeys = self._view["columns"][ci]["rows"][ri]["keys"]
        rowkeys.insert(ki + after, { "type": "key" })
        self._oskb.initKeyboards()
        self._selectState(False)
        self._selectState(True, rowkeys[ki + after]["_QWidget"])
        self._stir("Insert Key")

    def _insertSpacer(self, tuple, after = 0):
        spacerwidth, okbutton = QInputDialog.getDouble(self, "Spacer","Width:", 0.5, 0.1, 100, 1)
        if not okbutton:
            return
        ci, ri, ki = (tuple)
        rowkeys = self._view["columns"][ci]["rows"][ri]["keys"]
        rowkeys.insert(ki + after, { "type": "spacer", "width": str(spacerwidth) })
        self._oskb.initKeyboards()
        self._selectState(False)
        self._selectState(True, rowkeys[ki + after]["_QWidget"])
        self._stir("Insert Spacer")


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
        self._view_switch(self._oskb.getView())
        self._oskb.setButtonHandler(self._buttonHandler)
        self._stir()

    def _view_testmode(self):
        self._mode = "test"
        self._selectState(False)
        self._oskb.setButtonHandler()
        self._stir()

    def _view_switch(self, viewname):
        self._oskb.setView(viewname)
        self._view = self._kbd["views"][viewname]
        self._viewname = viewname
        self._fixMenu()

    def _view_delete(self):
        delview = self._oskb.getView()
        if delview == "default":
            QMessageBox.warning(self, "New View",
                "Cannot delete 'default' view", QMessageBox.Ok)
            return
        self._view_switch("default")
        del self._kbd["views"][delview]
        self._stir("Delete View")

    def _view_add(self):
        while True:
            viewname, result = QInputDialog.getText(self, "New View", "Name:")
            if not result: break
            if not re.fullmatch("[a-z_]+", viewname):
                QMessageBox.warning(self, "New View",
                    "View name can only contain lower case letters and underscores", QMessageBox.Ok)
                continue
            if self._kbd["views"].get(viewname):
                QMessageBox.warning(self, "New View",
                    "View " + viewname + " already exists", QMessageBox.Ok)
                continue
            self._kbd["views"][viewname] = { "columns": [ { "rows": [ { "keys": [] } ] } ] }
            self._stir("Add View")
            self._view_switch(viewname)
            self._fixMenu()
            break



    def _buttonHandler(self, widget, direction):
        if direction == oskb.PRESSED:
            # Read only once, is not state now but of last click event
            mod = QGuiApplication.keyboardModifiers()
            if mod & Qt.ControlModifier:
                self._selectState(not widget.data.get("_selected", False), widget)
            elif ( mod & Qt.ShiftModifier ):
                if self._lastclicked:
                    if widget.data.get("type") == "emptyrow":
                        return
                    selecting = False
                    for ci, ri, ki, keydata in self._iterateKeys():
                        thisone = keydata['_QWidget']
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
        self._oskb.updateKeyboard()
        self._fixMenu()

    def _doubleClick(self, widget):
        if widget.data.get("type") == "spacer":
            self._edit_spacer(widget)
        elif widget.data.get("type", "key") == "key":
            self._edit_key(widget)

    def _stir(self, actionname = None):
        if actionname:
            self._changed = True
            self._undo.insert(0, (actionname, self._viewname[:], oskb.oskbCopy(self._previouskbd)))
            self._previouskbd = oskb.oskbCopy(self._kbd)
            while len(self._undo) > MAX_UNDO:
                self._undo.pop(len(self._undo) - 1)
            self._redo = []
        self._oskb.initKeyboards()
        self._oskb.updateKeyboard()
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
                selkeys +=1
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


class EditCSS(QDialog):
    def __init__(self, kbd):
        super().__init__()
        self._kbd = kbd
        self.resize(500, 400)
        self.setMinimumSize(500, 400)
        self.setMaximumSize(500, 400)
        self.setWindowTitle("Stylesheets")
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.cancelsavebuttons = QDialogButtonBox(self)
        self.cancelsavebuttons.setGeometry(QRect(150, 360, 341, 32))
        self.cancelsavebuttons.setOrientation(Qt.Horizontal)
        self.cancelsavebuttons.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
        self.maintabs = QTabWidget(self)
        self.maintabs.setGeometry(QRect(10, 10, 481, 341))
        self.tab = QWidget()
        self.defaultcss = QTextEdit(self.tab)
        self.defaultcss.setGeometry(QRect(10, 10, 451, 291))
        self.defaultcss.setAcceptDrops(False)
        self.defaultcss.setReadOnly(True)
        self.defaultcss.setAcceptRichText(False)
        self.maintabs.addTab(self.tab, "default.css (readonly)")
        self.tab_2 = QWidget()
        self.maintabs.addTab(self.tab_2, "Keyboard Stylesheet")
        self.keyboardcss = QTextEdit(self.tab_2)
        self.keyboardcss.setGeometry(QRect(10, 10, 451, 291))
        self.keyboardcss.setAcceptDrops(False)
        self.keyboardcss.setReadOnly(False)
        self.keyboardcss.setAcceptRichText(False)
        self.maintabs.setCurrentIndex(1)
        self.cancelsavebuttons.accepted.connect(self.accept)
        self.cancelsavebuttons.rejected.connect(self.reject)
        self.defaultcss.setPlainText(pkg_resources.resource_string("oskb", "default.css").decode("utf-8"))
        self.keyboardcss.setPlainText(self._kbd.get("style", ""))

    def accept(self):
        self._kbd["style"] = self.keyboardcss.toPlainText()
        super().accept()


class EditSpacer(QDialog):
    def __init__(self, widget, oskbwidget):
        self._widget = widget
        self._oskbwidget = oskbwidget
        self.entryvalue = float(widget.data.get("width", "0.5"))
        super().__init__()
        self.resize(193, 81)
        self.setMinimumSize(193, 81)
        self.setMaximumSize(193, 81)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setWindowTitle("Spacer")
        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.setGeometry(QRect(10, 40, 171, 32))
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
        self.widthbox = QDoubleSpinBox(self)
        self.widthbox.setGeometry(QRect(100, 10, 81, 24))
        self.widthbox.setDecimals(1)
        self.widthbox.setMinimum(0.1)
        self.widthbox.setSingleStep(0.1)
        self.widthbox.setProperty("value", self.entryvalue)
        self.label = QLabel(self)
        self.label.setText("Width:")
        self.label.setGeometry(QRect(30, 10, 61, 21))
        self.label.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.widthbox.valueChanged.connect(self._tryItOut)

    def _tryItOut(self):
        self._widget.data["width"] = str(self.widthbox.value())
        self._oskbwidget.initKeyboards()
        self._oskbwidget.updateKeyboard()

    def reject(self):
        self._widget.data["width"] = str(self.entryvalue)
        self._oskbwidget.initKeyboards()
        self._oskbwidget.updateKeyboard()
        super().reject()


class Editkey(QDialog):
    def __init__(self, widget, oskbwidget, kbd):
        super().__init__()
        self._oskbwidget = oskbwidget
        self._d = widget.data
        self._backup = oskb.oskbCopy(widget.data)
        Editkey.resize(self, 565, 428)
        self.setMinimumSize(565, 428)
        self.setMaximumSize(565, 428)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setWindowTitle("Edit key properties")
        self.cancelsavebuttons = QDialogButtonBox(self)
        self.cancelsavebuttons.setGeometry(QRect(270, 390, 281, 32))
        self.cancelsavebuttons.setOrientation(Qt.Horizontal)
        self.cancelsavebuttons.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
        self.maintabs = QTabWidget(self)
        self.maintabs.setGeometry(QRect(10, 10, 541, 371))
        self.appearance = QWidget()
        self._ap_lbl_4 = QLabel(self.appearance)
        self._ap_lbl_4.setText("Additional captions:")
        self._ap_lbl_4.setGeometry(QRect(270, 20, 151, 16))
        self._ap_lbl_4.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignVCenter)
        self._ap_caption = QLineEdit(self.appearance)
        self._ap_caption.setGeometry(QRect(110, 20, 101, 21))
        self._ap_class = QLineEdit(self.appearance)
        self._ap_class.setGeometry(QRect(40, 135, 171, 21))
        self._ap_extracaptions = QTableWidget(self.appearance)
        self._ap_extracaptions.setGeometry(QRect(270, 40, 241, 101))
        font = QFont()
        font.setPointSize(11)
        self._ap_extracaptions.setFont(font)
        self._ap_extracaptions.setShowGrid(True)
        self._ap_extracaptions.setRowCount(0)
        self._ap_extracaptions.setColumnCount(2)
        item = QTableWidgetItem()
        self._ap_extracaptions.setHorizontalHeaderItem(0, item)
        item = QTableWidgetItem()
        self._ap_extracaptions.setHorizontalHeaderItem(1, item)
        self._ap_extracaptions.horizontalHeader().setCascadingSectionResizes(False)
        self._ap_extracaptions.horizontalHeader().setStretchLastSection(True)
        self._ap_extracaptions.verticalHeader().setStretchLastSection(False)
        item = self._ap_extracaptions.horizontalHeaderItem(0)
        item.setText("CSS class")
        item = self._ap_extracaptions.horizontalHeaderItem(1)
        item.setText("Caption")
        self._ap_lbl_3 = QLabel(self.appearance)
        self._ap_lbl_3.setText("Additional CSS classes, separated by spaces:")
        self._ap_lbl_3.setGeometry(QRect(30, 90, 171, 41))
        self._ap_lbl_3.setAlignment(Qt.AlignJustify|Qt.AlignVCenter)
        self._ap_lbl_3.setWordWrap(True)
        self._ap_lbl_1 = QLabel(self.appearance)
        self._ap_lbl_1.setText("Caption:")
        self._ap_lbl_1.setGeometry(QRect(20, 20, 81, 16))
        self._ap_lbl_1.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)
        self._ap_style = QTextEdit(self.appearance)
        self._ap_style.setGeometry(QRect(20, 190, 491, 101))
        self._ap_lbl_5 = QLabel(self.appearance)
        self._ap_lbl_5.setText("CSS StyleSheet specific to this key:")
        self._ap_lbl_5.setGeometry(QRect(40, 170, 291, 16))
        self._ap_lbl_5.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignVCenter)
        self._ap_lbl_6 = QLabel(self.appearance)
        self._ap_lbl_6.setText("(Usually better to add a CSS class and put the style info in the common stylesheet)")
        self._ap_lbl_6.setGeometry(QRect(20, 300, 491, 20))
        font = QFont()
        font.setPointSize(9)
        self._ap_lbl_6.setFont(font)
        self._ap_lbl_6.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)
        self._ap_lbl_2 = QLabel(self.appearance)
        self._ap_lbl_2.setText("Key width:")
        self._ap_lbl_2.setGeometry(QRect(20, 50, 81, 16))
        self._ap_lbl_2.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)
        self._ap_width = QDoubleSpinBox(self.appearance)
        self._ap_width.setGeometry(QRect(110, 50, 81, 24))
        self._ap_width.setDecimals(1)
        self._ap_width.setMinimum(0.1)
        self._ap_width.setSingleStep(0.1)
        self._ap_width.setProperty("value", 1.0)
        self._ap_deletecaption = QPushButton(self.appearance)
        self._ap_deletecaption.setGeometry(QRect(480, 140, 31, 21))
        font = QFont()
        font.setBold(True)
        font.setWeight(75)
        self._ap_deletecaption.setFont(font)
        self._ap_deletecaption.setDefault(False)
        self._ap_deletecaption.setFlat(False)
        self._ap_deletecaption.setText("-")
        self._ap_addcaption = QPushButton(self.appearance)
        self._ap_addcaption.setGeometry(QRect(450, 140, 31, 21))
        self._ap_addcaption.setDefault(False)
        self._ap_addcaption.setFlat(False)
        self._ap_addcaption.setText("+")
        self.maintabs.addTab(self.appearance, "")
        self.action = QWidget()
        self.actiontabs = QTabWidget(self.action)
        self.actiontabs.setGeometry(QRect(10, 20, 511, 311))
        font = QFont()
        font.setBold(True)
        font.setWeight(75)
        self.ac = {}
        for act in ["single", "double", "long"]:
            self.ac[act] = {}
            a = self.ac[act]
            a["tab"] = QWidget()
            a["send"] = QCheckBox(a["tab"])
            a["send"].setGeometry(QRect(20, 10, 151, 20))
            a["send"].setFont(font)
            a["send_keycode"] = QLineEdit(a["tab"])
            a["send_keycode"].setGeometry(QRect(110, 40, 81, 21))
            a["modifier_name"] = QLineEdit(a["tab"])
            a["modifier_name"].setGeometry(QRect(390, 70, 61, 21))
            a["keyboard"] = QCheckBox(a["tab"])
            a["keyboard"].setGeometry(QRect(300, 170, 191, 20))
            a["keyboard"].setFont(font)
            a["send_name"] = QLineEdit(a["tab"])
            a["send_name"].setGeometry(QRect(110, 70, 81, 21))
            a["keyboard_name"] = QLineEdit(a["tab"])
            a["keyboard_name"].setGeometry(QRect(390, 200, 101, 21))
            a["view"] = QCheckBox(a["tab"])
            a["view"].setGeometry(QRect(20, 150, 151, 20))
            a["view"].setFont(font)
            a["modifier_action"] = QComboBox(a["tab"])
            a["modifier_action"].setGeometry(QRect(390, 100, 91, 26))
            a["modifier_action"].addItem("")
            a["modifier_action"].addItem("")
            a["lbl_11"] = QLabel(a["tab"])
            a["lbl_11"].setGeometry(QRect(20, 70, 81, 16))
            a["lbl_11"].setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)
            a["modifier_keycode"] = QLineEdit(a["tab"])
            a["modifier_keycode"].setGeometry(QRect(390, 40, 81, 21))
            a["lbl_15"] = QLabel(a["tab"])
            a["lbl_15"].setGeometry(QRect(300, 100, 81, 16))
            a["lbl_15"].setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)
            a["lbl_14"] = QLabel(a["tab"])
            a["lbl_14"].setGeometry(QRect(300, 70, 81, 16))
            a["lbl_14"].setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)
            a["modifier_printable"] = QCheckBox(a["tab"])
            a["modifier_printable"].setGeometry(QRect(390, 130, 91, 20))
            a["view_until_checkbox"] = QCheckBox(a["tab"])
            a["view_until_checkbox"].setGeometry(QRect(40, 210, 121, 20))
            a["lbl_16"] = QLabel(a["tab"])
            a["lbl_16"].setGeometry(QRect(320, 200, 61, 20))
            a["lbl_16"].setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)
            a["lbl_13"] = QLabel(a["tab"])
            a["lbl_13"].setGeometry(QRect(300, 40, 81, 16))
            a["lbl_13"].setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)
            a["send_printable"] = QCheckBox(a["tab"])
            a["send_printable"].setGeometry(QRect(110, 100, 91, 20))
            a["send"] = QCheckBox(a["tab"])
            a["send"].setGeometry(QRect(20, 10, 151, 20))
            a["send"].setFont(font)
            a["view_until"] = QLineEdit(a["tab"])
            a["view_until"].setGeometry(QRect(220, 240, 71, 21))
            a["modifier"] = QCheckBox(a["tab"])
            a["modifier"].setGeometry(QRect(300, 10, 161, 20))
            a["modifier"].setFont(font)
            a["view_name"] = QComboBox(a["tab"])
            a["view_name"].setGeometry(QRect(40, 180, 131, 26))
            a["lbl_10"] = QLabel(a["tab"])
            a["lbl_10"].setGeometry(QRect(20, 40, 81, 16))
            a["lbl_10"].setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)
            a["view_thenview"] = QComboBox(a["tab"])
            a["view_thenview"].setGeometry(QRect(170, 210, 131, 26))
            a["lbl_12"] = QLabel(a["tab"])
            a["lbl_12"].setGeometry(QRect(40, 240, 171, 21))
            a["lbl_12"].setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)
            a["lbl_12"].setWordWrap(True)
            self.actiontabs.addTab(a["tab"], "")
        self.maintabs.addTab(self.action, "")
        self.maintabs.setCurrentIndex(0)
        self.actiontabs.setCurrentIndex(0)
        self.cancelsavebuttons.accepted.connect(self.accept)
        self.cancelsavebuttons.rejected.connect(self.reject)
        Editkey.setTabOrder(self.maintabs, self._ap_caption)
        Editkey.setTabOrder(self._ap_caption, self._ap_width)
        Editkey.setTabOrder(self._ap_width, self._ap_class)
        Editkey.setTabOrder(self._ap_class, self._ap_extracaptions)
        Editkey.setTabOrder(self._ap_extracaptions, self._ap_deletecaption)
        Editkey.setTabOrder(self._ap_deletecaption, self._ap_style)
        Editkey.setTabOrder(self._ap_style, self.actiontabs)
        Editkey.setTabOrder(self.actiontabs, self.ac["single"]["send"])
        lastone = self.actiontabs
        for act in ["single", "double", "long"]:
            a = self.ac[act]
            Editkey.setTabOrder(lastone, a["send"])
            Editkey.setTabOrder(a["send"], a["send_keycode"])
            Editkey.setTabOrder(a["send_keycode"], a["send_name"])
            Editkey.setTabOrder(a["send_name"], a["send_printable"])
            Editkey.setTabOrder(a["send_printable"], a["view"])
            Editkey.setTabOrder(a["view"], a["view_name"])
            Editkey.setTabOrder(a["view_name"], a["view_until_checkbox"])
            Editkey.setTabOrder(a["view_until_checkbox"], a["view_thenview"])
            Editkey.setTabOrder(a["view_thenview"], a["view_until"])
            Editkey.setTabOrder(a["view_until"], a["modifier"])
            Editkey.setTabOrder(a["modifier"], a["modifier_keycode"])
            Editkey.setTabOrder(a["modifier_keycode"], a["modifier_name"])
            Editkey.setTabOrder(a["modifier_name"], a["modifier_action"])
            Editkey.setTabOrder(a["modifier_action"], a["modifier_printable"])
            Editkey.setTabOrder(a["modifier_printable"], a["keyboard"])
            Editkey.setTabOrder(a["keyboard"], a["keyboard_name"])
            lastone = a["keyboard_name"]
        self.setStyleSheet("QLineEdit, QDoubleSpinBox { border: 1px solid #bcbebf; }")

        # Read values from oskb data to the elements in the window

        # Appearance
        self._ap_width.setProperty("value", float(self._d.get("width", "1.0")))
        self._ap_width.valueChanged.connect(self._tryItOut)
        self._ap_caption.setText(self._d.get("caption", ""))
        self._ap_caption.editingFinished.connect(self._tryItOut)
        self._ap_class.setText(self._d.get("class", ""))
        self._ap_class.editingFinished.connect(self._tryItOut)
        self._ap_style.setPlainText(self._d.get("style", ""))
        for c, t in self._d.get("extracaptions", {}).items():
            rows = self._ap_extracaptions.rowCount()
            self._ap_extracaptions.setRowCount(rows + 1)
            item = QTableWidgetItem()
            item.setText(c)
            self._ap_extracaptions.setItem(rows, 0, item)
            item = QTableWidgetItem()
            item.setText(t)
            self._ap_extracaptions.setItem(rows, 1, item)
        # Actions
        for act in ["single", "double", "long"]:
            a = self._d.get(act, {})
            b = self.ac[act]
            b["keyboard"].setText("Jump to keyboard")
            b["view"].setText("Jump to view")
            b["modifier_action"].setItemText(0, "toggle")
            b["modifier_action"].setItemText(1, "lock")
            b["lbl_11"].setText("name:")
            b["lbl_15"].setText("action:")
            b["lbl_14"].setText("name:")
            b["modifier_printable"].setText("printable")
            b["view_until_checkbox"].setText("Then jump to")
            b["lbl_16"].setText("name:")
            b["lbl_13"].setText("keycode:")
            b["send_printable"].setText("printable")
            b["send"].setText("Send keypress")
            b["modifier"].setText("Be a modifier key")
            b["lbl_10"].setText("keycode:")
            b["lbl_12"].setText("when key macthes")
            if a.get("send"):
                b["send"].setChecked(True)
                b["send_keycode"].setText(a["send"].get("keycode", ""))
                b["send_name"].setText(a["send"].get("name", ""))
                b["send_printable"].setChecked(a["send"].get("printable", True))
            for v in kbd["views"].keys():
                b["view_name"].addItem(v)
                b["view_thenview"].addItem(v)
            if a.get("view"):
                b["view"].setChecked(True)
                b["view_name"].setCurrentText(a["view"].get("name", ""))
                if a["view"].get("thenview"):
                    b["view_until_checkbox"].setChecked(True)
                    b["view_thenview"].setCurrentText(a["view"].get("thenview", ""))
                    b["view_until"].setText(a["view"].get("until", ""))
            if a.get("modifier"):
                b["modifier"].setChecked(True)
                b["modifier_keycode"].setText(a["modifier"].get("keycode", ""))
                b["modifier_name"].setText(a["modifier"].get("name", ""))
                b["modifier_action"].setCurrentText(a["modifier"].get("action", "toggle"))
                b["modifier_printable"].setChecked(a["modifier"].get("printable", True))
            if a.get("keyboard"):
                b["keyboard"].setChecked(True)
                b["keyboard_name"].setText(a["keyboard"].get("name", ""))
        self.maintabs.setTabText(self.maintabs.indexOf(self.appearance), "Appearance")
        self.actiontabs.setTabText(self.actiontabs.indexOf(self.ac["single"]["tab"]), "Single Tap")
        self.actiontabs.setTabText(self.actiontabs.indexOf(self.ac["double"]["tab"]), "Double Tap")
        self.actiontabs.setTabText(self.actiontabs.indexOf(self.ac["long"]["tab"]), "Press and hold")
        self.maintabs.setTabText(self.maintabs.indexOf(self.action), "Action")

    # Sticking the data from the elements on the screen back into oskb

    def _stickBack(self):
        # Appearance
        self._d["width"] = str(self._ap_width.value())
        self._d["caption"] = self._ap_caption.text()
        self._d["class"] = self._ap_class.text()
        self._d["style"] = self._ap_style.toPlainText()
        self._d["extracaptions"] = {}
        for n in range(self._ap_extracaptions.rowCount()):
            self._d["extracaptions"][self._ap_extracaptions.item(n, 0)] = self._ap_extracaptions.item(n, 1)
        # Actions
        for act in ["single", "double", "long"]:
            a = self.ac.get(act, {})
            b = self._d.get(act, {})
            b.clear()
            if a["send"].isChecked():
                b["send"] = {}
                b["send"]["keycode"] = a["send_keycode"].text()
                b["send"]["name"] = a["send_name"].text()
                b["send"]["printable"] = a["send_printable"].isChecked()
            if a["view"].isChecked():
                b["view"] = {}
                b["view"]["name"] = a["name"].currentText()
                if a["view_until_checkbox"].isChecked():
                    b["view"]["thenview"] = a["view_thenview"].currentText()
                    b["view"]["until"] = a["view_until"].text()
            if a["modifier"].isChecked():
                b["modifier"] = {}
                b["modifier"]["keycode"] = a["modifier_keycode"].text()
                b["modifier"]["name"] = a["modifier_name"].text()
                b["modifier"]["action"] = a["modifier_action"].currentText()
                b["modifier"]["printable"] = a["modifier_printable"].isChecked()
            if a["keyboard"].isChecked():
                b["keyboard"] = {}
                b["keyboard"]["name"] = a["keyboard_name"].text()

    def _tryItOut(self):
        self._stickBack()
        self._oskbwidget.initKeyboards()
        self._oskbwidget.updateKeyboard()

    def reject(self):
        oskb.oskbCopy(self._backup, self._d)
        self._oskbwidget.initKeyboards()
        self._oskbwidget.updateKeyboard()
        super().reject()

    def accept(self):
        self._stickBack()
        self._oskbwidget.initKeyboards()
        self._oskbwidget.updateKeyboard()
        super().accept()


if __name__ == "__main__":
    main()
