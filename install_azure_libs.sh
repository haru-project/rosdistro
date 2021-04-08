#!/bin/bash

curl -s https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
sudo apt-add-repository https://packages.microsoft.com/ubuntu/18.04/prod

export DEBIAN_FRONTEND=noninteractive

echo 'libk4abt1.1 libk4abt1.1/accepted-eula-hash string 03a13b63730639eeb6626d24fd45cf25131ee8e8e0df3f1b63f552269b176e38' | sudo debconf-set-selections
echo 'libk4abt1.1 libk4abt1.1/accept-eula boolean true' | sudo debconf-set-selections

echo 'libk4a1.4 libk4a1.4/accepted-eula-hash string 0f5d5c5de396e4fee4c0753a21fee0c1ed726cf0316204edda484f08cb266d76' | sudo debconf-set-selections
echo 'libk4a1.4 libk4a1.4/accept-eula boolean true' | sudo debconf-set-selections
    
if [ "$(lsb_release -c -s)" == "focal" ]; then
    curl -sSL https://packages.microsoft.com/config/ubuntu/18.04/prod.list | sudo tee /etc/apt/sources.list.d/microsoft-prod.list
fi

sudo apt update
sudo apt install libk4a1.4-dev -yq
sudo apt install libk4abt1.1-dev -yq
sudo apt install k4a-tools -yq
