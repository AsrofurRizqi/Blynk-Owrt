from __future__ import division
import BlynkLib as blynk
import RPi.GPIO as GPIO
from BlynkTimer import BlynkTimer

import subprocess
import psutil
import re
# import adafruit_dht
import time, serial
# import board

# auth token & sensor dht11 init pin
# DHT_SENSOR = adafruit_dht.DHT11(board.D4, use_pulseio=False)
TTY_PORT = '/dev/ttyACM0'
BAUDRATE = 115200
BLYNK_AUTH_TOKEN = 'BLYNK_AUTH_TOKEN'

# Init Blynk
blynk = blynk.Blynk(BLYNK_AUTH_TOKEN);
is_blynk_connected = False

# BlynkTimer Instance
timer = BlynkTimer()

# function connect blynk server
@blynk.on("connected")
def blynk_connected():
    global is_blynk_connected
    print("Connected to New Blynk2.0");
    is_blynk_connected = True
    time.sleep(2);

# function 
def tempCPU():
    try:
        cpu_usage = psutil.cpu_percent();
        free_ram = psutil.virtual_memory()[3]/1000000;
        process = subprocess.Popen(['vcgencmd', 'measure_temp'], stdout=subprocess.PIPE); # bisa pake cat /sys/class/thermal/thermal_zone0/temp
        output, _error = process.communicate();
        cpu_tmp = float(output[5:9]);
        blynk.virtual_write(5, cpu_usage);
        blynk.virtual_write(6, cpu_tmp);
        blynk.virtual_write(15, free_ram);
    except Exception as e:
        print(f'Error Message: {e}')

def SpeedTest():
    try:
        process = subprocess.Popen(['speedtest-cli', '--simple'], stdout=subprocess.PIPE);
        output, _error = process.communicate();
        ping = re.findall(r'Ping:\s(.*?)\s', output.decode('utf-8'));
        download = re.findall(r'Download:\s(.*?)\s', output.decode('utf-8'));
        upload = re.findall(r'Upload:\s(.*?)\s', output.decode('utf-8'));
        blynk.virtual_write(2, ping[0]);
        blynk.virtual_write(3, download[0]);
        blynk.virtual_write(4, upload[0]);
    except Exception as e:
        print(f'Error Message: {e}')

def sendAt(ser, command):
    ser.write((command + '\r\n').encode('utf-8'))
    time.sleep(1)
    response = ser.read_all().decode('utf-8')
    print(response)
    return response

def executeAt():
    try:
        ser = serial.Serial(TTY_PORT, BAUDRATE, timeout=2); # port serial & baudrate

        commandFibo = ['AT+CGPADDR', 'AT+MTSM=1', 'AT+XMCI=1', 'AT+RSRP?', 'AT+XLEC?', 'AT+CSQ', 'AT+COPS=3,0;+COPS?', 'AT+RSRQ?'] # AT command
        commandSnap = ['AT^DEBUG?', 'AT^CA_INFO?', 'AT^TEMP?', 'AT+TEMP?']
        type, ip, temp, rssi, rsrp, sinr, rsrq, band, cellid, operator = None, None, None, None, None, None, None, None, None, None

        checkDevice = sendAt(ser, 'AT+CGMM')
        if "L860" in checkDevice:
            type = 'L860-GL'
        elif "L850" in checkDevice:
            type = 'L850-GL'
        elif "DW5821e" in checkDevice:
            type = 'DW5821e'
        elif "Telit" in checkDevice:
            type = 'Telit'
        else:
            type = 'Unknown'

        if type == 'L860-GL' or type == 'L850-GL':
            for command in commandFibo:
                response = sendAt(ser, command)
                if "OK" in response:
                    if "+CGPADDR: 1," in response:
                        ip = re.findall(r'[0-9]+(?:\.[0-9]+){3}', response)
                    if "+MTSM:" in response:
                        temp = int(re.search(r'\b(\d+)\b', response).group())
                    if "+RSRP:" in response:
                        rsrp = response.split(':')[1].split(',')[2].split('.')[0]
                    if "+XMCI:" in response:
                        sinr = response.split(':')[1].split(',')[10]
                    if "+CSQ:" in response:
                        rssi = (int(response.split(':')[1].split(',')[0]) * 2) - 113
                    if "+XLEC:" in response:
                        def mhz(num):
                            if num == 1:
                                return '3 MHz'
                            elif num == 2:
                                return '5 MHz'
                            elif num == 3:
                                return '10 MHz'
                            elif num == 4:
                                return '15 MHz'
                            elif num == 5:
                                return '20 MHz'
                            else:
                                return '0 MHz'
                        ba = re.findall(r'BAND_LTE_(\d+)', response)
                        bw = re.findall(r'\b\d+\b', response)[:3]
                        if bw[1] == '1':
                            band = f'B{ba[0]} {mhz(int(bw[2]))}'
                        elif bw[1] == '2':
                            band = f'B{ba[0]} {mhz(int(bw[2]))} + B{ba[1]} {mhz(int(bw[0]))}'
                        elif bw[1] == '3':
                            band = f'B{ba[0]} {mhz(int(bw[2]))} + B{ba[1]} {mhz(int(bw[0]))} + B{ba[2]} {mhz(int(bw[0]))}'
                        elif bw[1] == '4':
                            band = f'B{ba[0]} {mhz(int(bw[2]))} + B{ba[1]} {mhz(int(bw[0]))} + B{ba[2]} {mhz(int(bw[0]))} + B{ba[3]} {mhz(int(bw[0]))}'

                    if "+COPS:" in response:
                        operator = response.split(':')[1].split(',')[2]
                    if "+CREG:" in response:
                        cellid = response.split(':')[1].split(',')[3] 
                    if "+RSRQ:" in response:
                        rsrq = response.split(':')[1].split(',')[2]
                else:
                    print(f'{command} failed')
        
        elif type == 'DW5821e' or type == 'Telit':
            for command in commandSnap:
                response = sendAt(ser, command)
                if "OK" in response:
                    if "RAT:LTE" in response:
                        rsrq = re.search(r"RSRQ: ([\d.-]+)dB", response).group(1)
                        sinr = re.search(r"RS-SNR: (\d+)dB", response).group(1)
                        rssi = re.search(r"RSSI: ([\d.-]+)dBm", response).group(1)
                        rsrp = re.search(r"RSRP: ([\d.-]+)dBm", response).group(1)
                        ip = re.findall(r'[0-9]+(?:\.[0-9]+){3}', response)
                        cellid = re.search(r"eNB ID\(PCI\): (\d+-\d+)\(\d+\)", response).group(1)
                    if "PCC info:" in response:
                        data = re.findall(r"Band is (\S+), Band_width is (\S+) MHz", response)
                        band = [f"{bnd} {bw} MHz" for bnd, bw in data].join('+')
                    if "TSENS:" in response:
                        temp = re.search(r"TSENS: (\d+)", response).group(1)
                    if "pa_therm1:" in response:
                        temp = re.search(r"pa_therm1: (\d+)", response).group(1)
                    if "tsens_tz_sensor0:" in response:
                        temp = re.search(r"tsens_tz_sensor0: (\d+)", response).group(1)
                else:
                    print(f'{command} failed')
                    
        else:
            print('Unknown Device')

        # send data to blynk server
        blynk.virtual_write(1, type);
        blynk.virtual_write(2, cellid);
        blynk.virtual_write(7, sinr);
        blynk.virtual_write(8, temp);
        blynk.virtual_write(9, rsrp);
        blynk.virtual_write(10, rssi);
        blynk.virtual_write(11, operator);
        blynk.virtual_write(12, band);
        blynk.virtual_write(16, ip[0]);
        blynk.virtual_write(17, rsrq);
    
        # close serial connection
        ser.close()
        print('Serial Closed')
    
    except Exception as e:
        print(f'Error Message: {e}')

# function call for collect & send data to blynk server  
timer.set_interval(5, tempCPU);
timer.set_interval(20, executeAt);

while True:
    blynk.run();
    timer.run();
