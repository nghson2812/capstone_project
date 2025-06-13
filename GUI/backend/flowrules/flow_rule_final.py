import json
import requests
from requests.auth import HTTPBasicAuth

# Flow definitions
# flow_templates = [
#     # Student flows
#     {"queueId": 1, "src_ip": "10.0.0.0/24", "dst_ip": "10.0.2.1/32"},  # Mail
#     {"queueId": 2, "src_ip": "10.0.0.0/24", "dst_ip": "10.0.2.2/32"},  # RTMP
#     {"queueId": 3, "src_ip": "10.0.0.0/24", "dst_ip": "10.0.2.3/32"},  # Call

#     # Faculty flows
#     {"queueId": 4, "src_ip": "10.0.1.0/24", "dst_ip": "10.0.2.1/32"},  # Mail
#     {"queueId": 5, "src_ip": "10.0.1.0/24", "dst_ip": "10.0.2.2/32"},  # RTMP
#     {"queueId": 6, "src_ip": "10.0.1.0/24", "dst_ip": "10.0.2.3/32"},  # Call
# ]

# flow_templates = [
#     # Student flows
#     {"queueId": 7, "src_ip": "10.0.0.0/24", "dst_ip": "10.0.2.1/32"},  # Mail
#     {"queueId": 8, "src_ip": "10.0.0.0/24", "dst_ip": "10.0.2.2/32"},  # RTMP
#     {"queueId": 9, "src_ip": "10.0.0.0/24", "dst_ip": "10.0.2.3/32"},  # Call

#     # Faculty flows
#     {"queueId": 10, "src_ip": "10.0.1.0/24", "dst_ip": "10.0.2.1/32"},  # Mail
#     {"queueId": 11, "src_ip": "10.0.1.0/24", "dst_ip": "10.0.2.2/32"},  # RTMP
#     {"queueId": 12, "src_ip": "10.0.1.0/24", "dst_ip": "10.0.2.3/32"},  # Call
# ]

flow_templates = [
    # Student flows
    {"queueId": 13, "src_ip": "10.0.0.0/24", "dst_ip": "10.0.2.1/32"},  # Mail
    {"queueId": 14, "src_ip": "10.0.0.0/24", "dst_ip": "10.0.2.2/32"},  # RTMP
    {"queueId": 15, "src_ip": "10.0.0.0/24", "dst_ip": "10.0.2.3/32"},  # Call

    # Faculty flows
    {"queueId": 16, "src_ip": "10.0.1.0/24", "dst_ip": "10.0.2.1/32"},  # Mail
    {"queueId": 17, "src_ip": "10.0.1.0/24", "dst_ip": "10.0.2.2/32"},  # RTMP
    {"queueId": 18, "src_ip": "10.0.1.0/24", "dst_ip": "10.0.2.3/32"},  # Call
]


# ONOS credentials and IP info (replace with actual values)
onos_ip = "192.168.180.130"      # Replace with ONOS controller IP
onos_port = 8181              # Default ONOS REST port
username = "onos"             # Replace with your ONOS username
password = "rocks"            # Replace with your ONOS password

# Switches to apply the flows to
switch_ids = [f'of:000000000000000{i}' for i in range(1, 9)]

def inject_flow_rules():
    """Inject flow rules into ONOS controller"""
    success_count = 0
    total_flows = len(switch_ids) * len(flow_templates)
    
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
                success_count += 1
            else:
                print(f"Failed to add Flow {i} to {device_id} | Status: {response.status_code}")
                print(response.text)
    
    return success_count == total_flows
