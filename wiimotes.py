#!/usr/bin/python
import cwiid
import time
import sys
from hid_wiimote import WiimoteHID, WiimoteContainer
from threading import Thread

# Hey StackOverflow !
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class WiimoteSearch(Thread):
	def __init__(self, usb_container):
		Thread.__init__(self)
		self.usb_container = usb_container
		self.should_stop = False

	def run(self):	
		max_wiimotes = 4
		while not self.should_stop:
			if (self.usb_container.devices_count == 0):
				print '[' + bcolors.OKBLUE + 'WiimoteSearch' + bcolors.ENDC + '] Looking for wiimotes (Press 1+2)'
				start = time.time()
				while (self.usb_container.devices_count < max_wiimotes and time.time() - start <= 60 and not self.should_stop):
					try:
						wiimote = cwiid.Wiimote()
						pass
					except (KeyboardInterrupt, SystemExit):
						sys.exit(0)
					except:
						time.sleep(1)
						continue
					else:
						print '[' + bcolors.OKBLUE + 'WiimoteSearch' + bcolors.ENDC + '] Found wiimote, assigning number #' + str(self.usb_container.devices_count+1)
						wiimote.led = eval('cwiid.LED' + str(self.usb_container.devices_count+1) + '_ON')
						wiimote.rpt_mode = cwiid.RPT_EXT | cwiid.RPT_BTN | cwiid.RPT_STATUS | cwiid.RPT_ACC	
						wiimote.enable(cwiid.FLAG_MESG_IFC);
						wiimote.rumble = True
						time.sleep(.15)
						wiimote.rumble = False

						device = WiimoteHID(self.usb_container)
						wiimote.mesg_callback = device.wiimotecallback
						device.setWiimote(wiimote, self.usb_container.devices_count+1)
						self.usb_container.add_usb_device(device)
						pass
				if (self.should_stop): print '[' + bcolors.OKBLUE + 'WiimoteSearch' + bcolors.ENDC + '] Was asked to stop, stopping...'
				else: print '[' + bcolors.OKBLUE + 'WiimoteSearch' + bcolors.ENDC + '] More than ' + str(max_wiimotes) + ' wiimotes were connected or 60 seconds passed, ending search'
			time.sleep(10)

	def getUsbContainer(self):
		return self.usb_container


def main():	
	usb_container = WiimoteContainer()
	wiimote_search = WiimoteSearch(usb_container)
	wiimote_search.start()
	try:
		usb_container.run()
	except (KeyboardInterrupt, SystemExit):
		print '\n[' + bcolors.WARNING + 'Main' + bcolors.ENDC + '] Received KeyboardInterrupt, shutting down'
		print '[' + bcolors.WARNING + 'Main' + bcolors.ENDC + '] "Detaching" all devices'
		usb_container.detach_all()
		print '[' + bcolors.WARNING + 'Main' + bcolors.ENDC + '] SocketServer shutting down'
		usb_container.server.shutdown()
		print '[' + bcolors.WARNING + 'Main' + bcolors.ENDC + '] Wiimote search thread shutting down'
		wiimote_search.should_stop = True
		wiimote_search.join()
		print '[' + bcolors.WARNING + 'Main' + bcolors.ENDC + '] Reached end'	
		sys.exit(0)
main()
