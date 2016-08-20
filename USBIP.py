import SocketServer
import struct
import types

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

class BaseStucture:
    _fields_ = []

    def __init__(self, **kwargs):
        self.init_from_dict(**kwargs)
        for field in self._fields_:
            if len(field) > 2:
                if not hasattr(self, field[0]):
                    setattr(self, field[0], field[2])

    def init_from_dict(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def size(self):
        return struct.calcsize(self.format())

    def format(self):

        pack_format = '>'
        for field in self._fields_:
            if type(field[1]) is types.InstanceType:
                if BaseStucture in field[1].__class__.__bases__:
                    pack_format += str(field[1].size()) + 's'
            elif 'si' == field[1]:
                pack_format += 'c'
            elif '<' in field[1]:
                pack_format += field[1][1:]
            else:
                pack_format += field[1]
        return pack_format

    def formatDevicesList(self, devicesCount):

        pack_format = '>'
        i = 0
        for field in self._fields_:
            if (i == devicesCount + 2):
                break
            if type(field[1]) is types.InstanceType:
                if BaseStucture in field[1].__class__.__bases__:
                    pack_format += str(field[1].size()) + 's'
            elif 'si' == field[1]:
                pack_format += 'c'
            elif '<' in field[1]:
                pack_format += field[1][1:]
            else:
                pack_format += field[1]
            i += 1
        return pack_format

    def pack(self):
        values = []
        for field in self._fields_:
            if type(field[1]) is types.InstanceType:
                if BaseStucture in field[1].__class__.__bases__:
                     values.append(getattr(self, field[0], 0).pack())
            else:
                if 'si' == field[1]:
                    values.append(chr(getattr(self, field[0], 0)))
                else:
                    values.append(getattr(self, field[0], 0))
        return struct.pack(self.format(), *values)

    def packDevicesList(self, devicesCount):
        values = []
        i = 0
        for field in self._fields_:
            if (i == devicesCount + 2):
                break
            if type(field[1]) is types.InstanceType:
                if BaseStucture in field[1].__class__.__bases__:
                     values.append(getattr(self, field[0], 0).pack())
            else:
                if 'si' == field[1]:
                    values.append(chr(getattr(self, field[0], 0)))
                else:
                    values.append(getattr(self, field[0], 0))
            i += 1
        return struct.pack(self.formatDevicesList(devicesCount), *values)

    def unpack(self, buf):
        values = struct.unpack(self.format(), buf)
        i=0
        keys_vals = {}
        for val in values:
            if '<' in self._fields_[i][1][0]:
                val = struct.unpack('<' +self._fields_[i][1][1], struct.pack('>' + self._fields_[i][1][1], val))[0]
            keys_vals[self._fields_[i][0]]=val
            i+=1

        self.init_from_dict(**keys_vals)


def int_to_hex_string(val):
    sval= format(val, 'x')
    if  len(sval) < 16:
       for i in range(len(sval),16):
         sval= '0'+sval
         #sval= sval+'0'
    return sval.decode('hex')


class USBIPHeader(BaseStucture):
    _fields_ = [
        ('version', 'H', 273),
        ('command', 'H'),
        ('status', 'I')
    ]



class USBInterface(BaseStucture):
    _fields_ = [
        ('bInterfaceClass', 'B'),
        ('bInterfaceSubClass', 'B'),
        ('bInterfaceProtocol', 'B'),
        ('align', 'B', 0)
    ]

class USBIPDevice(BaseStucture):
    _fields_ = [
        ('usbPath', '256s'),
        ('busID', '32s'),
        ('busnum', 'I'),
        ('devnum', 'I'),
        ('speed', 'I'),
        ('idVendor', 'H'),
        ('idProduct', 'H'),
        ('bcdDevice', 'H'),
        ('bDeviceClass', 'B'),
        ('bDeviceSubClass', 'B'),
        ('bDeviceProtocol', 'B'),
        ('bConfigurationValue', 'B'),
        ('bNumConfigurations', 'B'),
        ('bNumInterfaces', 'B'),
        ('interfaces', USBInterface())
    ]

class OPREPDevList(BaseStucture):

    def __init__(self, dictArg, count):
        self._fields_ = [
            ('base', USBIPHeader(), USBIPHeader(command=5,status=0)), # Declare this here to make sure it's in the right order
            ('nExportedDevice', 'I', count) # Same for this guy
        ]

        for key, value in dictArg.iteritems():
            field = (str(key), value[0], value[1])
            self._fields_.append(field)
        
        for field in self._fields_:
            if len(field) > 2:
                if not hasattr(self, field[0]):
                    setattr(self, field[0], field[2])

class OPREPImport(BaseStucture):
    _fields_ = [
        ('base', USBIPHeader()),
        ('usbPath', '256s'),
        ('busID', '32s'),
        ('busnum', 'I'),
        ('devnum', 'I'),
        ('speed', 'I'),
        ('idVendor', 'H'),
        ('idProduct', 'H'),
        ('bcdDevice', 'H'),
        ('bDeviceClass', 'B'),
        ('bDeviceSubClass', 'B'),
        ('bDeviceProtocol', 'B'),
        ('bConfigurationValue', 'B'),
        ('bNumConfigurations', 'B'),
        ('bNumInterfaces', 'B')
    ]

class USBIPRETSubmit(BaseStucture):
    _fields_ = [
        ('command', 'I'),
        ('seqnum', 'I'),
        ('devid', 'I'),
        ('direction', 'I'),
        ('ep', 'I'),
        ('status', 'I'),
        ('actual_length', 'I'),
        ('start_frame', 'I'),
        ('number_of_packets', 'I'),
        ('error_count', 'I'),
        ('setup', 'Q')
    ]

    def pack(self):
        packed_data = BaseStucture.pack(self)
        packed_data += self.data
        return packed_data

class USBIPCMDSubmit(BaseStucture):
    _fields_ = [
        ('command', 'I'),
        ('seqnum', 'I'),
        ('devid', 'I'),
        ('direction', 'I'),
        ('ep', 'I'),
        ('transfer_flags', 'I'),
        ('transfer_buffer_length', 'I'),
        ('start_frame', 'I'),
        ('number_of_packets', 'I'),
        ('interval', 'I'),
        ('setup', 'Q')
    ]

class USBIPUnlinkReq(BaseStucture):
    _fields_ = [
        ('command', 'I', 0x2),
        ('seqnum', 'I'),
        ('devid', 'I', 0x2),
        ('direction', 'I'),
        ('ep', 'I'),
        ('transfer_flags', 'I'),
        ('transfer_buffer_length', 'I'),
        ('start_frame', 'I'),
        ('number_of_packets', 'I'),
        ('interval', 'I'),
        ('setup', 'Q')
    ]




class StandardDeviceRequest(BaseStucture):
    _fields_ = [
        ('bmRequestType', 'B'),
        ('bRequest', 'B'),
        ('wValue', 'H'),
        ('wIndex', 'H'),
        ('wLength', '<H')
    ]

class DeviceDescriptor(BaseStucture):
    _fields_ = [
        ('bLength', 'B', 18),
        ('bDescriptorType', 'B', 1),
        ('bcdUSB', 'H', 0x1001),
        ('bDeviceClass', 'B'),
        ('bDeviceSubClass', 'B'),
        ('bDeviceProtocol', 'B'),
        ('bMaxPacketSize0', 'B'),
        ('idVendor', 'H'),
        ('idProduct', 'H'),
        ('bcdDevice', 'H'),
        ('iManufacturer', 'B'),
        ('iProduct', 'B'),
        ('iSerialNumber', 'B'),
        ('bNumConfigurations', 'B')
    ]


class DeviceConfigurations(BaseStucture):
    _fields_ = [
        ('bLength', 'B', 9),
        ('bDescriptorType', 'B', 2),
        ('wTotalLength', 'H', 0x2200),
        ('bNumInterfaces', 'B', 1),
        ('bConfigurationValue', 'B', 1),
        ('iConfiguration', 'B', 0),
        ('bmAttributes', 'B', 0x80),
        ('bMaxPower', 'B', 0x32)
    ]


class InterfaceDescriptor(BaseStucture):
    _fields_ = [
        ('bLength', 'B', 9),
        ('bDescriptorType', 'B', 4),
        ('bInterfaceNumber', 'B', 0),
        ('bAlternateSetting', 'B', 0),
        ('bNumEndpoints', 'B', 1),
        ('bInterfaceClass', 'B', 3),
        ('bInterfaceSubClass', 'B', 1),
        ('bInterfaceProtocol', 'B', 2),
        ('iInterface', 'B', 0)
    ]


class EndPoint(BaseStucture):
    _fields_ = [
        ('bLength', 'B', 7),
        ('bDescriptorType', 'B', 0x5),
        ('bEndpointAddress', 'B', 0x81),
        ('bmAttributes', 'B', 0x3),
        ('wMaxPacketSize', 'H', 0x8000),
        ('bInterval', 'B', 0x0A)
    ]



class USBRequest():
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class USBDevice():
    '''interfaces = [USBInterface(bInterfaceClass=0x3, bInterfaceSubClass=0x0, bInterfaceProtocol=0x0)]
    speed=2
    speed = 2
    vendorID = 0xc410
    productID = 0x0
    bcdDevice = 0x0
    bDeviceClass = 0x0
    bDeviceSubClass = 0x0
    bDeviceProtocol = 0x0
    bNumConfigurations = 1
    bConfigurationValue = 1
    bNumInterfaces = 1'''

    def __init__(self, container):
        self.generate_raw_configuration()
        self.usb_container = container

    def generate_raw_configuration(self):
        str = self.configurations[0].pack()
        str += self.configurations[0].interfaces[0].pack()
        str += self.configurations[0].interfaces[0].descriptions[0].pack()
        str += self.configurations[0].interfaces[0].endpoints[0].pack()
        self.all_configurations = str

    def send_usb_req(self, usb_req, usb_res, usb_len,  status=0):
        self.connection.sendall(USBIPRETSubmit(command=0x3,
                                                   seqnum=usb_req.seqnum,
                                                   ep=0,
                                                   status=status,
                                                   actual_length=usb_len,
                                                   start_frame=0x0,
                                                   number_of_packets=0x0,
                                                   interval=0x0,
                                                   data=usb_res).pack())

    def handle_get_descriptor(self, control_req, usb_req):
        handled = False
        #print "handle_get_descriptor {}".format(control_req.wValue,'n')
        if control_req.wValue == 0x1: # Device
            handled = True
            ret=DeviceDescriptor(bDeviceClass=self.bDeviceClass,
                                 bDeviceSubClass=self.bDeviceSubClass,
                                 bDeviceProtocol=self.bDeviceProtocol,
                                 bMaxPacketSize0=0x8,
                                 idVendor=self.vendorID,
                                 idProduct=self.productID,
                                 bcdDevice=self.bcdDevice,
                                 iManufacturer=0,
                                 iProduct=0,
                                 iSerialNumber=0,
                                 bNumConfigurations=1).pack()
            self.send_usb_req(usb_req, ret, len(ret))
        elif control_req.wValue == 0x2: # configuration
            handled = True
            ret= self.all_configurations[:control_req.wLength]
            self.send_usb_req(usb_req, ret, len(ret))

        elif control_req.wValue == 0xA: # config status ???
            handled = True
            self.send_usb_req(usb_req,'',0,1)


        return handled
 
   


    def handle_set_configuration(self, control_req, usb_req):
        handled = False
        #print "handle_set_configuration {}".format(control_req.wValue,'n')
        handled = True
        self.send_usb_req(usb_req,'',0,0)
        return handled

    def handle_usb_control(self, usb_req):
        control_req = StandardDeviceRequest()
        control_req.unpack(int_to_hex_string(usb_req.setup))
        handled = False
        #print "  UC Request Type {}".format(control_req.bmRequestType)
        #print "  UC Request {}".format(control_req.bRequest)
        #print "  UC Value  {}".format(control_req.wValue)
        #print "  UCIndex  {}".format(control_req.wIndex)
        #print "  UC Length {}".format(control_req.wLength)
        if control_req.bmRequestType == 0x80: # Host Request
            if control_req.bRequest == 0x06: # Get Descriptor
                handled = self.handle_get_descriptor(control_req, usb_req)
            if control_req.bRequest == 0x00: # Get STATUS
                self.send_usb_req(usb_req, "\x01\x00", 2);
                handled = True

        if control_req.bmRequestType == 0x00: # Host Request
            if control_req.bRequest == 0x09: # Set Configuration
                handled = self.handle_set_configuration(control_req, usb_req)

        if not handled:
            self.handle_unknown_control(control_req, usb_req)

    def handle_usb_request(self, usb_req):
        if usb_req.ep == 0:
            self.handle_usb_control(usb_req)
        else:
            self.handle_data(usb_req)

class USBContainer:
    usb_devices = {}
    attached_devices = {}
    devices_count = 0

    def add_usb_device(self, usb_device):
        self.devices_count += 1
        busID = '1-1.' + str(self.devices_count)
        self.usb_devices[busID] = usb_device
        self.attached_devices[busID] = False

    def remove_usb_device(self, usb_device):        
        for busid, dev in self.usb_devices.iteritems():
            if dev == usb_device:
                del self.attached_devices[busid]
                del self.usb_devices[busid]
                break
        self.devices_count -= 1

    def detach_all(self):
        self.attached_devices = {}
        self.usb_devices = {}
        self.devices_count = 0

    def handle_attach(self, busid):
        if (self.usb_devices[busid] != None):
            busnum = int(busid[4:])
            return OPREPImport(base=USBIPHeader(command=3, status=0),
                               usbPath='/sys/devices/pci0000:00/0000:00:01.2/usb1/' + busid,
                               busID=busid,
                               busnum=busnum,
                               devnum=2,
                               speed=2,
                               idVendor=self.usb_devices[busid].vendorID,
                               idProduct=self.usb_devices[busid].productID,
                               bcdDevice=self.usb_devices[busid].bcdDevice,
                               bDeviceClass=self.usb_devices[busid].bDeviceClass,
                               bDeviceSubClass=self.usb_devices[busid].bDeviceSubClass,
                               bDeviceProtocol=self.usb_devices[busid].bDeviceProtocol,
                               bNumConfigurations=self.usb_devices[busid].bNumConfigurations,
                               bConfigurationValue=self.usb_devices[busid].bConfigurationValue,
                               bNumInterfaces=self.usb_devices[busid].bNumInterfaces)

    def handle_device_list(self):
        devices = {}

        i = 0
        for busid, usb_dev in self.usb_devices.iteritems():
            i += 1
            devices['device' + str(i)] = [USBIPDevice(), USBIPDevice(
                usbPath='/sys/devices/pci0000:00/0000:00:01.2/usb1/' + busid,
                busID=busid,
                busnum=i,
                devnum=2,
                speed=2,
                idVendor=self.usb_devices[busid].vendorID,
                idProduct=self.usb_devices[busid].productID,
                bcdDevice=self.usb_devices[busid].bcdDevice,
                bDeviceClass=self.usb_devices[busid].bDeviceClass,
                bDeviceSubClass=self.usb_devices[busid].bDeviceSubClass,
                bDeviceProtocol=self.usb_devices[busid].bDeviceProtocol,
                bNumConfigurations=self.usb_devices[busid].bNumConfigurations,
                bConfigurationValue=self.usb_devices[busid].bConfigurationValue,
                bNumInterfaces=self.usb_devices[busid].bNumInterfaces,
                interfaces=USBInterface(bInterfaceClass=self.usb_devices[busid].configurations[0].interfaces[0].bInterfaceClass,
                                        bInterfaceSubClass=self.usb_devices[busid].configurations[0].interfaces[0].bInterfaceSubClass,
                                        bInterfaceProtocol=self.usb_devices[busid].configurations[0].interfaces[0].bInterfaceProtocol)
            )]

        return OPREPDevList(devices, len(self.usb_devices))


    def run(self, ip='0.0.0.0', port=3240):
        #SocketServer.TCPServer.allow_reuse_address = True
        self.server = SocketServer.ThreadingTCPServer((ip, port), USBIPConnection)
        self.server.usbcontainer = self
        self.server.serve_forever()


class USBIPConnection(SocketServer.BaseRequestHandler):
    attached = False
    attachedBusID = ''

    def handle(self):
        print '[' + bcolors.OKBLUE + 'USBIP' + bcolors.ENDC + '] New connection from', self.client_address
        req = USBIPHeader()
        while 1:
            if not self.attached:
                data = self.request.recv(8)
                if not data:
                    break
                req.unpack(data)
                print '[' + bcolors.OKBLUE + 'USBIP' + bcolors.ENDC + '] Header packet is valid'
                print '[' + bcolors.OKBLUE + 'USBIP' + bcolors.ENDC + '] Command is', hex(req.command)
                if req.command == 0x8005:
                    print '[' + bcolors.OKBLUE + 'USBIP' + bcolors.ENDC + '] Querying device list'
                    self.request.sendall(self.server.usbcontainer.handle_device_list().pack())
                elif req.command == 0x8003:                    
                    busid = self.request.recv(5).strip()  # receive bus id
                    print '[' + bcolors.OKBLUE + 'USBIP' + bcolors.ENDC + '] Attaching to device with busid', busid
                    self.request.recv(27)
                    self.request.sendall(self.server.usbcontainer.handle_attach(str(busid)).pack())
                    self.attached = True
                    self.attachedBusID = busid
            else:
                if (not self.attachedBusID in self.server.usbcontainer.usb_devices): 
                    self.request.close()
                    break
                else:
                    #print '----------------' 
                    #print 'handles requests'
                    cmd = USBIPCMDSubmit()
                    data = self.request.recv(cmd.size())
                    cmd.unpack(data)
                    #print "usbip cmd {}".format(cmd.command,'x')
                    #print "usbip seqnum {}".format(cmd.seqnum,'x')
                    #print "usbip devid {}".format(cmd.devid,'x')
                    #print "usbip direction {}".format(cmd.direction,'x')
                    #print "usbip ep {}".format(cmd.ep,'x')
                    #print "usbip flags {}".format(cmd.transfer_flags,'x')
                    #print "usbip number of packets {}".format(cmd.number_of_packets,'x')
                    #print "usbip interval {}".format(cmd.interval,'x')
                    #print "usbip setup {}".format(cmd.setup,'x')
                    #print "usbip buffer lenght  {}".format(cmd.transfer_buffer_length,'x')
                    usb_req = USBRequest(seqnum=cmd.seqnum,
                                         devid=cmd.devid,
                                         direction=cmd.direction,
                                         ep=cmd.ep,
                                         flags=cmd.transfer_flags,
                                         numberOfPackets=cmd.number_of_packets,
                                         interval=cmd.interval,
                                         setup=cmd.setup,
                                         data=data)
                    self.server.usbcontainer.usb_devices[self.attachedBusID].connection = self.request
                    self.server.usbcontainer.usb_devices[self.attachedBusID].handle_usb_request(usb_req)
        self.request.close()