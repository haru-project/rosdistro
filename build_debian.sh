#! /bin/bash

REPO_NAME=$1
cd /home/haru/catkin_ws/src
git clone https://github.com/haru-project/$REPO_NAME -b $2
cd ..

if [ "$2" == "master" ]; then
   echo "master"
   ./generate_debian_pkgs.sh --workspace_folder=$(pwd) --output_folder=$(pwd) --packages=$(cat src/$REPO_NAME/package.xml | grep name | sed -E 's/<\/?name>//g' | sed -e 's/^[ \t]*//') --notify --send-to-apt --resolv-depends
else
   echo "other branch"
   ./generate_debian_pkgs.sh --workspace_folder=$(pwd) --output_folder=$(pwd) --packages=$(cat src/$REPO_NAME/package.xml | grep name | sed -E 's/<\/?name>//g' | sed -e 's/^[ \t]*//') --notify --resolv-depends
fi




