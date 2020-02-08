import os, re, json, subprocess
from functools import partial
import pkg_resources

from PyQt5.QtCore import QTimer, QRect
from PyQt5.QtWidgets import QWidget, QPushButton


class Keyboard(QWidget):

    def __init__(self):
        super().__init__()

        self.modifiers = {}
        self.longpresswait = False
        self.keytimer = None

        self.kbds = []
        self.keypipe = None

    def setKeypipe(self, fn):
        self.keypipe = fn

    def readKeyboards(self, kbdfiles):
        for kbdfile in kbdfiles:
            kbd = None
            if os.access(kbdfile, os.R_OK):
                with open(kbdfile, 'r', encoding='utf-8') as f:
                    kbd = json.load(f)
            elif kbdfile == os.path.basename(kbdfile) and pkg_resources.resource_exists('oskb', 'keyboards/' + kbdfile):
                kbd = json.loads(pkg_resources.resource_string('oskb', 'keyboards/' + kbdfile))
            if kbd:
                kbd['name'] = os.path.basename(kbdfile)
                self.kbds.append(kbd)
            else:
                raise FileNotFoundError('Could not find ' + kbdfile)
        if len(self.kbds) > 1:
            self.kbds.append(self.makeChooser())
        self.insertDefaults()
        self.kbd = self.kbds[0]
        self.setView('default')

    def makeChooser(self):
        chooser = { "name": "chooser", "views": [ { "name": "default", "columns": [ { "rows": [] } ] } ] }
        for k in self.kbds:
            rows = chooser['views'][0]['columns'][0]['rows']
            rows.append( { 'keys': [ {'caption': k['description'], 'action': 'keyboard:' + k['name'] } ] } )
        return chooser


    def defaultStyleSheet(self):
        return """

            QWidget {
                background-color: #cccccc;
            }

            .key {
                background-color: #eeeeee;
                border: 1px solid black;
            }

            .key:pressed, .key.held {
                background-color: #999999;
            }

            .key.locked {
                background-color: #cc9999;
            }

        """

    def insertDefaults(self):
        # I don't want various defaults to be mandatory in config files. But I do like to iterate with 'for' and
        # python offers no easy 'isset()' or similar, so it would mean ugly try/except stuff everywhere instead
        # of just here. So this sticks in the various defaults.
        for kbd in self.kbds:
            try: kbd['style']
            except KeyError: kbd['style'] = self.defaultStyleSheet()
            for view in kbd['views']:
                try: view['style']
                except KeyError: view['style'] = ''
                for column in view['columns']:
                    try: column['style']
                    except KeyError: column['style'] = ''
                    try: column['class']
                    except KeyError: column['class'] = ''
                    try: column['width']
                    except KeyError: column['width'] = '1'           # Set default width to '1' for each column
                    try: column['rows']
                    except KeyError: column['rows'] = []    # add empty 'rows' to each empty column
                    for row in column['rows']:
                        try: row['style']
                        except KeyError: row['style'] = ''
                        try: row['class']
                        except KeyError: row['class'] = ''
                        try: row['height']
                        except KeyError: row['height'] = '1'         # Set default height to '1' for each rows
                        try: row['keys']
                        except KeyError: row['keys'] = []   # add empty 'keys' to each empty row
                        for keydata in row['keys']:
                            try: keydata['style']
                            except KeyError: keydata['style'] = ''
                            try: keydata['class']
                            except KeyError: keydata['class'] = ''
                            try: keydata['width']
                            except KeyError: keydata['width'] = '1'  # Set default width to '1' for each key
                            try: keydata['type']
                            except KeyError: keydata['type'] = 'key' # Set each key's type to 'key' if unset (i.e. not 'spacer')
                            try: c = 'send:' + keydata['caption']
                            except KeyError: c = 'none'
                            try: keydata['action']
                            except KeyError: keydata['action'] = c

    def setKeyboard(self, kbdname):
        for k in self.kbds:
            if k['name'] == kbdname:
                self.releaseModifiers()
                self.deleteKeyboard()
                self.kbd = k
                try:
                    cmd = ['setxkbmap']
                    cmd += (k['setxkbmap'].split(' '))
                    subprocess.check_output( cmd )
                except KeyError:
                    pass
                self.setView('default')

    def setView(self, viewname):
        for view in self.kbd['views']:
            if view['name'] == viewname:
                self.deleteKeyboard()
                self.view = view
                self.initKeyboard()
                return
        if viewname == 'default':
            self.deleteKeyboard()
            self.view = self.kbd['views'][0]
            self.initKeyboard()
            return
        self.setView('default')

    def divideSpace(self, budget, members, property):
        # This may be a bit of a complicated one to wrap your head around at first, but it's kinda cool
        #
        # Hand it a number of pixels available in total (in budget), a list of columns, rows, or keys
        # (in members) and the name of a property to adjucate on (mostly 'height' or 'width'). It will
        # then read that property for relative weights and create two new properties named 'calcWidth'
        # (or calc$whateverproperty) and 'calcBegin' with the absolute position in the budget.
        #
        # example: you pass it a list of three columns, one of which has 'width' property set to 2
        # it will then add up the weights (defaulting to 1 for the other columns, and divide the budget
        # by 4, and give the column with weight 2 half the budget and the other two a quarter
        totalweight = 0
        for member in members:
            if member[property][-2:] == 'px':
                budget -= int( member[property][:-2] )
            elif member[property] == 'remainder':
                pass
            else:
                totalweight += float(member[property])
        begin = 0
        for member in members:
            if member[property][-2:] == 'px':
                thisone = int( member[property][:-2] )
            else:
                weight = float(member[property])
                thisone = int( (budget / totalweight) * weight )
                totalweight -= weight
                budget -= thisone
            member['calc' + property.capitalize()] = thisone
            member['calcBegin'] = begin
            begin += thisone

    def findStdKeyWidth(self):
        # This returns the width of a key with width 1 (or no width, as 1 is the default) on the first
        # row. This, together with the height of a standard row (see below) is used to caculate a uniform
        # standard font size for the whole keyboard. (Turns out trying to autofit makes things really ugly.)
        #
        # If the first row on any keyboard has odd-sized keys you can specify any other row by giving it
        # "MeasureStdKeyWidthHere" with value "1" in the JSON file.
        unit = 0
        for column in self.view['columns']:
            for row in column['rows']:
                try:
                    row['MeasureStdKeyWidthHere']
                    unit = 0
                except KeyError:
                    pass
                if unit == 0 and len(row['keys']):
                    totalweight = 0
                    budget = column['calcWidth']
                    for keydata in row['keys']:
                        w = keydata['width']
                        if w[-2:] == 'px':
                            budget -= int(w[:-2])
                        else:
                            totalweight += float(w)
                    unit = int(budget / totalweight)
        return unit

    def findStdRowHeight(self):
        unit = 0
        totalweight = 0
        budget = self.height()
        for column in self.view['columns']:
            for row in column['rows']:
                h = row['height']
                if h[-2:] == 'px':
                    budget -= int(h[:-2])
                else:
                    totalweight += float(h)
            thisunit = int (budget / totalweight)
            if unit == 0 or thisunit < unit:
                unit = thisunit
        return unit


    def calcKeyboard(self):
        self.divideSpace(self.width(), self.view['columns'], 'width')
        for column in self.view['columns']:
            self.divideSpace(self.height(), column['rows'], 'height')
            self.stdKeyWidth = self.findStdKeyWidth()
            self.stdRowHeight = self.findStdRowHeight()
            for row in column['rows']:
                self.divideSpace(column['calcWidth'], row['keys'], 'width')

    def deleteKeyboard(self):
        try:
            self.view['columns']
        except:
            return
        for column in self.view['columns']:
            for row in column['rows']:
                for keydata in row['keys']:
                    try: keydata['QWidget']
                    except KeyError: continue
                    keydata['QWidget'].deleteLater()
                row['QWidget'].deleteLater()
            column['QWidget'].deleteLater()

    def initKeyboard(self):
        self.calcKeyboard()
        self.setStyleSheet(self.kbd['style'] + ' ' + self.view['style'])
        for column in self.view['columns']:
            c = QWidget(self)
            c.setProperty('class', 'column ' + column['class'])
            column['QWidget'] = c
            for row in column['rows']:
                r = QWidget(c)
                r.setProperty('class', 'row ' + row['class'])
                r.setStyleSheet(row['style'])
                row['QWidget'] = r
                for keydata in row['keys']:
                    if keydata['type'] == 'key':
                        k = QPushButton(r)
                        k.setProperty('class', 'key ' + keydata['class'])
                        k.setText(keydata['caption'])
                        k.data = keydata
                        k.pressed.connect(partial(self.pressedButton, k))
                        k.released.connect(partial(self.releasedButton, k))
                        k.setStyleSheet(keydata['style'])
                        # See if the key is a modifier, and create that modifier and set it to 0
                        # if it didn't exist yet
                        act, arg = self.parseAction(keydata['action'])
                        if act == 'modifier':
                            try:
                                self.modifiers[arg]
                            except KeyError:
                                self.modifiers[arg] = 0
                        keydata['QWidget'] = k
        self.updateModifiers()
        self.positionEverything()

    def updateModifiers(self):
        for column in self.view['columns']:
            for row in column['rows']:
                for keydata in row['keys']:
                    act, arg = self.parseAction(keydata['action'])
                    if act == 'modifier':
                        s = self.modifiers[arg]
                        if s == 0:
                            addclass = ''
                        elif s == 1:
                            addclass = ' held'
                        else:
                            addclass = ' locked'
                        keydata['QWidget'].setProperty('class', 'key ' + keydata['class'] + addclass)
        self.positionEverything()

    def releaseModifiers(self):
        for modifier, state in self.modifiers.items():
            if self.modifiers[modifier] == 1:
                self.injectKeys(modifier, 0)
                self.modifiers[modifier] = 0
        self.updateModifiers()

    def positionEverything(self):
        fontsize = int(min(self.stdKeyWidth / 1.5, self.stdRowHeight / 2))
        margin = min( int( (self.width() - 100) / 100), 6 )
        self.setStyleSheet(self.kbd['style'] + ' ' + self.view['style'] + ' .key { font-size: ' + str(fontsize) + 'px; margin: ' + str(margin) + 'px; border-radius: ' + str(margin * 2) + 'px }')
        for column in self.view['columns']:
            column['QWidget'].setGeometry(QRect(column['calcBegin'], 0, column['calcWidth'],  self.height()))
            column['QWidget'].setVisible(True)      # No idea why this is needed for subsequent view draws. But hey...
            column['QWidget'].setStyleSheet(self.fixStyleSheet(column['style'], fontsize))
            for row in column['rows']:
                row['QWidget'].setGeometry(QRect(0, row['calcBegin'], column['calcWidth'], row['calcHeight']))
                row['QWidget'].setStyleSheet(self.fixStyleSheet(row['style'], fontsize))
                for keydata in row['keys']:
                    try:
                        keydata['QWidget'].setGeometry(QRect(keydata['calcBegin'], 0, keydata['calcWidth'],  row['calcHeight']))
                        keydata['QWidget'].setStyleSheet(self.fixStyleSheet(keydata['style'], fontsize))
                    except KeyError:
                        pass
        self.show()

    def fixStyleSheet(self, stylesheet, fontsize):
        if stylesheet == '': return stylesheet
        #print ('in: ' + stylesheet)
        r = re.compile(r"font-size\s*:\s*(\d+)\%")
        i = r.finditer(stylesheet)
        for m in i:
            stylesheet = stylesheet.replace(m.group(0), 'font-size: ' + str( int ( (fontsize / 100) * int(m.group(1)) ) ) + 'px')
        #print ('out: ' + stylesheet)
        return stylesheet

    def resizeEvent(self, event):
        QWidget.resizeEvent(self, event)
        self.calcKeyboard()
        self.positionEverything()

    def parseAction(self, action):
        l = action.split(':', 1)
        if len(l) == 2:
            return ( l[0], l[1] )
        else:
            return ( l[0], None )


    # Button handling

    def pressedButton(self, button):
        try:
            button.data['longpress']
            self.longpresswait = True
            if self.keytimer:
                self.keytimer.stop()
                self.keytimer.deleteLater()
            self.keytimer = QTimer()
            self.keytimer.setSingleShot(True)
            self.keytimer.timeout.connect(partial(self.longPress, button))
            self.keytimer.start(500)
        except KeyError:
            self.doAction(button.data['action'], button, 1)

    def releasedButton(self, button):
        if self.keytimer:
            self.keytimer.stop()
        if self.longpresswait:
            self.longpresswait = False
            self.doAction(button.data['action'], button, 1)
        self.doAction(button.data['action'], button, 0)

    def longPress(self, button):
        if self.keytimer:
            self.keytimer.stop()
        self.longpresswait = False
        self.doAction(button.data['longpress'], button, 1)
        self.doAction(button.data['longpress'], button, 0)

    def doAction(self, action, button, down):
        c, a = self.parseAction(action)
        if c == 'view':
            if down:
                self.setView(a)
        if c == 'send':
            self.injectKeys(a, down)
            if not down:
                self.releaseModifiers()
                try:
                    self.setView(button.data['flipback'])
                except KeyError:
                    try:
                        self.setView(self.view['flipback'])
                    except KeyError:
                        pass
        if c == 'modifier' and down:
            if self.modifiers[a] == 0:
                self.modifiers[a] = 1
                self.injectKeys(a, 1)
            else:
                self.modifiers[a] = 0
                self.injectKeys(a, 0)
            self.updateModifiers()
        if c == 'keyboard' and down:
            if not a == "":
                self.setKeyboard(a)
            elif len(self.kbds) > 1:
                self.setKeyboard('chooser')

    # From buttons to keypresses

    def injectKeys(self, keystr, down):
        if self.keypipe:
            inject = open(self.keypipe, 'wb', 0)
            keylist = keystr.split("+")
            if down:
                for keycode in keylist:
                    inject.write( keycode.encode() + ' 1\n'.encode())
            else:
                for keycode in reversed(keylist):
                    inject.write( keycode.encode() + ' 0\n'.encode())
            inject.flush()
            inject.close()


if __name__ == '__main__':
    main()