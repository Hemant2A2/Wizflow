import subprocess
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os

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

def execute_email(task):
    load_dotenv()
    sender_email = os.getenv("SENDER_EMAIL")
    password = os.getenv("APP_PASSWORD") 

    subject = task['subject']
    body = task['body']

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
            print("Email sent successfully!")
        except Exception as e:
            print(f"Error sending email: {e}")

    raise NotImplementedError("Email task execution is not implemented yet.")

def execute_task(task):
    task_type = task['type']
    if task_type == "SHELL":
        return execute_shell(task)
    elif task_type == "RESTAPI":
        return execute_rest(task)
    elif task_type == "EMAIL":
        return execute_email(task)
    else:
        raise ValueError(f"Unsupported task type: {task_type}")
