#!/bin/bash

SERVICE=mqtt_pyicloud
MYDIR=$(pwd)
APPDIR=$(dirname $0)
cd ${APPDIR}
# if ! test -d .venv
# then
#     echo creating virtual env
#     python3 -m venv .venv
#     . .venv/bin/activate
#     .venv/bin/pip install --upgrade pip 
#     .venv/bin/python3 -m pip install -r requirements.txt
# else
#     . .venv/bin/activate
# fi

# ( cd src ; ../.venv/bin/python3 app.py --daemon )
( cd src ; python3 app.py)
cd ${MYDIR}

exit 0