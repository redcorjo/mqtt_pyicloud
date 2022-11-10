#!/usr/bin/python3

from pyicloud import PyiCloudService
import asyncio
import sys, getopt
import requests
import json
import os
import logging
import paho.mqtt.client as paho
import configparser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get2fa(api):
    logger.warning("Required 2Factor auth")
    print("Two-factor authentication required.")
    publish_mqtt("icloudauth", "required_2factor")
    sys.exit(1)
    # code = input("Enter the code you received of one of your approved devices: ")
    # result = api.validate_2fa_code(code)
    # print("Code validation result: %s" % result)

    # if not result:
    #     print("Failed to verify security code")
    #     sys.exit(1)

    # if not api.is_trusted_session:
    #     print("Session is not trusted. Requesting trust...")
    #     result = api.trust_session()
    #     print("Session trust result %s" % result)

    #     if not result:
    #         print("Failed to request trust. You will likely be prompted for the code again in the coming weeks")


def get2sa(api):
    logger.warning("Required 2SAFactor auth")
    publish_mqtt("icloudauth", "required_2safactor")
    sys.exit(1)
    # import click
    # print("Two-step authentication required. Your trusted devices are:")

    # devices = api.trusted_devices
    # for i, device in enumerate(devices):
    #     print(
    #         "  %s: %s" % (i, device.get('deviceName',
    #         "SMS to %s" % device.get('phoneNumber')))
    #     )

    # device = click.prompt('Which device would you like to use?', default=0)
    # device = devices[device]
    # if not api.send_verification_code(device):
    #     print("Failed to send verification code")
    #     sys.exit(1)

    # code = click.prompt('Please enter validation code')
    # if not api.validate_verification_code(device, code):
    #     print("Failed to verify verification code")
    #     sys.exit(1)

def publish_openhab(item_name,payload):
    logger.info(f"Publish openhab item={item_name} payload={payload}")
    openhab_server = getConfig("OPENHAB_SERVER")
    if openhab_server != None:
        response = requests.put(openhab_server + '/rest/items/'+item_name+'/state', str(payload), headers={'Content-type': 'text/plain'})    
        if response.status_code == 404:
            logger.warning(f"Does not exists {item_name} at openhab instane")
        else:
            logger.debug(f"Published event for item {item_name}")
    return True


def on_publish_mqtt(client,userdata,result): 
    logger.debug("data published \n")
    pass

def publish_mqtt(item_name, payload):
    mqtt_server = getConfig("MQTT_SERVER")
    mqtt_topic = getConfig("MQTT_TOPIC")
    if mqtt_server != None:
        logger.info(f"Publish mqtt item={item_name} payload={payload}")
        client1=paho.Client("mqtt_icloud")
        client1.on_publish = on_publish_mqtt
        client1.connect(mqtt_server)
        client1.publish(f"{mqtt_topic}/{item_name}/state",str(payload)) 
    return True

def getConfig(key):
    config_file = __file__.replace(".py", ".ini")
    value = None
    if os.path.exists(config_file):
        config = configparser.ConfigParser()
        config.read(config_file)
        if "settings" in config and key in config["settings"]:
            value = config["settings"][key]
        else:
            value = os.environ.get(key)
    else:
        value = os.environ.get(key)
        logger.info(f"Creating initial version of the configuration file {config_file}")
        username = input("Enter the icloud username: ")
        password = input("Enter the icloud password: ")
        TEMPLATE = f"""
[settings]
ICLOUD_USERNAME = {username}
ICLOUD_PASSWORD = {password}
#MQTT_SERVER = 127.0.0.1
#OPENHAB_SERVER = http://127.0.0.1:8080
#MQTT_TOPIC = mqtt_icloud
        """
        with open(config_file, "w") as myfile:
            myfile.writelines(TEMPLATE)
    # if value == None and key == "MQTT_SERVER":
    #     value = "127.0.0.1"
    # if value == None and key == "OPENHAB_SERVER":
    #     value = "http://127.0.0.1:8080"
    if value == None and key == "MQTT_TOPIC":
        value = "mqtt_icloud"
    return value

async def icloud():
    username = getConfig("ICLOUD_USERNAME")
    password = getConfig("ICLOUD_PASSWORD")
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
            device_display_name = device_data["deviceDisplayName"]
            item_name = device_name + device_display_name
            item_name = item_name.replace(" ","").replace("’","")
            device_status = device.status()
            try:
                device_location = device.location()
                device_location_gps = str(device_location['latitude']) + "," + str(device_location['longitude'])
                publish_openhab(f"{item_name}_Location", device_location_gps)
            except Exception as e:
                logger.warning(f"Exception {device_name} {device_id} " + str(e))
            publish_mqtt(f"{item_name}_status", device_status)
        publish_mqtt("icloudauth", "ok")
asyncio.run(icloud())
