## Raspberry Pi 5 Running Hailo Model Webcam Streaming.


**Webcam Streaming** on a Raspberry Pi 5 with a Hailo AI chip using **YOLOv11 Nano** to detect objects and stream the results live to a web page via FastAPI routes.

**Webcam Streaming Demo**
![alt text](../Ressources/phone_video_demo.gif)


To use this application, please install the [DeGirum PySDK](https://github.com/DeGirum/hailo_examples/blob/main/README.md).

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
