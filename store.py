import redis
import json

r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

def publish_event(wf_id, payload):
    channel = f"wf:{wf_id}:events"
    r.publish(channel, json.dumps(payload))

def init_workflow(wf_id, task_ids):
    key_tasks = f"wf:{wf_id}:tasks"
    mapping = {tid: "PENDING" for tid in task_ids}
    r.hset(key_tasks, mapping=mapping)
    r.set(f"wf:{wf_id}:status", "PENDING")
    publish_event(wf_id, {"type": "workflow_update", "status": "PENDING"})
    for tid in task_ids:
        publish_event(wf_id, {"type": "task_update", "task_id": tid, "status": "PENDING"})

def set_task_status(wf_id, task_id, status):
    r.hset(f"wf:{wf_id}:tasks", task_id, status)
    publish_event(wf_id, {
        "type": "task_update",
        "task_id": task_id,
        "status": status
    })

def get_task_status(wf_id):
    return r.hgetall(f"wf:{wf_id}:tasks")

def set_workflow_status(wf_id, status):
    r.set(f"wf:{wf_id}:status", status)
    publish_event(wf_id, {
        "type": "workflow_update",
        "status": status
    })

def get_workflow_status(wf_id):
    return r.get(f"wf:{wf_id}:status")
