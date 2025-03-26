## Raspberry Pi 5 Running Hailo Model with a FastAPI Server

To use this application, please install the [DeGirum PySDK](https://github.com/DeGirum/hailo_examples/blob/main/README.md).

## Screenshot of a Video Stream via WebSocket
![alt text](Ressources/Screenshot.png)

---

### Install Requirements

```bash
pip install fastapi uvicorn degirum degirum_tools
```

Make sure to also install the DeGirum SDK as described in their documentation.

---

### To Run the Server

1. Activate the virtual environment:

   ```bash
   source degirum_env/bin/activate
   ```

2. Start the FastAPI server:

   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

