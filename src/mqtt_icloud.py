#!/usr/bin/python3

from pyicloud import PyiCloudService
import sys
import requests
import json
import os
import logging
import paho.mqtt.client as paho
import configparser
import base64
import socket
import time
from apscheduler.schedulers.background import BackgroundScheduler

LOGLEVEL = os.getenv("DEBUG", "INFO").upper()
if LOGLEVEL == "DEBUG":
    level = logging.DEBUG
elif LOGLEVEL == "INFO":
    level = logging.INFO
elif LOGLEVEL == "WARNING" or LOGLEVEL == "WARN":
    level = logging.WARNING
elif LOGLEVEL == "ERROR":
    level = logging.ERROR
else:
    level = logging.INFO

ENVIRONMENT = os.environ.get("ENVIRONMENT", "prod").lower()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
stream_handler = logging.StreamHandler()
logging_formatter = logging.Formatter(
    '%(levelname)-8s [%(filename)s:%(lineno)d] (' + ENVIRONMENT + ') - %(message)s')
stream_handler.setFormatter(logging_formatter)
logger.addHandler(stream_handler)

global icloud_token
icloud_token = None

def get2fa(api):
    logger.warning("Required 2Factor auth")
    print("Two-factor authentication required.")
    publish_mqtt("icloudauth", "required_2factor")
    my_interactive_session = sys.stdout.fileno()
    logger.warning(f"my_interactive_session={my_interactive_session}")
    
    code = None
    if my_interactive_session:
        subscribe_mqtt("icloud_token")
        token_file = "/tmp/icloud_token.txt"
        for iteration in range(300):
            time.sleep(1)
            global icloud_token
            if os.path.exists(token_file):
                with open(token_file) as my_file:
                    logger.info(f"Readed token file {token_file}")
                    code = my_file.readline().replace("\n","")
                    try:
                        os.remove(token_file)
                    except Exception as e:
                        logger.error("Problem deleting lock file " + token_file + " .Exception " + str(e))
                    logger.info(f"Deleted token file {token_file}")
                    break
            elif icloud_token != None:
                logger.info("Obtained icloud token from variable")
                code = icloud_token
                icloud_token = None
                break
    else:
        code = input("Enter the code you received of one of your approved devices: ")
    if code == None:
        sys.exit(1)
    result = api.validate_2fa_code(code)
    print("Code validation result: %s" % result)

    if not result:
        print("Failed to verify security code")
        sys.exit(1)

    if not api.is_trusted_session:
        print("Session is not trusted. Requesting trust...")
        result = api.trust_session()
        print("Session trust result %s" % result)

        if not result:
            print("Failed to request trust. You will likely be prompted for the code again in the coming weeks")


def get2sa(api):
    logger.warning("Required 2SAFactor auth")
    publish_mqtt("icloudauth", "required_2safactor")
    my_interactive_session = sys.stdout.fileno()
    logger.warning(f"my_interactive_session={my_interactive_session}")
    if not my_interactive_session:
        sys.exit(1)
    import click
    print("Two-step authentication required. Your trusted devices are:")

    devices = api.trusted_devices
    for i, device in enumerate(devices):
        print(
            "  %s: %s" % (i, device.get('deviceName',
            "SMS to %s" % device.get('phoneNumber')))
        )

    device = click.prompt('Which device would you like to use?', default=0)
    device = devices[device]
    if not api.send_verification_code(device):
        print("Failed to send verification code")
        sys.exit(1)

    code = click.prompt('Please enter validation code')
    if not api.validate_verification_code(device, code):
        print("Failed to verify verification code")
        sys.exit(1)

def publish_openhab(item_name,payload):
    openhab_server = getConfig("OPENHAB_SERVER", section="openhab")
    if openhab_server != None:
        logger.info(f"Publish openhab item={item_name} payload={payload}")
        response = requests.put(openhab_server + '/rest/items/'+item_name+'/state', str(payload), headers={'Content-type': 'text/plain'})    
        if response.status_code == 404:
            logger.warning(f"Does not exists {item_name} at openhab instane")
        else:
            logger.debug(f"Published event for item {item_name}")
    return True


def on_publish_mqtt(client,userdata,result): 
    logger.debug("data published \n")
    pass

def on_message_mqtt(client,userdata,result): 
    logger.debug("data published \n")
    global icloud_token
    icloud_token = result.payload.decode()
    pass

def subscribe_mqtt(item_name):
    mqtt_server = getConfig("MQTT_SERVER", section="mqtt")
    mqtt_topic = getConfig("MQTT_TOPIC", section="mnqtt")
    if mqtt_server != None:
        logger.info(f"Subscribe mqtt item={item_name}")
        client1=paho.Client("mqtt_icloud")
        client1.on_message = on_message_mqtt
        client1.connect(mqtt_server)
        client1.subscribe(f"{mqtt_topic}/{item_name}/state", qos=0) 
        client1.loop_start() 
    return True

def publish_mqtt(item_name, payload):
    mqtt_server = getConfig("MQTT_SERVER", section="mqtt")
    mqtt_topic = getConfig("MQTT_TOPIC", section="mnqtt")
    if mqtt_server != None:
        logger.info(f"Publish mqtt item={item_name} payload={payload}")
        client1=paho.Client("mqtt_icloud")
        client1.on_publish = on_publish_mqtt
        try:
            client1.connect(mqtt_server)
            client1.publish(f"{mqtt_topic}/{item_name}/state",str(payload)) 
        except Exception as e:
            logger.warning("Exception " + str(e))
            return False
    return True

def getConfig(key, section="settings"):
    config_file = __file__.replace(".py", ".ini")
    value = None
    if os.path.exists(config_file):
        config = configparser.ConfigParser(allow_no_value=True)
        config.read(config_file)
        if section in config and key in config[section]:
            value = config[section][key]
        else:
            value = os.environ.get(key)
    else:
        value = os.environ.get(key)
        logger.info(f"Creating initial version of the configuration file {config_file}")
        username = input("Enter the icloud username: ")
        password = input("Enter the icloud password: ")
        password = encode_value(password)
        TEMPLATE = f"""
[settings]
ICLOUD_USERNAME = {username}
ICLOUD_PASSWORD = {password}
[mqtt]
;MQTT_SERVER = 127.0.0.1
;MQTT_TOPIC = mqtt_icloud
[openhab]
;OPENHAB_SERVER = http://127.0.0.1:8080
[alias]
;name1 = alias
        """
        with open(config_file, "w") as myfile:
            myfile.writelines(TEMPLATE)
    if value == None and key == "MQTT_TOPIC":
        value = "mqtt_icloud"
    if "password" in key.lower() and value != None and not value.startswith("(ENC)"):
        logger.info(f"Masquerade value for key {key}")
        value = encode_value(value)
        with open(config_file, "w") as myfile:
            config[section][key] = value
            config.write(myfile)
    value = decode_value(value)
    return value

def encode_value(value):
    if value != None and not value.startswith("(ENC)"):
        master_key = socket.gethostname()
        my_value = base64.b64encode(value.encode()).decode()
        encoded_string = f"(ENC){my_value}"
    else:
        encoedd_string = value
    return encoded_string 

def decode_value(value):
    if value != None and value.startswith("(ENC)"):
        master_key = socket.gethostname()
        value = value.replace("(ENC)", "")
        decoded_string = base64.b64decode(value.encode()).decode()
    else:
        decoded_string = value
    return decoded_string

def process_iteration():
    username = getConfig("ICLOUD_USERNAME", section="settings")
    password = getConfig("ICLOUD_PASSWORD", section="settings")
    if username == None or password == None:
        logger.warning("Missing credentials. Exit from execute")
        sys.exit(-1)
    api = PyiCloudService(username, password)
    if api.requires_2fa:
        logger.warning("Required 2Factor auth")
        get2fa(api)
    elif api.requires_2sa:
        logger.warning("Required 2SA auth")
        get2sa(api)
    else:
        all_devices = api.devices
        for device in all_devices:
            device_data = device.data
            device_id = device_data["id"]
            device_name = device_data["name"]
            device_alias = getConfig(device_name, section="alias")
            device_display_name = device_data["deviceDisplayName"]
            if device_alias != None:
                item_name = device_alias + device_display_name
            else:
                item_name = device_name + device_display_name
            item_name = item_name.replace(" ","").replace("’","")
            device_status = device.status()
            try:
                device_location = device.location()
                device_location_gps = str(device_location['latitude']) + "," + str(device_location['longitude'])
                item_location = f"{item_name}_Location"
                item_alias = getConfig(item_location, section="alias")
                if item_alias != None:
                    item_location = item_alias
                publish_openhab(item_location, device_location_gps)
            except Exception as e:
                logger.warning(f"Exception {device_name} {device_id} " + str(e))
            item_status = f"{item_name}_status"
            item_alias = getConfig(item_status, section="alias")
            if item_alias != None:
                item_status = item_alias
            publish_mqtt(item_status, device_status)
        publish_mqtt("icloudauth", "ok")

def main():
    process_iteration()

if __name__ == "__main__":
    main()