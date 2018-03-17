# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Form.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui , QtWidgets , QtWebEngineWidgets
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
	_encoding = QtWidgets.QApplication.UnicodeUTF8
	def _translate(context, text, disambig):
		return QtWidgets.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
	def _translate(context, text, disambig):
		return QtWidgets.QApplication.translate(context, text, disambig)

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
		self.main_layout = QtWidgets.QGridLayout(self.central)
		#self.setLayout(self.main_layout)
		self.webView = QtWebEngineWidgets.QWebEngineView()
		#self.webView.setGeometry(QtCore.QRect(120, 10, 271, 241))
		self.webView.setUrl(QtCore.QUrl(_fromUtf8("about:blank")))
		self.webView.setObjectName(_fromUtf8("webView"))
		self.pushButton = QtWidgets.QPushButton("Push Here")
		#self.pushButton.setGeometry(QtCore.QRect(320, 260, 75, 31))
		self.pushButton.setObjectName(_fromUtf8("pushButton"))
		self.textEdit = QtWidgets.QTextEdit()
		self.textEdit.setGeometry(QtCore.QRect(20, 260, 291, 31))
		self.textEdit.setObjectName(_fromUtf8("textEdit"))
		self.listView = QtWidgets.QListWidget()
		self.listView.setGeometry(QtCore.QRect(20, 10, 91, 241))
		self.listView.setObjectName(_fromUtf8("listView"))

		self.pushButton.pressed.connect(self.sendmessage)

		self.stolas = Stolas(logging=True, logdown=True)
		self.stolas.start()
		self.stolas.networker.peer_add(("localhost", 62538))
		print("Stolas connected")
		print(self.stolas.networker.peers)

		self.destroyed.connect(self.close_stolas)
		#self.aboutToQuit.connect(self.close_stolas)

		self.main_layout.addWidget(self.pushButton, 3, 0)
		#self.main_layout.addWidget(self.pushButton)
		self.main_layout.addWidget(self.textEdit, 0, 1)
		self.main_layout.addWidget(self.listView, 0, 0, 3, 1)
		#self.main_layout.addWidget(self.listView)
		self.main_layout.addWidget(self.webView, 1, 1, 2, 2)
		#self.main_layout.addWidget(self.webView)

		self.create_menubar()
		self.create_list_view()
		self.stolas.mpile.register_on_add(lambda x: self.on_new_message(x))

		#self.retranslateUi()
		self.setCentralWidget(self.central)
		QtCore.QMetaObject.connectSlotsByName(self)

	def create_menubar(self):
		#self.menubar = QtWidgets.QMenuBar(self)
		self.filemenu = QtWidgets.QMenu("File")
		self.menuBar().addMenu(self.filemenu)

	def format_message_entry(self, timestamp, channel, content):
		return "[{0}] {1} - {2}".format(channel,
			time.strftime("%d/%m/%Y %H:%M", time.localtime(timestamp)),
			TitleFinder(content.decode("utf8")).get_title_or_None()
		)

	def create_list_view(self):
		self.cursor.execute("""SELECT uuid, timestamp, channel, message FROM inbox""")
		rows = self.cursor.fetchall()
		for row in rows:
			self.recent_msg = self.format_message_entry(row[1], row[2], row	[3])
			self.listView.addItem(self.recent_msg)

	def close_stolas(self):
		self.stolas.stop()

	def on_new_message(self, message):
		uuid = message.usig()
		timestamp = message.get_timestamp()
		channel = message.get_channel()
		payload = message.get_payload()

		self.cursor.execute("""INSERT INTO inbox(uuid, timestamp, channel, message) VALUES(?, ?, ?, ?)""",(uuid, timestamp, channel, payload))
		text = self.format_message_entry(timestamp, channel, payload)
		self.listView.addItem(text)
		self.conn.commit()
		print(message)


	def sendmessage(self):
		msg = Message(payload=self.textEdit.toPlainText().encode("utf8"), ttl=120)
		self.stolas.message_broadcast(msg)
		#assert(len(self.stolas.networker.peers) != 0)
		#print("{}".format(len(self.stolas.networker.peers)))

	def retranslateUi(self):
		Form.setWindowTitle(_translate("Form", "Form", None))
		self.pushButton.setText(_translate("Form", "PushButton", None))


if __name__ == "__main__":
	import sys
	app = QtWidgets.QApplication(sys.argv)
	gui = Ui_Form()
	gui.setupUi()
	gui.show()
	val = app.exec_()
	gui.close_stolas()
	sys.exit(val)
