Prerequisites:

1. fernet key

Make a secrets/ directory where the docker-compose.yaml is, and inside make a text file fernet_key.txt

Generate a fernet key by using the command:

python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

It will look something like:

u7s2YyFvZog91XOXp7lUtqBfRexvR4XCh3NwVHoMiCs=

Note:

This action requires python3 and cryptography, installing for example on Arch Linux:

# Install Python 3 and pip (if not already installed)
sudo pacman -Syu python python-pip

# Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate

# Install cryptography
pip install cryptography

# Once the key is generated, leave virtual environment
deactivate

2. docker, docker-compose

Install docker with:

sudo pacman -Syu docker docker-compose

Enable docker service:

sudo systemctl enable --now docker.service

Verify docker status:

sudo systemctl status docker

How to run:

sudo docker-compose up -d
