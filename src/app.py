from typing import Optional
from fastapi import FastAPI
from starlette.responses import RedirectResponse
from enum import Enum
import uvicorn
import logging
import os
from icloud_library import IcloudLibrary

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

fastapi_parameters = {
    "title": "mqtt_pyicloud",
    "description": "Broker APIs to interact with Apple Icloud and mqtt endpoints",
    "version": "0.2.1",
    "contact": {
        "name": "Jordi Redondo",
        "email": "jordipromotions@gmail.com",
        "url": "https://github.com/redcorjo/mqtt_pyicloud"
    },
    "license_info": {
        "name": "GNU GPLv3",
        "url": "https://raw.githubusercontent.com/redcorjo/mqtt_pyicloud/master/LICENSE.md"
    }
}

app = FastAPI(**fastapi_parameters)
icloud_task = IcloudLibrary()


@app.get("/getdata")
async def get_data():
    payload = icloud_task.process_iteration()    
    return payload

@app.post("/frequency")
async def post_refresh_frequency(frequency: int):
    payload = icloud_task.setFrequency(frequency)   
    return {"payload": payload}

@app.post("/icloud_token")
async def post_set_icloud_token(icloud_token: str):
    payload = icloud_task.set_icloud_token(icloud_token)
    return {"payload": payload}

@app.get("/")
async def redirect_docs():
    response = RedirectResponse(url='/docs')
    return response

def launch_fastapp(port=8000, host="0.0.0.0", settings=None):
    if settings != None:
        app.state.config = settings
    else:
        app.state.config = {}
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    hostname = icloud_task.getConfig("hostname", section="web")
    port = icloud_task.getConfig("port", section="web")
    launch_fastapp( host=hostname, port=int(port))