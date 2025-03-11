[Unit]
Description=Alarm System Application
After=network.target

[Service]
Type=simple
User=nathan
WorkingDirectory=/home/nathan/Documents/AlarmePython
ExecStart=/bin/bash -c "source venv/bin/activate && python app.py --web"
Restart=on-failure
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target