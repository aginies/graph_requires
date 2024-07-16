# Goal

Generate a **graph** of all packages that require any of the provides of a package for SUSE and openSUSE).
This use **zypper** with **--requires-pkg** option on current system, so its using the actual Repositories set on the system.
If you are using some extra repository this can report false result compare to an '''official''' installation.
To avoid any false result it is recommended to use the container way.

# SUSE SLES case

To be able to access all repositories you need an SCC credentials, and the container requires a writable file, and as use there is some limitation, so you need as root to change the ACL on the file:
```shell
setfacl -m u:aginies:r /etc/zypp/credentials.d/SCCcredentials
```

About SCC and credentials, look at the online documentation at https://scc.suse.com/docs/userguide

# Usage

First clone this repo:
```shell
git clone https://github.com/aginies/graph_requires.git
```

Switch the script to executable and use it on your system:
```shell
cd graph_requires
chmod 755 graph_requires.py
./graph_requires.py PACKAGE_NAME,PKG2,PKG3 [OPTIONNAL_DIRECTORY]
```

# Example

```shell
./graph_requires.py qemu

Generate a graph of packages which requires another one.
This use zypper on current system, so using the actual Repositories set on this system.

Working with package qemu
check deps of docker-img-store-setup
check deps of patterns-public-cloud-15-Amazon-Web-Services-Instance-Tools
check deps of patterns-public-cloud-15-Google-Cloud-Platform
...
check deps of libvirt-daemon-config-network
check deps of libvirt-daemon-config-nwfilter
check deps of libvirt-daemon-driver-interface
check deps of libvirt-daemon-driver-libxl
...
check deps of qemu-ui-gtk
check deps of qemu-ui-spice-app
check deps of qemu-ui-spice-core
check deps of qemu-x86
check deps of xen-tools
DOT file '/tmp/graph/qemu.dot' generated successfully.
Image file '/tmp/graph/qemu_graph-sles15-sp6.jpg' generated successfully.
```

![image](https://github.com/aginies/graph_requires/blob/9c633963000ea28d850241e8c8e292d931a9c2de/examples/qemu_graph-sles15-sp6.jpg)

# Container

This provide you a clean environement to check requires.

Build the container:
```shell
./graph-container-manage.sh build
1. openSUSE Leap 15.5
2. openSUSE Leap 15.6
3. openSUSE Tumbleweed
4. SUSE SLES 15SP5
5. SUSE SLES 15SP6

Enter your OS choice [1-5]: 2
STEP 1/23: FROM opensuse/leap:15.6
STEP 2/23: LABEL Description="Graph requires Container"
..............
```

Use it:
```shell
./graph-container-manage.sh run
./graph-container-manage.sh run
localhost/graph-sles15-sp6      latest      7f7bfcf697fc  3 seconds ago  223 MB
Enter the container ID: 7f7bfcf697fc
Enter the package name (separated by comma): qemu,libvirt

Generate a graph of all packages that require any of the provides of a package.
This use zypper on current system, so using the actual Repositories set on the system.

Working with package qemu
check deps of docker-img-store-setup
check deps of patterns-public-cloud-15-Amazon-Web-Services-Instance-Tools
check deps of patterns-public-cloud-15-Google-Cloud-Platform
.....
check deps of virt-top
check deps of virt-viewer
check deps of virtual-host-gatherer-Libvirt
Generating libvirt dot file
DOT file '/tmp/graph/qemu_libvirt.dot' generated successfully.
Image file '/tmp/graph/qemu_libvirt_15-SP6.jpg' generated successfully.
Generating image /tmp/graph/qemu_libvirt_graph-sles15-sp6.jpg locally
```

![image](https://github.com/aginies/graph_requires/blob/db7ab2f046a0b4a966aa255abc7173f7fc919df2/examples/qemu_libvirt_spice_graph-sles15-sp6.jpg)

# Limit

If you try to graph what requires glibc... don't expect any result soon, this can be very slow to render...

# TODO

* fix limit filename size
* avoid redundant loop in graph

# Licence

GPL V3
