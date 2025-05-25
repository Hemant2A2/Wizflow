# 🧠 Wizflow Backend – Nutanix Hackathon 2025 Submission

This is the **backend** service for **Wizflow**, our submission for the **Nutanix Hackathon 2025**. It is designed to receive a workflow definition in JSON format, generate an executable DAG, and execute tasks such as shell scripts or REST API calls. Real-time updates are pushed via WebSocket.

> 🔗 **[Frontend Repository](https://github.com/dis70rt/Wizflow)**  
> Refer to the frontend repo for the user interface and workflow builder.

---

## 💡 Features

- JSON-based dynamic workflow definitions
- Supports Shell scripts and REST API tasks
- Real-time logs via WebSocket
- Redis for task queuing and storage
- DAG generation engine with caching
- Modular and extensible Python architecture

---

## 📦 Relevant Packages

Some of the key dependencies used in this project:

| Package            | Purpose                                              |
|--------------------|------------------------------------------------------|
| **FastAPI**        | High-performance web framework for WebSocket & APIs |
| **Uvicorn**        | ASGI server to run FastAPI                          |
| **Websockets**     | WebSocket communication                             |
| **Redis**          | Task caching, queuing, and storage backend          |
| **Graphviz**       | DAG visualization and generation                    |
| **jsonpath-ng**    | Extract values from JSON payloads                   |
| **python-dotenv**  | Load env variables from `.env`                      |
| **cryptography**   | Encryption/decryption utilities                     |
| **aiohttp**        | Async HTTP client                                   |
| **requests**       | Synchronous HTTP client (for internal usage)        |
| **Pydantic v2**    | Data validation and parsing                         |
| **Starlette**      | ASGI toolkit used under FastAPI                     |

> Refer to `requirements.txt` or `Pipfile` for the full list of packages and versions.

---

## 📁 Project Structure

```plaintext
wizflow-backend/
├── logs/                     # Log outputs (workflow.log)
├── uploads/                  # Uploaded assets/files
├── venv/                     # Virtual environment
├── .env                      # Environment variables
├── .gitignore
├── app.py                    # FastAPI app entry
├── cache.py                  # Redis caching utilities
├── encrypt.py                # Optional encryption logic
├── engine.py                 # Workflow DAG generation logic
├── logging_config.py         # Logging configuration
├── main.py                   # Script to execute workflows from JSON
├── sample.json               # Sample workflow definition
├── shell.json                # Shell-specific task example
├── websocket.json            # WebSocket-compatible workflow
├── store.py                  # Redis store manager
├── tasks.py                  # Task executor logic (shell, http, etc.)
├── test_ws.py                # Test WebSocket communication
├── utils.py                  # Utility functions
├── ws_api.py                 # WebSocket server using FastAPI
├── workflow/                 # Workflow node/task definitions
├── workflow.png              # Visual reference for workflow
├── large.json                # Large-scale workflow demo
├── requirements.txt          # Python dependencies
├── Pipfile                   # Pipenv configuration
├── README.md
```

---

## 🧪 For Testing Locally

### 1. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up Redis Locally

Ensure Redis is running locally on the default port (6379).  
Install via:

```bash
# Ubuntu
sudo apt install redis

# Mac (Homebrew)
brew install redis
```

Then start it:

```bash
redis-server
```

### 4. Generate DAG From JSON

```bash
python main.py sample.json
```

This will read `sample.json`, generate the execution plan (DAG), and log events to `logs/workflow.log`.

---

## 🧬 Running the WebSocket Server

### 1. Start FastAPI WebSocket Server

```bash
uvicorn ws_api:app --reload --host 0.0.0.0 --port 8000
```

Server is now available at `ws://localhost:8000/ws`.

### 2. Monitor Logs

In a **separate terminal**, run:

```bash
tail -F logs/workflow.log
```

This will live-stream task execution logs.

### 3. Test a Workflow

In another **separate terminal**, run:

```bash
python test_ws.py
```

This sends a test JSON payload over WebSocket.

---

## 📄 License

MIT License

---
