# Mac Mini M4 Production Server - SSH Access & Security Hardening

This document contains the complete protocol for securing SSH access to the Mac Mini M4 production server and ensuring proper container isolation.

## Overview

With the Mac Mini M4 fully available for production, securing access is the top priority. This guide covers:

1. **SSH Hardening** - Securing the front door (SSH connection)
2. **Container Isolation** - Ensuring internal services (MongoDB/Redis) are completely hidden

---

## Part 1: SSH Hardening (The Front Door)

You must disable insecure password login and switch entirely to **SSH Keys**. This ensures that even if a hacker guesses your macOS password, they cannot log into the server remotely.

### Step 1: Generate SSH Keys (On MacBook Pro)

Use the secure Ed25519 algorithm:

```bash
ssh-keygen -t ed25519 -C "indigo_litecoin_prod"
```

**Important:** When prompted, **set a strong passphrase** for your private key. This key is your ultimate master key.

### Step 2: Copy Public Key to M4 Mini

Since you have physical access, the easiest way to add your key is:

```bash
# Run this on your MacBook Pro, replacing 'username' with your Mac Mini's username
ssh-copy-id -i ~/.ssh/id_ed25519.pub username@<Mac_Mini_Local_IP>
```

*It will ask for your Mac Mini password one last time.*

### Step 3: Disable Password Login (CRITICAL STEP)

On the **M4 Mac Mini**, edit the SSH daemon configuration file. This stops the server from accepting passwords.

```bash
# Use nano or vi to edit the configuration file
sudo nano /etc/ssh/sshd_config
```

Find and change (or add/uncomment) these three lines:

```
# Find these lines and ensure they are set to 'no'
PasswordAuthentication no
ChallengeResponseAuthentication no
UsePAM no
```

**Note:** Setting `UsePAM no` is often necessary on macOS to ensure password login is fully disabled.

### Step 4: Restart the SSH Service

Apply the changes by restarting the service:

```bash
sudo launchctl stop com.openssh.sshd
sudo launchctl start com.openssh.sshd
```

**TEST IMMEDIATELY:** 
- Try to log in from your MacBook Pro using only the password (it should fail)
- Then try with your key (it should succeed)

---

## Part 2: Container Isolation (The Backend Vault)

Docker Compose automatically creates a secure, isolated **Bridge Network** for all your services (`backend`, `mongodb`, `redis`). This is a huge win for security.

### Service Security Status

| Service | Goal | Status in YAML | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **Backend (FastAPI)** | Must be publicly accessible. | Mapped to host via `ports: "8000:8000"` (or Cloudflare). | **Status Quo.** This is necessary for the Chatbot UI. |
| **MongoDB** | Must be hidden from the host/internet. | No explicit `ports:` mapping in YAML. | **Security Confirmed.** MongoDB is only reachable by the service name `mongodb` *inside* the Docker network. |
| **Redis** | Must be hidden from the host/internet. | No explicit `ports:` mapping in YAML. | **Security Confirmed.** Redis is only reachable by the service name `redis` *inside* the Docker network. |
| **Grafana/Prometheus** | Only accessible by you. | `ports: "127.0.0.1:9090:9090"` (Prometheus) and `ports: "127.0.0.1:3002:3000"` (Grafana). | **Security Confirmed.** By binding the ports to `127.0.0.1` (localhost), they are accessible only from the Mac Mini itself or via a secure SSH Tunnel. They are hidden from the public internet. |

### Action Item: Confirm Backend Connection Strings

Make sure the FastAPI backend is connecting to the databases using the **service names**, not `localhost` or an external IP.

In your `backend/.env`, your connection URI should look like this for the containers:

```env
MONGO_URI=mongodb://mongodb:27017/litecoin_rag_db
REDIS_HOST=redis
```

**Note:** If you are using MongoDB Atlas, your `MONGO_URI` will point to the public cloud connection string, which is fine, but you should ensure your Redis/other internal caches use the internal service names.

---

## Quick Reference: SSH Connection

Once configured, connect to the Mac Mini from your MacBook Pro using:

```bash
ssh -i ~/.ssh/id_ed25519 username@<Mac_Mini_Local_IP>
```

Or configure your `~/.ssh/config` for easier access:

```
Host mac-mini-prod
    HostName <Mac_Mini_Local_IP>
    User <username>
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
```

Then simply use:
```bash
ssh mac-mini-prod
```

---

## Security Checklist

- [ ] SSH keys generated with Ed25519 algorithm
- [ ] Public key copied to Mac Mini
- [ ] Password authentication disabled in `/etc/ssh/sshd_config`
- [ ] SSH service restarted
- [ ] Password login test failed (as expected)
- [ ] SSH key login test succeeded
- [ ] Backend connection strings verified (using service names, not localhost)
- [ ] MongoDB and Redis ports not exposed to host
- [ ] Grafana/Prometheus bound to localhost only

---

## Architecture Summary

This architecture is robust. You've protected the internal data sources and hardened the external access point. The Docker bridge network provides automatic isolation, and SSH key-only access ensures that even if your macOS password is compromised, remote access remains secure.

