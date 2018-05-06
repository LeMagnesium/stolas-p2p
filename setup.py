from setuptools import setup, find_packages

setup(
	name="stolas",
	provides=["stolas"],
	version="0.0.6",
	author=["Lymkwi", "MathisF"],
	url="https://github.com/LeMagnesium/stolas-p2p",
	author_email="mg<dot>minetest<at>gmail<dot>com",
	packages=find_packages(),
	license="CC0",
	description="P2P Communication Client",
	install_requires = [
		'PyQt5'
	],
	platforms=["linux", "linux2", "win32", "cygwin"],
	include_package_data = True,
	#package_data = {' ': ['*.png']},
	scripts = ["scripts/stolas"]
)
