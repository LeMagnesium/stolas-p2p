#!/usr/bin/python3

# Stolas : Disk Manager utility

import os, random

class FileAccess:
	def __init__(self, fptrs, ident, informer):
		self.fptrs = fptrs
		self.__id = ident
		self.__informer = informer

	def __plural_execute(self, lam):
		return list(map(lam, self.fptrs))

	def flush(self):
		self.fptrs[0].flush()

	def seek(self, position, whence = 0):
		self.__plural_execute(lambda x: x.seek(position, whence))

	def __del__(self):
		self.__informer.delete_access(self.__id)
		self.__plural_execute(lambda x: x.close())

	def read(self, length = -1):
		if length >= 0:
			data = self.fptrs[1].read(length)
		else:
			data = self.fptrs[1].read()
		return data

	def write(self, data):
		length = self.fptrs[0].write(data)
		self.flush()
		self.fptrs[1].seek(len(data), 1)
		return length

	def tell(self):
		return self.fptrs[0].tell()

	def truncate(self):
		self.fptrs[0].truncate()

class DiskCacheManager:
	def __init__(self, **kwargs):
		#self.storage_path = kwargs.get("storage_path", self.__determine_storage_path())
		self.cache_path = kwargs.get("cache_path", self.__determine_cache_path())

		self.registers = []

	def __generate_random_filename(self):
		return hex(random.randrange(2**63, 2**64))[-16:]

	def __attempt_creation(self, dir):
		try:
			os.mkdir(dir)
		except FileExistsError:
			pass

	def delete_access(self, ident):
		if ident in self.registers:
			self.registers.remove(ident)
			os.remove(self.cache_path + ident)

	def create_access(self):
		while True:
			rfile = self.__generate_random_filename()
			if not rfile in self.registers:
				break

		wptr = open(self.cache_path + rfile, "wb")
		rptr = open(self.cache_path + rfile, "rb")
		self.registers.append(rfile)
		return FileAccess((wptr, rptr), rfile, self)

	def __determine_cache_path(self):
		if os.name == "nt":
			path = os.environ["APPDATA"] + "/Stolas/temp"
			self.__attempt_creation(path)
			return path
		elif os.name == "posix":
			self.__attempt_creation("/tmp/stolas/")
			return "/tmp/stolas/"
		else:
			return "." # FIXME: Find other values

global GlobalDiskCacheManager
GlobalDiskCacheManager = DiskCacheManager()
