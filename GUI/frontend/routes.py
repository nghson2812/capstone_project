import subprocess
import json
import os
import requests
import importlib
import time
from requests.auth import HTTPBasicAuth
from flask import render_template, jsonify, request
from app import app
# Import from backend directory
import sys
import os
sys.path.append('../backend/topologies')  # Add topology directory to Python path
sys.path.append('../backend/flowrules')   # Add flowrules directory to Python path

# Default modules
current_topology = None
current_flow_rule = None

# Global network instance
net = None

# ONOS configuration - can be overridden by environment variables
ONOS_IP = os.getenv("ONOS_IP", "127.0.0.1")
ONOS_PORT = os.getenv("ONOS_PORT", "8181")
ONOS_USERNAME = os.getenv("ONOS_USERNAME", "onos")
ONOS_PASSWORD = os.getenv("ONOS_PASSWORD", "rocks")

@app.route("/")
def dashboard():
    """Main dashboard view"""
    return render_template("dashboard.html")

@app.route("/topology")
def topology():
    """Network topology view"""
    return render_template("topology.html")

@app.route("/control")
def control_panel():
    """Network control panel"""
    return render_template("control_panel.html")

@app.route("/monitoring")
def monitoring():
    """Network monitoring view"""
    return render_template("monitoring.html")

@app.route("/flows")
def flow_rules():
    """Flow rules management"""
    return render_template("flow_rules.html")

@app.route("/qos")
def qos():
    """QoS configuration view"""
    return render_template("qos.html")

# API Endpoints
@app.route("/api/start", methods=["POST"])
def start_network():
    """Start the Mininet network"""
    global net, current_topology
    try:
        if net is not None:
            return jsonify({"status": "error", "message": "Network is already running"}), 400

        if current_topology is None:
            return jsonify({"status": "error", "message": "No topology selected"}), 400

        net = current_topology.run()
        return jsonify({"status": "success", "message": "Network started successfully"})
    except Exception as e:
        app.logger.error(f"Error starting network: {str(e)}")
        return jsonify({"status": "error", "message": f"Failed to start network: {str(e)}"}), 500

@app.route("/api/stop", methods=["POST"])
def stop_network():
    """Stop the Mininet network"""
    global net
    try:
        if net is None:
            return jsonify({"status": "error", "message": "Network is not running"}), 400

        net.stop()
        net = None
        return jsonify({"status": "success", "message": "Network stopped successfully"})
    except Exception as e:
        app.logger.error(f"Error stopping network: {str(e)}")
        return jsonify({"status": "error", "message": f"Failed to stop network: {str(e)}"}), 500

@app.route("/api/status")
def network_status():
    """Get network status"""
    global net
    try:
        is_running = net is not None

        # Get device information from ONOS
        devices = []
        try:
            if is_running:
                devices = get_onos_devices()
        except Exception as e:
            app.logger.error(f"Error getting ONOS devices: {str(e)}")
            # Don't fail the entire status call for ONOS errors

        return jsonify({
            "status": "success",
            "network_running": is_running,
            "devices": devices,
            "device_count": len(devices)
        })
    except Exception as e:
        app.logger.error(f"Error in network_status: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to get network status",
            "network_running": False,
            "devices": [],
            "device_count": 0
        }), 500

@app.route("/api/pingall")
def ping_all():
    """Run ping test between all hosts"""
    global net, current_topology
    try:
        if net is None:
            return jsonify({"status": "error", "message": "Network is not running"}), 400

        if current_topology is None:
            return jsonify({"status": "error", "message": "No topology selected"}), 400

        # Check if topology has ping_all function, otherwise use net.pingAll()
        if hasattr(current_topology, 'ping_all'):
            result = current_topology.ping_all(net)
        else:
            result = net.pingAll()

        # Calculate packet statistics
        if isinstance(result, (int, float)):
            packet_loss_percent = result
            # Estimate based on network size and typical ping behavior
            student_number = getattr(current_topology, 'student_number', 8)
            faculty_number = getattr(current_topology, 'faculty_number', 8)
            total_hosts = student_number + faculty_number + 3  # +3 for servers
            total_possible_connections = total_hosts * (total_hosts - 1)
            
            dropped_packets = int((packet_loss_percent / 100.0) * total_possible_connections)
            successful_packets = total_possible_connections - dropped_packets
        else:
            packet_loss_percent = "Unknown"
            total_possible_connections = "Unknown"
            dropped_packets = "Unknown"
            successful_packets = "Unknown"
            
        return jsonify({
            "status": "success", 
            "message": "Full network ping test completed successfully",
            "result": str(result),
            "packet_loss": f"{packet_loss_percent}%" if isinstance(packet_loss_percent, (int, float)) else packet_loss_percent,
            "total_packets": total_possible_connections,
            "dropped_packets": dropped_packets,
            "successful_packets": successful_packets
        })
    except Exception as e:
        app.logger.error(f"Error running ping test: {str(e)}")
        return jsonify({"status": "error", "message": f"Ping test failed: {str(e)}"}), 500

def run_iperf():
    """Run iPerf TCP multithreaded performance test using topology function"""
    global net, current_topology
    try:
        if net is None:
            return jsonify({"status": "error", "message": "Network is not running"}), 400

        if current_topology is None:
            return jsonify({"status": "error", "message": "No topology selected"}), 400

        # Check if the topology has the required function
        if not hasattr(current_topology, 'run_iperf_multithreaded_tcp'):
            return jsonify({"status": "error", "message": "Selected topology does not support multithreaded TCP testing"}), 400

        # Capture output from the multithreaded TCP function
        import io
        import sys
        from contextlib import redirect_stdout, redirect_stderr

        # Create string buffers to capture output
        output_buffer = io.StringIO()
        error_buffer = io.StringIO()

        # Use the actual TCP multithreaded function from topology with correct parameters
        with redirect_stdout(output_buffer), redirect_stderr(error_buffer):
            current_topology.run_iperf_multithreaded_tcp(net, num_requests=3)

        # Get the captured output
        output_text = output_buffer.getvalue()
        error_text = error_buffer.getvalue()

        # Parse the results from the topology function output
        results = parse_tcp_multithreaded_results(output_text)

        return jsonify({
            "status": "success", 
            "message": "TCP multithreaded iPerf test completed successfully",
            "results": results,
            "raw_output": output_text if output_text else "No output captured",
            "error_output": error_text if error_text else None
        })

    except Exception as e:
        app.logger.error(f"Error running TCP multithreaded iPerf test: {str(e)}")
        return jsonify({"status": "error", "message": f"TCP multithreaded iPerf test failed: {str(e)}"}), 500

@app.route("/api/iperf")
def call_run_iperf():
    return run_iperf()

@app.route("/api/iperf/<server_name>")
def run_iperf_server(server_name):
    """Run iPerf test to specific server"""
    global net
    try:
        if net is None:
            return jsonify({"status": "error", "message": "Network is not running"}), 400

        if server_name not in ['srv1', 'srv2', 'srv3']:
            return jsonify({"status": "error", "message": "Invalid server name"}), 400

        # Get topology info for host counts
        student_number = getattr(current_topology, 'student_number', 8)
        faculty_number = getattr(current_topology, 'faculty_number', 8)

        # Run targeted test to specific server
        server = net.get(server_name)
        student_hosts = [net.get(f'h{i+1}s') for i in range(student_number)]
        faculty_hosts = [net.get(f'h{i+1}f') for i in range(faculty_number)]

        results = {
            "server": server_name,
            "student_results": {},
            "faculty_results": {},
            "summary": {}
        }

        # Test from student hosts
        for host in student_hosts:
            try:
                output = host.cmd(f'iperf -c {server.IP()} -t 2')
                bandwidth = parse_iperf_output_tcp(output)['bandwidth_mbps']
                results["student_results"][host.name] = bandwidth
            except:
                results["student_results"][host.name] = 0.0

        # Test from faculty hosts  
        for host in faculty_hosts:
            try:
                output = host.cmd(f'iperf -c {server.IP()} -t 2')
                bandwidth = parse_iperf_output_tcp(output)['bandwidth_mbps']
                results["faculty_results"][host.name] = bandwidth
            except:
                results["faculty_results"][host.name] = 0.0

        # Calculate summary
        all_results = list(results["student_results"].values()) + list(results["faculty_results"].values())
        if all_results:
            results["summary"] = {
                "avg_bandwidth": sum(all_results) / len(all_results),
                "max_bandwidth": max(all_results),
                "min_bandwidth": min(all_results),
                "total_tests": len(all_results)
            }

        return jsonify({
            "status": "success",
            "message": f"iPerf test to {server_name} completed",
            "results": results
        })

    except Exception as e:
        app.logger.error(f"Error running iPerf test to {server_name}: {str(e)}")
        return jsonify({"status": "error", "message": f"iPerf test failed: {str(e)}"}), 500

def parse_tcp_multithreaded_results(output):
    """Parse TCP multithreaded iPerf output from topology function"""
    import re

    results = {
        "student_results": {},
        "faculty_results": {},
        "summary": {
            "total_tests": 0,
            "avg_bandwidth": 0,
            "max_bandwidth": 0,
            "min_bandwidth": float('inf')
        }
    }

    # Parse individual host results from output like "h1s -> srv1 [Request 1]: 25.50 Mbps, Latency: 2.50 ms"
    lines = output.split('\n')
    bandwidth_values = []
    latency_values = []

    for line in lines:
        # Parse individual test results
        match = re.search(r'(h\d+[sf])\s*->\s*srv1\s*\[Request\s*\d+\]:\s*(\d+\.\d+)\s*Mbps,\s*Latency:\s*(\d+\.\d+)\s*ms', line)
        if match:
            host = match.group(1)
            bandwidth = float(match.group(2))
            latency = float(match.group(3))
            
            bandwidth_values.append(bandwidth)
            latency_values.append(latency)
            
            if host.endswith('s'):  # Student host
                if host not in results["student_results"]:
                    results["student_results"][host] = []
                results["student_results"][host].append({
                    "bandwidth": bandwidth,
                    "latency": latency
                })
            elif host.endswith('f'):  # Faculty host
                if host not in results["faculty_results"]:
                    results["faculty_results"][host] = []
                results["faculty_results"][host].append({
                    "bandwidth": bandwidth,
                    "latency": latency
                })

    # Parse summary lines from topology output
    for line in lines:
        # Look for summary lines like "Student to srv1: Avg Bandwidth: 25.50 Mbps, Avg Latency: 1.23 ms"
        match = re.search(r'(Student|Faculty) to srv1: Avg Bandwidth: ([\d.]+) Mbps, Avg Latency: ([\d.]+) ms', line)
        if match:
            group = match.group(1).lower()
            avg_bw = float(match.group(2))
            avg_lat = float(match.group(3))
            
            results["summary"][f"{group}_avg_bandwidth"] = avg_bw
            results["summary"][f"{group}_avg_latency"] = avg_lat

    # Calculate summary statistics
    if bandwidth_values:
        results["summary"]["total_tests"] = len(bandwidth_values)
        results["summary"]["avg_bandwidth"] = sum(bandwidth_values) / len(bandwidth_values)
        results["summary"]["max_bandwidth"] = max(bandwidth_values)
        results["summary"]["min_bandwidth"] = min(bandwidth_values)
    else:
        results["summary"]["min_bandwidth"] = 0

    return results

def parse_iperf_results(output):
    """Parse iPerf output to extract bandwidth results"""
    import re

    results = {
        "student_to_servers": {},
        "faculty_to_servers": {},
        "summary": {
            "total_tests": 0,
            "avg_bandwidth": 0,
            "max_bandwidth": 0,
            "min_bandwidth": float('inf')
        }
    }

    # Parse the average bandwidth lines from topology output
    lines = output.split('\n')
    bandwidth_values = []

    for line in lines:
        # Look for summary lines like "Student to srv1: Avg Bandwidth: 25.50 Mbps"
        if 'Avg Bandwidth:' in line and ('Student to' in line or 'Faculty to' in line):
            # Extract bandwidth value
            match = re.search(r'Avg Bandwidth:\s*(\d+\.\d+)\s*Mbps', line)
            if match:
                bandwidth = float(match.group(1))
                bandwidth_values.append(bandwidth)

                if 'Student to' in line:
                    server_match = re.search(r'Student to (srv\d+)', line)
                    if server_match:
                        results["student_to_servers"][server_match.group(1)] = bandwidth
                elif 'Faculty to' in line:
                    server_match = re.search(r'Faculty to (srv\d+)', line)
                    if server_match:
                        results["faculty_to_servers"][server_match.group(1)] = bandwidth

    # If no summary format found, try to parse individual test results
    if not bandwidth_values:
        for line in lines:
            if 'Mbits/sec' in line:
                match = re.search(r'(\d+\.\d+)\s+Mbits/sec', line)
                if match:
                    bandwidth = float(match.group(1))
                    bandwidth_values.append(bandwidth)

    # Calculate summary statistics
    if bandwidth_values:
        results["summary"]["total_tests"] = len(bandwidth_values)
        results["summary"]["avg_bandwidth"] = sum(bandwidth_values) / len(bandwidth_values)
        results["summary"]["max_bandwidth"] = max(bandwidth_values)
        results["summary"]["min_bandwidth"] = min(bandwidth_values)
    else:
        results["summary"]["min_bandwidth"] = 0

    return results

@app.route("/api/inject_flows", methods=["POST"])
def inject_flows():
    """Inject QoS flow rules into ONOS (Set 1)"""
    try:
        if current_flow_rule is None:
            return jsonify({"status": "error", "message": "No flow rule selected"}), 400

        success = current_flow_rule.inject_flow_rules()

        if success:
            return jsonify({
                "status": "success", 
                "message": "Flow rules injected successfully"
            })
        else:
            return jsonify({
                "status": "error", 
                "message": "Failed to inject some flow rules"
            }), 500
    except Exception as e:
        app.logger.error(f"Error injecting flows: {str(e)}")
        return jsonify({"status": "error", "message": f"Flow injection failed: {str(e)}"}), 500



@app.route("/api/flows")
def get_flows():
    """Get current flow rules from ONOS"""
    try:
        url = f"http://{ONOS_IP}:{ONOS_PORT}/onos/v1/flows"
        response = requests.get(url, auth=HTTPBasicAuth(ONOS_USERNAME, ONOS_PASSWORD))

        if response.status_code == 200:
            flows_data = response.json()
            return jsonify({"status": "success", "flows": flows_data.get("flows", [])})
        else:
            return jsonify({"status": "error", "message": "Failed to retrieve flows"}), 500
    except Exception as e:
        app.logger.error(f"Error getting flows: {str(e)}")
        return jsonify({"status": "error", "message": f"Failed to get flows: {str(e)}"}), 500

@app.route("/api/devices")
def get_devices():
    """Get device information from ONOS"""
    try:
        devices = get_onos_devices()
        return jsonify({"status": "success", "devices": devices})
    except Exception as e:
        app.logger.error(f"Error getting devices: {str(e)}")
        return jsonify({"status": "error", "message": f"Failed to get devices: {str(e)}"}), 500

@app.route("/api/qos")
def get_qos_info():
    """Get QoS configuration information"""
    try:
        # Get queue information from OVS
        result = subprocess.run(['sudo', 'ovs-vsctl', 'list', 'queue'], capture_output=True, text=True)

        qos_info = {
            "queues": [],
            "bandwidth_limits": {
                "student_mail": "5 Mbps",
                "student_rtmp": "25 Mbps", 
                "student_call": "10 Mbps",
                "faculty_mail": "15 Mbps",
                "faculty_rtmp": "50 Mbps",
                "faculty_call": "20 Mbps"
            }
        }

        if result.returncode == 0:
            qos_info["ovs_output"] = result.stdout

        return jsonify({"status": "success", "qos": qos_info})
    except Exception as e:
        app.logger.error(f"Error getting QoS info: {str(e)}")
        return jsonify({"status": "error", "message": f"Failed to get QoS info: {str(e)}"}), 500



# New API endpoints for topology and flow rule selection
@app.route("/api/topologies")
def get_available_topologies():
    """Get list of available topology files"""
    try:
        topology_dir = "../backend/topologies"
        topology_files = []

        for file in os.listdir(topology_dir):
            if file.endswith('.py') and not file.startswith('__'):
                module_name = file[:-3]  # Remove .py extension
                topology_files.append({
                    "name": module_name,
                    "filename": file,
                    "selected": current_topology and current_topology.__name__ == module_name
                })

        return jsonify({"status": "success", "topologies": topology_files})
    except Exception as e:
        app.logger.error(f"Error getting topologies: {str(e)}")
        return jsonify({"status": "error", "message": f"Failed to get topologies: {str(e)}"}), 500

@app.route("/api/select_topology", methods=["POST"])
def select_topology():
    """Select a topology to use"""
    global current_topology
    try:
        data = request.get_json()
        topology_name = data.get('topology_name')

        if not topology_name:
            return jsonify({"status": "error", "message": "Topology name required"}), 400

        # Import the selected topology module
        current_topology = importlib.import_module(topology_name)

        return jsonify({
            "status": "success", 
            "message": f"Selected topology: {topology_name}",
            "topology_name": topology_name
        })
    except Exception as e:
        app.logger.error(f"Error selecting topology: {str(e)}")
        return jsonify({"status": "error", "message": f"Failed to select topology: {str(e)}"}), 500

@app.route("/api/flowrules")
def get_available_flowrules():
    """Get list of available flow rule files"""
    try:
        flowrule_dir = "../backend/flowrules"
        flowrule_files = []

        for file in os.listdir(flowrule_dir):
            if file.endswith('.py') and not file.startswith('__'):
                module_name = file[:-3]  # Remove .py extension
                flowrule_files.append({
                    "name": module_name,
                    "filename": file,
                    "selected": current_flow_rule and current_flow_rule.__name__ == module_name
                })

        return jsonify({"status": "success", "flowrules": flowrule_files})
    except Exception as e:
        app.logger.error(f"Error getting flow rules: {str(e)}")
        return jsonify({"status": "error", "message": f"Failed to get flow rules: {str(e)}"}), 500

@app.route("/api/select_flowrule", methods=["POST"])
def select_flowrule():
    """Select a flow rule to use"""
    global current_flow_rule
    try:
        data = request.get_json()
        flowrule_name = data.get('flowrule_name')

        if not flowrule_name:
            return jsonify({"status": "error", "message": "Flow rule name required"}), 400

        # Import the selected flow rule module
        current_flow_rule = importlib.import_module(flowrule_name)

        return jsonify({
            "status": "success", 
            "message": f"Selected flow rule: {flowrule_name}",
            "flowrule_name": flowrule_name
        })
    except Exception as e:
        app.logger.error(f"Error selecting flow rule: {str(e)}")
        return jsonify({"status": "error", "message": f"Failed to select flow rule: {str(e)}"}), 500

@app.route("/api/current_selection")
def get_current_selection():
    """Get currently selected topology and flow rule"""
    try:
        return jsonify({
            "status": "success",
            "current_topology": getattr(current_topology, '__name__', None) if current_topology else None,
            "current_flowrule": getattr(current_flow_rule, '__name__', None) if current_flow_rule else None
        })
    except Exception as e:
        app.logger.error(f"Error getting current selection: {str(e)}")
        return jsonify({"status": "error", "message": f"Failed to get current selection: {str(e)}"}), 500


@app.route("/api/topology")
def get_topology():
    """Get dynamic topology information from selected topology"""
    try:
        if current_topology is None:
            return jsonify({
                "status": "error", 
                "message": "No topology selected",
                "topology": None
            }), 200  # Return 200 instead of 400 to prevent browser errors

        # Get topology info dynamically from the selected topology module
        student_number = getattr(current_topology, 'student_number', 8)
        faculty_number = getattr(current_topology, 'faculty_number', 8)

        topology_info = {
            "subnets": {
                "student": {
                    "network": "10.0.0.0/24",
                    "hosts": [f"h{i+1}s" for i in range(student_number)],
                    "ips": [f"10.0.0.{i+1}" for i in range(student_number)]
                },
                "faculty": {
                    "network": "10.0.1.0/24", 
                    "hosts": [f"h{i+1}f" for i in range(faculty_number)],
                    "ips": [f"10.0.1.{i+1}" for i in range(faculty_number)]
                },
                "server": {
                    "network": "10.0.2.0/24",
                    "hosts": ["srv1", "srv2", "srv3"],
                    "ips": ["10.0.2.1", "10.0.2.2", "10.0.2.3"],
                    "services": ["Mail", "RTMP", "Call"]
                }
            },
            "switches": [f"s{i+1}" for i in range(8)],
            "router": {
                "name": "r0",
                "interfaces": [
                    {"subnet": "student", "ip": "10.0.0.250/24"},
                    {"subnet": "faculty", "ip": "10.0.1.250/24"},
                    {"subnet": "server", "ip": "10.0.2.250/24"}
                ]
            },
            "switch_connections": [
                {"from": "s1", "to": "s6"},
                {"from": "s1", "to": "s7"},
                {"from": "s2", "to": "s6"},
                {"from": "s2", "to": "s8"},
                {"from": "s3", "to": "s4"},
                {"from": "s3", "to": "s6"},
                {"from": "s3", "to": "s7"},
                {"from": "s5", "to": "s6"},
                {"from": "s5", "to": "s7"}
            ],
            "selected_topology": getattr(current_topology, '__name__', 'Unknown'),
            "student_count": student_number,
            "faculty_count": faculty_number
        }

        return jsonify({"status": "success", "topology": topology_info})
    except Exception as e:
        app.logger.error(f"Error getting topology info: {str(e)}")
        return jsonify({"status": "error", "message": f"Failed to get topology info: {str(e)}"}), 500

def get_onos_devices():
    """Helper function to get device information from ONOS"""
    try:
        url = f"http://{ONOS_IP}:{ONOS_PORT}/onos/v1/devices"
        response = requests.get(url, auth=HTTPBasicAuth(ONOS_USERNAME, ONOS_PASSWORD))

        if response.status_code == 200:
            devices_data = response.json()
            return devices_data.get("devices", [])
        else:
            app.logger.error(f"Failed to get devices from ONOS: {response.status_code}")
            return []
    except Exception as e:
        app.logger.error(f"Error connecting to ONOS: {str(e)}")
        return []

def parse_tcp_multithreaded_results(output):
    """Parses the output from the multithreaded TCP iperf test."""
    import re
    
    results = {
        "student_results": {},
        "faculty_results": {},
        "summary": {
            "student_avg_bandwidth": 0,
            "student_avg_latency": 0,
            "faculty_avg_bandwidth": 0,
            "faculty_avg_latency": 0,
            "total_tests": 0,
            "avg_bandwidth": 0,
            "max_bandwidth": 0,
            "min_bandwidth": 0
        }
    }
    
    lines = output.split('\n')
    bandwidth_values = []
    latency_values = []
    
    # Parse individual test results
    for line in lines:
        # Look for lines like "h1s -> srv1 [Request 1]: 25.50 Mbps, Latency: 1.23 ms"
        match = re.search(r'(h\d+[sf]) -> (srv\d+) \[Request \d+\]: ([\d.]+) Mbps, Latency: ([\d.]+) ms', line)
        if match:
            host = match.group(1)
            bandwidth = float(match.group(3))
            latency = float(match.group(4))
            
            bandwidth_values.append(bandwidth)
            latency_values.append(latency)
            
            if host.endswith('s'):
                if host not in results["student_results"]:
                    results["student_results"][host] = []
                results["student_results"][host].append({"bandwidth": bandwidth, "latency": latency})
            else:
                if host not in results["faculty_results"]:
                    results["faculty_results"][host] = []
                results["faculty_results"][host].append({"bandwidth": bandwidth, "latency": latency})
    
    # Parse summary lines from topology output
    for line in lines:
        # Look for summary lines like "Student to srv1: Avg Bandwidth: 25.50 Mbps, Avg Latency: 1.23 ms"
        match = re.search(r'(Student|Faculty) to srv\d+: Avg Bandwidth: ([\d.]+) Mbps, Avg Latency: ([\d.]+) ms', line)
        if match:
            group = match.group(1).lower()
            avg_bw = float(match.group(2))
            avg_lat = float(match.group(3))
            
            results["summary"][f"{group}_avg_bandwidth"] = avg_bw
            results["summary"][f"{group}_avg_latency"] = avg_lat
    
    # Calculate overall summary statistics
    if bandwidth_values:
        results["summary"]["avg_bandwidth"] = sum(bandwidth_values) / len(bandwidth_values)
        results["summary"]["max_bandwidth"] = max(bandwidth_values)
        results["summary"]["min_bandwidth"] = min(bandwidth_values)
    
    # Calculate total tests
    total_tests = sum(len(tests) for tests in results["student_results"].values())
    total_tests += sum(len(tests) for tests in results["faculty_results"].values())
    results["summary"]["total_tests"] = total_tests
    
    return results
