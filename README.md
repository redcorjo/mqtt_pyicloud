# MQTT PYICLOUD

This project is a wrapper to obtain icloud data to feed openhab and mqtt. This code relies in python module pyicloud https://github.com/picklepete/pyicloud . Ensure prior of installing this app, to install:

1. python3 (ideally versions 3.7 or higher)
2. python modules
    1. paho-mqtt==1.5.0
    2. requests==2.21.0
    3. pyicloud==1.0.0

After installing all above components, at the same OS account to run this python program, first to execute at command line:

icloud --username \<youriclouduser>

first time the python program mqtt_icloud.py is executed, it will create a template of mqtt_icloud.ini configuration file. That configuration file is to be created at the same folder.

The script will loop for every device reported at the own icloud profile, and will provide in json all retrieved values. Values can be reported to openhab items and to mqtt queues. To enable those, MQTT_SERVER and OPENHAB_SERVER values shall be defined at configuration level

# Example mqtt_icloud.ini

```
[settings]
ICLOUD_USERNAME = username@icloud.com
ICLOUD_PASSWORD = mypassword
[mqtt]
MQTT_SERVER = 127.0.0.1
MQTT_TOPIC = mqtt_icloud
[openhab]
OPENHAB_SERVER = http://127.0.0.1:8080
[alias]
name1 = alias1
```

# Notes of usage

If icloud credentials are expired, we can be alerted by receiving the message at either below three approaches:

1. logger at console
2. openhab item icloudauth
3. mqtt topic icloudauth 

By that we can plug the alerting to other automations at our convenience. The big challenge of using icloud, it is the requirement of having a 2factor authentication initilized first.

The password added at the config file, if it is added on clear, the same script will masquerade and upodate it at config file

Version: 2022112700