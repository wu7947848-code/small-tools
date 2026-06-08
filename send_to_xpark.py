"""Transfer file to xpark via base64 pipe."""
import paramiko
import base64
import os
import sys

HOST = '172.20.10.10'
USER = 'xfusion'
PASS = '123456'

def send_file(local_path, remote_path):
    """Send a file to remote server via base64 pipe."""
    # Read and encode file
    with open(local_path, 'rb') as f:
        data = base64.b64encode(f.read()).decode()

    # Connect
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, password=PASS, timeout=15)

    # Send in chunks (paramiko exec_command may have limits)
    chunk_size = 256 * 1024  # 256KB base64 per chunk
    total = len(data)
    sent = 0

    # Start with truncate
    c.exec_command(f'truncate -s 0 {remote_path}', timeout=10)

    while sent < total:
        chunk = data[sent:sent+chunk_size]
        sent += len(chunk)
        cmd = f"echo '{chunk}' >> {remote_path}"
        stdin, stdout, stderr = c.exec_command(cmd, timeout=30)
        stdout.channel.recv_exit_status()
        print(f"  Progress: {sent}/{total} ({100*sent//total}%)", end='\r')

    # Decode base64 to binary
    print("\nDecoding...")
    c.exec_command(f"base64 -d {remote_path} > {remote_path}.bin && mv {remote_path}.bin {remote_path}", timeout=30)
    c.close()
    print(f"Done: {local_path} -> {remote_path} ({total} base64 chars)")

def send_project(local_dir, remote_dir):
    """Pack local dir into tarball, send, extract on remote."""
    import subprocess
    tar_path = '/tmp/_send_project.tar.gz'
    print("Creating tarball...")
    subprocess.run(['tar', 'czf', tar_path, '-C', os.path.dirname(local_dir),
                    os.path.basename(local_dir)], check=True)

    remote_tar = os.path.join(remote_dir, '_project.tar.gz')
    print("Uploading...")
    send_file(tar_path, remote_tar)

    print("Extracting on remote...")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, password=PASS, timeout=15)
    c.exec_command(f'mkdir -p {remote_dir} && tar xzf {remote_tar} -C /tmp/_extract && cp -r /tmp/_extract/* {remote_dir}/ && rm -rf /tmp/_extract {remote_tar}', timeout=60)
    c.close()
    os.remove(tar_path)
    print("Done!")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python send.py <local> <remote_path>")
        sys.exit(1)
    send_file(sys.argv[2], sys.argv[3])
