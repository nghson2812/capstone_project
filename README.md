# Modeling a Campus Network with Software-Defined Networking to Enhance Quality of Service: A Comparative Study 

## Setup Instructions

**Prerequisites**  

Ensure that both **Mininet** and **ONOS** are installed and running.

### Steps to setup

1. **Access Mininet** via SSH.

2. Change the IP of ONOS in the file.

3. In the Mininet terminal, run:
   ```bash
   sudo python3 topo_cam3.py
   ```
   
- This initializes the custom campus topology and sets up basic QoS configurations.

4. Open a second terminal and execute:
   ```bash
   sudo python3 flow_rule.py
   ```

5. Verify that the flow rules are added successfully:
- Access ONOS GUI and check the flow table.

6. Test connectivity using any of the following: iperf, ping, pingall,...

These tests help verify the network's performance and QoS under the SDN setup.
