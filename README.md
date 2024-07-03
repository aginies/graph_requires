# Goal

Generate a graph of all packages that require any of the provides of a package (SUSE/openSUSE).
This use zypper on current system, so its using the actual Repositories set on the system.
If you are using some extra repository this can report false result compare to an '''official''' installation.
To avoid any false result it is recommended to use the container way.

# Usage

First clone this repo:
```shell
git clone https://github.com/aginies/graph_requires.git
```

Switch the script to executable and use it on your system:
```shell
cd graph_requires
chmod 755 graph_requires.py
./graph_requires.py PACKAGE_NAME [OPTIONNAL_DIRECTORY]
```

# Example

```shell
./graph_requires.py qemu-tools

Generate a graph of packages which requires another one.
This use zypper on current system, so using the actual Repositories set on this system.

check deps of diskimage-builder
check deps of infos-creator-rpm
check deps of kiwi-systemdeps-filesystems
check deps of kiwi-image-oem-requires
check deps of kiwi-image-pxe-requires
check deps of kiwi-image-vmx-requires
check deps of kiwi-systemdeps
check deps of kiwi-systemdeps-disk-images
check deps of kiwi-systemdeps-iso-media
check deps of libguestfs-appliance
check deps of libguestfs
check deps of live-fat-stick
check deps of live-usb-gui
check deps of live-grub-stick
check deps of os-autoinst-devel
check deps of openQA-devel
check deps of os-autoinst-qemu-kvm
check deps of os-autoinst-qemu-x86
check deps of qemu-tools
DOT file '/tmp/graph/qemu-tools.dot' generated successfully.
Image file '/tmp/graph/qemu-tools.jpg' generated successfully.
```

![image](https://github.com/aginies/graph_requires/blob/343637c8f144036901b734c2c323a2945dd674c5/examples/qemu-tools.jpg)

# Container

This provide you a clean environement to check requires.

Build the container:
```shell
./graph-container-manage.sh build
1. openSUSE Leap 15.5
2. openSUSE Leap 15.6
3. openSUSE Tumbleweed
Enter your OS choice [1-3]: 2
STEP 1/23: FROM opensuse/leap:15.6
STEP 2/23: LABEL Description="Graph requires Container"
..............
```

Use it:
```shell
./graph-container-manage.sh run
localhost/graph-opensuse/leap        15.6        0e77c8ce4c3d  12 minutes ago  204 MB
Enter the container ID: 0e77c8ce4c3d
Enter the package name: qemu

Generate a graph of all packages that require any of the provides of a package.
This use zypper on current system, so using the actual Repositories set on the system.
check deps of diskimage-builder
check deps of docker-img-store-setup
check deps of gnome-boxes
check deps of gnome-boxes-lang
.....
check deps of xen-tools
DOT file '/tmp/graph/qemu.dot' generated successfully.
Image file '/tmp/graph/qemu.jpg' generated successfully.
```

# Licence

GPL V3
