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

@blynk.on("disconnected")
def blynk_disconnected():
    global is_blynk_connected
    is_blynk_connected = False
    print("Disconnected from Blynk")

# function 
def tempCPU():
    cpu_usage = psutil.cpu_percent();
    free_ram = psutil.virtual_memory()[3]/1000000;
    process = subprocess.Popen(['vcgencmd', 'measure_temp'], stdout=subprocess.PIPE); # bisa pake cat /sys/class/thermal/thermal_zone0/temp
    output, _error = process.communicate();
    cpu_tmp = float(output[5:9]);
    blynk.virtual_write(13, cpu_usage);
    blynk.virtual_write(14, cpu_tmp);
    blynk.virtual_write(15, free_ram);

def send_at(ser, command):
    ser.write((command + '\r\n').encode('utf-8'))
    time.sleep(1)
    response = ser.read_all().decode('utf-8')
    print(response)
    return response

def execute_at():
    try:
        ser = serial.Serial('/dev/ttyACM0', 115200, timeout=2); # port serial & baudrate

        commands = ['AT+CGMM','AT+CGPADDR', 'AT+MTSM=1', 'AT+XMCI=1', 'AT+RSRP?', 'AT+XLEC?', 'AT+CSQ', 'AT+COPS=3,0;+COPS?'] # AT command

        type, ip, temp, rssi, rsrp, sinr, band, operator = None, None, None, None, None, None, None, None

        for command in commands:
            response = send_at(ser, command)

            if "OK" in response:
                # decode response and send to blynk server
                if "Module" in response:
                    type = response.split('\n')[0]
                if "+CGPADDR: 1," in response:
                    ip = re.findall(r'[0-9]+(?:\.[0-9]+){3}', response)
                if "+MTSM:" in response:
                    temp = int(re.search(r'\b(\d+)\b', response).group())
                if "+RSRP:" in response:
                    rsrp = response.split(':')[1].split(',')[2].split('.')[0]
                if "+XMCI:" in response:
                    sinr = response.split(':')[1].split(',')[10]
                if "+CSQ:" in response:
                    rssi = re.findall(r'[0-9]+', response)
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
            else:
                print(f'{command} failed')

        # send data to blynk server
        blynk.virtual_write(16, ip[0]);
        blynk.virtual_write(8, temp);
        blynk.virtual_write(9, rsrp);
        blynk.virtual_write(10, '-' + rssi[0]);
        blynk.virtual_write(7, sinr);
        blynk.virtual_write(12, band);
        blynk.virtual_write(11, 'Live On'); # bisa pake variabel operator / manual
    
        # close serial connection
        ser.close()
        print('Serial Closed')
    
    except Exception as e:
        print(f'Error Message: {e}')

# function call for collect & send data to blynk server  
timer.set_interval(5, tempCPU);
timer.set_interval(20, execute_at);

while True:
    blynk.run();
    timer.run();
