# A complete solution for the Traveling Salesman Problem using the Branch and Bound algorithm with enhanced authentication and user management.
### The solution follows a client-server model:

### The FastAPI server ([main.py](main.py)) handles all logic: user authentication, TSP calculations using the Branch and Bound algorithm, and data persistence. The console client ([client.py](client.py)) provides an interactive command-line interface for user interaction, sending requests to the server and displaying results.

### Quick Start:

  1. Launch server:
     ```python
     client:uvicorn main:app --reload
  2. Launch client:
     ```python
     python client.py
### Requirements:

  1. Python 3+
  2. FastAPI
  3. Pydantic
  4. Requests

### Requirements installation:
     ```python
     pip install fastapi uvicorn pydantic requests
