import requests
import json
from requests.auth import HTTPBasicAuth

# ONOS controller info
onos_ip = "10.236.108.129"  # Change this if needed
onos_port = "8181"
username = "onos"
password = "rocks"

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

# Fetch the list of devices (switches) from ONOS
# def get_device_ids():
#   url = f"http://{onos_ip}:{onos_port}/onos/v1/devices"
#   response = requests.get(url, auth=HTTPBasicAuth(username, password))
#
#   if response.status_code == 200:
#     devices = response.json()
#     device_ids = [device['id'] for device in devices.get('devices', [])]
#     return device_ids
#   else:
#     print(f"Failed to retrieve devices. Status code: {response.status_code}")
#     print(response.text)
#     return []


# Get the device IDs from ONOS
switch_ids = ['of:0000000000000003']

# Post flow rule to each switch
for device_id in switch_ids:
    for i, flow_def in enumerate(flow_templates, start=1):
        flow = {
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

        payload = {"flows": [flow]}
        url = f"http://{onos_ip}:{onos_port}/onos/v1/flows"
        headers = {"Content-Type": "application/json"}

        response = requests.post(
            url,
            headers=headers,
            auth=HTTPBasicAuth(username, password),
            data=json.dumps(payload)
        )

        if response.status_code in [200, 201]:
            print(f"Flow {i} added to {device_id}")
        else:
            print(f"Failed to add Flow {i} to {device_id} | Status: {response.status_code}")
            print(response.text)