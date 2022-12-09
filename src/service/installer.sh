#!/bin/bash

create_service()
{
cat <<EOF>/tmp/${SERVICE}.service
[Unit]
Description=${SERVICE}
After=multi-user.target

[Service]
Type=simple
User=${MYUSER}
WorkingDirectory=${WORKDIR}/
ExecStart=${WORKDIR}/${SERVICE}.sh
Restart=on-abort

[Install]
WantedBy=multi-user.target
EOF
}

SERVICE=mqtt_pyicloud
echo "Execute as pi user"
MYDIR=$(pwd)
APPDIR=$(dirname $0)
WORKDIR=$(cd ${APPDIR}; cd ../.. ; pwd)
MYUSER=$(whoami)
echo "Create service file ${SERVICE}.service"
create_service
sudo mv /tmp/${SERVICE}.service /lib/systemd/system/${SERVICE}.service
echo "Reload daemon ${SERVICE}"
sudo systemctl daemon-reload
echo "Enable daemon ${SERVICE}"
sudo systemctl enable ${SERVICE}.service
echo "Start daemon ${SERVICE}"
sudo systemctl start ${SERVICE}.service
echo "Check status daemon ${SERVICE}"
sudo systemctl status ${SERVICE}.service
exit