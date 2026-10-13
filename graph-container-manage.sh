#!/bin/bash
# aginies@suse.com
# quick script to manage/use the container

# Place to store results. Must match DEFAULT_OUTPUT_DIR in graph_requires.py
# and the container's --dir default; override with DATA=... when calling.
DATA=${DATA:-/tmp/graph}
# Max length of the generated file stem. Must match MAX_NAME_LEN in
# graph_requires.py so this fallback finds the files the script wrote.
MAX_NAME_LEN=64

check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo "Error: $1 is not installed or not in your PATH."
        exit 1
    fi
}

show_info() {
    local file="$1"
    echo "${file} is not readable"
    echo "As root do:"
    echo "setfacl -m u:${USER}:r ${file}"
}

check_readable() {
    local file="$1"
    if [ -r "${file}" ]; then
        echo "${file} is readable"
    elif [ ! -f "${file}" ]; then
        echo "${file} is not present or readable by user"
        show_info "${file}"
        exit 1
    else
        show_info "${file}"
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
    local containerid="$1"
    local package="$2"
    mkdir -p "${DATA}"
    # No fixed '--name graph': a crashed earlier run would leave that name
    # taken and block this one; '--rm' still cleans up on normal exit.
    podman run \
        --rm -ti \
        -v /etc/zypp/credentials.d/SCCcredentials:/etc/zypp/credentials.d/SCCcredentials \
        --volume "${DATA}:${DATA}" \
        "${containerid}" "${package}"
}

build_container() {
    echo "1. openSUSE Leap 15.5"
    echo "2. openSUSE Leap 15.6"
    echo "3. openSUSE Leap 15.7"
    echo "4. openSUSE Tumbleweed"
    echo "5. SUSE SLES 15SP5"
    echo "6. SUSE SLES 15SP6"
    echo "7. SUSE SLES 15SP7"
    echo "8. SUSE SLE 16"
    echo
    echo "Note: for SLES you need to have graphviz-gd installed on your system to render the dot file"
    echo
    read -r -p "Enter your OS choice [1-8]: " choice

    if ! [[ "$choice" =~ ^[0-9]+$ ]]; then
        echo "Invalid input. Please enter a number."
        exit 1
    fi

    local osreg pkgatoi os
    case "$choice" in
        1) osreg="opensuse/leap:15.5"; pkgatoi="graphviz-gd"; os="leap-15.5" ;;
        2) osreg="opensuse/leap:15.6"; pkgatoi="graphviz-gd"; os="leap-15.6" ;;
        3) osreg="opensuse/leap:15.7"; pkgatoi="graphviz-gd"; os="leap-15.7" ;;
        4) osreg="opensuse/tumbleweed"; pkgatoi="graphviz-gd"; os="tumbleweed" ;;
        5) osreg="bci/bci-base:15.5"; pkgatoi="suseconnect-ng"; os="sles15-sp5"; check_sles ;;
        6) osreg="bci/bci-base:15.6"; pkgatoi="suseconnect-ng"; os="sles15-sp6"; check_sles ;;
        7) osreg="bci/bci-base:15.7"; pkgatoi="suseconnect-ng"; os="sles15-sp7"; check_sles ;;
        8) osreg="bci/bci-base:16.0"; pkgatoi="suseconnect-ng"; os="sle16";    check_sles ;;
        *)
            echo "Invalid choice. Please enter a correct number..."
            exit 1
            ;;
    esac

    podman build \
        --build-arg="OSREG=${osreg}" \
        --build-arg="PACKAGETOI=${pkgatoi}" \
        --tag "graph-${os}" .
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
check_command podman

action="${1:-}"
case "${action}" in
    run)
        if ! podman images | grep graph; then
            echo "No local 'graph' images found. Build one first: $0 build"
            exit 1
        fi
        read -r -p "Enter the container ID: " containerid
        read -r -p "Enter the package name (separated by comma): " packages
        run_container "${containerid}" "${packages}"
        # if this is a SLES, jpg can not be generated inside the container,
        # fixing this locally with the host's graphviz.
        os=$(podman images | awk -v id="${containerid}" \
            'NR>1 && $3==id { split($1, parts, "/"); print parts[length(parts)]; exit }')
        # Mirror graph_requires.py naming: strip spaces, ',' -> '_',
        # truncate to MAX_NAME_LEN and rstrip '_' after truncation.
        packagesm="${packages//[[:space:]]/}"
        packagesm=${packagesm//,/_}
        if [ "${#packagesm}" -gt "${MAX_NAME_LEN}" ]; then
            packagesm="${packagesm:0:${MAX_NAME_LEN}}"
            while [[ ${packagesm} == *_ ]]; do packagesm="${packagesm%_}"; done
            echo "Name truncated to ${MAX_NAME_LEN} characters"
        fi
        if [ ! -e "${DATA}/${packagesm}.dot" ]; then
            echo "Error: ${DATA}/${packagesm}.dot not found; skipping local image generation."
            exit 1
        elif [ ! -e "${DATA}/${packagesm}_${os}.jpg" ]; then
            check_command dot
            echo "Generating image ${DATA}/${packagesm}_${os}.jpg locally"
            dot -Tjpg "${DATA}/${packagesm}.dot" -o "${DATA}/${packagesm}_${os}.jpg"
        else
            echo "${DATA}/${packagesm}_${os}.jpg already exist.... exiting"
        fi
        ;;
    rmcache)
        podman images | grep graph || echo "No local 'graph' images found."
        echo " podman rmi -f IMAGE"
        ;;
    build)
        build_container
        ;;
    *)
        info
        ;;
esac
