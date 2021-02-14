#!/usr/bin/env python3
from devices import edgeOS
from devices import icmp
from utils import prettyPrint
import logging
import time
import json

import signal
import sys

from board import SCL, SDA
import busio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306

# Setup I2C Display

i2c = busio.I2C(SCL, SDA)
disp = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c)
width = disp.width
height = disp.height
image = Image.new("1", (width, height))

draw = ImageDraw.Draw(image)

# Load font
font = ImageFont.load_default()

# Draw some shapes.
# First define some constants to allow easy resizing of shapes.
padding = -2
top = padding
bottom = height - padding
# Move left to right keeping track of the current x position for drawing shapes.
x = 0

# Setup stats
f = open('./secrets.json')
config = json.load(f)

edgeos = edgeOS.EdgeOS(config['edgeos']['url'], config['edgeos']['username'],
                       config['edgeos']['password'], config['edgeos']['verifySSL'])

# Logging
logging.basicConfig(filename='./logs/main.log',
                    format='[%(asctime)s][%(levelname)s][%(module)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

outboundInterface = config['edgeos']['outboundInterface']
outboundInterfaceParent = config['edgeos']['outboundInterfaceParent']
APInerface = config['edgeos']['APInterface']

APAddress = config['icmp'][0]['address']
APInterval = config['icmp'][0]['interval']
OutboundAddress = config['icmp'][1]['address']
OutInterval = config['icmp'][1]['interval']


APIcmp = icmp.icmp(APAddress, APInterval)
OutboundIcmp = icmp.icmp(OutboundAddress, OutInterval)

banner = 'Pending'
cpu = 'TBD'
mem = 'TBD'
externalIP = 'TBD'
isUp = 'TBD'
parentIsUP = False
download = 'TBD'
upload = 'TBD'
APSpeed = 'TBD'


# Handle SIGINT, stop the display gracefully
def signal_handler(sig, frame):
    global draw, disp
    logging.info('Exiting...')
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    disp.image(image)
    disp.show()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


while True:
    routerData = edgeos.getData()
    apData = APIcmp.getData()
    outboundData = OutboundIcmp.getData()
    err = 0
    if routerData['status'] != False:
        if 'system-stats' in routerData['data']:
            cpu = routerData['data']['system-stats']['cpu']
            mem = routerData['data']['system-stats']['mem']
        if 'interfaces' in routerData['data']:
            if outboundInterface in routerData['data']['interfaces']:
                isUp = routerData['data']['interfaces'][outboundInterface]['up'] == 'true'
            else:
                isUp = False
            if outboundInterfaceParent in routerData['data']['interfaces']:
                parentIsUP = routerData['data']['interfaces'][outboundInterfaceParent]['up'] == 'true'
            else:
                parentIsUP = False
            if APInerface in routerData['data']['interfaces']:
                APSpeed = routerData['data']['interfaces'][APInerface]['speed']
            else:
                APSpeed = 'TBD'
            if isUp:
                externalIP = routerData['data']['interfaces'][outboundInterface]['addresses'][0].split(
                    '/')[0]
            else:
                externalIP = 'TBD'
        if outboundInterface in routerData['data']['speed']['interfaces']:
            pppoeStats = routerData['data']['speed']['interfaces'][outboundInterface]
            download = pppoeStats['rx'] * 8
            upload = pppoeStats['tx'] * 8
    else:
        cpu = 'TBD'
        mem = 'TBD'
        externalIP = 'TBD'
        isUp = 'TBD'
        download = 'TBD'
        upload = 'TBD'
        parentIsUP = False
    # Clear Darwing
    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    if APSpeed != '1000' and APSpeed != 'TBD':
        banner = 'AP Speed Outage'
        logging.warning(banner)
        err += 1
    if apData['status'] == False:
        banner = 'AP Down'
        logging.warning(banner)
        err += 1
    if outboundData['status'] == False:
        banner = 'Outbound outage'
        logging.warning(banner)
        err += 1
    if isUp == False:
        banner = 'PPPoE Down'
        logging.warning(banner)
        err += 1
        if parentIsUP == False:
            banner = 'ISP Disconnected'
            logging.warning(banner)
            err += 1
    if routerData['status'] == False:
        banner = routerData['msg']
        logging.warning(banner)
        err += 1

    if err == 0:
        banner = 'Operational'

    # Date
    draw.text((x, top + 0), prettyPrint.currentDate(), font=font, fill=255)
    draw.text((x, top + 8), banner, font=font, fill=255)
    draw.text((x, top + 16), 'R: CPU {}% MEM {}%'.format(cpu, mem),
              font=font, fill=255)
    draw.text((x, top + 24), 'IP: {}'.format(externalIP), font=font, fill=255)
    draw.text((x, top + 32),
              'U: {}'.format(prettyPrint.speed(upload)), font=font, fill=255)
    draw.text((x, top + 40),
              'D: {}'.format(prettyPrint.speed(download)), font=font, fill=255)
    draw.text((x, top + 48), 'AP: {} {}mbps'.format('UP' if(apData['status'] == True) else 'DOWN', APSpeed),
              font=font, fill=255)
    draw.text((x, top + 56), 'Outage(s): {}'.format(err), font=font, fill=255)

    # Display image.
    disp.image(image)
    disp.show()
    time.sleep(0.1)
