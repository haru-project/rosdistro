#!/bin/bash

release=$(lsb_release -c -s)

if [ "$release" == "bionic" ]; then

    export DEBIAN_FRONTEND=noninteractive

    curl -sSL https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
    echo 'libk4abt1.0-dev libk4abt1.0-dev/accepted-eula-hash string 03a13b63730639eeb6626d24fd45cf25131ee8e8e0df3f1b63f552269b176e38' | debconf-set-selections
    echo 'libk4abt1.0-dev libk4abt1.0-dev/accept-eula boolean true' | debconf-set-selections

    echo 'libk4abt1.0 libk4abt1.0/accepted-eula-hash string 03a13b63730639eeb6626d24fd45cf25131ee8e8e0df3f1b63f552269b176e38' | debconf-set-selections
    echo 'libk4abt1.0 libk4abt1.0/accept-eula boolean true' | debconf-set-selections

    echo 'libk4a1.3 libk4a1.3/accepted-eula-hash string 0f5d5c5de396e4fee4c0753a21fee0c1ed726cf0316204edda484f08cb266d76' | debconf-set-selections
    echo 'libk4a1.3 libk4a1.3/accept-eula boolean true' | debconf-set-selections

    apt-add-repository https://packages.microsoft.com/ubuntu/18.04/prod && apt update && apt install -yq libk4a1.3 libk4a1.3-dev libk4abt1.0 libk4abt1.0-dev
fi
