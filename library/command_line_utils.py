import subprocess


def bash_cmd(cmd):
    result = subprocess.run(cmd, shell=True, check=True, text=True, capture_output=True)
    return result.stdout.strip()
