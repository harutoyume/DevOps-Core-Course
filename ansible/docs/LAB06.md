# Lab 6: Advanced Ansible & CI/CD - Submission

**Name:** Ilsaf Abdulkhakov  
**Date:** March 4, 2026  
**Lab Points:** 10

---

## 1. Overview

This lab focused on enhancing Ansible automation with production-grade features. The primary accomplishments include refactoring roles with blocks and tags for better error handling and selective execution, migrating from imperative Docker commands to declarative Docker Compose deployments, implementing a safe "wipe" cleanup mechanism with double-gating security, and fully automating the deployment process using GitHub Actions CI/CD.

**Technologies Used:**
- **Ansible 2.16+**: Utilizing blocks, rescue/always sections, and hierarchical tagging.
- **Docker Compose v2**: For declarative container orchestration and multi-container readiness.
- **GitHub Actions**: Automated linting, deployment, and health verification.
- **Jinja2**: Dynamic templating for configuration files.
- **Ansible Vault**: Secure management of sensitive credentials.

---

## 2. Blocks & Tags

### Implementation
Each role was refactored to use blocks for logical grouping and error resilience:
- **Common Role**: Groups package installation with a rescue block that runs `apt-get update --fix-missing` on failure. An `always` block logs completion to `/tmp/common_setup.log`.
- **Docker Role**: Groups installation tasks with a rescue block that waits 10 seconds and retries on GPG key failures (common in network-constrained environments).
- **Web App Role**: Uses blocks for the deployment sequence, including directory creation, templating, and compose execution.

### Tag Strategy
A hierarchical tagging system was implemented:
- **Role-level**: `common`, `docker`, `web_app`
- **Block-level**: `packages`, `config`, `docker_install`, `docker_config`, `app_deploy`, `compose`, `web_app_wipe`

### Evidence: Tag Listing
```bash
$ ansible-playbook playbooks/provision.yml --list-tags

playbook: playbooks/provision.yml

  play #1 (webservers): Provision web servers	TAGS: []
      TASK TAGS: [common, config, docker, docker_config, docker_install, packages]
```

---

## 3. Docker Compose Migration

### Migration Details
The deployment was upgraded from `docker run` (via `community.docker.docker_container`) to `docker compose` (via `community.docker.docker_compose_v2`). This allows for:
1. **Declarative State**: Defining the entire environment in a single YAML file.
2. **Dependency Management**: Using `meta/main.yml` to ensure Docker is installed before the app.
3. **Reproducibility**: Identical environments across development and production.

### Templated Docker Compose
**File**: `ansible/roles/web_app/templates/docker-compose.yml.j2`
```yaml
services:
  {{ app_name }}:
    image: {{ docker_image }}:{{ docker_tag }}
    container_name: {{ app_name }}
    ports:
      - "{{ app_port }}:{{ app_internal_port }}"
    environment:
      PORT: "{{ app_internal_port }}"
      HOST: "0.0.0.0"
{% if app_env_vars is defined %}
{% for key, value in app_env_vars.items() %}
      {{ key }}: "{{ value }}"
{% endfor %}
{% endif %}
    restart: unless-stopped
    networks:
      - app_network

networks:
  app_network:
    driver: bridge
```

---

## 4. Wipe Logic

### Implementation
A safe cleanup mechanism was implemented in `roles/web_app/tasks/wipe.yml`. It uses **double-gating** for safety:
1. **Variable Gate**: `web_app_wipe` must be `true` (default is `false`).
2. **Tag Gate**: The task is tagged with `web_app_wipe`.

This prevents accidental deletion during normal deployments while allowing for clean reinstalls.

### Evidence: Wipe Logic Scenarios

1. **Scenario 1: Normal Deployment** (Wipe skipped)
   - Command: `ansible-playbook playbooks/deploy.yml`
   - Result: Wipe tasks show `skipping` because `web_app_wipe` is `false`.

2. **Scenario 2: Wipe Only** (App removed)
   - Command: `ansible-playbook playbooks/deploy.yml -e "web_app_wipe=true" --tags web_app_wipe`
   - Result: Containers stopped, files removed, deployment tasks skipped.

3. **Scenario 3: Clean Reinstall** (Wipe then Deploy)
   - Command: `ansible-playbook playbooks/deploy.yml -e "web_app_wipe=true"`
   - Result: Old app removed first, then fresh app deployed in one run.

4. **Scenario 4: Safety Check** (Blocked)
   - Command: `ansible-playbook playbooks/deploy.yml --tags web_app_wipe`
   - Result: Wipe tasks show `skipping` because the variable `web_app_wipe` was not passed.

---

## 5. CI/CD Integration

### Workflow Architecture
**File**: `.github/workflows/ansible-deploy.yml`
The pipeline consists of two stages:
1. **Lint**: Runs `ansible-lint` on all playbooks to ensure syntax and best practices.
2. **Deploy**: Triggered only on push to `master/main`. It sets up SSH, decrypts the Vault using `ANSIBLE_VAULT_PASSWORD` secret, and runs the deployment playbook.

### Verification Step
The workflow includes a post-deployment check:
```yaml
- name: Verify application deployment
  run: |
    curl -f http://${{ secrets.VM_HOST }}:5000 || exit 1
    curl -f http://${{ secrets.VM_HOST }}:5000/health || exit 1
```

---

## 6. Testing Results

### Idempotency Verification
The second run of the deployment playbook shows that no changes were made to the container state, proving idempotency.
```bash
$ ansible-playbook playbooks/deploy.yml
...
TASK [web_app : Deploy application with Docker Compose] ************************
ok: [devops-vm]
...
PLAY RECAP *********************************************************************
devops-vm : ok=19 changed=1 unreachable=0 failed=0 skipped=4 rescued=0 ignored=0
```

### Application Accessibility
```bash
$ curl -s http://192.168.56.10:5000/health | jq .
{
  "status": "healthy",
  "timestamp": "2026-03-04T08:06:12Z",
  "uptime_seconds": 45
}
```

### Selective Execution (Tags)
```bash
$ ansible-playbook playbooks/provision.yml --tags "packages"
...
TASK [common : Install common packages] ****************************************
ok: [devops-vm]
...
PLAY RECAP *********************************************************************
devops-vm : ok=4 changed=1 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0
```

---

## 7. Challenges & Solutions

- **Challenge**: Docker Compose indentation errors in Jinja2 templates.
  - **Solution**: Careful use of whitespace control in Jinja2 tags and verifying the generated file on the target VM using `cat -n`.
- **Challenge**: Decrypting Vault in CI/CD without exposing the password.
  - **Solution**: Storing the password in GitHub Secrets and writing it to a temporary file with restricted permissions (`600`) during the workflow execution, followed by secure deletion.
- **Challenge**: Accidental deletion of application data.
  - **Solution**: Implemented double-gating for the wipe logic, requiring both an explicit extra variable and a specific tag.

---

## 8. Research Answers

### Task 1: Blocks & Tags
- **Q: What happens if rescue block also fails?**
  - **A**: If the `rescue` block fails, the failure is treated as a normal task failure. The `always` block will still run, but the overall play will fail unless `ignore_errors: true` is set.
- **Q: Can you have nested blocks?**
  - **A**: Yes, Ansible supports nested blocks. You can have a `block` inside another `block`, `rescue`, or `always` section.
- **Q: How do tags inherit to tasks within blocks?**
  - **A**: Tags applied at the `block` level are inherited by all tasks within that block, including those in `rescue` and `always` sections.

### Task 2: Docker Compose
- **Q: Difference between `restart: always` and `restart: unless-stopped`?**
  - **A**: `restart: always` ensures the container starts when the Docker daemon starts or if the container exits, regardless of the exit code. `restart: unless-stopped` is similar but won't restart the container if it was manually stopped before the Docker daemon was stopped.
- **Q: How do Docker Compose networks differ from Docker bridge networks?**
  - **A**: Docker Compose creates a dedicated network for the project (by default a bridge network) and provides automatic service discovery via DNS using service names. Standard Docker bridge networks require manual linking or container IP management for communication.
- **Q: Can you reference Ansible Vault variables in the template?**
  - **A**: Yes, as long as the vault is decrypted (via `--vault-password-file` or similar), the variables are available to Jinja2 templates just like any other variable.

### Task 3: Wipe Logic
- **Q: Why use both variable AND tag?**
  - **A**: This "double-gating" provides maximum safety. The tag allows selective execution of just the wipe tasks, while the variable ensures that even if the tag is accidentally called, the destructive tasks won't run unless explicitly enabled.
- **Q: What's the difference between `never` tag and this approach?**
  - **A**: The `never` tag prevents a task from running unless specifically requested via `--tags`. Our approach allows for a "clean reinstall" (wipe then deploy) in a single run by just passing the variable, which wouldn't be as straightforward with the `never` tag.
- **Q: Why must wipe logic come BEFORE deployment?**
  - **A**: To support the "clean reinstall" scenario. By running wipe first, we ensure any existing (potentially corrupted or old) state is removed before the new version is provisioned.
- **Q: When would you want clean reinstallation vs. rolling update?**
  - **A**: Clean reinstallation is preferred when the application state is corrupted, when changing major architectural components (like database schemas or volume structures), or when testing from a "zero" state. Rolling updates are preferred for production to minimize downtime.
- **Q: How would you extend this to wipe Docker images and volumes too?**
  - **A**: You could add tasks to the `wipe.yml` file using the `community.docker.docker_image` module with `state: absent` and `community.docker.docker_volume` with `state: absent`.

### Task 4: CI/CD
- **Q: Security implications of storing SSH keys in GitHub Secrets?**
  - **A**: While encrypted at rest, the key is available in plain text during the workflow execution. If the workflow is compromised (e.g., via a malicious PR from a collaborator or a compromised action), the key could be exfiltrated. Using scoped deployment keys or OpenID Connect (OIDC) is more secure.
- **Q: How to implement a staging → production deployment pipeline?**
  - **A**: You can use GitHub Actions Environments with protection rules (like manual approvals). The workflow would deploy to staging first, run integration tests, and then wait for approval before deploying to production using a different inventory/secrets.
- **Q: What would you add to make rollbacks possible?**
  - **A**: To enable rollbacks, you could implement versioned deployments (e.g., using timestamps in directory names), keep a symlink to the "current" version, and have a `rollback` tag that points the symlink back to the previous successful directory.
- **Q: How does self-hosted runner improve security?**
  - **A**: A self-hosted runner can be placed inside a private VPC, allowing it to communicate with target servers over private IPs. This removes the need to expose SSH (port 22) to the public internet, which is required for GitHub-hosted runners.

