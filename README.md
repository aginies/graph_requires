# Goal

Generate a graph of all packages that require any of the provides of a package (SUSE/openSUSE).
This use zypper on current system, so its using the actual Repositories set on the system.
If you are using some extra repository this can report false result compare to an '''official''' installation.

# Usage

```shell
git clone https://github.com/aginies/graph_requires.git
cd graph_requires
chmod 755 graph_requires.py
./graph_requires.py PACKAGE_NAME
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
DOT file 'qemu-tools.dot' generated successfully.
Image file 'qemu-tools.jpg' generated successfully.
```

![image](https://github.com/aginies/graph_requires/blob/343637c8f144036901b734c2c323a2945dd674c5/examples/qemu-tools.jpg)

# Licence

GPL V3
