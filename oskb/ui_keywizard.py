# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'KeyWizard.ui'
#
# Created by: PyQt5 UI code generator 5.14.1
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_KeyWizard(object):
    def setupUi(self, KeyWizard):
        KeyWizard.setObjectName("KeyWizard")
        KeyWizard.resize(400, 189)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(KeyWizard.sizePolicy().hasHeightForWidth())
        KeyWizard.setSizePolicy(sizePolicy)
        KeyWizard.setModal(True)
        self.label = QtWidgets.QLabel(KeyWizard)
        self.label.setGeometry(QtCore.QRect(30, 20, 341, 141))
        self.label.setAlignment(QtCore.Qt.AlignJustify | QtCore.Qt.AlignTop)
        self.label.setWordWrap(True)
        self.label.setObjectName("label")
        self.lineEdit = QtWidgets.QLineEdit(KeyWizard)
        self.lineEdit.setGeometry(QtCore.QRect(350, 160, 41, 21))
        self.lineEdit.setCursor(QtGui.QCursor(QtCore.Qt.BlankCursor))
        self.lineEdit.setAutoFillBackground(False)
        self.lineEdit.setStyleSheet("background-color: transparent; border:none")
        self.lineEdit.setClearButtonEnabled(False)
        self.lineEdit.setObjectName("lineEdit")

        self.retranslateUi(KeyWizard)
        QtCore.QMetaObject.connectSlotsByName(KeyWizard)

    def retranslateUi(self, KeyWizard):
        _translate = QtCore.QCoreApplication.translate
        KeyWizard.setWindowTitle(_translate("KeyWizard", "Key Wizard"))
        self.label.setText(
            _translate(
                "KeyWizard",
                "This is the Key Wizard. Simply press the key you would like to assign, and the key caption and keycodes will be set automatically. If you want to add functions for long presses or doubleclicks, or if you would like to add more captions, you can always edit the key manually later by doubleclicking it.",
            )
        )
