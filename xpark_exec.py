"""SSH client for xpark — run commands and transfer files."""
import paramiko
import sys
import os

HOST = '172.20.10.10'
USER = 'xfusion'
PASS = '123456'

def connect():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, password=PASS, timeout=15)
    return c

def run(cmd, timeout=30):
    """Execute command on xpark, return (stdout, stderr, exit_code)."""
    c = connect()
    try:
        stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode()
        err = stderr.read().decode()
        code = stdout.channel.recv_exit_status()
        return out, err, code
    finally:
        c.close()

def upload(local_path, remote_path):
    """Upload a file to xpark."""
    c = connect()
    try:
        sftp = c.open_sftp()
        sftp.put(local_path, remote_path)
        sftp.close()
        print(f"Uploaded: {local_path} -> {remote_path}")
    finally:
        c.close()

def upload_dir(local_dir, remote_dir):
    """Recursively upload a directory."""
    c = connect()
    try:
        sftp = c.open_sftp()
        # Create remote base dir
        try:
            sftp.mkdir(remote_dir)
        except (IOError, OSError):
            pass

        for root, dirs, files in os.walk(local_dir):
            rel_root = os.path.relpath(root, local_dir)
            remote_root = os.path.join(remote_dir, rel_root).replace('\\', '/')
            if rel_root == '.':
                remote_root = remote_dir

            for d in dirs:
                rdir = os.path.join(remote_root, d).replace('\\', '/')
                try:
                    sftp.mkdir(rdir)
                except (IOError, OSError):
                    pass

            for f in files:
                local = os.path.join(root, f)
                remote = os.path.join(remote_root, f).replace('\\', '/')
                try:
                    sftp.put(local, remote)
                except Exception as e:
                    print(f"  SKIP {f}: {e}")
        sftp.close()
        print(f"Uploaded directory: {local_dir} -> {remote_dir}")
    finally:
        c.close()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python xpark_exec.py [run <cmd> | upload <local> <remote> | upload-dir <local> <remote>]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == 'run':
        out, err, code = run(sys.argv[2])
        print(out)
        if err:
            print("STDERR:", err, file=sys.stderr)
        sys.exit(code)
    elif cmd == 'upload':
        upload(sys.argv[2], sys.argv[3])
    elif cmd == 'upload-dir':
        upload_dir(sys.argv[2], sys.argv[3])
