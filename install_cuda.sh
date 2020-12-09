#!/bin/bash

release=$(lsb_release -c -s)
export DEBIAN_FRONTEND=noninteractive

if [ "$release" == "bionic" ]; then
    wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu1804/x86_64/cuda-ubuntu1804.pin
    mv cuda-ubuntu1804.pin /etc/apt/preferences.d/cuda-repository-pin-600
    
    wget http://developer.download.nvidia.com/compute/cuda/11.0.1/local_installers/cuda-repo-ubuntu1804-11-0-local_11.0.1-450.36.06-1_amd64.deb
    dpkg -i cuda-repo-ubuntu1804-11-0-local_11.0.1-450.36.06-1_amd64.deb
    
    apt-key add /var/cuda-repo-ubuntu1804-11-0-local/7fa2af80.pub
    apt update && apt -yq install cuda

elif [ "$release" == "xenial" ]; then
    wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu1604/x86_64/cuda-ubuntu1604.pin
    sudo mv cuda-ubuntu1604.pin /etc/apt/preferences.d/cuda-repository-pin-600
    
    wget https://developer.download.nvidia.com/compute/cuda/10.2/Prod/local_installers/cuda-repo-ubuntu1604-10-2-local-10.2.89-440.33.01_1.0-1_amd64.deb
    dpkg -i cuda-repo-ubuntu1604-10-2-local-10.2.89-440.33.01_1.0-1_amd64.deb
    
    apt-key add /var/cuda-repo-10-2-local-10.2.89-440.33.01/7fa2af80.pub
    apt-get update && apt-get -yq install cuda
fi
