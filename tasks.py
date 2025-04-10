import subprocess
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os
import logging
logger = logging.getLogger(__name__)

EXECUTION_FLAGS = {
    "paused": False,
}

results = {}
error_info = None

def execute_shell(task, cwd = None):
    command = task['command']
    run_dir = cwd or None
    try:
        result = subprocess.run(command, shell=True, check=True,
                                capture_output=True, text=True, cwd=run_dir)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise Exception(f"Shell task failed: {e.stderr.strip()}")

def execute_rest(task, cwd=None):
    method  = task["method"].upper()
    url     = task["url"]
    headers = task.get("headers", {})
    body    = task.get("body", None)

    resp = requests.request(method, url, headers=headers, json=body)
    resp.raise_for_status()

    run_dir = cwd or os.getcwd()
    for name, spec in task.get("outputs", {}).items():
        if spec.get("type") == "json":
            path = os.path.join(run_dir, spec["json_path"])
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(resp.text)
    try:
        return resp.json()
    except ValueError:
        return resp.text

def execute_email(task):
    load_dotenv()
    sender_email = os.getenv("SENDER_EMAIL")
    password = os.getenv("APP_PASSWORD") 

    subject = task['subject']
    body = task['emailBody']

    for recipient in task['recipients']:
        receiver_email = recipient
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(sender_email, password)
                server.sendmail(sender_email, receiver_email, msg.as_string())
            return "Email sent successfully!"
        except Exception as e:
            logger.debug(f"Error sending email: {e}")

    raise NotImplementedError("Email task execution is not implemented yet.")

def execute_task(task, cwd=None):
    task_type = task['type']
    if task_type == "SHELL":
        return execute_shell(task, cwd)
    elif task_type == "RESTAPI":
        return execute_rest(task, cwd)
    elif task_type == "EMAIL":
        return execute_email(task)
    else:
        raise ValueError(f"Unsupported task type: {task_type}")
