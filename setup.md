# SDN Environment Setup

This repository contains scripts and configuration files for setting up a Software Defined Networking (SDN) environment using ONOS and Mininet on Ubuntu 24.04.

## System Requirements

Platform: Ubuntu 24.04 (VM)

Components:

* ONOS Controller (Docker)
* Mininet 2.3.0
* Python 3.12 + Tkinter

## Initial Setup

### System Update & Tool Installation

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3-pip python3-tk xterm openssh-server curl
```

### Mininet Installation

```bash
sudo apt install mininet -y
mn --version  # Verify installation (should show 2.3.0)
```

### Docker Setup

#### Install Docker

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker  # Or reboot VM
```

## ONOS Container Management

### Pull ONOS image

```bash
sudo docker pull onosproject/onos
```

### Start container (general)

```bash
sudo docker run -t -d -p 6653:6653 -p 8181:8181 -p 8101:8101 -p 5005:5005 -p 830:830 --name onos onosproject/onos
```

### Verify container

```bash
wget -q -O - http://192.168.180.130:8181/onos/ui > /dev/null
```

### Container management commands

```bash
sudo docker rm -f onos   # Remove container
sudo docker start onos   # Restart container
sudo docker ps           # Check running containers
```

## Network Configuration

### IP Address Check

General command:

```bash
ip addr | grep eth0
```

Example output:

```
inet 192.168.180.130/24 brd 192.168.180.255 scope global eth0
```

## ONOS Access

### Web Interface

* General URL: [http://](http://<your-vm-ip>:8181/onos/ui)[:8181/onos/ui](http://<your-vm-ip>:8181/onos/ui)
* Example URL: [http://192.168.180.130:8181/onos/ui](http://192.168.180.130:8181/onos/ui)
* Credentials: `onos/rocks`

### SSH Access

General command:

```bash
ssh -p 8101 karaf@<ONOS_IP>
```

Example command:

```bash
ssh -p 8101 karaf@192.168.180.130
# Password: karaf
```

### Activate required apps

```bash
app activate org.onosproject.openflow
app activate org.onosproject.proxyarp
apps -s -a  # Verify activated apps
```

### SSH Key Maintenance (use when karaf timeout)

General command:

```bash
ssh-keygen -f ~/.ssh/known_hosts -R '[<ONOS_IP>]:8101'
```

Example command:

```bash
ssh-keygen -f ~/.ssh/known_hosts -R '[192.168.180.130]:8101'
```

## File Transfer

### SCP Transfer (from PC to VM)

General format:

```bash
scp -P 22 <local-files> <username>@<vm-ip>:<destination-path>
```

Example:

```bash
scp -P 22 gui.py flow_rule.py topo_cam5.py jason@192.168.180.130:/home/jason/SDN
```

## Application Execution

Run application:

```bash
sudo python3 main.py
```

Visit:

```bash
http://<vm-ip>:5000/
```

Example:

```bash
http://192.168.180.130:5000/
```