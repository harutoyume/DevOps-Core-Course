# Lab 4 - Infrastructure as Code (Local VM with Vagrant)

This directory contains the Infrastructure as Code implementation for Lab 4 using a local VM approach with Vagrant.

## Overview

For this lab, I chose to use a **local VM with Vagrant** instead of cloud providers. This approach is explicitly allowed by the lab instructions for students who prefer not to use cloud services.

**Why Vagrant qualifies as Infrastructure as Code:**
- Declarative configuration in `Vagrantfile`
- Version-controlled infrastructure
- Reproducible VM creation
- Infrastructure lifecycle management (create, update, destroy)
- Automated provisioning

## Prerequisites

Before starting, ensure you have the following installed on macOS:

```bash
# Install Vagrant
brew install --cask vagrant

# Install VirtualBox (Vagrant provider)
brew install --cask virtualbox
```

**Verify installations:**
```bash
vagrant --version    # Should show Vagrant 2.x or higher
vboxmanage --version # Should show VirtualBox version
```

## VM Specifications

The Vagrantfile defines a VM with the following specifications (ready for Lab 5 - Ansible):

- **OS:** Ubuntu 24.04 LTS (Noble Numbat)
- **Box:** `bento/ubuntu-24.04` (compatible with Apple Silicon/ARM64)
- **Memory:** 2 GB RAM
- **CPUs:** 2 cores
- **Network:** 
  - Private network: `192.168.56.10`
  - Port forwarding: 
    - Guest 5000 -> Host 5001 (Flask app)
    - Guest 80 -> Host 8080 (HTTP)
- **Hostname:** `devops-lab-vm`
- **SSH:** Configured and ready for Ansible

**Note for Apple Silicon (M1/M2/M3) Macs:** This Vagrantfile uses the `bento/ubuntu-24.04` box which has ARM64 support and works with VirtualBox 7.x on Apple Silicon.

## Quick Start

### 1. Start the VM

```bash
cd terraform
vagrant up
```

This command will:
- Download the Ubuntu 24.04 box (first time only, ~800 MB - 1.5 GB)
- Create and configure the VM
- Set up networking
- Install essential packages (SSH, curl, wget, git)
- Display VM connection information

**Note:** First-time setup downloads the Vagrant box. This may take several minutes depending on your internet connection.

### 2. Verify VM is Running

```bash
vagrant status
```

Expected output:
```
Current machine states:

default                   running (virtualbox)
```

### 3. Connect to VM

**Option A: Using Vagrant (recommended):**
```bash
vagrant ssh
```

**Option B: Using SSH directly:**
```bash
ssh vagrant@192.168.56.10
# Password: vagrant
```

### 4. Test VM

Once connected to the VM:
```bash
# Check OS version
cat /etc/os-release

# Check network
ip addr show

# Check SSH service
systemctl status ssh

# Exit VM
exit
```

## VM Management

### Common Commands

```bash
# Start VM
vagrant up

# Stop VM (graceful shutdown)
vagrant halt

# Restart VM
vagrant reload

# Destroy VM (delete everything)
vagrant destroy

# Recreate VM from scratch
vagrant destroy -f && vagrant up

# SSH into VM
vagrant ssh

# View VM status
vagrant status

# Suspend VM (save state)
vagrant suspend

# Resume suspended VM
vagrant resume
```

### Troubleshooting

**Issue: Box not found (404 error)**
```bash
# If the bento box doesn't work, try Ubuntu 22.04 LTS instead
# Edit Vagrantfile and change box to: "bento/ubuntu-22.04"
vagrant up
```

**Issue: VM won't start (Apple Silicon)**
```bash
# Ensure you're using VirtualBox 7.x (has ARM64 support)
vboxmanage --version

# Check VirtualBox is running
vboxmanage list vms

# Try explicit provider
vagrant up --provider=virtualbox
```

**Issue: Network not accessible**
```bash
# Reload VM
vagrant reload

# Check VirtualBox network settings
vboxmanage list hostonlyifs
```

**Issue: SSH connection refused**
```bash
# Reprovision VM
vagrant provision

# Or recreate VM
vagrant destroy -f && vagrant up
```

**Issue: VirtualBox kernel extension blocked (macOS)**
```bash
# Go to: System Settings → Privacy & Security
# Allow Oracle kernel extension
# Then restart VirtualBox and try again
```

## Infrastructure Lifecycle

This VM demonstrates Infrastructure as Code lifecycle management:

### Create
```bash
vagrant up
```
Creates the VM from the Vagrantfile definition.

### Update
Edit the `Vagrantfile`, then:
```bash
vagrant reload
```
Applies configuration changes.

### Destroy
```bash
vagrant destroy
```
Deletes the VM completely. Can be recreated anytime with `vagrant up`.

### Reproduce
Anyone with this `Vagrantfile` can create an identical VM:
```bash
git clone <your-repo>
cd terraform
vagrant up
```

## Lab 5 Preparation

This VM is configured and ready for Lab 5 (Ansible) with:
- ✅ Ubuntu 24.04 LTS
- ✅ SSH server installed and running
- ✅ Accessible via SSH (vagrant@192.168.56.10)
- ✅ SSH key authentication configured (via Vagrant)
- ✅ Static IP address (192.168.56.10)
- ✅ Sufficient resources (2 GB RAM, 2 CPUs)

For Lab 5, you can target this VM in your Ansible inventory:
```ini
[lab_vms]
devops-vm ansible_host=192.168.56.10 ansible_user=vagrant ansible_password=vagrant
```

## Documentation

Full lab documentation is available in [`docs/LAB04.md`](docs/LAB04.md).

## Files

- **`Vagrantfile`** - VM definition (Infrastructure as Code)
- **`.gitignore`** - Excludes VM state files from Git
- **`README.md`** - This file
- **`docs/LAB04.md`** - Complete lab documentation

## Cost

**Total cost: $0**

Using a local VM with Vagrant is completely free. No cloud account or credit card required.

## Cleanup

When finished with the VM:

```bash
# Stop VM (keeps disk image)
vagrant halt

# Or completely remove VM
vagrant destroy
```

The VM can be recreated anytime with `vagrant up`.

## Why Local VM Instead of Cloud?

**Advantages:**
- ✅ No cloud account setup required
- ✅ No costs or billing concerns
- ✅ Works offline
- ✅ Full control over VM
- ✅ Easy to destroy and recreate
- ✅ Still demonstrates IaC concepts

**Trade-offs:**
- ❌ Uses local machine resources
- ❌ Not accessible from internet
- ❌ Requires VirtualBox installation
- ❌ Less "production-like" than cloud

For learning IaC concepts, a local VM is perfectly adequate and explicitly allowed by the lab instructions.
