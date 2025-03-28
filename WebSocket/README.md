## Raspberry Pi 5 Running Hailo Model with a FastAPI Server over WebSocket.

I'm using a Raspberry Pi 5 with a Hailo AI chip to detect objects in a video and stream the results live to a web page using **WebSocket Streaming** via FastAPI routes.

To use this application, please install the [DeGirum PySDK](https://github.com/DeGirum/hailo_examples/blob/main/README.md).

## Screenshot of a Video Stream via WebSocket
![alt text](../Ressources/Screenshot-FPS.png)

---

### Install Requirements

```bash
pip install fastapi uvicorn degirum degirum_tools
```

Make sure to also install the [DeGirum SDK](https://github.com/DeGirum/hailo_examples) as described in their documentation.

---

### To Run the Server

1. **Activate the ``degirum_env`` virtual environment**:

   ```bash
   source degirum_env/bin/activate
   ```

2. **Start the FastAPI server**:

   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

3. **Access Video Stream**:
   - Open a web browser and navigate to `http://127.0.0.1:8001/`view the AI-processed video stream.
