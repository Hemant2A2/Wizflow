import redis
import json

r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

def load_task_cache(wf_key: str, task_id: str):
    key = f"{wf_key}:cache:{task_id}"
    data = r.get(key)
    if not data:
        return None
    obj = json.loads(data)
    return obj["outputs"], obj["config_hash"]

def save_task_cache(wf_key: str, task_id: str, outputs: dict, config_hash: str):
    key = f"{wf_key}:cache:{task_id}"
    payload = json.dumps({"outputs": outputs, "config_hash": config_hash})
    r.set(key, payload)
