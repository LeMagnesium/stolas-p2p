from setuptools import setup

setup(
	name="stolas",
	provides=["stolas"],
	version="0.0.5",
	authors=["Lymkwi", "MathisF"],
	url="https://github.com/LeMagnesium/stolas-p2p",
	author_email="mg<dot>minetest<at>gmail<dot>com",
	packages=['stolas'],
	license="CC0",
	description="P2P Communication Client",
	install_requires = [
		'PyQt5'
	]
	platforms=["linux", "linux2", "win32", "cygwin"],
)
