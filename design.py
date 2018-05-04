import ctypes
ctypes.CDLL("libGL.so.1", mode=ctypes.RTLD_GLOBAL)

from PyQt5 import QtCore, QtGui , QtWidgets , QtWebEngineWidgets

from PyQt5.QtWidgets import QMessageBox, QAbstractScrollArea, QWidget, QGridLayout, QPushButton, QApplication, QLineEdit, QMenu, QAction, QSplitter
from PyQt5.QtGui import QIcon

import time
import sqlite3
import os
import os.path

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

def find_storage_directory():
	if os.name == "nt":
		# Use env
		return os.environ.get("APPDATA", "") + os.sep + "Stolas"
	elif os.name == "posix":
		return os.environ.get("HOME", "") + os.sep + ".stolas"
	else:
		#TODO: Do other platforms
		return ""

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

from stolas.stolas import Stolas
from stolas.protocol import Message
from stolas.utils import b2i, i2b
class Ui_Form(QtWidgets.QMainWindow):
	_storage_directory = find_storage_directory()
	def setupUi(self):
		# Here be database stuff
		if not os.path.isdir(self._storage_directory):
			os.mkdir(self._storage_directory)

		self.conn = sqlite3.connect(self._storage_directory + os.sep + "data.db")
		self.cursor = self.conn.cursor()
		self.cursor.execute('''CREATE TABLE IF NOT EXISTS inbox(
		     uuid TEXT PRIMARY KEY,
		     timestamp INT,
			 channel TEXT,
			 message BLOB
			 )''')
		self.conn.commit()

		# Qt Initialization
		self.central = QtWidgets.QWidget(None)
		self.setObjectName(_fromUtf8("Form"))
		self.resize(1000, 800)
		self.main_layout = QGridLayout(self.central)
		#self.setLayout(self.main_layout)
		self.webView = QtWebEngineWidgets.QWebEngineView()
		#self.webView.setGeometry(QtCore.QRect(120, 10, 271, 241))
		self.webView.setUrl(QtCore.QUrl(_fromUtf8("about:blank")))
		self.webView.setObjectName(_fromUtf8("webView"))
		self.pushButton = QPushButton("Send Message")
		self.pushButton.setIcon(QIcon.fromTheme("document-send"))
		#self.pushButton.setGeometry(QtCore.QRect(320, 260, 75, 31))
		self.pushButton.setObjectName(_fromUtf8("pushButton"))
		self.textEdit = QtWidgets.QTextEdit()
		self.textEdit.setGeometry(QtCore.QRect(20, 260, 291, 31))
		self.textEdit.setObjectName(_fromUtf8("textEdit"))
		self.inboxTable = QtWidgets.QTableWidget()
		#from PyQt5.QtWidgets import QSizePolicy
		self.inboxTable.horizontalHeader().setStretchLastSection(True)
		from PyQt5.QtWidgets import QAbstractItemView
		self.inboxTable.setSelectionBehavior(QAbstractItemView.SelectRows)

		self.pushButton.pressed.connect(self.sendmessage)

		self.stolas = Stolas(logging=True, logdown=True)
		self.stolas.start()
		self.stolas.networker.peer_add(("localhost", 62538))
		print("Stolas connected")
		print(self.stolas.networker.peers)

		self.destroyed.connect(self.close_stolas)
		#self.aboutToQuit.connect(self.close_stolas)

		"""self.main_layout.addWidget(self.pushButton, 3, 0)
		#self.main_layout.addWidget(self.pushButton)
		self.main_layout.addWidget(self.textEdit, 0, 1)
		self.main_layout.addWidget(self.inboxTable, 0, 0, 3, 1)
		#self.main_layout.addWidget(self.inboxList)
		self.main_layout.addWidget(self.webView, 1, 1, 2, 2)
		#self.main_layout.addWidget(self.webView)"""
		splitver = QSplitter()
		splitver.setOrientation(QtCore.Qt.Vertical)
		splitver.addWidget(self.textEdit)
		splitver.addWidget(self.webView)
		splithor = QSplitter()
		splithor.addWidget(self.inboxTable)
		splithor.addWidget(splitver)

		self.main_layout.addWidget(splithor)

		self.create_menubar()
		self.create_list_view()
		self.stolas.mpile.register_on_add(lambda x: self.on_new_message(x))
		print("Hook registration complete")

		#self.retranslateUi()
		self.setCentralWidget(self.central)
		print("Central Widget set")
		QtCore.QMetaObject.connectSlotsByName(self)
		print("Initialization complete")

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


		self.debugmenu = QMenu(_fromUtf8("Debug"))
		self.debugacts = {}

		self.debugacts["connect"] = QAction(QIcon.fromTheme("network-transmit-receive"), _fromUtf8("Connect to Peer..."))
		self.debugacts["connect"].setShortcut(QtCore.Qt.Key_C | QtCore.Qt.ControlModifier | QtCore.Qt.MetaModifier)
		self.debugacts["connect"].triggered.connect(self.debug_connect_dialog)
		self.debugmenu.addAction(self.debugacts["connect"])

		self.menuBar().addMenu(self.debugmenu)

	def debug_connect_dialog(self):
		textenter = QtWidgets.QInputDialog.getText(self, _fromUtf8("Debug Peer Connect..."),
			_fromUtf8("Enter Peer Tuple"), QLineEdit.Normal)

		if textenter[1]:
			self.stolas.networker.peer_add((textenter[0].split(",")[0], int(textenter[0].split(",")[1])))
			print("Added")

	def delete_current_item_from_listview(self):
		reply = QMessageBox.question(self, "Message Deletion", "Are you sure you want to permanently remove those message?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
		if reply == QMessageBox.No:
			return

		select = self.inboxTable.selectionModel()

		# Delete from db
		for item in select.selectedRows():
			uuid = self.inboxTable.item(item.row(), 0).data(QtCore.Qt.UserRole)
			self.cursor.execute('DELETE from inbox WHERE uuid=?', (uuid,))
			print("Removing", uuid)

		self.conn.commit()

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
		#self.inboxTable.setSelectionBehaviour(QAbstractItemView.SelectItems);
		#self.inboxTable.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
		self.cursor.execute("""SELECT uuid, timestamp, channel, message FROM inbox""")
		for row in self.cursor.fetchall():
			self.add_message_to_listview(row[0], row[1], row[2], row[3])
		# Signals & Slots
		self.inboxTable.itemSelectionChanged.connect(self.show_message)
		pass

	def show_message(self):
		if len(self.inboxTable.selectedItems()) == 0:
			# The list's empty
			self.webView.setHtml("")
			return

		usig = self.inboxTable.selectedItems()[0].data(QtCore.Qt.UserRole)
		print("Querying {}...".format(usig[:50]))
		self.cursor.execute("""SELECT message FROM inbox WHERE uuid=?""",(usig,))
		message_var = (self.cursor.fetchone() or [None])[0]
		if message_var != None:
			self.webView.setHtml(message_var.decode("utf8"))
		else:
			self.webView.setHtml("<h1>Error</h1><p>An error occured while loading the message</p>")

	def close_stolas(self):
		self.stolas.stop()

	def add_message_to_listview(self, usig, timestamp, channel, payload):
		print("Adding {}...".format(usig[:50]))
		row = self.inboxTable.rowCount()
		self.inboxTable.insertRow(row)

		citem = QtWidgets.QTableWidgetItem(channel)
		citem.setData(QtCore.Qt.UserRole, usig)
		self.inboxTable.setItem(row, 0, citem)

		titem = QtWidgets.QTableWidgetItem(time.strftime("%d/%m/%Y %H:%M", time.localtime(timestamp)))
		self.inboxTable.setItem(row, 1, titem)

		litem = QtWidgets.QTableWidgetItem(TitleFinder(payload.decode("utf8")).get_title_or_None())
		self.inboxTable.setItem(row, 2, litem)

	def on_new_message(self, message):
		uuid = message.usig()
		timestamp = message.get_timestamp()
		channel = message.get_channel()
		payload = message.get_payload()

		# We can't use "self" because this is executed in another thread
		conn = sqlite3.connect(self._storage_directory + os.sep + "data.db")
		cursor = conn.cursor()
		cursor.execute("""INSERT INTO inbox(uuid, timestamp, channel, message) VALUES(?, ?, ?, ?)""",(uuid, timestamp, channel, payload))
		conn.commit()
		self.add_message_to_listview(uuid, timestamp, channel, payload)

	def sendmessage(self):
		text = self.textEdit.toPlainText()
		print("Lentext: ", len(text))
		reply = QMessageBox.Yes
		if len(text) == 0:
			reply = dialog = QMessageBox.question(self, "Empty Message", "Are you sure you want to send an empty message?", QMessageBox.Yes | QMessageBox.No)

		if reply == QMessageBox.Yes:
			msg = Message(payload=text.encode("utf8"), ttl=120)
			self.stolas.message_broadcast(msg)
			self.textEdit.clear()

	def retranslateUi(self):
		Form.setWindowTitle(_translate("Form", "Form", None))
		self.pushButton.setText(_translate("Form", "PushButton", None))


if __name__ == "__main__":
	import sys
	app = QApplication(sys.argv)
	gui = Ui_Form()
	gui.setupUi()
	print("Done")
	gui.show()
	print("Shown")
	val = app.exec_()
	gui.close_stolas()
	sys.exit(val)
