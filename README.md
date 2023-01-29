# rosdistro

Service Robotics Lab custom debian related scripts:

* **rosdep.yaml**: rosdep lists. Relation between the name of the packages as dependency (package.xml) and the name of the APT debian package. To use it, you have to tell rosdep where it can find this file. To do so, add a new file called `50-haru.list` in `/etc/ros/rosdep/sources.list.d` and add the following line:

    ```bash
    yaml https://raw.githubusercontent.com/haru-project/rosdistro/master/rosdep.yaml
    ```
    You can now update your sources:

    ```bash
    rosdep update
    ```

* **generate_debian_pkgs.sh**: script to generate multiple catkin packages hosted in the same catkin workspace (including the dependencies, which could be also installed instead of to be in the workspace) using Bloom. To use it, you will need to install some packages:

    ```bash
    sudo apt-get install python-bloom fakeroot parallel debhelper -y
    ```

    **Important**: If you are running Ubuntu 20 replace ```python-bloom``` by ```python3-bloom```.

    * **Mandatory params**:
        * *--workspace_folder=/path/to/folder* 
        
            Path to the ROS workspace's root folder.

        * *--output_folder=/path/to/folder* 
            
            Path to folder where the generated deb should be moved to.
    * **Optional params**:
        * *--parallel=N_THREADS*

            Use multiple threads to generate the .deb files. The script will spawn one worker thread per core. You can force a given number of threads by adding a number to the option (e.g, --parallel=4).
        
        * *--packages=package1:package2* 
        
            By default, the script generates debian files for all the packages in the workspace. This option can be used to specify what packages you want to generate. Note that the list delimiter is ':'.

        * *--resolv-depends 
        
            Used to resolv the dependencies using rosdep to avoid installing them manually. 

