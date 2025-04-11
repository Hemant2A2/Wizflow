## For TESTING
1) Create virtual env in python
2) `pip install -r requirements.txt`
3) Setup redis database locally
4) Run `python main.py sample.json` to generate the DAG

## Running the websocket server:

1) Run `uvicorn ws_api:app --reload --host 0.0.0.0 --port 8000` to start the server.
2) Enter `tail -F logs/workflow.log` on a separte terminal ( the logs will appear here )
3) Run `python test_ws.py` again on a separte terminal to test any json file.
