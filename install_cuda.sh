#!/bin/bash

release=$(lsb_release -c -s)
export DEBIAN_FRONTEND=noninteractive

if [ "$release" == "bionic" ]; then
    wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu1804/x86_64/cuda-ubuntu1804.pin
    sudo mv cuda-ubuntu1804.pin /etc/apt/preferences.d/cuda-repository-pin-600

    wget https://developer.download.nvidia.com/compute/cuda/10.2/Prod/local_installers/cuda-repo-ubuntu1804-10-2-local-10.2.89-440.33.01_1.0-1_amd64.deb
    sudo dpkg -i cuda-repo-ubuntu1804-10-2-local-10.2.89-440.33.01_1.0-1_amd64.deb
    
    sudo apt-key add /var/cuda-repo-10-2-local-10.2.89-440.33.01/7fa2af80.pub
    sudo apt-get update && sudo apt-get -y install cuda

elif [ "$release" == "xenial" ]; then
    wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu1604/x86_64/cuda-ubuntu1604.pin
    sudo mv cuda-ubuntu1604.pin /etc/apt/preferences.d/cuda-repository-pin-600
    
    wget https://developer.download.nvidia.com/compute/cuda/10.2/Prod/local_installers/cuda-repo-ubuntu1604-10-2-local-10.2.89-440.33.01_1.0-1_amd64.deb
    dpkg -i cuda-repo-ubuntu1604-10-2-local-10.2.89-440.33.01_1.0-1_amd64.deb
    
    apt-key add /var/cuda-repo-10-2-local-10.2.89-440.33.01/7fa2af80.pub
    apt-get update && apt-get -yq install cuda

elif [ "$release" == "focal" ]; then

wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-ubuntu2004.pin
sudo mv cuda-ubuntu2004.pin /etc/apt/preferences.d/cuda-repository-pin-600
wget https://developer.download.nvidia.com/compute/cuda/11.2.2/local_installers/cuda-repo-ubuntu2004-11-2-local_11.2.2-460.32.03-1_amd64.deb
sudo dpkg -i cuda-repo-ubuntu2004-11-2-local_11.2.2-460.32.03-1_amd64.deb
sudo apt-key add /var/cuda-repo-ubuntu2004-11-2-local/7fa2af80.pub
sudo apt-get update && sudo apt-get -y install cuda
fi
