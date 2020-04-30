# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'KbdProperties.ui'
#
# Created by: PyQt5 UI code generator 5.14.0
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_KbdProperties(object):
    def setupUi(self, KbdProperties):
        KbdProperties.setObjectName("KbdProperties")
        KbdProperties.resize(515, 401)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(KbdProperties.sizePolicy().hasHeightForWidth())
        KbdProperties.setSizePolicy(sizePolicy)
        KbdProperties.setMinimumSize(QtCore.QSize(515, 401))
        KbdProperties.setMaximumSize(QtCore.QSize(515, 401))
        self.buttonBox = QtWidgets.QDialogButtonBox(KbdProperties)
        self.buttonBox.setGeometry(QtCore.QRect(150, 360, 341, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Save)
        self.buttonBox.setObjectName("buttonBox")
        self.maintabs = QtWidgets.QTabWidget(KbdProperties)
        self.maintabs.setGeometry(QtCore.QRect(20, 80, 481, 271))
        self.maintabs.setObjectName("maintabs")
        self.tab = QtWidgets.QWidget()
        self.tab.setObjectName("tab")
        self.defaultcss = QtWidgets.QTextEdit(self.tab)
        self.defaultcss.setGeometry(QtCore.QRect(10, 10, 451, 221))
        self.defaultcss.setAcceptDrops(False)
        self.defaultcss.setReadOnly(True)
        self.defaultcss.setAcceptRichText(False)
        self.defaultcss.setObjectName("defaultcss")
        self.maintabs.addTab(self.tab, "")
        self.tab_2 = QtWidgets.QWidget()
        self.tab_2.setObjectName("tab_2")
        self.keyboardcss = QtWidgets.QTextEdit(self.tab_2)
        self.keyboardcss.setGeometry(QtCore.QRect(10, 10, 451, 221))
        self.keyboardcss.setAcceptDrops(False)
        self.keyboardcss.setReadOnly(False)
        self.keyboardcss.setAcceptRichText(False)
        self.keyboardcss.setObjectName("keyboardcss")
        self.maintabs.addTab(self.tab_2, "")
        self.description = QtWidgets.QLineEdit(KbdProperties)
        self.description.setGeometry(QtCore.QRect(120, 10, 201, 21))
        self.description.setMaxLength(30)
        self.description.setObjectName("description")
        self.layout = QtWidgets.QLineEdit(KbdProperties)
        self.layout.setGeometry(QtCore.QRect(120, 40, 113, 21))
        self.layout.setMaxLength(16)
        self.layout.setObjectName("layout")
        self.label = QtWidgets.QLabel(KbdProperties)
        self.label.setGeometry(QtCore.QRect(20, 10, 91, 21))
        self.label.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label.setObjectName("label")
        self.label_2 = QtWidgets.QLabel(KbdProperties)
        self.label_2.setGeometry(QtCore.QRect(20, 40, 91, 20))
        self.label_2.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_2.setObjectName("label_2")

        self.retranslateUi(KbdProperties)
        self.maintabs.setCurrentIndex(1)
        self.buttonBox.accepted.connect(KbdProperties.accept)
        self.buttonBox.rejected.connect(KbdProperties.reject)
        QtCore.QMetaObject.connectSlotsByName(KbdProperties)

    def retranslateUi(self, KbdProperties):
        _translate = QtCore.QCoreApplication.translate
        KbdProperties.setWindowTitle(_translate("KbdProperties", "Keyboard Properties"))
        self.maintabs.setTabText(self.maintabs.indexOf(self.tab), _translate("KbdProperties", "default.css (readonly)"))
        self.maintabs.setTabText(self.maintabs.indexOf(self.tab_2), _translate("KbdProperties", "Keyboard Stylesheet"))
        self.label.setText(_translate("KbdProperties", "Description:"))
        self.label_2.setText(_translate("KbdProperties", "Layout:"))
