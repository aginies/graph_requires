#!/bin/bash
# aginies@suse.com
# quick script to manage/use the container

# place to store result (default path of graph_requires.py script)
DATA=/tmp/graph

function check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo "Error: $1 is not installed or not in your PATH."
        exit 1
    fi
}


show_info() {
FILE=$1
    echo "${FILE} is not readable"
    echo "As root do:"
    echo "setfacl -m u:${USER}:r ${FILE}"
}

check_readable() {
FILE=$1
if [ -r "${FILE}" ]; then
    echo "${FILE} is readable"
elif [[ ! -f "${FILE}" ]]; then
    echo "${FILE} is not present or readable by user"
    show_info ${FILE}
    exit 1
else
    show_info ${FILE}
    exit 1
fi
}

check_sles() {
# graphviz needs to be installed on current system
check_command dot
# Credentials is required to get access to all repositories on SLES
check_readable /etc/zypp/credentials.d/SCCcredentials
}

run_container() {
containerid=$1
PACKAGE=$2
mkdir ${DATA}
podman run \
    --name graph \
    --rm -ti \
    -v /etc/zypp/credentials.d/SCCcredentials:/etc/zypp/credentials.d/SCCcredentials \
    --volume ${DATA}:${DATA} \
    ${containerid} ${PACKAGE}
}

build_container() {
echo "1. openSUSE Leap 15.5"
echo "2. openSUSE Leap 15.6"
echo "3. openSUSE Tumbleweed"
echo "4. SUSE SLES 15SP5"
echo "5. SUSE SLES 15SP6"
echo
echo "Note: for SLES you need to have graphviz-gd installed on your system to render the dot file"
echo
read -p "Enter your OS choice [1-5]: " choice

if ! [[ "$choice" =~ ^[0-9]+$ ]]; then
    echo "Invalid input. Please enter a number."
    exit 1
fi

case $choice in
	1)
	OSREG="opensuse/leap:15.5"
	PACKAGETOI="graphviz-gd"
	OS="leap-15.5"
	;;
	2)
	OSREG="opensuse/leap:15.6"
	PACKAGETOI="graphviz-gd"
	OS="leap-15.6"
	;;
	3)
	OSREG="opensuse/tumbleweed"
	PACKAGETOI="graphviz-gd"
	OS="tumbleweed"
	;;
	4)
	OSREG="bci/bci-base:15.5"
	PACKAGETOI="suseconnect-ng"
	OS="sles15-sp5"
	check_sles
	;;
	5)
	OSREG="bci/bci-base:15.6"
	PACKAGETOI="suseconnect-ng"
	OS="sles15-sp6"
	check_sles
	;;
	*)
        echo "Invalid choice. Please enter a correct number..."
	exit 1
        ;;
esac

podman build \
	--build-arg="OSREG=${OSREG}" \
	--build-arg="PACKAGETOI=${PACKAGETOI}" \
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
case ${plop} in
    run)
	podman images | grep graph
	read -p "Enter the container ID: " containerid
	read -p "Enter the package name (separated by comma): " PACKAGES
	run_container ${containerid} ${PACKAGES}
	# if this a SLES, jpg can not be generated, fixing this locally
	OS=`podman images | awk -v id="${containerid}" 'NR>1 && $3==id { split($1, parts, "/"); repo_name = parts[length(parts)]; print repo_name; exit }'`
	PACKAGESM=${PACKAGES//,/_)}
	if [ ! -e "${DATA}/${PACKAGESM}.jpg" ]; then
		echo "Generating image ${DATA}/${PACKAGESM}_${OS}.jpg locally"
		dot -Tjpg ${DATA}/${PACKAGESM}.dot -o ${DATA}/${PACKAGESM}_${OS}.jpg
	else
		echo "${DATA}/${PACKAGESM}_${OS}.jpg already exist.... exiting"
	fi
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
