import socket 
import hashlib
import struct
import logging
from message import iRODSMessage, StartupMessage
from . import MAX_PASSWORD_LENGTH

class iRODSSession(object):
	def __init__(self, host=None, port=None, user=None, zone=None, password=None):
		self.host = host
		self.port = port
		self.user = user
		self.zone = zone
		self.password = password	
		self.socket = None
		self.authenticated = False
		self._connect()

	def __del__(self):
		if self.socket:
			self.disconnect()

	def _send(self, message):
		str = message.pack()
		logging.debug(str)
		return self.socket.send(str)

	def _recv(self):
		return iRODSMessage.recv(self.socket)

	def _connect(self):
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.socket.connect((self.host, self.port))
		main_message = StartupMessage(user=self.user, zone=self.zone)
		msg = iRODSMessage(type='RODS_CONNECT', msg=main_message.pack())
		self._send(msg)
		version_msg = self._recv()

	def disconnect(self):
		disconnect_msg = iRODSMessage(type='RODS_DISCONNECT')
		self._send(disconnect_msg)
		self.socket.close()

	def _login(self):
		# authenticate
		auth_req = iRODSMessage(type='RODS_API_REQ', int_info=703)
		self._send(auth_req)

		# challenge
		challenge = self._recv()
		padded_pwd = struct.pack("%ds" % MAX_PASSWORD_LENGTH, self.password)
		m = hashlib.md5()
		m.update(challenge.msg)
		m.update(padded_pwd)
		encoded_pwd = m.digest()

		encoded_pwd = encoded_pwd.replace('\x00', '\x01')
		pwd_msg = encoded_pwd + self.user + '\x00'
		pwd_request = iRODSMessage(type='RODS_API_REQ', int_info=704, msg=pwd_msg)
		self._send(pwd_request)

		auth_response = self._recv()
		if auth_response.error:
			raise Exception("Unsuccessful login attempt")
		else:
			self.authenticated = True
			logging.debug("Successful login")
