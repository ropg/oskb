# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ValueEdit.ui'
#
# Created by: PyQt5 UI code generator 5.14.1
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_ValueEdit(object):
    def setupUi(self, ValueEdit):
        ValueEdit.setObjectName("ValueEdit")
        ValueEdit.resize(247, 103)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(ValueEdit.sizePolicy().hasHeightForWidth())
        ValueEdit.setSizePolicy(sizePolicy)
        ValueEdit.setMinimumSize(QtCore.QSize(247, 103))
        ValueEdit.setMaximumSize(QtCore.QSize(247, 103))
        self.buttonBox = QtWidgets.QDialogButtonBox(ValueEdit)
        self.buttonBox.setGeometry(QtCore.QRect(60, 60, 171, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Save)
        self.buttonBox.setObjectName("buttonBox")
        self.doubleSpinBox = QtWidgets.QDoubleSpinBox(ValueEdit)
        self.doubleSpinBox.setGeometry(QtCore.QRect(130, 20, 81, 24))
        self.doubleSpinBox.setDecimals(1)
        self.doubleSpinBox.setMinimum(0.1)
        self.doubleSpinBox.setSingleStep(0.1)
        self.doubleSpinBox.setProperty("value", 0.5)
        self.doubleSpinBox.setObjectName("doubleSpinBox")
        self.label = QtWidgets.QLabel(ValueEdit)
        self.label.setGeometry(QtCore.QRect(10, 20, 111, 21))
        self.label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter)
        self.label.setObjectName("label")

        self.retranslateUi(ValueEdit)
        self.buttonBox.accepted.connect(ValueEdit.accept)
        self.buttonBox.rejected.connect(ValueEdit.reject)
        QtCore.QMetaObject.connectSlotsByName(ValueEdit)

    def retranslateUi(self, ValueEdit):
        _translate = QtCore.QCoreApplication.translate
        ValueEdit.setWindowTitle(_translate("ValueEdit", "Enter Value"))
        self.label.setText(_translate("ValueEdit", "Width:"))
