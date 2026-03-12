#!/usr/bin/env python3
"""Fetch recent Celery worker logs from the cloud."""
import os
import paramiko

HOST = os.getenv("AIHR_SERVER_HOST", "")
KEY_FILE = os.getenv("AIHR_SSH_KEY", os.path.expanduser("~/.ssh/id_rsa_linode"))

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username="root", key_filename=KEY_FILE, timeout=30)

stdin, stdout, stderr = ssh.exec_command("docker logs aihr-worker --tail=200", timeout=30)
print(stdout.read().decode())
err = stderr.read().decode().strip()
if err:
    print(err)

ssh.close()

