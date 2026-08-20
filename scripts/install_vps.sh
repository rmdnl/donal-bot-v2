#!/bin/bash
# Fresh VPS installer untuk DONAL Bot Pro
set -e
cd "$(dirname "$0")/.."

echo ">> Installing system packages"
sudo apt update
sudo apt install -y python3-venv python3-pip git

echo ">> Creating virtualenv + installing dependencies"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f .env ]; then
    cp .env.example .env
    echo ">> .env dibuat - ISI CREDENTIALS: nano .env"
fi

echo ">> Registering systemd service"
sudo cp donal-bot-pro.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable donal-bot-pro

echo ""
echo "Instalasi selesai."
echo "1) nano .env          (isi API keys + Telegram token)"
echo "2) nano config.yaml   (opsional: sesuaikan parameter)"
echo "3) sudo systemctl start donal-bot-pro"
echo "4) journalctl -u donal-bot-pro -f"
