# PythonUSBIP
This work is heavily based on [this repository](https://github.com/lcgamboa/USBIP-Virtual-USB-Device).
However, there a many differences, mainly because this new version supports any number of devices.
It is still missing a proper detach protocol.

## Usage
The whole USBIP code is in the USBIP.py file. The best way to understand how to implement a device is to look at how the wiimote example is implemented or to see [the example of lcgamboa's repository](https://github.com/lcgamboa/USBIP-Virtual-USB-Device/blob/master/python/hid-keyboard.py).

## Using with Windows
Using USBIP on Windows can be a huge pain. I have done a lot of research before finally getting it to work correctly. Therefore, here are the things you should know :
* If you've already installed the USBIP driver, uninstall it, it causes BSODs
* If you've already downloaded the USBIP binary, remove it
* Use [this driver & binary](https://sourceforge.net/p/usbip/discussion/418507/thread/86c5e473/) instead (the driver is located in the `output` folder)
* This is not directly related to this post, but if you're having issues attaching a device from Windows to a linux host, this is because usbip has been merged into the kernel since 3.14. However, no need to downgrade, there is [a fix](https://sourceforge.net/p/usbip/discussion/418507/thread/7ff86875/?limit=25&page=5#cd87) !

## Wiimote example
This repository contains a fully fonctionnal USBIP wiimote example. It uses cwiid to communicate with the wiimotes.
Everything is implemented, including using multiple wiimotes and using a nunchuk.
All wiimotes are represented as a Generic USB Joystick with USBIP, they are therefore accessible without any specific driver.
In order to use it, launch `python wiimotes.py` and follow the instructions.

### Wiimote menu
Pressing the HOME button on a wiimote will put it into a "menu" mode. There are four entries that can be selected using the MINUS and PLUS buttons. Activating the selected entry is made by pressing the A button :

1. If nunchuk is plugged, send its values instead of the values of the accelerometer
2. Easy "Mario Kart" switch. Remaps some buttons to use the wiimote as a steering wheel
3. Trigger a new wiimote scan to add new wiimotes (useful in a "headless" system)
4. Disconnect this wiimote
