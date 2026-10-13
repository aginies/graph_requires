#!/usr/bin/env python3
# for python3.6+
# aginies@suse.com
"""
Quick tool to find packages which require another (reverse dependencies).
This will draw a graph using Graphviz, an interactive 2D HTML, or a 3D view.
"""

import argparse
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from string import Template

# Shared defaults; graph-container-manage.sh mirrors these values
# (DATA=/tmp/graph, MAX_NAME_LEN=64) for its local image fallback.
# By design this is a shared, human-browsable output location (the graphs
# are not sensitive); do not store confidential data there.
DEFAULT_OUTPUT_DIR = "/tmp/graph"
MAX_NAME_LEN = 64

# Node depth legend shared by every renderer:
#   0 = requested root package, 1 = direct reverse dependency,
#   2 = Round-2 dependency (a dependency of a dependency).
DEPTH_ROOT, DEPTH_DIRECT, DEPTH_ROUND2 = 0, 1, 2

# One palette shared by the DOT/image views and the interactive 3D view.
DEPTH_COLORS = {
    DEPTH_ROOT: "#add8e6",    # light blue
    DEPTH_DIRECT: "#90ee90",  # light green
    DEPTH_ROUND2: "#ffc0cb",  # pink
}
DEPTH_SIZES_3D = {DEPTH_ROOT: 10, DEPTH_DIRECT: 5, DEPTH_ROUND2: 2}

EDGE_COLOR_ROOT_3D = "#ff4444"
EDGE_COLOR_DEFAULT_3D = "#aaaaaa"

def cmd_exists(cmd):
    """Check if a command exists on the system."""
    return shutil.which(cmd) is not None

def check_binaries(require_dot=True):
    """Verify required system binaries are available."""
    if not cmd_exists("zypper"):
        print("Error: 'zypper' not found. This tool requires a SUSE/openSUSE system.")
        sys.exit(1)
    if require_dot and not cmd_exists("dot"):
        print("Error: 'dot' not found. Please install the 'graphviz' package.")
        sys.exit(1)

def get_os_info(key):
    """Extract information from /etc/os-release."""
    try:
        with open('/etc/os-release') as f:
            for line in f:
                if line.startswith(f'{key}='):
                    return line.strip().split('=', 1)[1].strip('"')
    except (FileNotFoundError, IndexError):
        return f"Unknown_{key}"
    return f"Unknown_{key}"

def dot_node_attrs(depth):
    """DOT styling for a node depth; root packages are drawn as boxes."""
    color = DEPTH_COLORS.get(depth, DEPTH_COLORS[DEPTH_ROUND2])
    if depth == DEPTH_ROOT:
        return f'shape=box, style=filled, fillcolor="{color}", penwidth=2'
    return f'shape=ellipse, style=filled, fillcolor="{color}"'

def dot_edge_style(target_depth):
    """DOT styling for an edge; edges pointing at a root package are red."""
    if target_depth == DEPTH_ROOT:
        return 'color=red, penwidth=1.5'
    return 'color="#777777"'

def js_template_literal_escape(text):
    """Make text safe to embed inside a JavaScript template literal (`...`).

    Escapes backslashes first, then the template-literal delimiters
    (backtick, ${...}) and any '</script' sequence so the embedded data
    cannot terminate the literal or the surrounding <script> block.
    """
    return (
        text.replace("\\", "\\\\")
            .replace("`", "\\`")
            .replace("${", "\\${")
            .replace("</script", "<\\/script")
    )

def get_reverse_dependencies(package, nodes, edges, expand=False, searched=None):
    """
    Find packages that directly require the given package.

    Node depths: 0 for the queried package, 1 for its direct reverse
    dependencies, 2 for Round-2 nodes (dependencies of dependencies).
    When expand is True (--round2), direct dependencies are expanded one
    more level; the walk never goes deeper than 2.

    'searched' memoizes packages already looked up with zypper so each
    package is expanded at most once, even when shared between several
    root packages (avoids redundant loops and duplicate Round-2 prints).
    """
    if searched is None:
        searched = set()

    # Roots keep depth 0; a node already recorded (e.g. as a Round-2
    # dependent) keeps its existing depth.
    nodes.setdefault(package, DEPTH_ROOT)

    if package in searched:
        return nodes, edges
    searched.add(package)

    try:
        command = ["zypper", "-q", "-x", "search", "--requires-pkg", package]
        # stdout/stderr=PIPE instead of capture_output on purpose:
        # capture_output needs Python 3.7+, and the SLE 15 SP5/SP6 BCI
        # containers this tool targets ship python3-base 3.6.
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

        if result.returncode != 0:
            return nodes, edges

        # Input is the XML printed by the locally installed zypper (trusted
        # feed); defusedxml is deliberately not used because the target
        # python3-base container image only provides the stdlib parser.
        root = ET.fromstring(result.stdout)
        solvables = root.findall(".//solvable")

        for solvable in solvables:
            name = solvable.get("name")
            if not name or name == package or "debuginfo" in name:
                continue

            edges.add((name, package))
            if name not in nodes:
                # Direct dependents of a root are depth 1; Round-2 dependents
                # are depth 2 (capped, the walk never goes deeper).
                nodes[name] = min(nodes[package] + 1, DEPTH_ROUND2)

            # Round 2: expand each direct dependent of a root exactly once.
            if expand and name not in searched:
                print(f"  Expanding '{name}' (Round 2)...", end="\r")
                get_reverse_dependencies(name, nodes, edges, expand=False, searched=searched)

    except (subprocess.SubprocessError, ET.ParseError) as err:
        print(f"\nError processing {package}: {err}")

    return nodes, edges

def generate_dot_file(nodes, edges, title, output_path, layout="dot"):
    """Generate a DOT file from the collected nodes and edges.

    Styling comes from the shared depth constants: root packages are the
    ones recorded at DEPTH_ROOT.
    """
    os_name = get_os_info('PRETTY_NAME')
    current_date = date.today()
    label = f"{title}\\n{os_name} ({current_date})"

    try:
        with open(output_path, 'w') as f:
            f.write("digraph PackageDependencies {\n")
            f.write(f'    graph [label="{label}", layout={layout}, fontsize=24, fontname="Arial", rankdir=BT, overlap=false, splines=true, nodesep=0.15, ranksep=0.4];\n')
            f.write('    node [fontname="Arial", fontsize=10, margin=0.05];\n')
            f.write('    edge [arrowhead=vee, color="#555555", arrowsize=0.6];\n\n')

            # Node styling based on depth
            for name, depth in sorted(nodes.items(), key=lambda x: x[1]):
                f.write(f'    "{name}" [{dot_node_attrs(depth)}];\n')

            f.write("\n")
            # Edges
            for source, target in sorted(edges):
                style = dot_edge_style(nodes.get(target, DEPTH_ROUND2))
                f.write(f'    "{source}" -> "{target}" [{style}];\n')

            f.write("}\n")
    except OSError as err:
        print(f"Error writing DOT file {output_path}: {err}")
        sys.exit(1)

HTML_2D_TEMPLATE = Template("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>$title</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style type="text/css">
        body, html { margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; font-family: Arial, sans-serif; }
        #network { width: 100%; height: 100%; background-color: #f5f5f5; }
        #controls { position: absolute; top: 10px; left: 10px; background: rgba(255, 255, 255, 0.9); padding: 15px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); z-index: 100; border: 1px solid #ddd; width: 250px; }
        h2 { margin: 0 0 10px 0; font-size: 16px; color: #333; }
        .hint { font-size: 11px; color: #666; margin-bottom: 15px; line-height: 1.4; }
        .control-group { margin-bottom: 15px; }
        label { display: block; font-size: 12px; font-weight: bold; margin-bottom: 5px; color: #444; }
        input[type="range"] { width: 100%; cursor: pointer; }
        button {
            background: #007bff; color: white; border: none; padding: 8px 12px; border-radius: 4px;
            cursor: pointer; font-size: 12px; transition: background 0.2s; margin-right: 5px; margin-bottom: 5px;
            width: 100%;
        }
        button:hover { background: #0056b3; }
        button.active { background: #dc3545; }
        button.secondary { background: #6c757d; }
        button.secondary:hover { background: #5a6268; }
        #status { font-size: 11px; margin-top: 8px; color: #d9534f; font-weight: bold; text-align: center; }
    </style>
</head>
<body>
    <div id="controls">
        <h2>$title</h2>
        <div class="hint">Scroll to zoom, drag to pan. Click nodes to see info.</div>

        <div class="control-group">
            <label for="spacing">Node Spacing (Expand View)</label>
            <input type="range" id="spacing" min="50" max="500" value="100" oninput="updateSpacing(this.value)">
        </div>

        <button id="physicsBtn" onclick="togglePhysics()">Freeze Graph</button>
        <button class="secondary" onclick="network.fit()">Reset Zoom</button>

        <div id="status">Stabilizing...</div>
    </div>
    <div id="network"></div>

    <script type="text/javascript">
        const dotData = `$dot_content`;
        const container = document.getElementById('network');
        const data = vis.parseDOTNetwork(dotData);
        const statusEl = document.getElementById('status');
        const physicsBtn = document.getElementById('physicsBtn');
        const spacingInput = document.getElementById('spacing');

        let physicsEnabled = true;

        const options = {
            nodes: {
                font: { size: 14, face: 'Arial' },
                shape: 'dot',
                size: 16,
                borderWidth: 2
            },
            edges: {
                smooth: { type: 'continuous', forceDirection: 'none' },
                arrows: { to: { enabled: true, scaleFactor: 0.5 } },
                color: { inherit: 'from', opacity: 0.6 },
                selectionWidth: 2
            },
            physics: {
                enabled: true,
                solver: 'barnesHut',
                barnesHut: {
                    gravitationalConstant: -3000,
                    centralGravity: 0.3,
                    springLength: 100,
                    springConstant: 0.05,
                    damping: 0.09,
                    avoidOverlap: 0.8
                },
                stabilization: {
                    enabled: true,
                    iterations: 1000,
                    updateInterval: 50
                }
            },
            interaction: {
                hover: true,
                navigationButtons: true,
                keyboard: true,
                tooltipDelay: 200,
                hideEdgesOnDrag: true
            }
        };

        const network = new vis.Network(container, data, options);

        network.on("stabilizationProgress", function(params) {
            statusEl.innerText = "Stabilizing: " + Math.round((params.iterations / params.total) * 100) + "%";
        });

        network.on("stabilizationIterationsDone", function() {
            statusEl.innerText = "Stabilized (Static)";
            statusEl.style.color = "#5cb85c";
            disablePhysics();
        });

        function updateSpacing(value) {
            const val = parseInt(value);
            const gravity = -3000 * (val / 100);

            network.setOptions({
                physics: {
                    barnesHut: {
                        springLength: val,
                        gravitationalConstant: gravity
                    }
                }
            });

            if (!physicsEnabled) {
                enablePhysics();
            }
        }

        function disablePhysics() {
            network.setOptions({ physics: { enabled: false } });
            physicsEnabled = false;
            physicsBtn.innerText = "Unfreeze (Allow Movement)";
            physicsBtn.classList.add('active');
        }

        function enablePhysics() {
            network.setOptions({ physics: { enabled: true } });
            physicsEnabled = true;
            physicsBtn.innerText = "Freeze Graph";
            physicsBtn.classList.remove('active');
            statusEl.innerText = "Re-stabilizing...";
            statusEl.style.color = "#f0ad4e";
        }

        function togglePhysics() {
            if (physicsEnabled) {
                disablePhysics();
                statusEl.innerText = "Frozen";
            } else {
                enablePhysics();
            }
        }
    </script>
</body>
</html>
""")

def generate_html_view(dot_path, output_path, title):
    """Generate an interactive 2D HTML view using vis-network."""
    try:
        with open(dot_path) as f:
            dot_content = f.read()
    except OSError as err:
        print(f"Error reading DOT file {dot_path}: {err}")
        return

    try:
        with open(output_path, 'w') as f:
            f.write(HTML_2D_TEMPLATE.substitute(
                title=title,
                dot_content=js_template_literal_escape(dot_content)
            ))
    except OSError as err:
        print(f"Error writing HTML file {output_path}: {err}")
        return

    print(f"Interactive HTML view generated: {output_path}")

HTML_3D_TEMPLATE = Template("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>$title (3D)</title>
    <script src="https://unpkg.com/3d-force-graph"></script>
    <script src="https://unpkg.com/three"></script>
    <script src="https://unpkg.com/three-spritetext"></script>
    <style>
        body { margin: 0; background-color: #050505; color: #fff; font-family: 'Segoe UI', Arial, sans-serif; overflow: hidden; }
        #controls { position: absolute; top: 10px; left: 10px; background: rgba(20, 20, 20, 0.85); padding: 15px; border-radius: 10px; z-index: 100; border: 1px solid #444; width: 240px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
        h2 { margin: 0 0 10px 0; font-size: 14px; color: #00d2ff; text-transform: uppercase; letter-spacing: 1px; }
        .hint { font-size: 11px; color: #999; margin-bottom: 15px; line-height: 1.4; }
        button {
            background: #333; color: #eee; border: 1px solid #555; padding: 10px; border-radius: 5px;
            cursor: pointer; font-size: 12px; width: 100%; margin-bottom: 8px; transition: all 0.2s;
        }
        button:hover { background: #444; border-color: #777; }
        button.active { background: #007bff; border-color: #00d2ff; color: white; }
        #info { position: absolute; bottom: 10px; right: 10px; font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div id="controls">
        <h2>$title</h2>
        <div class="hint">
            <b>Rotate:</b> Left-click + drag<br>
            <b>Pan:</b> Right-click + drag<br>
            <b>Zoom:</b> Mouse wheel<br>
            <b>Focus:</b> Click node
        </div>
        <button id="rotationBtn" onclick="toggleRotation()">Enable Auto-Rotate</button>
        <button onclick="Graph.zoomToFit(600)">Reset View</button>
    </div>
    <div id="info">Nodes: $node_count | Links: $link_count</div>
    <div id="3d-graph"></div>

    <script>
        const gData = $json_data;
        let isRotating = false;

        const Graph = ForceGraph3D()(document.getElementById('3d-graph'))
            .graphData(gData)
            .nodeThreeObject(node => {
                const sprite = new SpriteText(node.name);
                sprite.color = node.color;
                sprite.textHeight = 8;
                return sprite;
            })
            .linkColor('color')
            .linkWidth(link => link.highlight ? 1.5 : 0.5)
            .linkDirectionalArrowLength(3)
            .linkDirectionalArrowRelPos(1)
            .onNodeClick(node => {
                const distance = 100;
                const distRatio = 1 + distance/Math.hypot(node.x, node.y, node.z);
                Graph.cameraPosition(
                    { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio },
                    node,
                    2000
                );
            });

        function toggleRotation() {
            isRotating = !isRotating;
            document.getElementById('rotationBtn').classList.toggle('active', isRotating);
            Graph.controls().autoRotate = isRotating;
            Graph.controls().autoRotateSpeed = 0.5;
        }
    </script>
</body>
</html>
""")

def generate_html_3d_view(nodes, edges, title, output_path):
    """Generate an interactive 3D view using 3d-force-graph.

    Colors and node sizes come from the same depth palette as the DOT view;
    edges pointing at a root package are highlighted (see dot_edge_style).
    """
    json_nodes = []
    for name, depth in nodes.items():
        json_nodes.append({
            "id": name,
            "name": name,
            "val": DEPTH_SIZES_3D.get(depth, DEPTH_SIZES_3D[DEPTH_ROUND2]),
            "color": DEPTH_COLORS.get(depth, DEPTH_COLORS[DEPTH_ROUND2]),
            "depth": depth
        })

    json_links = []
    for source, target in edges:
        highlight = nodes.get(target, DEPTH_ROUND2) == DEPTH_ROOT
        json_links.append({
            "source": source,
            "target": target,
            "color": EDGE_COLOR_ROOT_3D if highlight else EDGE_COLOR_DEFAULT_3D,
            "highlight": highlight
        })

    data = {"nodes": json_nodes, "links": json_links}
    json_data = json.dumps(data)

    try:
        with open(output_path, 'w') as f:
            f.write(HTML_3D_TEMPLATE.substitute(
                title=title,
                json_data=json_data,
                node_count=len(nodes),
                link_count=len(edges)
            ))
    except OSError as err:
        print(f"Error writing HTML file {output_path}: {err}")
        return

    print(f"Interactive 3D HTML view generated: {output_path}")

def generate_image(dot_path, extension="jpg", layout="dot", stagger=0):
    """Convert DOT file to an image using Graphviz."""
    version = get_os_info('VERSION')
    image_path = dot_path.with_name(f"{dot_path.stem}_{version}.{extension}")

    try:
        # Build the command chain
        if stagger > 0 and cmd_exists("unflatten"):
            # Use unflatten to stagger leaf nodes and reduce width
            print(f"Applying unflatten (stagger: {stagger}) to reduce width...")
            unflatten_cmd = ["unflatten", "-l", str(stagger), str(dot_path)]
            dot_cmd = [layout, f"-T{extension}", "-o", str(image_path)]

            p1 = subprocess.Popen(unflatten_cmd, stdout=subprocess.PIPE)
            p2 = subprocess.Popen(dot_cmd, stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if p1.stdout is not None:
                p1.stdout.close()
            _out, err = p2.communicate()
            if p2.returncode != 0:
                print(f"Error in dot command: {err.decode()}")
        else:
            command = [layout, f"-T{extension}", str(dot_path), "-o", str(image_path)]
            # (PIPE kept instead of capture_output for Python 3.6, see above)
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            if result.returncode != 0:
                print(f"Error in dot command: {result.stderr.decode()}")

        if image_path.is_file():
            print(f"Graph image generated: {image_path}")
            return image_path
    except Exception as err:
        print(f"Error generating image: {err}")
    return None

def main():
    parser = argparse.ArgumentParser(description="Generate a reverse dependency graph for packages.")
    parser.add_argument("packages", help="Comma-separated list of package names")
    parser.add_argument("-d", "--dir", default=DEFAULT_OUTPUT_DIR,
                        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--format", default="html", choices=["html", "html3d", "jpg", "png", "svg", "pdf"], help="Output format (default: html)")
    parser.add_argument("--layout", default="dot", choices=["dot", "sfdp", "fdp", "twopi", "circo"], help="Graphviz layout engine (default: dot)")
    parser.add_argument("--stagger", type=int, default=0, help="Stagger leaf nodes to reduce width (uses 'unflatten -l')")
    parser.add_argument("--round2", action="store_true", help="Expand requirements of requirements (limited for target packages)")

    args = parser.parse_args()

    # Only require 'dot' if we're generating an image
    require_dot = args.format not in ["html", "html3d"]
    check_binaries(require_dot=require_dot)

    package_list = [p.strip() for p in args.packages.split(",") if p.strip()]
    if not package_list:
        print("Error: No valid packages provided.")
        sys.exit(1)

    wdir = Path(args.dir)
    wdir.mkdir(parents=True, exist_ok=True)

    result_name = "_".join(package_list)
    if len(result_name) > MAX_NAME_LEN:
        result_name = result_name[:MAX_NAME_LEN].rstrip("_")

    print(f"Analyzing reverse dependencies for: {', '.join(package_list)}")

    all_nodes = {}
    all_edges = set()
    searched = set()

    # Root packages are always depth 0; mark them all up-front so a root
    # that is itself required by another root still gets depth-1 styling
    # for its direct dependents.
    for pkg in package_list:
        all_nodes[pkg] = DEPTH_ROOT

    for pkg in package_list:
        print(f"Finding packages requiring '{pkg}'...")
        get_reverse_dependencies(pkg, all_nodes, all_edges, expand=args.round2, searched=searched)

    print(f"\nTotal nodes found: {len(all_nodes)}")
    if not all_nodes:
        print("No dependencies found for the specified packages.")
        sys.exit(0)

    dot_file = wdir / f"{result_name}.dot"
    title = f"Reverse Dependencies for {', '.join(package_list)}"

    generate_dot_file(all_nodes, all_edges, title, dot_file, layout=args.layout)
    print(f"DOT file generated: {dot_file}")

    if args.format == "html":
        html_file = wdir / f"{result_name}.html"
        generate_html_view(dot_file, html_file, title)
    elif args.format == "html3d":
        html_file = wdir / f"{result_name}_3d.html"
        generate_html_3d_view(all_nodes, all_edges, title, html_file)
    else:
        # Suggest staggering if nodes are many and stagger is 0
        stagger = args.stagger
        if len(all_nodes) > 100 and stagger == 0 and args.layout == "dot":
            print("Tip: Many nodes found. If the graph is too wide, try using '--stagger 10' or '--layout sfdp'.")
        generate_image(dot_file, extension=args.format, layout=args.layout, stagger=stagger)

if __name__ == "__main__":
    main()
