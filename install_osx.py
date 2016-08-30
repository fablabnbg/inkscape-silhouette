#!/usr/bin/env python
'''
Makes installing inkscape_silhouette easier on OSX

This installer adds the extension to the user's local Inkscape extensions rather
than inside the Inkscape.app bundle. This should, in theory, allow it to survive
between inscape upgrades.

@author: Brian Bustin
@contact: brian at bustin.us
'''
import os, sys, shutil, logging, subprocess

logger = logging.getLogger(__name__)

prerequisites = ["lxml", "pyusb", "libusb1"]
extensions_dir = os.path.join(os.path.expanduser("~"), ".config", "inkscape", "extensions")
extension_files = ["sendto_silhouette.inx", "sendto_silhouette.py", "silhouette"]

def install_inkscape_silhouette():
	try:
		logger.info("inkscape_silhouette install starting")

		# make sure this is os x
		logger.debug("making sure running on OS X")
		sys_platform = sys.platform.lower()
		logger.debug("platform: %s", sys_platform)
		if not sys_platform.startswith('darwin'):
			logger.error("Installer only works with OS X")
			return

		if not os.path.isdir(extensions_dir):
			logger.info("creating extensions dir %s", extensions_dir)
			os.makedirs(extensions_dir)

		install_prerequisites()
		install_extension()
		check_libusb()
		logger.info("inkscape_silhouette extension install ended")
	except Exception as ex:
		logger.warning("inkscape_silhouette install was unsuccessful. Please check previous messages for the cause. Details: %s", ex)


def install_prerequisites():
	logger.info("installing inkscape_silhouette prerequisites")
	for prerequisite in prerequisites:
		logger.debug("installing %s", prerequisite)
		try:
			return_code = subprocess.call("easy_install {}".format(prerequisite), shell=True)
			if return_code > 0:
				raise OSError("command returned code {}, try running again using sudo".format(return_code))
		except OSError:
			logger.error("unable to install module. Try running 'easy_install %s' manually", prerequisite)
			raise

def check_libusb():
	logger.info("making sure libusb is installed")
	try:
		import usb.core
	except ImportError:
		logger.error("pyusb is not installed. Install script usually fails here on first attempt. Running it again should allow installation to complete.")
		raise

	try:
		usb.core.find()
	except usb.core.NoBackendError:
		logger.error("libusb is probably not installed. Refer to the instructions in README.md to install it.")
		raise
	except Exception as ex:
		logger.error("something is not right with either pyusb or libusb. Details: %s", ex)
		raise

def install_extension():
	logger.info("installing extension")
	for file in extension_files:
		path = os.path.join(os.getcwd(), file)
		if os.path.isfile(path):
			logger.debug("copying %s => %s", path, extensions_dir)
			shutil.copy(path, extensions_dir)
		else:
			destination_dir = os.path.join(extensions_dir, file)
			if os.path.isdir(destination_dir):
				logger.info("directory already exists '%s'. Removing it and recreating it.", destination_dir)
				shutil.rmtree(destination_dir)
			logger.debug("copying %s => %s", path, destination_dir)
			shutil.copytree(path, destination_dir)

def uninstall_extension():
	logger.info("uninstalling extension")
	for file in extension_files:
		file_path = os.path.join(extensions_dir, file)
		logger.debug("deleting %s", file_path)
		try:
			os.remove(file_path)
		except OSError:
			logger.info("unable to delete %s. It may have been previously removed or was never installed", file_path)

if __name__ == "__main__":
	import logging.handlers

	log_level = logging.INFO

	# set up logging
	logger.setLevel(log_level)
	log_console = logging.StreamHandler()
	log_console.setLevel(log_level)
	log_formatter = logging.Formatter('%(levelname)s: %(message)s')
	log_console.setFormatter(log_formatter)
	logger.addHandler(log_console)

	# run installer
	install_inkscape_silhouette()

