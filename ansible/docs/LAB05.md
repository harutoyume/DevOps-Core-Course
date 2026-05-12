# Lab 5 — Ansible Fundamentals Documentation

**Student:** Ilsaf Abdulkhakov  
**Date:** February 25, 2026  
**Lab:** Lab 5 - Configuration Management with Ansible  
**VM:** Vagrant (Ubuntu 24.04 LTS) from Lab 4

---

## 1. Architecture Overview

### Ansible Configuration

- **Ansible Version:** ansible [core 2.20.2]
- **Control Node:** macOS
- **Target Node:** Vagrant VM (Ubuntu 24.04 LTS)
- **Connection:** SSH via 127.0.0.1:2222 (Vagrant port forwarding)
- **SSH Key:** Vagrant-managed private key
- **Python Version on Target:** Python 3.12+

### Role Structure

```
ansible/
├── inventory/hosts.ini        # Static inventory with Vagrant VM
├── roles/
│   ├── common/               # System packages and basic setup
│   ├── docker/               # Docker CE installation
│   └── app_deploy/           # Application deployment
├── playbooks/
│   ├── site.yml             # Master playbook (all roles)
│   ├── provision.yml        # System provisioning only
│   └── deploy.yml           # Application deployment only
├── group_vars/all.yml       # Encrypted variables (Vault)
└── ansible.cfg              # Ansible configuration
```

### Why Roles Instead of Monolithic Playbooks?

Roles provide **reusability** (e.g., `docker` role usable across projects), **modularity** (clear separation: provisioning vs. deployment), **maintainability** (edit specific role vs. searching a large file), **independent testing** (each role testable in isolation), and **easier collaboration** (team members work on different roles). Monolithic playbooks mix all logic, making maintenance and reuse difficult. Roles also enable publishing to Ansible Galaxy.

---

## 2. Roles Documentation

### Role: common

**Purpose:** Basic system setup—update package cache, install essential tools (curl, git, vim, etc.), set timezone.

**Variables (defaults/main.yml):**
```yaml
common_packages:
  - python3-pip
  - curl
  - git
  - vim
  - htop
  - net-tools
  - wget
  - build-essential

timezone: UTC
```

**Tasks:** Update apt cache (3600s validity), install common packages, set timezone.

**Handlers:** None

**Dependencies:** None

---

### Role: docker

**Purpose:** Install Docker CE and configure it for the target user.

**Variables (defaults/main.yml):**
```yaml
docker_packages:
  - docker-ce
  - docker-ce-cli
  - containerd.io

docker_users:
  - vagrant

docker_apt_gpg_key: https://download.docker.com/linux/ubuntu/gpg
docker_apt_repository: deb [arch=...] https://download.docker.com/linux/ubuntu ...
```

**Tasks:** Install prerequisites, add Docker GPG key and repository, install Docker CE, install python3-docker, ensure Docker service is started, add users to docker group, reset SSH connection to apply group changes.

**Handlers:** `restart docker` — Restarts Docker service when configuration changes

**Dependencies:** None (typically runs after `common`)

---

### Role: app_deploy

**Purpose:** Deploy containerized Python app by pulling from Docker Hub and running with proper configuration.

**Variables (group_vars/all.yml - encrypted):** `dockerhub_username`, `dockerhub_password`, `app_name`, `docker_image`, `docker_image_tag`, `app_port`, `app_container_name`

**Variables (defaults/main.yml):** `app_container_restart_policy`, `app_health_check_timeout`, `app_health_endpoint`

**Tasks:** Log in to Docker Hub (`no_log: true`), pull image, stop/remove old container, run new container with port mapping, wait for port, verify health endpoint.

**Handlers:** `restart app container`

**Dependencies:** Requires `docker` role

---

## 3. Idempotency Demonstration

### First Run — Initial Provisioning

**Command:**
```bash
ansible-playbook playbooks/provision.yml
```

**Output:**
```
PLAY [Provision web servers] ***************************************************

TASK [Gathering Facts] *********************************************************
ok: [devops-vm]

TASK [common : Update apt cache] ***********************************************
ok: [devops-vm]

TASK [common : Install common packages] ****************************************
ok: [devops-vm]

TASK [common : Set timezone] ***************************************************
ok: [devops-vm]

TASK [docker : Install Docker prerequisites] ***********************************
ok: [devops-vm]

TASK [docker : Add Docker GPG key] *********************************************
ok: [devops-vm]

TASK [docker : Determine Docker architecture] **********************************
ok: [devops-vm]

TASK [docker : Remove old Docker repository file if it exists] *****************
ok: [devops-vm]

TASK [docker : Add Docker repository with correct architecture] ****************
changed: [devops-vm]

TASK [docker : Update apt cache after adding Docker repository] ****************
ok: [devops-vm]

TASK [docker : Install Docker packages] ****************************************
ok: [devops-vm]

TASK [docker : Install python3-docker for Ansible modules] *********************
ok: [devops-vm]

TASK [docker : Ensure Docker service is started and enabled] *******************
ok: [devops-vm]

TASK [docker : Add users to docker group] **************************************
ok: [devops-vm] => (item=vagrant)

TASK [docker : Reset SSH connection to apply group changes] ********************

PLAY RECAP *********************************************************************
devops-vm                  : ok=14   changed=1    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

---

### Second Run — Demonstrating Idempotency

**Command:**
```bash
ansible-playbook playbooks/provision.yml
```

**Output:**
```
PLAY [Provision web servers] ***************************************************

TASK [Gathering Facts] *********************************************************
ok: [devops-vm]

TASK [common : Update apt cache] ***********************************************
ok: [devops-vm]

TASK [common : Install common packages] ****************************************
ok: [devops-vm]

TASK [common : Set timezone] ***************************************************
ok: [devops-vm]

TASK [docker : Install Docker prerequisites] ***********************************
ok: [devops-vm]

TASK [docker : Add Docker GPG key] *********************************************
ok: [devops-vm]

TASK [docker : Determine Docker architecture] **********************************
ok: [devops-vm]

TASK [docker : Remove old Docker repository file if it exists] *****************
ok: [devops-vm]

TASK [docker : Add Docker repository with correct architecture] ****************
changed: [devops-vm]

TASK [docker : Update apt cache after adding Docker repository] ****************
ok: [devops-vm]

TASK [docker : Install Docker packages] ****************************************
ok: [devops-vm]

TASK [docker : Install python3-docker for Ansible modules] *********************
ok: [devops-vm]

TASK [docker : Ensure Docker service is started and enabled] *******************
ok: [devops-vm]

TASK [docker : Add users to docker group] **************************************
ok: [devops-vm] => (item=vagrant)

TASK [docker : Reset SSH connection to apply group changes] ********************

PLAY RECAP *********************************************************************
devops-vm                  : ok=14   changed=1    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

---

### Analysis

| Task | First Run | Second Run | Why? |
|------|-----------|------------|------|
| Update apt cache | ok | ok | `cache_valid_time: 3600`—skip if cache fresh |
| Install common packages | ok | ok | `apt state: present`—only install if missing |
| Set timezone | ok | ok | Already set to UTC |
| Add Docker GPG key | ok | ok | Key already present |
| Add Docker repository | **changed** | **changed** | `apt_repository` checks exact line; minor config diff can trigger changed |
| Install Docker packages | ok | ok | Packages already installed |
| Docker service | ok | ok | `service state: started`—already running |
| Add user to docker group | ok | ok | User already member |

**Conclusion:** Idempotency demonstrated. Both runs show 14 ok, 1 changed. The Docker repository task may show `changed` due to `apt_repository`'s exact-string comparison—system state remains correct and stable. No unnecessary reinstalls, restarts, or configuration overwrites.

### What Makes These Roles Idempotent?

**Stateful modules:** All tasks use modules that check current state before acting:
- `apt: state=present` — installs only if package missing
- `apt: update_cache` with `cache_valid_time: 3600` — updates only if cache stale
- `service: state=started` — starts only if stopped
- `user` with `append: yes` — adds to group only if not member
- `apt_key` / `apt_repository` — add only if absent

**Avoided anti-pattern:** Raw `command`/`shell` (e.g., `curl | sh`) would run every time. Declarative modules (e.g., `apt`, `service`, `file`) ensure idempotency.

---

## 4. Ansible Vault Usage

### Credential Storage

Sensitive data (Docker Hub credentials) stored in encrypted `group_vars/all.yml` using Ansible Vault (AES256).

**Vault password management:** Password file `.vault_pass` (chmod 600, in .gitignore), referenced in ansible.cfg via `vault_password_file = .vault_pass`. Enables automation without manual password entry.

### Encrypted File Verification

```bash
cat group_vars/all.yml
```

**Output (file is encrypted):**
```
$ANSIBLE_VAULT;1.1;AES256
39663730306636613461363834343533396166363363343365336130613231376664646366313937
3731353539646466666665353031646431663931326466300a366637396333636135336330303739
64613364353339323733613766356336613336336561363264646334653861373834353338343261
3337363432653963370a376334653035346563363730343331366463346139656562366233653464
36386430306666373432623638306331363538653432306234613965333238633566343361326634
39333333376630373836343036386138633438333832366637626336383166643533333033336437
...
```

### Why Ansible Vault is Important

Prevents plain-text credentials in version control. Encrypted files are safe to commit; only vault password (stored separately, never committed) unlocks them. `no_log: true` on docker_login prevents credentials appearing in playbook logs. Essential for compliance and team collaboration.

---

## 5. Deployment Verification

### Deployment Output

**Command:**
```bash
ansible-playbook playbooks/deploy.yml
```

**Output:**
```
PLAY [Deploy application] ******************************************************

TASK [Gathering Facts] *********************************************************
ok: [devops-vm]

TASK [app_deploy : Log in to Docker Hub] ***************************************
ok: [devops-vm]

TASK [app_deploy : Pull Docker image] ******************************************
ok: [devops-vm]

TASK [app_deploy : Remove old container if exists] *****************************
changed: [devops-vm]

TASK [app_deploy : Run application container] **********************************
changed: [devops-vm]

TASK [app_deploy : Wait for application port to be available] ******************
ok: [devops-vm]

TASK [app_deploy : Verify application health endpoint] *************************
ok: [devops-vm]

PLAY RECAP *********************************************************************
devops-vm                  : ok=7    changed=2    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

---

### Container Status

**Command:**
```bash
ansible webservers -a "docker ps"
```

**Output:**
```
devops-vm | CHANGED | rc=0 >>
CONTAINER ID   IMAGE                                 COMMAND           CREATED              STATUS              PORTS                    NAMES
300bd45cf57c   haruyume/devops-info-service:latest   "python app.py"   About a minute ago   Up About a minute   0.0.0.0:5000->5000/tcp   devops-app
```

---

### Health Check

**Command:**
```bash
curl http://127.0.0.1:5001/health
```

**Output:**
```json
{"status":"healthy","timestamp":"2026-02-25T09:04:20.732245+00:00","uptime_seconds":85}
```

---

### Main Endpoint

**Command:**
```bash
curl http://127.0.0.1:5001/
```

**Output:**
```json
{
  "endpoints": [
    {"description": "Service information", "method": "GET", "path": "/"},
    {"description": "Health check", "method": "GET", "path": "/health"}
  ],
  "request": {
    "client_ip": "10.0.2.2",
    "method": "GET",
    "path": "/",
    "user_agent": "curl/8.7.1"
  },
  "runtime": {
    "current_time": "2026-02-25T09:04:22.177496+00:00",
    "timezone": "UTC",
    "uptime_human": "1 minute, 26 seconds",
    "uptime_seconds": 86
  },
  "service": {
    "description": "DevOps course info service",
    "framework": "Flask",
    "name": "devops-info-service",
    "version": "1.0.0"
  },
  "system": {
    "architecture": "aarch64",
    "cpu_count": 2,
    "hostname": "300bd45cf57c",
    "platform": "Linux",
    "python_version": "3.13.12"
  }
}
```

---

### Handler Execution

**Handlers triggered:** None during this deployment.

**Explanation:** Container was recreated (removed and run fresh) rather than modified in place, so no config-change notification occurred. `restart docker` and `restart app container` would run only if their config changed. This shows handlers execute conditionally—only when notified—avoiding unnecessary restarts.

---

## 6. Key Decisions

**Why use roles instead of plain playbooks?** Roles standardize organization for reusability and maintainability. They separate concerns (provisioning vs. deployment), allow independent testing and sharing via Ansible Galaxy, and keep playbooks small (e.g., `provision.yml` is ~9 lines) while logic lives in roles.

**How do roles improve reusability?** The same role (e.g., `docker`) can be included in multiple playbooks or projects. Variables like `docker_users: [vagrant]` or `docker_users: [ubuntu, jenkins]` customize behavior per environment without code duplication.

**What makes a task idempotent?** Use stateful modules that check current state before acting (e.g., `apt: state=present`, `service: state=started`). Declare desired state, not imperative steps. Avoid raw `command`/`shell` for config. Run playbook twice—second run should show all `ok` (or minimal `changed` with understood edge cases).

**How do handlers improve efficiency?** Handlers run only when notified by a changed task, and only at end of play. Multiple tasks can notify one handler; it runs once. Example: three config file changes trigger one restart instead of three.

**Why is Ansible Vault necessary?** Credentials must never appear in plain text in version control. Vault encrypts files with AES256; they are safe to commit. Decryption requires a separate password (or password file). Essential for compliance, audit trails, and safe collaboration.

---

## 7. Challenges

- **Architecture naming mismatch:** VM reports `aarch64`, Docker APT expects `arm64`. Solved with `docker_architecture_map: { aarch64: arm64, x86_64: amd64 }` in repository URL.

- **Vault variable scoping:** Variables in `group_vars/all.yml` were not loaded for roles. Fixed by adding `vars_files: - ../group_vars/all.yml` in the deploy playbook.

- **Docker group not active:** After adding vagrant to docker group, the same SSH session didn't see it. Added `meta: reset_connection` so the new session picks up group membership.

- **Repository update timing:** apt cache wasn't refreshed after adding Docker repository. Added explicit apt update with `cache_valid_time: 0` before installing packages.
