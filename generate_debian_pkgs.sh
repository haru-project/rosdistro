#!/usr/bin/env bash
 
function find_in_list()
{
   [[ "$2" == *"$1"* ]] && return 0 || return 1;
}
 
function add_path_to_rules()
{
   # The idea was to pass an extra path
   # to CMAKE_PREFIX_PATH pointing to the install folder in the workspace, so the
   # debian generator was able to compile it. I was not able to pass the flag using dh
   # so I had to modify the rules file that gets generated and append the path
   # at the end of the line...
   sed -i "/CMAKE_PREFIX_PATH=*\"/ s#.\$#;$1\"#" debian/rules
}
 
function get_current_commit()
{
   git rev-parse --short HEAD
}
 
function add_commit_to_control()
{
   sed -i "/^Description:/ s/$/ [$(get_current_commit)]/" debian/control
}
 
function get_package_paths()
{
   # Find all packages in the workspace (folders containing both a 'package.xml' and a 'CMakeLists.txt')
   # -prune is used to exclude subfolders after a match has been found (packages inside packages)
   find "$1" -type d -exec test -f '{}'/package.xml -a -f '{}'/CMakeLists.txt \; -printf "%p\n" -prune | sort | uniq
}
 
function generate_binary_package()
{
   local directory=$1
 
   # Extract the package name from the CMakeLists.txt file. This is just to get an unique
   # id for each build folder. It could have been a number or a random string.
   # It doesn't have to be the package name
   package_name=$(grep -m 1 "project(" "${directory}/CMakeLists.txt" | cut -d"(" -f2 | cut -d" " -f1 | cut -d")" -f1)
 
   # Check if the package should be processed (because it's in the list or because)
   # all the packages should be processed
 
   if [[ -v PACKAGES ]] && ! find_in_list "$package_name" "$PACKAGES"; then
       echo "$package_name not found in package list. Skipping..."
       return 0
   fi
 
   # It seems the bloom-generate has to be executed in the package folder itself or
   # or in a parent folder (aka, it's not valid to try to generate it from /tmp)
   cd "$directory" 
   local os_release=$(cat /etc/os-release | grep UBUNTU_CODENAME= | sed 's/=/\n/g' | tail -1)
   bloom-generate rosdebian --os-name ubuntu --os-version "$os_release" --ros-distro "$ROS_DISTRO" "$directory"
 
   add_path_to_rules "${WORKSPACE_FOLDER}"/install
   add_commit_to_control
 
   # Replace previous postint scripts if any
   test -f debian/postinst && rm --force debian/postinst
   test -f "$directory"/postinst && cp --force "$directory"/postinst debian/
   
   # Replace previous postrm scripts if any
   test -f debian/postrm && rm --force debian/postrm
   test -f "$directory"/postrm && cp --force "$directory"/postrm debian/
 
   # Replace previous preinst scripts if any
   test -f debian/preinst && rm --force debian/preinst
   test -f "$directory"/preinst && cp --force "$directory"/preinst debian/
 
   # Replace previous prerm scripts if any
   test -f debian/prerm && rm --force debian/prerm
   test -f "$directory"/prerm && cp --force "$directory"/prerm debian/
 
   # I didn't manage to pass pamaters to dh by calling the rules script directly, but
   # it seems it's possible to call dh by hand and add the options. The rules script
   # will be executed automatically
   fakeroot dh binary --buildsystem=cmake --parallel \
                      --sourcedirectory="$directory" \
                      --builddirectory="${BUILD_PREFIX}/bloom_build/${package_name}" \
                      --tmpdir="${BUILD_PREFIX}/bloom_tmp/${package_name}" \
                      --dpkg-shlibdeps-params="--ignore-missing-info -l${WORKSPACE_FOLDER}/install/lib/
                          -l${WORKSPACE_FOLDER}/install/lib/${package_name}/lib"
   if [ ! -z "$NOTIFY" ]; then                 
      if [ $? -eq 0 ]
      then
        echo "Debian file built succesfully"
        curl -X POST -H 'Content-type: application/json' --data '{"text":"Built '"${package_name}"' '"${package_version}"' debian package for '"${ubuntu_version}"' "}' "$SLACK_WEBHOOK_NOTIFICATION"
      else
        echo "Could not create debian file" >&2
        curl -X POST -H 'Content-type: application/json' --data '{"text":"Failed to build '"${package_name}"' '"${package_version}"' for '"${ubuntu_version}"' "}' "$SLACK_WEBHOOK_NOTIFICATION"
        exit 1
      fi
   fi
}
# NOTE: Add here libraries that are included in the package directly and they are not a system dependency (like Qt for the routine generator app)
 
 
function parse_arguments()
{
   for i in "$@"
   do
       case $i in
           --parallel=*)
               NUM_THREADS="${i#*=}"
               shift # past argument=value
               ;;
           --parallel)
               # Get num cores if no value has been provided
               NUM_THREADS=$(grep -c ^processor /proc/cpuinfo)
               shift # past argument=value
               ;;
           --workspace_folder=*)
               WORKSPACE_FOLDER="${i#*=}"
               shift # past argument=value
               ;;
           --output_folder=*)
               OUTPUT_FOLDER="${i#*=}"
               shift # past argument=value
               ;;
           --send-to-apt)
               SEND_TO_APT=1
               shift
               ;;
            --notify)
               NOTIFY=1
               shift
               ;;
            --resolv-depends)
               RESOLV_DEPENDS=1
               shift
               ;;
           --packages=*)
               PACKAGES="${i#*=}"
               shift # past argument=value
               ;;
           *)
               # unknown option
               ;;
       esac
   done
 
   if [[ -v WORKSPACE_FOLDER ]] && [[ -v OUTPUT_FOLDER ]]; then
       return 1
   fi
 
   return 0
}
 
if parse_arguments "$@"; then
   echo "Usage: $0 [--parallel[=num_threads]] [--packages=package1[:package2...]] --workspace_folder=/path/to/folder --output_folder=/path/to/folder --send-to-apt --notify" 
   exit 1
fi
 
# Check if the path provided is a catkin_workspace (workspaces contain a .catkin_workspace file)
if [ ! -f "${WORKSPACE_FOLDER}/.catkin_workspace" ]; then
   echo "Error. ${WORKSPACE_FOLDER} is not the root of a catkin workspace"
   exit 1
fi
 
# This is a workaround to allow the workflow generate the debain package in focal with gcc7 compiler....
if [ "$PACKAGES" = "strawberry_ros_zz" ] && [ "$(lsb_release -cs)" = "focal" ]; then

   update-alternatives --set gcc /usr/bin/gcc-7
   update-alternatives --set g++ /usr/bin/g++-7
fi

# Delete any previous compilation
BUILD_PREFIX=/tmp/bloom_debian
rm --force -R $BUILD_PREFIX
mkdir -p $BUILD_PREFIX
 
cd "${WORKSPACE_FOLDER}"
WORKSPACE_FOLDER=$(pwd)

if [ ! -z $RESOLV_DEPENDS ]; then
   rosdep install --from-paths ./src --rosdistro "$(rosversion -d)" -y -r --os=ubuntu:"$(lsb_release -c --short)"
fi

package_version=$(catkin_package_version)
ubuntu_version=$(lsb_release -d | awk '{print $2,$3,$4}' )
 
# catkin_make install is run first.
# This will be used later to generate the binary packages
 
# Run debian package generation in parallel if NUM_THREADS has been provided (requires GNU parallel)
if [[ -v NUM_THREADS ]]; then
 
   if ! catkin_make install -j "$NUM_THREADS"; then
      exit 1
   fi
   
   # Local functions and vars have to be exported so they can be found by GNU parallel
   export -f generate_binary_package
   export -f add_path_to_rules
   export -f find_in_list
   export -f add_commit_to_control
   export -f get_current_commit
 
   export WORKSPACE_FOLDER
   export BUILD_PREFIX
   export PACKAGES
 
   parallel --jobs "$NUM_THREADS" --will-cite -u "generate_binary_package {}" ::: $(get_package_paths "$WORKSPACE_FOLDER")
 
else
   if ! catkin_make install; then  
      exit 1
   fi
   # Runs in sequence if parallel has not been set
   for directory in $(get_package_paths "$WORKSPACE_FOLDER"); do
       generate_binary_package "$directory"
   done
fi
 
# Move the generated debs to the output folder
# and remove the debian/ folder left after
mkdir -p "$OUTPUT_FOLDER"
 
for directory in $(get_package_paths "$WORKSPACE_FOLDER"); do
   mv --force  "$directory"/../*.deb "$OUTPUT_FOLDER"
   rm --force -R "$directory/debian/"
done

if [ "$PACKAGES" = "strawberry_ros_zz" ];then

   cd "$OUTPUT_FOLDER"
   mkdir temp_zz
   dpkg-deb -R ros-"$ROS_DISTRO"-strawberry-ros-zz_* temp_zz/
   rm ros-"$ROS_DISTRO"-strawberry-ros-zz_*
   sed -i 's/flowdesigner,//g' temp_zz/DEBIAN/control 
   version=$(cat temp_zz/DEBIAN/control | grep Version | cut -d ":" -f2 | sed 's/^ *//g')
   dpkg-deb -b temp_zz/ ros-"$ROS_DISTRO"-strawberry-ros-zz_"$version"_amd64.deb
   rm -rf temp_zz/
fi 
if [ ! -z $SEND_TO_APT ]; then

   cd "${WORKSPACE_FOLDER}"
   scp *.deb haru-bot@robotics.upo.es:~/automated_deploy
   ssh -t haru-bot@robotics.upo.es 'sudo ./add_pkg.sh' 
   
   if [ ! -z "$NOTIFY" ]; then
      if [ $? -eq 0 ]
      then
           curl -X POST -H 'Content-type: application/json' --data '{"text":" '"${package_name}"' '"${package_version}"' for '"${ubuntu_version}"' added to apt repository"}' "$SLACK_WEBHOOK_NOTIFICATION"
      else
           curl -X POST -H 'Content-type: application/json' --data '{"text":"Failed to add '"${package_name}"' '"${package_version}"' for '"${ubuntu_version}"' to apt repository"}' "$SLACK_WEBHOOK_NOTIFICATION"
      fi
   fi
fi
