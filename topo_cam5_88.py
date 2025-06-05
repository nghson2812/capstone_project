# This version has the multithread iperf function (one host send multiple TCP request at a time)
# Also update run_iperf to provide more data.
# Modify by Khai Nguyen

# run iperf test on each server one by one. 
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.topo import Topo
from mininet.log import setLogLevel, info
from mininet.cli import CLI
import threading
import re
import time
from subprocess import check_output, call, CalledProcessError

# ONOS controller info
onos_ip = "127.0.0.1"  # Change this if needed
onos_port = 6653
student_number = 8
faculty_number = 8
TOTAL_MAX_RATE = 1_000_000_000  # 8 Gbps in bits per second for 8 buildings

QUEUE_CONFIG = {
    'q1s': 0.1 / student_number,  # 5% for Student - Mail Service
    'q2s': 0.25 / student_number,  # 35% for Student - RTMP Service
    'q3s': 0.15 / student_number,  # 15%   for Student - Call Service
    'q1f': 0.1 / faculty_number,  # 5% for Faculty - Mail Service
    'q2f': 0.25 / faculty_number,  # 25%   for Faculty - RTMP Service
    'q3f': 0.15 / faculty_number,  # 15%   for Faculty - Call Service
    #######
    'q1s2': 0.178 / student_number,  # 5% for Student - Mail Service
    'q2s2': 0.444 / student_number,  # 35% for Student - RTMP Service
    'q3s2': 0.267 / student_number,  # 15%   for Student - Call Service
    'q1f2': 0.022 / faculty_number,  # 5% for Faculty - Mail Service
    'q2f2': 0.056 / faculty_number,  # 25%   for Faculty - RTMP Service
    'q3f2': 0.033 / faculty_number,  # 15%   for Faculty - Call Service
    #######
    'q1s3': 0.19 / student_number,  # 5% for Student - Mail Service
    'q2s3': 0.475 / student_number,  # 35% for Student - RTMP Service
    'q3s3': 0.285 / student_number,  # 15%   for Student - Call Service
    'q1f3': 0.01 / faculty_number,  # 5% for Faculty - Mail Service
    'q2f3': 0.025 / faculty_number,  # 25%   for Faculty - RTMP Service
    'q3f3': 0.015 / faculty_number,  # 15%   for Faculty - Call Service
}


def cleanup_qos():
    try:
        print("Cleaning up QoS configurations...")
        # Get all ports with QoS settings
        qos_ports = check_output(['sudo', 'ovs-vsctl', '--format=csv', '--columns=name,qos', 'list', 'Port']).decode()
        for line in qos_ports.strip().split('\n')[1:]:  # Skip CSV header
            parts = line.strip().split(',')
            if len(parts) == 2 and parts[1] != '[]':
                port_name = parts[0].strip('"')
                print(f"Removing QoS from port: {port_name}")
                call(['sudo', 'ovs-vsctl', 'remove', 'Port', port_name, 'qos', parts[1]])

        # Delete all QoS and Queue entries
        call(['sudo', 'ovs-vsctl', '--all', 'destroy', 'qos'])
        call(['sudo', 'ovs-vsctl', '--all', 'destroy', 'queue'])
        print("QoS cleanup completed.")
    except CalledProcessError as e:
        print(f"Error during QoS cleanup: {e}")


def setup_qos_on_host_ports(net):
    try:
        # Build queue creation arguments
        queue_cmds = []
        for queue_name, percentage in QUEUE_CONFIG.items():
            rate = int(TOTAL_MAX_RATE * percentage)
            queue_cmds += ['--', f'--id=@{queue_name}', 'create', 'queue', f'other-config:max-rate={rate}']

        # QoS command with all queues
        qos_cmd = [
            'sudo', 'ovs-vsctl',
            *queue_cmds,
            '--', '--id=@newqos', 'create', 'qos', 'type=linux-htb',
            f'other-config:max-rate={TOTAL_MAX_RATE}',
            'queues:1=@q1s', 'queues:2=@q2s', 'queues:3=@q3s',
            'queues:4=@q1f', 'queues:5=@q2f', 'queues:6=@q3f',

            'queues:7=@q1s2', 'queues:8=@q2s2', 'queues:9=@q3s2',
            'queues:10=@q1f2', 'queues:11=@q2f2', 'queues:12=@q3f2',

            'queues:13=@q1s3', 'queues:14=@q2s3', 'queues:15=@q3s3',
            'queues:16=@q1f3', 'queues:17=@q2f3', 'queues:18=@q3f3'

        ]

        qos_result = check_output(qos_cmd).decode()
        qos_ids = qos_result.strip().split('\n')
        qos_id = qos_ids[-1]  # Last line contains the QoS ID
        print(f"Created QoS with UUID: {qos_id}")

        # Apply QoS to switch ports connected to hosts (excluding router)
        for host in net.hosts:
            if host.name == 'r0':
                continue
            intf = host.defaultIntf()
            link = intf.link
            if link:
                switch_intf = link.intf1 if link.intf2.node == host else link.intf2
                port_name = switch_intf.name
                print(f"Applying QoS to port: {port_name}")
                call(['sudo', 'ovs-vsctl', 'set', 'port', port_name, f'qos={qos_id}'])

    except CalledProcessError as e:
        print(f"Error executing OVS command: {e}")


class SimpleTopo(Topo):
    def build(self):
        # Switches
        switches = [self.addSwitch(f's{i + 1}', protocols='OpenFlow13') for i in range(8)]

        # Student hosts: 10.0.0.0/16
        student_hosts = [self.addHost(f'h{i + 1}s', ip=f'10.0.0.{i + 1}/24') for i in range(student_number)]

        # Faculty hosts: 10.0.1.0/16
        faculty_hosts = [self.addHost(f'h{i + 1}f', ip=f'10.0.1.{i + 1}/24') for i in range(faculty_number)]

        # Server hosts: 10.0.2.0/16
        server_hosts = [self.addHost(f'srv{i + 1}', ip=f'10.0.2.{i + 1}/24') for i in range(3)]

        # Router
        router = self.addHost('r0')
        self.addLink(router, switches[0])  # student subnet
        self.addLink(router, switches[1])  # faculty subnet
        self.addLink(router, switches[2])  # server subnet

        # Connect hosts evenly to switches
        def connect_hosts_to_switches(hosts):
            for i, host in enumerate(hosts):
                sw = switches[i % len(switches)]
                self.addLink(host, sw)

        connect_hosts_to_switches(student_hosts)
        connect_hosts_to_switches(faculty_hosts)

        # Connect servers to a designated switch (s3)
        for server in server_hosts:
            self.addLink(server, switches[2])

        # Switch interconnections (full mesh or partial mesh as desired)
        # Remove port tracking
        self.addLink(switches[0], switches[5])
        self.addLink(switches[0], switches[6])
        self.addLink(switches[1], switches[5])
        self.addLink(switches[1], switches[7])
        self.addLink(switches[2], switches[3])
        self.addLink(switches[2], switches[5])
        self.addLink(switches[2], switches[6])
        self.addLink(switches[4], switches[5])
        self.addLink(switches[4], switches[6])


def run():
    c0 = RemoteController('c0', ip=onos_ip, port=onos_port)

    net = Mininet(topo=SimpleTopo(),
                  controller=c0,
                  switch=OVSSwitch)

    net.start()

    # Configure the router (host r0) interfaces
    router = net.get('r0')
    router.setIP('10.0.0.250/24', intf='r0-eth0')  # Student subnet
    router.setIP('10.0.1.250/24', intf='r0-eth1')  # Faculty subnet
    router.setIP('10.0.2.250/24', intf='r0-eth2')  # Server subnet

    router.cmd('sysctl -w net.ipv4.ip_forward=1')  # Enable IP forwarding

    # Set default route for student hosts
    for i in range(student_number):
        student_host = net.get(f'h{i + 1}s')
        student_host.cmd('ip route add default via 10.0.0.250')

    # Set default route for faculty hosts
    for i in range(faculty_number):
        faculty_host = net.get(f'h{i + 1}f')
        faculty_host.cmd('ip route add default via 10.0.1.250')

    # Set default routes on server hosts
    for i in range(3):
        server_host = net.get(f'srv{i + 1}')
        server_host.cmd('ip route add default via 10.0.2.250')

    for switch in net.switches:
        switch.cmd('sudo ovs-vsctl set Bridge {} stp_enable=true'.format(switch.name))

    setup_qos_on_host_ports(net)

    print("\nNetwork is up. Starting CLI...\n")
    custom_cli(net)

    # QoS cleanup after CLI exits
    cleanup_qos()

    net.stop()


# change to h8f

# def ping_h1s_to_h8f(net):
#     h1s = net.get('h1s')
#     h8f = net.get('h8f')
#     print(f"\n*** Pinging from {h1s.name} to {h8f.name} with 5 packets")
#     result = h1s.cmd(f'ping -c 5 {h8f.IP()}')
#     print(result)

def parse_bandwidth(output):
    """Extract Mbps value from iperf output."""
    match = re.search(r'(\d+\.\d+|\d+)\s+Mbits/sec', output)
    return float(match.group(1)) if match else 0.0


# TCP iperf output parser
def parse_iperf_output_tcp(output):
    duration_match = re.search(r'(\d+\.\d+)-\s*(\d+\.\d+)\s+sec', output)
    bandwidth_match = re.search(r'(\d+\.\d+|\d+)\s+Mbits/sec', output)
    transferred_match = re.search(r'(\d+\.\d+|\d+)\s+MBytes', output)

    return {
        "duration_sec": float(duration_match.group(2)) - float(duration_match.group(1)) if duration_match else 0.0,
        "bandwidth_mbps": float(bandwidth_match.group(1)) if bandwidth_match else 0.0,
        "transferred_mbytes": float(transferred_match.group(1)) if transferred_match else 0.0,
    }


def parse_iperf_output_udp(output):
    result = {
        "duration_sec": 0.0,
        "bandwidth_mbps": 0.0,
        "transferred_mbytes": 0.0,
        "lost_packets": 0,
        "total_packets": 0,
        "loss_percent": 0.0,
        "jitter_ms": 0.0
    }

    # Try to find the summary line like:
    # [  3] 0.0-10.0 sec  19.5 MBytes  16.3 Mbits/sec  2.123 ms  200/1400 (14.3%)
    match = re.search(
        r'(\d+\.\d+)-\s*(\d+\.\d+)\s+sec\s+([\d\.]+)\s+MBytes\s+([\d\.]+)\s+Mbits/sec\s+([\d\.]+)\s+ms\s+(\d+)/(\d+)\s+\(([\d\.]+)%\)',
        output
    )

    if match:
        result["duration_sec"] = float(match.group(2)) - float(match.group(1))
        result["transferred_mbytes"] = float(match.group(3))
        result["bandwidth_mbps"] = float(match.group(4))
        result["jitter_ms"] = float(match.group(5))
        result["lost_packets"] = int(match.group(6))
        result["total_packets"] = int(match.group(7))
        result["loss_percent"] = float(match.group(8))

    return result


# def run_iperf_tcp(net):
#     servers = [net.get(f'srv{i+1}') for i in range(3)]
#     student_hosts = [net.get(f'h{i+1}s') for i in range(student_number)]
#     faculty_hosts = [net.get(f'h{i+1}f') for i in range(faculty_number)]
#     all_hosts = student_hosts + faculty_hosts

#     for server in servers:
#         server_name = server.name
#         info(f'\n*** Starting iperf TCP server on {server_name}\n')
#         server.cmd('killall -9 iperf')
#         server.cmd('iperf -s &')
#         time.sleep(1)

#         for host in all_hosts:
#             group = 'student' if host.name.endswith('s') else 'faculty'
#             info(f'*** {host.name} testing TCP connection to {server_name} ({server.IP()})\n')
#             output = host.cmd(f'iperf -c {server.IP()} -t 2')
#             result = parse_iperf_output_tcp(output)
#             print(f'{host.name} -> {server_name} [TCP]: {result["bandwidth_mbps"]:.2f} Mbps, '
#                   f'{result["transferred_mbytes"]:.2f} MB in {result["duration_sec"]:.2f} sec')

#         server.cmd('killall -9 iperf')
#         info(f'*** Stopped iperf TCP server on {server_name}\n')

def run_iperf_multithreaded_tcp(net, num_requests=3):
    server = net.get('srv1')  # Only use server 1
    student_hosts = [net.get(f'h{i + 1}s') for i in range(student_number)]
    faculty_hosts = [net.get(f'h{i + 1}f') for i in range(faculty_number)]

    all_hosts = student_hosts + faculty_hosts
    bandwidth_data = {
        'student': [],
        'faculty': []
    }

    server_name = server.name
    info(f'\n*** Starting TCP iperf server on {server_name}\n')
    server.cmd('killall -9 iperf')
    server.cmd('iperf -s &')
    time.sleep(1)  # wait for server ready

    def client_test(host, server_ip, group):
        for i in range(num_requests):
            info(f'*** {host.name} TCP request {i + 1} to {server_name}\n')
            output = host.cmd(f'iperf -c {server_ip} -t 2')
            bw = parse_bandwidth(output)
            bandwidth_data[group].append(bw)
            print(f'{host.name} -> {server_name} [Request {i + 1}]: {bw:.2f} Mbits/sec')

    threads = []
    for host in all_hosts:
        group = 'student' if host.name.endswith('s') else 'faculty'
        t = threading.Thread(target=client_test, args=(host, server.IP(), group))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    server.cmd('killall -9 iperf')
    info(f'*** Stopped TCP iperf server on {server_name}\n')

    # Average bandwidth output
    print("\n=== Average TCP Bandwidth to srv1 (Mbits/sec) ===")
    for group in ['student', 'faculty']:
        bw_list = bandwidth_data[group]
        if bw_list:
            avg_bw = sum(bw_list) / len(bw_list)
            print(f'{group.title()} to {server_name}: {avg_bw:.2f} Mbits/sec')
        else:
            print(f'{group.title()} to {server_name}: No data')


def run_udp_iperf_test_to_srv2(net, num_requests=3, duration=5, bandwidth='10M'):
    server = net.get('srv2')
    server_ip = server.IP()

    student_hosts = [net.get(f'h{i + 1}s') for i in range(student_number)]
    faculty_hosts = [net.get(f'h{i + 1}f') for i in range(faculty_number)]
    all_hosts = student_hosts + faculty_hosts

    # Prepare results
    result_data = {
        'student': {'bw': [], 'jitter': [], 'lost': 0, 'total': 0},
        'faculty': {'bw': [], 'jitter': [], 'lost': 0, 'total': 0}
    }

    info(f'\n*** Starting UDP iperf server on {server.name}\n')
    server.cmd('killall -9 iperf')
    server.cmd('iperf -s -u &')
    time.sleep(1)

    def run_client_test(host, group):
        for i in range(num_requests):
            info(f'*** {host.name} UDP Request {i + 1} to {server.name}\n')
            output = host.cmd(f'iperf -c {server_ip} -u -t {duration} -b {bandwidth}')
            result = parse_iperf_output_udp(output)

            data = result_data[group]
            data['bw'].append(result['bandwidth_mbps'])
            data['jitter'].append(result['jitter_ms'])
            data['lost'] += result['lost_packets']
            data['total'] += result['total_packets']

            print(f'{host.name} -> {server.name} [Req {i + 1}]: '
                  f'{result["bandwidth_mbps"]:.2f} Mbps, '
                  f'{result["transferred_mbytes"]:.2f} MB, '
                  f'Loss: {result["lost_packets"]}/{result["total_packets"]} '
                  f'({result["loss_percent"]:.2f}%), '
                  f'Jitter: {result["jitter_ms"]:.2f} ms over {result["duration_sec"]:.2f} sec')

    # Start all threads
    threads = []
    for host in all_hosts:
        group = 'student' if host.name.endswith('s') else 'faculty'
        t = threading.Thread(target=run_client_test, args=(host, group))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    server.cmd('killall -9 iperf')
    info(f'*** Stopped UDP iperf server on {server.name}\n')

    # Final report
    print(f"\n=== Average UDP Performance to {server.name} ===")
    for group, data in result_data.items():
        if data['bw']:
            avg_bw = sum(data['bw']) / len(data['bw'])
            avg_jitter = sum(data['jitter']) / len(data['jitter'])
            loss_pct = (data['lost'] / data['total']) * 100 if data['total'] > 0 else 0
            print(f'{group.title()} -> {server.name}: '
                  f'Avg BW: {avg_bw:.2f} Mbps, '
                  f'Avg Jitter: {avg_jitter:.2f} ms, '
                  f'Loss: {data["lost"]}/{data["total"]} ({loss_pct:.2f}%)')
        else:
            print(f'{group.title()} -> {server.name}: No data')


# def run_iperf_udp(net):
#     servers = [net.get(f'srv{i+1}') for i in range(3)]
#     student_hosts = [net.get(f'h{i+1}s') for i in range(student_number)]
#     faculty_hosts = [net.get(f'h{i+1}f') for i in range(faculty_number)]
#     all_hosts = student_hosts + faculty_hosts

#     for server in servers:
#         server_name = server.name
#         info(f'\n*** Starting iperf UDP server on {server_name}\n')
#         server.cmd('killall -9 iperf')
#         server.cmd('iperf -s -u &')
#         time.sleep(1)

#         for host in all_hosts:
#             group = 'student' if host.name.endswith('s') else 'faculty'
#             info(f'*** {host.name} testing UDP connection to {server_name} ({server.IP()})\n')
#             output = host.cmd(f'iperf -c {server.IP()} -u -t 2 -b 10M')  # UDP with bandwidth limit 10Mbps
#             result = parse_iperf_output_udp(output)
#             print(f'{host.name} -> {server_name} [UDP]: {result["bandwidth_mbps"]:.2f} Mbps, '
#                   f'{result["transferred_mbytes"]:.2f} MB, Loss: {result["lost_packets"]}/'
#                   f'{result["total_packets"]} ({result["loss_percent"]:.2f}%), '
#                   f'Jitter: {result["jitter_ms"]:.2f} ms in {result["duration_sec"]:.2f} sec')

#         server.cmd('killall -9 iperf')
#         info(f'*** Stopped iperf UDP server on {server_name}\n')

def ping_all(net):
    info('*** Running pingAll()\n')
    print(net.pingAll())


def custom_cli(net):
    while True:
        cmd = input("custom-cli> ").strip()
        if cmd == "exit":
            break
        # elif cmd == "run iperf tcp":
        #     run_iperf_tcp(net)
        # elif cmd == "run iperf udp":
        #     run_iperf_udp(net)
        elif cmd == "run iperf tcp mt":
            run_iperf_multithreaded_tcp(net, num_requests=3)
        elif cmd == "run iperf udp mt":
            run_udp_iperf_test_to_srv2(net, num_requests=3)
        # elif cmd == "h1s ping h8f":
        #     ping_h1s_to_h8f(net)
        elif cmd == "pingall":
            ping_all(net)
        elif cmd.startswith("sh "):
            print(net.getNodeByName('h1').cmd(cmd[3:]))
        else:
            print(
                "Unknown command. Available: run iperf tcp, run iperf udp, run iperf tcp mt, run iperf udp mt, pingall, h1s ping h8f, exit, sh <host_cmd>")


if __name__ == '__main__':
    setLogLevel('info')
    run()
