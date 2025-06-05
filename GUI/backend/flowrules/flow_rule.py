import requests
import json
import os
from requests.auth import HTTPBasicAuth

# ONOS controller info - can be overridden by environment variables
onos_ip = os.getenv("ONOS_IP", "192.168.180.130")
onos_port = os.getenv("ONOS_PORT", "8181")
username = os.getenv("ONOS_USERNAME", "onos")
password = os.getenv("ONOS_PASSWORD", "rocks")

# Define flow rules using a list of dictionaries
flow_templates = [
    # Student flows
    {"queueId": 1, "src_ip": "10.0.0.0/24", "dst_ip": "10.0.2.1/32"},  # Mail
    {"queueId": 2, "src_ip": "10.0.0.0/24", "dst_ip": "10.0.2.2/32"},  # RTMP
    {"queueId": 3, "src_ip": "10.0.0.0/24", "dst_ip": "10.0.2.3/32"},  # Call

    # Faculty flows
    {"queueId": 4, "src_ip": "10.0.1.0/24", "dst_ip": "10.0.2.1/32"},  # Mail
    {"queueId": 5, "src_ip": "10.0.1.0/24", "dst_ip": "10.0.2.2/32"},  # RTMP
    {"queueId": 6, "src_ip": "10.0.1.0/24", "dst_ip": "10.0.2.3/32"},  # Call
]

def get_device_ids():
    """Get list of switch device IDs from ONOS"""
    try:
        url = f"http://{onos_ip}:{onos_port}/onos/v1/devices"
        response = requests.get(url, auth=HTTPBasicAuth(username, password))

        if response.status_code == 200:
            devices = response.json()
            device_ids = [device['id'] for device in devices.get('devices', []) if device.get('available', False)]
            print(f"Found {len(device_ids)} available devices: {device_ids}")
            return device_ids
        else:
            print(f"Failed to get devices. Status: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error getting device IDs: {e}")
        return []

def get_flow_count():
    """Get current number of flow rules in ONOS"""
    try:
        url = f"http://{onos_ip}:{onos_port}/onos/v1/flows"
        response = requests.get(url, auth=HTTPBasicAuth(username, password))

        if response.status_code == 200:
            flows = response.json()
            return len(flows.get('flows', []))
        else:
            return 0
    except Exception as e:
        print(f"Error getting flow count: {e}")
        return 0

def inject_flow_rules():
    """Inject QoS flow rules into ONOS"""
    # Get all available switch IDs
    switch_ids = get_device_ids()

    if not switch_ids:
        print("No available switches found. Exiting.")
        return False

    success_count = 0
    total_flows = len(switch_ids) * len(flow_templates)

    print(f"Injecting {total_flows} flow rules to {len(switch_ids)} switches...")

    # Push flows to each switch
    for device_id in switch_ids:
        print(f"\nProcessing device: {device_id}")

        for i, flow_def in enumerate(flow_templates, start=1):
            flow_rule = {
                "priority": 50000,
                "timeout": 0,
                "isPermanent": True,
                "deviceId": device_id,
                "treatment": {
                    "instructions": [
                        {"type": "QUEUE", "queueId": flow_def["queueId"]},
                        {"type": "OUTPUT", "port": "NORMAL"}
                    ]
                },
                "selector": {
                    "criteria": [
                        {"type": "ETH_TYPE", "ethType": "0x800"},
                        {"type": "IPV4_SRC", "ip": flow_def["src_ip"]},
                        {"type": "IPV4_DST", "ip": flow_def["dst_ip"]}
                    ]
                }
            }

            payload = {"flows": [flow_rule]}
            url = f"http://{onos_ip}:{onos_port}/onos/v1/flows"
            headers = {"Content-Type": "application/json"}

            try:
                response = requests.post(url, json=payload, auth=HTTPBasicAuth(username, password), headers=headers)

                if response.status_code in [200, 201]:
                    print(f"  ✅ Flow {i}/6 injected successfully")
                    success_count += 1
                else:
                    print(f"  ❌ Flow {i}/6 failed. Status: {response.status_code}")
                    print(f"     Response: {response.text}")

            except Exception as e:
                print(f"  ❌ Flow {i}/6 failed with exception: {e}")

    print(f"\n=== Injection Summary ===")
    print(f"Total flows attempted: {total_flows}")
    print(f"Successful injections: {success_count}")
    print(f"Failed injections: {total_flows - success_count}")

    return success_count == total_flows

def validate_onos_connection():
    """Validate connection to ONOS controller"""
    try:
        url = f"http://{onos_ip}:{onos_port}/onos/v1/applications"
        response = requests.get(url, auth=HTTPBasicAuth(username, password), timeout=5)

        if response.status_code == 200:
            print(f"✅ Successfully connected to ONOS at {onos_ip}:{onos_port}")
            return True
        else:
            print(f"❌ ONOS connection failed. Status: {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to ONOS: {e}")
        return False

if __name__ == "__main__":
    print("=== ONOS Flow Rule Injection Tool ===")
    print(f"ONOS Controller: {onos_ip}:{onos_port}")
    print(f"Username: {username}")

    # Validate connection first
    if not validate_onos_connection():
        print("Cannot proceed without ONOS connection. Please check your configuration.")
        exit(1)

    # Show current flow count
    current_flows = get_flow_count()
    print(f"Current flow rules in ONOS: {current_flows}")

    # Inject the QoS flow rules
    success = inject_flow_rules()

    # Show final flow count
    final_flows = get_flow_count()
    print(f"Final flow rules in ONOS: {final_flows}")

    if success:
        print("\n🎉 All flow rules injected successfully!")
    else:
        print("\n⚠️  Some flow rules failed to inject. Check the logs above.")
