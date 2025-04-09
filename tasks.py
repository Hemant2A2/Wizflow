import subprocess
import requests

EXECUTION_FLAGS = {
    "paused": False,
}

results = {}
error_info = None

def execute_shell(task):
    command = task['command']
    try:
        result = subprocess.run(command, shell=True, check=True,
                                capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise Exception(f"Shell task failed: {e.stderr.strip()}")

def execute_rest(task):
    method = task['method'].upper()
    url = task['url']
    headers = task.get('headers', {})
    body = task.get('body', {})
    try:
        response = requests.request(method, url, headers=headers, json=body)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise Exception(f"REST task failed: {str(e)}")

def execute_task(task):
    task_type = task['type']
    if task_type == "SHELL":
        return execute_shell(task)
    elif task_type == "RESTAPI":
        return execute_rest(task)
    else:
        raise ValueError(f"Unsupported task type: {task_type}")
