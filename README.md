# nova_fitness_sds011
- Script in Python3.6 for air quality sensor (Nova Fitness SDS011, SDS018), save data in .CSV file or push to MQTT server
- the script works with Python3.6 without modifying `print` or any Python3 (have to modify `print`)
- work with SDS011 and SDS18
- to run the script, check the USB port. In linux, the port can be found by `ls /dev/ttyUSB*`
- run `python3.6 runfile.py 0`

## here is what looks like in CLI:
<p align="center">
  <img src="img/Screenshot-1.png"/>
</p>

## The CSV file stored data locally
[CSV file](http://Nov2019/sds018_test.csv)

## if the MQTT is enabled through the flag `push_mqtt=True`, here is the data in the server
<p align="center">
  <img src="img/Screenshot-2.png"/>
</p>
