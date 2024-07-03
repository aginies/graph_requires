#!/bin/bash
# aginies@suse.com
# quick script to manage/use the container

function check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo "Error: $1 is not installed or not in your PATH."
        exit 1
    fi
}

DATA=/tmp/graph

run_container() {
containerid=$1
PACKAGE=$2
mkdir ${DATA}
podman run \
    --name graph \
    --rm -ti \
    --volume ${DATA}:${DATA} \
    ${containerid} ${PACKAGE}
}

build_container() {
echo "1. openSUSE Leap 15.5"
echo "2. openSUSE Leap 15.6"
echo "3. openSUSE Tumbleweed"
#echo "4. SUSE SLES 15SP5"
#echo "5. SUSE SLES 15SP6"

read -p "Enter your OS choice [1-5]: " choice

if ! [[ "$choice" =~ ^[0-9]+$ ]]; then
    echo "Invalid input. Please enter a number."
    exit 1
fi

case $choice in
	1)
	OS="opensuse/leap:15.5"
	;;
	2)
	OS="opensuse/leap:15.6"
	;;
	3)
	OS="opensuse/tumbleweed"
	;;
	4)
	OS="bci/bci-base:15.5"
	;;
	5)
	OS="bci/bci-base:15.6"
	;;
	*)
        echo "Invalid choice. Please enter a correct number..."
	exit 1
        ;;
esac

podman build \
       	--build-arg="OS=${OS}" \
	--tag graph-${OS} .
}

info() {
cat <<EOF 
#####################################################
DATA: '${DATA}'
#####################################################
EOF

echo "
First ARG is mandatory:
$0 [build|run|rmcache]


USAGE:

run
    podman run container

build
    build a local image of this container

rmcache
    remove the container image in cache
 "
}

###########
# MAIN
###########
#set -uxo pipefail
check_command podman

plop=$1
case $plop in
    run)
	podman images | grep graph
	read -p "Enter the container ID: " containerid
	read -p "Enter the package name: " PACKAGE
	run_container ${containerid} ${PACKAGE}
    ;;
    rmcache)
	podman images | grep graph
	echo " podman rmi -f IMAGE"
    ;;
    build)
	build_container	   
	;;
    *)
	info
esac
