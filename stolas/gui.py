import ctypes
ctypes.CDLL("libGL.so.1", mode=ctypes.RTLD_GLOBAL)

from PyQt5 import QtCore, QtGui , QtWidgets , QtWebEngineWidgets

from PyQt5.QtWidgets import QInputDialog
from PyQt5.QtWidgets import QMessageBox, QAbstractScrollArea, QWidget, QGridLayout, QPushButton, QApplication, QLineEdit, QMenu, QAction, QSplitter
from PyQt5.QtGui import QIcon

import time
import os
import os.path

from pkg_resources import resource_filename

try:
	_fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
	def _fromUtf8(s):
		return s


try:
	_encoding = QApplication.UnicodeUTF8
	def _translate(context, text, disambig):
		return QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
	def _translate(context, text, disambig):
		return QApplication.translate(context, text, disambig)

from html.parser import HTMLParser
class TitleFinder(HTMLParser):
	def __init__(self, content):
		HTMLParser.__init__(self)
		self.title_found = None
		self.seeking_title = False
		self.feed(content)

	def get_title_or_None(self):
		return self.title_found

	def handle_starttag(self, tag, attrs):
		if tag == "title":
			self.seeking_title = True

	def handle_data(self, data):
		if self.seeking_title:
			self.title_found = data
			self.seeking_title = False

class QHorizontalLine(QtWidgets.QFrame):
	def __init__(self, **kwargs):
		super().__init__(self, **kwargs)
		self.setFrameShape(QtWidgets.QFrame.HLine)
		self.setFrameShadow(QtWidgets.QFrame.Sunken)

class QVerticalLine(QtWidgets.QFrame):
	def __init__(self, **kwargs):
		super().__init__(self, **kwargs)
		self.setFrameShape(QtWidgets.QFrame.VLine)
		self.setFrameShadow(QtWidgets.QFrame.Sunken)

from stolas.stolas import Stolas
from stolas.protocol import Message
from stolas.utils import b2i, i2b
class StolasGUI(QtWidgets.QMainWindow):
	def setupUi(self, **stolaskwargs):

		self.enable_logs = stolaskwargs.get("guilog", False)

		self.stolas = Stolas(**stolaskwargs)
		self.inbox = self.stolas.inbox
		self.stolas.start()
		self.log("Stolas online")
		self.destroyed.connect(self.close_stolas)

		# Qt Initialization
		self.central = QtWidgets.QWidget(None)
		self.setObjectName(_fromUtf8("Form"))
		self.resize(1000, 800)
		self.setWindowIcon(QIcon(resource_filename("stolas.resources.icons", "icon64.png")))
		self.setWindowTitle("Stolas")
		self.main_layout = QGridLayout(self.central)

		self.webView = QtWebEngineWidgets.QWebEngineView()
		self.webView.setUrl(QtCore.QUrl(_fromUtf8("about:blank")))
		self.webView.setObjectName(_fromUtf8("webView"))

		self.pushButton = QPushButton("Send Message")
		self.pushButton.setIcon(QIcon.fromTheme("document-send"))
		self.pushButton.setObjectName(_fromUtf8("pushButton"))
		self.pushButton.pressed.connect(self.sendmessage)

		self.textEdit = QtWidgets.QTextEdit()
		self.textEdit.setGeometry(QtCore.QRect(20, 260, 291, 31))
		self.textEdit.setObjectName(_fromUtf8("textEdit"))

		self.ttlSpin = QtWidgets.QSpinBox()
		self.ttlSpin.setPrefix("TTL:")
		self.ttlSpin.setMaximumSize(self.ttlSpin.size()/2)
		self.ttlSpin.setMinimum(60)
		self.ttlSpin.setMaximum(223200)
		self.ttlSpin.setValue(120)
		self.ttlSpin.setSuffix(" secs")

		self.chanLabel = QtWidgets.QLabel()
		self.chanLabel.setText("Channel: ")
		self.chanLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

		self.chanCombox = QtWidgets.QComboBox()
		self.chanCombox.addItems(self.stolas.tuned_channels)
		self.stolas.register_on_channel_tune_in((lambda x: self.chanCombox.addItem(x)))
		self.stolas.register_on_channel_tune_out((lambda x: self.chanCombox.removeItem(self.chanCombox.findText(x))))

		self.inboxTable = QtWidgets.QTableWidget()
		self.inboxTable.horizontalHeader().setStretchLastSection(True)
		self.inboxTable.horizontalHeader().setHighlightSections(False)
		self.inboxTable.verticalHeader().setVisible(False)
		from PyQt5.QtWidgets import QAbstractItemView
		self.inboxTable.setSelectionBehavior(QAbstractItemView.SelectRows)

		splitver = QSplitter()
		splitver.setOrientation(QtCore.Qt.Vertical)
		datahor = QSplitter()
		datahor.setOrientation(QtCore.Qt.Horizontal)
		datahor.addWidget(self.ttlSpin)
		datahor.addWidget(self.chanLabel)
		datahor.addWidget(self.chanCombox)
		splitver.addWidget(self.textEdit)
		splitver.addWidget(datahor)
		splitver.addWidget(self.webView)
		splithor = QSplitter()
		splithor.addWidget(self.inboxTable)
		splithor.addWidget(splitver)

		self.main_layout.addWidget(splithor)

		self.create_menubar()
		self.create_list_view()
		self.stolas.register_on_new_message(
			lambda x, y:
				self.add_message_to_listview(x, y["timestamp"], y["channel"], y["payload"])
		)
		self.log("Hook registration complete")

		#self.retranslateUi()
		self.setCentralWidget(self.central)
		self.log("Central Widget set")
		QtCore.QMetaObject.connectSlotsByName(self)
		self.log("Initialization complete")

	def log(self, *args, **kwargs):
		if self.enable_logs:
			print(*args, **kwargs)

	def create_menubar(self):
		#self.menubar = QtWidgets.QMenuBar(self)
		self.filemenu = QMenu(_fromUtf8("File"))
		self.fileacts = {}

		self.fileacts["exit"] = QAction(QIcon.fromTheme("application-exit"), _fromUtf8("Quit"))
		self.fileacts["exit"].setShortcut(QtCore.Qt.Key_Q | QtCore.Qt.ControlModifier)
		self.fileacts["exit"].triggered.connect(self.close)
		self.filemenu.addAction(self.fileacts["exit"])

		self.menuBar().addMenu(self.filemenu)


		self.itemmenu = QMenu(_fromUtf8("Message"))
		self.itemacts = {}

		self.itemacts["send"] = QAction(QIcon.fromTheme("document-send"), _fromUtf8("Send"))
		self.itemacts["send"].setShortcut(QtCore.Qt.Key_M | QtCore.Qt.ControlModifier)
		self.itemacts["send"].triggered.connect(self.sendmessage)
		self.itemmenu.addAction(self.itemacts["send"])

		self.itemacts["delete"] = QAction(QIcon.fromTheme("edit-delete"), _fromUtf8("Delete"))
		self.itemacts["delete"].setShortcut(QtCore.Qt.ControlModifier | QtCore.Qt.Key_Delete)
		self.itemacts["delete"].triggered.connect(self.delete_current_item_from_listview)
		self.itemmenu.addAction(self.itemacts["delete"])

		self.menuBar().addMenu(self.itemmenu)

		self.chanmenu = QMenu(_fromUtf8("Channel"))
		self.chanacts = {}

		self.chanacts["tune_in"] = QAction(QIcon.fromTheme("network-transmit-receive"), _fromUtf8("Tune in..."))
		self.chanacts["tune_in"].setShortcut(QtCore.Qt.Key_I | QtCore.Qt.ControlModifier)
		self.chanacts["tune_in"].triggered.connect(self.channel_tune_in)
		self.chanmenu.addAction(self.chanacts["tune_in"])

		self.chanacts["tune_out"] = QAction(QIcon.fromTheme("network-error"), _fromUtf8("Tune out..."))
		self.chanacts["tune_out"].setShortcut(QtCore.Qt.Key_O | QtCore.Qt.ControlModifier)
		self.chanacts["tune_out"].triggered.connect(self.channel_tune_out)
		self.chanacts["tune_out"].setEnabled(self.chanCombox.count() > 1)
		self.chanmenu.addAction(self.chanacts["tune_out"])

		self.menuBar().addMenu(self.chanmenu)


		self.debugmenu = QMenu(_fromUtf8("Debug"))
		self.debugacts = {}

		self.debugacts["connect"] = QAction(QIcon.fromTheme("network-wireless"), _fromUtf8("Connect to Peer..."))
		self.debugacts["connect"].setShortcut(QtCore.Qt.Key_C | QtCore.Qt.ControlModifier | QtCore.Qt.MetaModifier)
		self.debugacts["connect"].triggered.connect(self.debug_connect_dialog)
		self.debugmenu.addAction(self.debugacts["connect"])

		self.menuBar().addMenu(self.debugmenu)

	def channel_tune_in(self):
		value, ok = QInputDialog.getText(self, _fromUtf8("Channel Tune In..."), _fromUtf8("What channel do you want to tune into?"), QLineEdit.Normal, "")
		if ok:
			self.stolas.tune_in(value)
			self.chanCombox.setCurrentIndex(self.chanCombox.findText(value))
			self.chanacts["tune_out"].setEnabled(True)

	def channel_tune_out(self):
		value, ok = QInputDialog.getItem(self, _fromUtf8("Channel Tune Out..."), _fromUtf8("What channel do you wish to tune out from?"), [x for x in self.stolas.tuned_channels if x != ""], 0, False)
		if ok:
			self.stolas.tune_out(value)
			self.chanacts["tune_out"].setEnabled(self.chanCombox.count() > 1)

	def debug_connect_dialog(self):
		textenter = QtWidgets.QInputDialog.getText(self, _fromUtf8("Debug Peer Connect..."),
			_fromUtf8("Enter Peer Tuple"), QLineEdit.Normal)

		if textenter[1] and "," in textenter:
			self.stolas.networker.peer_add((textenter[0].split(",")[0], int(textenter[0].split(",")[1])))
			self.log("Added")

	def delete_current_item_from_listview(self):
		reply = QMessageBox.question(self, "Message Deletion", "Are you sure you want to permanently remove those message?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
		if reply == QMessageBox.No:
			return

		select = self.inboxTable.selectionModel()

		# Delete from db
		for item in select.selectedRows():
			uuid = self.inboxTable.item(item.row(), 0).data(QtCore.Qt.UserRole)
			self.stolas.remove_inbox_message(uuid)
			self.log("Removing {}...".format(uuid[:50]))

		offset = 0
		oldrow = -1
		# Delete from list
		for item in select.selectedRows():
			if oldrow == -1:
				oldrow = item.row()
			elif oldrow < item.row():
				offset += 1
			self.inboxTable.removeRow(item.row() - offset)

	def create_list_view(self):
		self.inboxTable.setGeometry(QtCore.QRect(20, 10, 91, 241))
		self.inboxTable.setObjectName(_fromUtf8("listTable"))
		for i in range(3):
			self.inboxTable.insertColumn(i)
		self.inboxTable.setHorizontalHeaderLabels(["Channel", "Date", "Title"])
		for uuid, msg in self.inbox:
			self.add_message_to_listview(uuid, msg["timestamp"], msg["channel"], msg["payload"])
		# Signals & Slots
		self.inboxTable.itemSelectionChanged.connect(self.show_message)

	def show_message(self):
		if len(self.inboxTable.selectedItems()) == 0:
			# The list's empty
			self.webView.setHtml("")
			return

		usig = self.inboxTable.selectedItems()[0].data(QtCore.Qt.UserRole)
		self.log("Querying {}...".format(usig[:50]))
		message_var = self.inbox.get(usig)
		if message_var != None:
			self.webView.setHtml(message_var["payload"].decode("utf8"))
		else:
			self.webView.setHtml("<h1>Error</h1><p>An error occured while loading the message</p>")

	def close_stolas(self):
		self.stolas.stop()

	def add_message_to_listview(self, usig, timestamp, channel, payload):
		self.log("Adding {}...".format(usig[:50]))
		row = self.inboxTable.rowCount()
		self.inboxTable.insertRow(row)

		citem = QtWidgets.QTableWidgetItem(channel)
		citem.setData(QtCore.Qt.UserRole, usig)
		self.inboxTable.setItem(row, 0, citem)

		titem = QtWidgets.QTableWidgetItem(time.strftime("%d/%m/%Y %H:%M", time.localtime(timestamp)))
		self.inboxTable.setItem(row, 1, titem)

		litem = QtWidgets.QTableWidgetItem(TitleFinder(payload.decode("utf8")).get_title_or_None())
		self.inboxTable.setItem(row, 2, litem)

		for item in [citem, titem, litem]:
			item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEditable)

	def sendmessage(self):
		payload = self.textEdit.toPlainText().encode("utf8")
		ttl = self.ttlSpin.value()
		channel = self.chanCombox.currentText()

		self.log("Lentext: ", len(payload))
		reply = QMessageBox.Yes
		if len(payload) == 0:
			reply = dialog = QMessageBox.question(self, "Empty Message", "Are you sure you want to send an empty message?", QMessageBox.Yes | QMessageBox.No)

		if reply == QMessageBox.Yes:
			self.stolas.send_message(channel, payload, ttl)
			self.textEdit.clear()

	def retranslateUi(self):
		pass


if __name__ == "__main__":
	import sys
	app = QApplication(sys.argv)
	gui = StolasGUI()
	gui.setupUi()
	gui.show()
	val = app.exec_()
	gui.close_stolas()
	sys.exit(val)
