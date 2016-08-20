import time
import random
import datetime
import struct
from USBIP import BaseStucture, USBDevice, InterfaceDescriptor, DeviceConfigurations, EndPoint, USBContainer
import cwiid
from bitarray import bitarray
from bitstring import Bits

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

class HIDClass(BaseStucture):
    _fields_ = [
        ('bLength', 'B', 9),
        ('bDescriptorType', 'B', 0x21),  # HID
        ('bcdHID', 'H'),
        ('bCountryCode', 'B'),
        ('bNumDescriptors', 'B'),
        ('bDescriptorType2', 'B'),
        ('wDescriptionLength', 'H'),
    ]


hid_class = HIDClass(bcdHID=0x0100,  # keyboard
                     bCountryCode=0x0,
                     bNumDescriptors=0x1,
                     bDescriptorType2=0x22,  # Report
                     wDescriptionLength=0x3400)  # Little endian


interface_d = InterfaceDescriptor(bAlternateSetting=0,
                                  bNumEndpoints=1,
                                  bInterfaceClass=0x03,  # class HID
                                  bInterfaceSubClass=0,
                                  bInterfaceProtocol=0, #joystick
                                  iInterface=0)

end_point = EndPoint(bEndpointAddress=0x81,
                     bmAttributes=0x3,
                     wMaxPacketSize=0x0800,  # Little endian
                     bInterval=0xA)  # interval to report


configuration = DeviceConfigurations(wTotalLength=0x2200,
                                     bNumInterfaces=0x1,
                                     bConfigurationValue=0x1,
                                     iConfiguration=0x0,  # No string
                                     bmAttributes=0x80,  # valid self powered
                                     bMaxPower=50)  # 100 mah current

interface_d.descriptions = [hid_class]  # Supports only one description
interface_d.endpoints = [end_point]  # Supports only one endpoint
configuration.interfaces = [interface_d]   # Supports only one interface

class WiimoteContainer(USBContainer):

    def remove_usb_device(self, usb_device):
        USBContainer.remove_usb_device(self, usb_device)
        wiimoteNumber = usb_device.wiimote_number
        for busid, dev in self.usb_devices.iteritems():
            if (dev.wiimote_number > wiimoteNumber):
                dev.updateWiimoteNumber(dev.wiimote_number - 1)

class WiimoteHID(USBDevice):
    vendorID = 0x0079
    productID = 0x0006
    bcdDevice = 0x0
    bcdUSB = 0x0
    bNumConfigurations = 0x1
    bNumInterfaces = 0x1
    bConfigurationValue = 0x1
    configurations = []
    bDeviceClass = 0x0
    bDeviceSubClass = 0x0
    bDeviceProtocol = 0x0
    configurations = [configuration]  # Supports only one configuration
    wiimote = None
    sent = False
    wiimote_number = 0
    finalX = 0
    finalY = 0
    menu_option = -1
    nunchuk_acc = False
    is_in_menu_mode = False
    mk_mode = False

    def setWiimote(self, wm, number):
        self.wiimote = wm
        self.wiimote_number = number

    def updateWiimoteNumber(self, number):
        self.wiimote_number = number
        self.wiimote.led = eval('cwiid.LED' + str(number) + '_ON')

    def __init__(self, container):
        USBDevice.__init__(self, container)
        self.data = bitarray(48, endian='little')
        self.data.setall(False)
        self.start_time = datetime.datetime.now()
        self.isNunchukCalibrated = False
        self.center_x = 1
        self.x_neg_range = 1
        self.x_pos_range = 1

        self.center_y = 1
        self.y_neg_range = 1
        self.y_pos_range = 1

        self.previousAccX = 0
        self.previousAccY = 0

    def generate_hid_report(self):        
        arr = [
            0x05, 0x01,                    # USAGE_PAGE (Generic Desktop)
            0x09, 0x04,                    # USAGE (Joystick)
            0xa1, 0x01,                    # COLLECTION (Application)
            0x09, 0x04,                    #   USAGE (Joystick)
            0xa1, 0x00,                    #   COLLECTION (Physical)
            0x09, 0x30,                    #     USAGE (X)
            0x09, 0x31,                    #     USAGE (Y)
            0x09, 0x32,                    #     USAGE (Z)
            0x09, 0x33,                    #     USAGE (Rx)
            0x75, 0x08,                    #     REPORT_SIZE (8)
            0x95, 0x04,                    #     REPORT_COUNT (4)
            0x46, 0xff, 0x00,              #     PHYSICAL_MAXIMUM (255)
            0x35, 0x00,                    #     PHYSICAL_MINIMUM (0)
            0x15, 0x00,                    #     LOGICAL_MINIMUM (0)
            0x26, 0xff, 0x00,              #     LOGICAL_MAXIMUM (255)
            0x81, 0x02,                    #     INPUT (Data,Var,Abs)
            0x05, 0x09,                    #     USAGE_PAGE (Button)
            0x19, 0x01,                    #     USAGE_MINIMUM (Button 1)
            0x25, 0x01,                    #     LOGICAL_MAXIMUM (1)
            0x15, 0x00,                    #     LOGICAL_MINIMUM (0)
            0x29, 0x10,                    #     USAGE_MAXIMUM (Button 16)
            0x75, 0x01,                    #     REPORT_SIZE (1)
            0x95, 0x10,                    #     REPORT_COUNT (16)
            0x81, 0x02,                    #     INPUT (Data,Var,Abs)
            0xc0,                          #   END_COLLECTION
            0xc0                           # END_COLLECTION
        ]
        return_val = ''
        for val in arr:
            return_val+=chr(val)
        return return_val

    def comp(self,val):
        if val >= 0: 
          return val
        else:
          return 256+val

    def calibrateNunchuk(self):        
        buf = buffer(self.wiimote.read(cwiid.RW_REG | cwiid.RW_DECODE, 0xA40028, 6))
        if (buf == 0): print '[' + bcolors.FAIL + 'WiimoteHID' + bcolors.ENDC + '] #' + str(self.wiimote_number) + '\'s nunchuk calibration failed'
        self.center_x = int(buf[2].encode('hex'), 16)
        self.x_neg_range = (self.center_x - 10) - int(buf[1].encode('hex'), 16)
        self.x_pos_range = int(buf[0].encode('hex'), 16) - (self.center_x + 10)

        self.center_y = int(buf[5].encode('hex'), 16)
        self.y_pos_range = int(buf[3].encode('hex'), 16) - (self.center_y + 10);
        self.y_neg_range = 0 - self.y_pos_range;

    def exitMenuMode(self):
        self.is_in_menu_mode = False
        self.menu_option = -1
        self.wiimote.rumble = True
        time.sleep(.15)
        self.wiimote.rumble = False
        self.wiimote.led = eval('cwiid.LED' + str(self.wiimote_number) + '_ON')
        print '[' + bcolors.OKGREEN + 'WiimoteHID' + bcolors.ENDC + '] #' + str(self.wiimote_number) + ' left menu mode'

    def handleMenuMode(self, msg_list):
        if (self.menu_option == -1):
            print '[' + bcolors.OKGREEN + 'WiimoteHID' + bcolors.ENDC + '] #' + str(self.wiimote_number) + ' entered menu mode'
            self.wiimote.rumble = True
            led = cwiid.LED1_ON
            self.wiimote.led = led
            time.sleep(.05)
            self.wiimote.rumble = False
            time.sleep(.05)
            self.wiimote.rumble = True
            led = cwiid.LED2_ON
            self.wiimote.led = led
            time.sleep(.05)
            self.wiimote.rumble = False
            time.sleep(.05)
            self.wiimote.rumble = True
            led = cwiid.LED3_ON
            self.wiimote.led = led
            time.sleep(.05)
            self.wiimote.rumble = False
            time.sleep(.05)
            self.wiimote.rumble = True
            led = cwiid.LED4_ON
            self.wiimote.led = led
            time.sleep(.05)
            self.wiimote.rumble = False
            time.sleep(.05)
            self.wiimote.rumble = True
            led = cwiid.LED1_ON
            self.wiimote.led = led
            self.menu_option = 1
            self.wiimote.rumble = False
        for mesg in msg_list:
            if mesg[0] == cwiid.MESG_BTN:
                if mesg[1] & cwiid.BTN_HOME:
                    self.exitMenuMode()
                    break
                if mesg[1] & cwiid.BTN_A:
                    if (self.menu_option == 1):
                        if (not self.isNunchukCalibrated and not self.nunchuk_acc):
                            self.wiimote.rumble = True
                            self.wiimote.led = cwiid.LED1_ON | cwiid.LED2_ON | cwiid.LED3_ON | cwiid.LED4_ON
                            time.sleep(.15)
                            self.wiimote.rumble = False
                            time.sleep(1)
                            self.wiimote.led = eval('cwiid.LED' + str(self.menu_option) + '_ON')
                        else:
                            self.nunchuk_acc ^= True
                            print '[' + bcolors.OKGREEN + 'WiimoteHID' + bcolors.ENDC + '] #' + str(self.wiimote_number) + ' changed nunchuk_acc to', self.nunchuk_acc
                        self.exitMenuMode()                        
                        break
                    if (self.menu_option == 2):
                        if (self.nunchuk_acc and self.isNunchukCalibrated):
                            self.wiimote.rumble = True
                            self.wiimote.led = cwiid.LED1_ON | cwiid.LED2_ON | cwiid.LED3_ON | cwiid.LED4_ON
                            time.sleep(.15)
                            self.wiimote.rumble = False
                            time.sleep(1)
                        else:
                            self.mk_mode ^= True
                            print '[' + bcolors.OKGREEN + 'WiimoteHID' + bcolors.ENDC + '] #' + str(self.wiimote_number) + ' changed mk_mode to', self.mk_mode
                        self.exitMenuMode()
                        break
                    if (self.menu_option == 3):
                        self.wiimote.led = cwiid.LED1_ON | cwiid.LED2_ON | cwiid.LED3_ON | cwiid.LED4_ON
                        print '[' + bcolors.WARNING + 'WiimoteHID' + bcolors.ENDC + '] #' + str(self.wiimote_number) + ' asked for a wiimote search'
                        time.sleep(2)
                        try:
                            wiimote = cwiid.Wiimote()
                            pass
                        except:
                            print '[' + bcolors.FAIL + 'WiimoteHID' + bcolors.ENDC + '] #' + str(self.wiimote_number) + '\'s wiimote search failed'
                            self.wiimote.rumble = True
                            self.wiimote.led = 0
                            time.sleep(.1)
                            self.wiimote.led = cwiid.LED1_ON | cwiid.LED2_ON | cwiid.LED3_ON | cwiid.LED4_ON
                            time.sleep(.05)
                            self.wiimote.rumble = False
                            time.sleep(1)
                        else:
                            print '[' + bcolors.OKGREEN + 'WiimoteHID' + bcolors.ENDC + '] #' + str(self.wiimote_number) + '\'s wiimote search found a wiimote, assigning number #' + str(self.usb_container.devices_count+1)
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
                            self.wiimote.led = cwiid.LED3_ON
                            time.sleep(.05)
                            self.wiimote.led = 0
                            time.sleep(.05)
                            self.wiimote.led = cwiid.LED3_ON
                            time.sleep(.05)
                            self.wiimote.led = 0
                            time.sleep(.05)
                            self.wiimote.led = cwiid.LED3_ON

                        self.exitMenuMode()
                        break
                    if (self.menu_option == 4):                        
                        self.exitMenuMode()
                        print '[' + bcolors.WARNING + 'WiimoteHID' + bcolors.ENDC + '] #' + str(self.wiimote_number) + ' initiated disconnect'
                        self.usb_container.remove_usb_device(self)
                        self.wiimote.close()
                        print '[' + bcolors.WARNING + bcolors.BOLD + 'WiimoteHID' + bcolors.ENDC + '] #' + str(self.wiimote_number) + ' disconnected'
                if mesg[1] & cwiid.BTN_PLUS:
                    self.menu_option += 1
                    if self.menu_option >4: self.menu_option = 4
                    self.wiimote.led = eval('cwiid.LED' + str(self.menu_option) + '_ON')
                if mesg[1] & cwiid.BTN_MINUS:
                    self.menu_option -= 1
                    if self.menu_option < 0: self.menu_option = 0
                    self.wiimote.led = eval('cwiid.LED' + str(self.menu_option) + '_ON')

    def wiimotecallback(self, msg_list, id):
        stablePos = Bits(uintle=128,length=8)

        #Define buttons
        btn_A = 0
        btn_B = 1
        btn_PLUS = 2
        btn_MINUS = 3
        btn_1 = 4
        btn_UP = 5
        btn_DOWN = 6
        btn_LEFT = 7
        btn_RIGHT = 8
        btn_2 = 9
        btn_nunC = 10
        btn_nunZ = 11

        if (self.mk_mode):
            btn_A = 9
            btn_B = 1
            btn_1 = 10
            btn_UP = 5
            btn_DOWN = 6
            btn_LEFT = 7
            btn_RIGHT = 8
            btn_2 = 0

        if (self.sent): 
            self.sent = False

            #Reset Nunchuk in case there is none plugged in
            for i in range(8):
                    self.data[i] = stablePos[7-i]
                    self.data[8+i] = stablePos[7-i]

        if (self.is_in_menu_mode):
            self.handleMenuMode(msg_list)
        else:
            self.finalY = 0
            self.finalX = 0
            btn_offset = 32
            for mesg in msg_list:
                if mesg[0] == cwiid.MESG_STATUS:
                    if (not self.isNunchukCalibrated) and mesg[1]['ext_type'] == cwiid.EXT_NUNCHUK:
                        print '[' + bcolors.OKGREEN + 'WiimoteHID' + bcolors.ENDC + '] #' + str(self.wiimote_number) + '\'s nunchuk was plugged, calibrating...'
                        self.isNunchukCalibrated = True
                        self.calibrateNunchuk()
                        print '[' + bcolors.OKGREEN + 'WiimoteHID' + bcolors.ENDC + '] #' + str(self.wiimote_number) + '\'s nunchuk was calibrated'
                    if self.isNunchukCalibrated and mesg[1]['ext_type'] == cwiid.EXT_NONE:
                        print '[' + bcolors.OKGREEN + 'WiimoteHID' + bcolors.ENDC + '] #' + str(self.wiimote_number) + '\'s nunchuk was uunplugged'
                        self.isNunchukCalibrated = False

                if mesg[0] == cwiid.MESG_BTN:
                    if mesg[1] & cwiid.BTN_A:
                        self.data[btn_offset + btn_A] = True
                    else:
                        self.data[btn_offset + btn_A] = False
                    if mesg[1] & cwiid.BTN_B:
                        self.data[btn_offset + btn_B] = True
                    else:
                        self.data[btn_offset + btn_B] = False
                    if mesg[1] & cwiid.BTN_PLUS:
                        self.data[btn_offset + btn_PLUS] = True
                    else:
                        self.data[btn_offset + btn_PLUS] = False
                    if mesg[1] & cwiid.BTN_MINUS:
                        self.data[btn_offset + btn_MINUS] = True
                    else:
                        self.data[btn_offset + btn_MINUS] = False
                    if mesg[1] & cwiid.BTN_1:
                        self.data[btn_offset + btn_1] = True
                    else:
                        self.data[btn_offset + btn_1] = False
                    if mesg[1] & cwiid.BTN_UP:
                        self.data[btn_offset + btn_UP] = True
                    else:
                        self.data[btn_offset + btn_UP] = False
                    if mesg[1] & cwiid.BTN_DOWN:
                        self.data[btn_offset + btn_DOWN] = True
                    else:
                        self.data[btn_offset + btn_DOWN] = False
                    if mesg[1] & cwiid.BTN_LEFT:
                        self.data[btn_offset + btn_LEFT] = True
                    else:
                        self.data[btn_offset + btn_LEFT] = False
                    if mesg[1] & cwiid.BTN_RIGHT:
                        self.data[btn_offset + btn_RIGHT] = True
                    else:
                        self.data[btn_offset + btn_RIGHT] = False
                    if mesg[1] & cwiid.BTN_2:
                        self.data[btn_offset + btn_2] = True
                    else:
                        self.data[btn_offset + btn_2] = False
                    #Handle disconnect
                    if mesg[1] & cwiid.BTN_HOME:
                        self.is_in_menu_mode = True
                        break
                if mesg[0] == cwiid.MESG_NUNCHUK:
                    if mesg[1]['buttons'] & cwiid.NUNCHUK_BTN_C:
                        self.data[btn_offset + btn_nunC] = True
                    else:
                        self.data[btn_offset + btn_nunC] = False
                    if mesg[1]['buttons'] & cwiid.NUNCHUK_BTN_Z:
                        self.data[btn_offset + btn_nunZ] = True
                    else:
                        self.data[btn_offset + btn_nunZ] = False
                    stx = mesg[1]['stick'][0];
                    sty = mesg[1]['stick'][1];
                    # d(x|y)(n|p): "delta x, direction=negative", etc. 
                    dxn = (self.center_x - 10) - stx;
                    dxp = stx - (self.center_x + 10);
                    dyn = (self.center_y - 10) - sty;
                    dyp = sty - (self.center_y + 10);

                    # TODO: with -REL_Y, we go down slower than we go up.
                    # += (vs =): to accumulate the result of multiple events.
                    if (dxn >= 0):
                        self.finalX = -(dxn * 12 / self.x_neg_range)
                    else:
                        if (dxp >= 0):
                            self.finalX = (dxp * 12 / self.x_pos_range)
                        else:
                            self.finalX = 0

                    if (dyn >= 0):
                        self.finalY = -(dyn * 12 / self.y_neg_range)
                    else:
                        if (dyp >= 0):
                            self.finalY = -(dyp * 12 / self.y_pos_range)
                        else:
                            self.finalY = 0

                    x = self.finalX*10 + 128
                    y = self.finalY*10 + 128

                    if (x > 255): x = 255
                    if (y > 255): y = 255
                    if (x < 0): x = 0
                    if (y < 0): y = 0

                    xBits = Bits(uintle=x,length=8)
                    yBits = Bits(uintle=y,length=8)
                    for i in range(8):
                        self.data[i] = xBits[7-i]
                        if self.nunchuk_acc: self.data[24+i] = xBits[7-i]
                        self.data[8+i] = yBits[7-i]

                if mesg[0] == cwiid.MESG_ACC and not (self.nunchuk_acc and self.isNunchukCalibrated):
                    x = mesg[1][cwiid.X]
                    y = mesg[1][cwiid.Y]

                    y = ((y-96)*255)/49 + 3

                    if (x > 255): x = 255
                    if (y > 255): y = 255
                    if (x < 0): x = 0
                    if (y < 0): y = 0                

                    if (abs(self.previousAccX - x) >= 12):                    
                        yBits = Bits(uintle=255-y,length=8)
                        for i in range(8):
                            self.data[24+i] = yBits[7-i]
                    else:
                        yBits = Bits(uintle=self.previousAccY,length=8)
                        for i in range(8):
                            self.data[24+i] = stablePos[7-i]
                    self.previousAccY = y

                    for i in range(8):
                            self.data[16+i] = stablePos[7-i]

    def handle_data(self, usb_req):
        self.sent = True
        return_val = self.data.tobytes()
        self.send_usb_req(usb_req, return_val, len(return_val))
        time.sleep(0.05)

    def tohex(self, val, nbits):
      return hex((val + (1 << nbits)) % (1 << nbits))

    def handle_unknown_control(self, control_req, usb_req):
        if control_req.bmRequestType == 0x81:
            if control_req.bRequest == 0x6:  # Get Descriptor
                if control_req.wValue == 0x22:  # send initial report
                    #print 'send initial report'
                    print '[' + bcolors.OKGREEN + 'WiimoteHID' + bcolors.ENDC + '] #' + str(self.wiimote_number) + ' sending HID descriptor'
                    ret=self.generate_hid_report()
                    self.send_usb_req(usb_req, ret, len(ret))

        if control_req.bmRequestType == 0x21:  # Host Request
            if control_req.bRequest == 0x0a:  # set idle
                #print '[' + bcolors.OKGREEN + 'WiimoteHID' + bcolors.ENDC + '] #' + str(self.wiimote_number) + ' HID idle'
                # Idle
                self.send_usb_req(usb_req, '', 0,0)
                pass
            if control_req.bRequest == 0x09:  # set report
                #print 'set report'
                data = usb_container.usb_devices[0].connection.recv(control_req.wLength)
                #use data ? 
                self.send_usb_req(usb_req, '', 0,0)
                pass
