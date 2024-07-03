#!/usr/bin/env python3
# for python3.6 (as some limitation compare to 3.7 or 3.11....)
# aginies@suse.com
"""
quick tool to find package which requires another
this will draw a graph
"""

import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
import sys
import shutil
import os
from datetime import date

def cmd_exists(cmd):
    """
    check a command exist
    """
    return shutil.which(cmd) is not None

def check_binairies():
    """
    check everything is available on the system
    """
    if cmd_exists("zypper") is False:
        print("Sounds like you are not using a SUSE/openSUSE system....\n")
        exit(1)
    if cmd_exists("dot") is False:
        print("dot is not available, please install graphviz\n")
        exit(1)

def get_pretty_name() -> str:
    """
    grab the os name
    """
    try:
        with open('/etc/os-release', 'r') as file:
            for line in file:
                if line.startswith('PRETTY_NAME='):
                    # Remove the 'PRETTY_NAME=' part and strip surrounding quotes
                    pretty_name = line.strip().split('=', 1)[1].strip('"')
                    return pretty_name
    except FileNotFoundError:
        return "The file '/etc/os-release' does not exist."

def get_package_dependencies(package, depth=0, seen_packages=None):
    """
    Retrieve the list of package dependencies
    """
    if seen_packages is None:
        seen_packages = set()

    # avoid infinite loop
    if depth > 1:
        return []

    try:
        command = ["zypper", "-q", "-x", "search", "--requires-pkg", package]
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, _error = result.communicate()

        if result.returncode != 0:
            return []

        root = ET.fromstring(output.decode())
        dependencies = {}

        for solvable in root.findall(".//solvable"):
            name = solvable.get("name")
            # avoid same name package
            if name == package:
                pass
            # avoid debuginfo package
            if name and "debuginfo" in name:
                pass
            elif name and name not in seen_packages:
                print(f"check deps of {name}")
                seen_packages.add(name)
                requires_pkg = get_package_dependencies(name, depth + 1, seen_packages)
                dependencies[name] = requires_pkg

        return dependencies

    except subprocess.CalledProcessError as err:
        print(f"Error executing zypper command: {err}")
        return []
    except ET.ParseError as err:
        print(f"Error parsing XML: {err}")
        return []

def check_seen_before(filename, pattern):
    """
    check if there is a need to recreate a deps between two packages
    """
    try:
        with open(filename, 'r') as file:
            line_number = 0
            found = False
            for line in file:
                line_number += 1
                if pattern in line:
                    #print(f"{pattern} found in line {line_number}: {line.strip()}")
                    found = True
                    return True
            if not found:
                #print(f"{pattern} not found in the file.")
                return False

    except FileNotFoundError:
        print(f"The file '{filename}' does not exist.")


def generate_dot_file(deps, package_n, filename="dependencies.dot", directory="/tmp/graph"):
    """
    Generate a DOT file from the package dependencies.
    """
    filename = directory +"/"+ filename+".dot"
    with open(filename, "w") as dotf:
        dotf.write("digraph PackageDependencies {\n")
        osrelease = get_pretty_name()
        current_date = date.today()
        label = "Requires "+package_n+" - "+osrelease+" ("+str(current_date)+")"
        dotf.write(f"graph [label=\"{label}\", layout=fdp, fontsize=32, fontname=\"Arial\"];\n")
        dotf.write("node [shape=box, style=filled, fillcolor=lightgreen];\n")
        dotf.write(f"\"{package_n}\" [shape=circle, style=filled, fillcolor=lightblue];\n")
        dotf.write("edge [arrowhead=vee];\n")
    dotf.close()

    for package, requires_pkg in deps.items():
        if isinstance(requires_pkg, dict):
            if requires_pkg:
                for dep_package in requires_pkg:
                    if package_n == package:
                        # first level of requires
                        with open(filename, "a") as dotf:
                            dotf.write(f'"{dep_package}" -> "{package}";\n')
                        dotf.close()
                    else:
                        # second level of requires so ellipse
                        with open(filename, "a") as dotf:
                            dotf.write(f"\"{dep_package}\" [shape=ellipse, style=filled, fillcolor=pink];\n")
                        dotf.close()
                        pattern = "\"" + package + "\"" + " -> " + "\"" + package_n + "\""
                        if check_seen_before(filename, pattern) is False:
                            with open(filename, "a") as dotf:
                                dotf.write(f'"{dep_package}" -> "{package}" -> "{package_n}";\n')
                            dotf.close()
                        else:
                            with open(filename, "a") as dotf:
                                dotf.write(f'"{dep_package}" -> "{package}";\n')
                            dotf.close()

    with open(filename, "a") as dotf:
        dotf.write("}\n")
    dotf.close()
    print(f"DOT file '{filename}' generated successfully.")

def generate_image(filename="dependencies", extension="jpg", directory="/tmp/graph"):
    """
    generate the image file
    the py graphviz package in not available on SLES for py3.6
    so keeping it by command line
    """
    image_filename = directory+"/" + filename + "." + extension
    try:
        command = ["dot", "-T"+extension, directory+"/"+filename+".dot", "-o", image_filename]
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _output, _error = result.communicate()

        my_file = Path(image_filename)
        if my_file.is_file():
            print(f"Image file '{image_filename}' generated successfully.")
        else:
            print(f"Error generating Image file: {image_filename}, \ncommand was: {command}")

    except Exception as err:
        print(f"Error generating Image file: {err}")

if __name__ == "__main__":
    """
    Main stuff which do everything
    """
    check_binairies()
    print("\nGenerate a graph of all packages that require any of the provides of a package.")
    print("This use zypper on current system, so using the actual Repositories set on the system.\n")

    if len(sys.argv) < 2:
        print("Usage: python3 graph.py PACKAGE_NAME")
        sys.exit(1)
    PACKAGE_NAME = sys.argv[1].strip()

    if len(sys.argv) > 2:
        WDIR = sys.argv[2].strip()
        if not os.path.exists(WDIR):
            os.makedirs(WDIR)
    else:
        WDIR = "/tmp/graph"

    if not PACKAGE_NAME:
        print("Please enter a valid package name.")
        exit(1)

    print(f"Working with package {PACKAGE_NAME}")
    DEPENDENCIES_ALL = get_package_dependencies(PACKAGE_NAME)

    if DEPENDENCIES_ALL:
        generate_dot_file(DEPENDENCIES_ALL, PACKAGE_NAME, filename=PACKAGE_NAME, directory=WDIR)
        generate_image(filename=PACKAGE_NAME, extension="jpg", directory=WDIR)
    else:
        print(f"No dependencies found for '{PACKAGE_NAME}'.")
