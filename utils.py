import json
import hashlib
from collections import defaultdict, deque
from jsonpath_ng import parse
from graphviz import Digraph

def compute_hash(obj):
    normalized = json.dumps(obj, sort_keys=True).encode("utf‑8")
    return hashlib.sha256(normalized).hexdigest()

def build_dag(tasks):
    dag = defaultdict(list)
    indegree = {}
    nodes = {}

    for t in tasks:
        tid = t["id"]
        nodes[tid] = t
        indegree.setdefault(tid, 0)

    for t in tasks:
        tid = t["id"]
        for parent in t.get("depends_on", []):
            if parent not in nodes:
                raise ValueError(f"Task '{tid}' depends on unknown '{parent}'")
            dag[parent].append(tid)
            indegree[tid] = indegree.get(tid, 0) + 1

    return dag, indegree, nodes

def topological_sort(dag, indegree):
    q = deque([n for n,deg in indegree.items() if deg == 0])
    order = []
    while q:
        node = q.popleft()
        order.append(node)
        for child in dag.get(node, []):
            indegree[child] -= 1
            if indegree[child] == 0:
                q.append(child)
    if len(order) != len(indegree):
        raise RuntimeError("Cycle detected in workflow graph")
    return order

def resolve_input_mappings(task, results):
    import copy
    t = copy.deepcopy(task)
    for var, mapping in t.get("input_mappings", {}).items():
        parent = mapping["from_task"]
        output_key = mapping["output"]
        if parent not in results or output_key not in results[parent]:
            raise KeyError(f"Missing output '{output_key}' from task '{parent}'")
        value = results[parent][output_key]
        placeholder = f"{{{{{var}}}}}"
        for field in ("command", "url"):
            if field in t and isinstance(t[field], str):
                t[field] = t[field].replace(placeholder, str(value))
        if "headers" in t:
            for k,v in t["headers"].items():
                if isinstance(v, str):
                    t["headers"][k] = v.replace(placeholder, str(value))
        if "body" in t:
            body_str = json.dumps(t["body"])
            body_str = body_str.replace(placeholder, str(value))
            t["body"] = json.loads(body_str)
    return t

def extract_outputs(task, raw_output):
    outputs = {}
    for name, spec in task.get("outputs", {}).items():
        typ = spec.get("type")
        if typ == "json":
            expr = parse(spec["json_path"])
            matches = [m.value for m in expr.find(raw_output)]
            outputs[name] = matches[0] if matches else None
        elif typ == "file":
            outputs[name] = spec["path"]
        else:
            outputs[name] = raw_output
    return outputs

def dag_to_dot(dag, filename="workflow.dot", engine_name=None):
    dot = Digraph(comment=engine_name or "Workflow DAG", format="png")
    for node in dag:
        dot.node(node, node)
    for parent, children in dag.items():
        for child in children:
            dot.edge(parent, child)
    dot.save(filename)
    dot.render(filename, view=False)
    return filename + ".png"
