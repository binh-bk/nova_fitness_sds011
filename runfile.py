
import serial
import sys
import time
import json
import os
import paho.mqtt.publish as publish
import socket
from sds011 import SDS011

# get info of MQTT authenicated by envirenment variable
# hardcoded works too, e.g mqtt = '192.168.1.20',
mqtt = os.environ.get('MQTT_SERVER_IP')
username = os.environ.get('MQTT_USER')
password = os.environ.get('MQTT_PW')
# print(mqtt, username, password)
sensor_name = "sds018_test"
lastTime = 0
logName = f'{sensor_name}.csv'
tmpName = f'{sensor_name}_tmpLog.txt'
is_tmp_file = False

AQIs = {'Good': {'aqi': [0, 50], 'PM2.5': [0, 12.0], 'PM10': [0, 54]},
        'Moderate': {'aqi': [51, 100], 'PM2.5': [12.0, 35.4], 'PM10': [54, 154]},
        'Unhealthy for Sensitive Groups': {'aqi': [101, 150], 'PM2.5': [35.5, 55.4], 'PM10': [154, 254]},
        'Unhealthy': {'aqi': [151, 200], 'PM2.5': [55.4, 150.4], 'PM10': [254, 354]},
        'Very Unhealthy': {'aqi': [201, 300], 'PM2.5': [150.5, 250.4], 'PM10': [354, 425]},
        'Hazardous': {'aqi': [301, 400], 'PM2.5': [250.4, 350.4], 'PM10': [425, 504]},
        'Very Harzadous': {'aqi': [401, 500], 'PM2.5': [350.4, 500.4], 'PM10': [504, 1004]}
        }

topic = f'sensors/{sensor_name}'.lower()
print(topic)
auth = {'username': username, 'password': password}

if len(sys.argv) == 2:
    '''this will take the integer number for the USB port'''

    _port = sys.argv[1]
else:
    print('Please enter a number for USB port. Existing.')
    exit()

port = '/dev/ttyUSB{}'.format(_port)
sensor = SDS011(port, use_query_mode=True)


def internet_ready():
    '''check if internet connect is ready'''
    try:
        _ = socket.create_connection((mqtt, 1883), 3)
        return True
    except Exception as e:
        print("Error {}".format(e))
        return False


def rename_tmp():
    '''renaming a temporary file that stores data
    when the connect to MQTT was down'''

    tmpFile = os.path.join(host_folder(), tmpName)
    new_name = time.strftime('%Y%b%m_%H%M%S.txt')
    newtmp = os.path.join(host_folder(), new_name)
    os.rename(tmpFile, newtmp)
    return None


def findRange(pollulant, conc):
    '''return key of the category, PM2.5, 30 ug/m3'''
    for key, value in AQIs.items():
            range_ = value[pollulant]
            if conc >= range_[0] and conc <= range_[1]:
                    return key


def calAQI(pollulant, conc):
    '''return AQI based US EPA for PM2.5 and PM10, p16, 2013 Technical Asst.'''
    key = findRange(pollulant, conc)
    I_Lo = AQIs[key]['aqi'][0]
    I_Hi = AQIs[key]['aqi'][1]
    BP_Lo = AQIs[key][pollulant][0]
    BP_Hi = AQIs[key][pollulant][1]
    AQI_X = (I_Hi-I_Lo)*(conc-BP_Lo)/(BP_Hi-BP_Lo) + I_Lo
    return round(AQI_X, 1), key


def host_folder():
    '''create a new filter for each month to store locally'''

    this_month_folder = time.strftime('%b%Y')
    basedir = os.path.abspath(os.path.dirname(__file__))
    all_dirs = [d for d in os.listdir(basedir) if os.path.isdir(d)]
    if len(all_dirs) == 0 or this_month_folder not in all_dirs:
        os.makedirs(this_month_folder)
        print('created: {}'.format(this_month_folder))
    # else:
    #     this_month_folder = max(all_dirs, key=os.path.getmtime)
    return os.path.join(basedir, this_month_folder)


def add_header():
    '''CUSTOMIZE YOUR HEADER
    add header the CSV file'''

    global logFile
    logFile = os.path.join(host_folder(), logName)
    print('Logfile {}'.format(logFile))
    with open(logFile, 'a+') as f:
        f.seek(0)
        head_ = f.readline()
        if not head_.startswith("Date"):
            header = 'Date Time, PM2.5, PM10, AQI2.5, AQI10, Air Quality\n'
            f.write(header)
        else:
            ts = time.strftime('%x %X', time.localtime())
            sprtor = '{}, 0, 0, 0, 0, 0\n'.format(ts)
            f.write(sprtor)
    return None

def push_MQTT(mesg):
    '''optionally push the data to MQTT server'''

    try:
        publish.single(topic, mesg, hostname=mqtt, auth=auth)
    except Exception as e:
        print('Error: {}'.format(e))
        pass
    return None

def add_missing():
    '''repush data from a tmp file after the connect to MQTT is restored'''

    count = 0
    with open(logFile, 'r+') as f:
        lines = f.readlines()
    for line in lines:
        push_MQTT(line.strip())
        count += 1
        time.sleep(0.2)
        print('{}:{}'.format(count, line.strip()))
    return None


def run():
    '''to setup to working cycle for Nova Fitness SDS011'''

    global pm10, pm25
    sensor.sleep(sleep=False) # wakup
    time.sleep(30) # stablizing == 30 sec turn on the fan
    pm25, pm10 = sensor.query()
    sensor.sleep()
    return None


def schedule(snapTime=570,push_mqtt=True):
    '''master function
    this function will call other sub-routine function above to perform'''

    global lastTime
    if lastTime == 0:
        add_header()
    if time.time()-lastTime >= snapTime:
        ts = time.strftime('%x %X', time.localtime())
        print("Run script at: {}, lastRun was {}".format(ts, lastTime))
        
        run()
        aqi_pm25, status_pm25 = calAQI('PM2.5', pm25)
        aqi_pm10, status_pm10 = calAQI('PM10', pm10)

        if aqi_pm25 > aqi_pm10:
            air_quality = status_pm25
            air_aqi = aqi_pm25
        else:
            air_quality = status_pm10
            air_aqi = aqi_pm10
        # save data to the local folder
        payload = ','.join([ts, str(pm25), str(pm10), str(
            aqi_pm25), str(aqi_pm10), air_quality]) + '\n'
        
        '''save data locally with CSV file'''
        with open(logFile, 'a+') as f:
            f.write(payload)
            print('Save data: {}'.format(payload))
 
        '''optionally push data to MQTT server'''
        global is_tmp_file
        if push_mqtt:
            #~ prepare the load
            mesg = {'sensor': sensor_name, 'timestamp': ts, 'pm25': pm25, 'pm10': pm10,
                'aqi25': aqi_pm25, 'aqi10': aqi_pm10, 'level': air_quality}
            print(mesg)
            # print(type(mesg))
            mesg = json.dumps(mesg)
            if internet_ready():
                # push if internet is ready
                push_MQTT(mesg)
                print('Pushed MSG {}'.format(mesg))
                #~ republish data for downtime store
                if is_tmp_file:
                    add_missing()
                    rename_tmp()
                    is_tmp_file = False
            else:
                # write temporary to file
                tempLogFile = os.path.join(host_folder(), tmpName)
                is_tmp_file = True
                with open(tempLogFile, 'a+') as f:
                    f.write(mesg)
                    f.write('\n')
                    print('No interet, saved: {}'.format(mesg))
        # finally set the time post            
        lastTime = int(time.time())
    else:
        time.sleep(1.0)
    return None

if __name__ == '__main__':
    while True:
        schedule(snapTime=60, push_mqtt=True)
