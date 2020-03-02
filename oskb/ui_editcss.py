# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'EditCSS.ui'
#
# Created by: PyQt5 UI code generator 5.14.1
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_EditCSS(object):
    def setupUi(self, EditCSS):
        EditCSS.setObjectName("EditCSS")
        EditCSS.resize(515, 401)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(EditCSS.sizePolicy().hasHeightForWidth())
        EditCSS.setSizePolicy(sizePolicy)
        EditCSS.setMinimumSize(QtCore.QSize(515, 401))
        EditCSS.setMaximumSize(QtCore.QSize(515, 401))
        self.buttonBox = QtWidgets.QDialogButtonBox(EditCSS)
        self.buttonBox.setGeometry(QtCore.QRect(150, 360, 341, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Save)
        self.buttonBox.setObjectName("buttonBox")
        self.maintabs = QtWidgets.QTabWidget(EditCSS)
        self.maintabs.setGeometry(QtCore.QRect(20, 10, 481, 341))
        self.maintabs.setObjectName("maintabs")
        self.tab = QtWidgets.QWidget()
        self.tab.setObjectName("tab")
        self.defaultcss = QtWidgets.QTextEdit(self.tab)
        self.defaultcss.setGeometry(QtCore.QRect(10, 10, 451, 291))
        self.defaultcss.setAcceptDrops(False)
        self.defaultcss.setReadOnly(True)
        self.defaultcss.setAcceptRichText(False)
        self.defaultcss.setObjectName("defaultcss")
        self.maintabs.addTab(self.tab, "")
        self.tab_2 = QtWidgets.QWidget()
        self.tab_2.setObjectName("tab_2")
        self.keyboardcss = QtWidgets.QTextEdit(self.tab_2)
        self.keyboardcss.setGeometry(QtCore.QRect(10, 10, 451, 291))
        self.keyboardcss.setAcceptDrops(False)
        self.keyboardcss.setReadOnly(False)
        self.keyboardcss.setAcceptRichText(False)
        self.keyboardcss.setObjectName("keyboardcss")
        self.maintabs.addTab(self.tab_2, "")

        self.retranslateUi(EditCSS)
        self.maintabs.setCurrentIndex(1)
        self.buttonBox.accepted.connect(EditCSS.accept)
        self.buttonBox.rejected.connect(EditCSS.reject)
        QtCore.QMetaObject.connectSlotsByName(EditCSS)

    def retranslateUi(self, EditCSS):
        _translate = QtCore.QCoreApplication.translate
        EditCSS.setWindowTitle(_translate("EditCSS", "Stylesheets"))
        self.maintabs.setTabText(
            self.maintabs.indexOf(self.tab), _translate("EditCSS", "default.css (readonly)")
        )
        self.maintabs.setTabText(
            self.maintabs.indexOf(self.tab_2), _translate("EditCSS", "Keyboard Stylesheet")
        )
