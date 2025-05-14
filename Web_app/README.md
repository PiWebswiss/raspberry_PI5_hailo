# Web App

I'm building a user-friendly, real-time video loop web application called **`Web_app`**, which performs object detection using a Hailo model on a Raspberry Pi 5.

I load all models, compiled for the Hailo-8L accelerator, using the [DeGirum SDK](https://github.com/DeGirum/hailo_examples).

**In brief:**  
The browser capture camera frames and streams them to the server using WebRTC. The server runs object detection and streams the annotated video back to the user.

**Video demonstration:**
![alt text](../Ressources/demo_web_app.gif)

---

**Install DeGirum SDK**:
   - Do the guided installation for [DeGirum SDK](https://github.com/DeGirum/hailo_examples).

**Activate the virtual environment**:
Make sure to activate ``degirum_env``
   ```bash
   source degirum_env/bin/activate
   ```

Install **WebRTC-based**:
```bash
pip install aiortc
```
Install **python-multipart**:

This is used to uploaded files sent by the user browser. 
```bash
pip install python-multipart
```

> Make sure that you have ``ffmpeg`` installed system-wide

**Check that you have ``ffmpeg``**

```bash
ffmpeg -version`
```
**if not installed then run:** 

```bash
sudo apt update
sudo apt install ffmpeg
```

Then, go to the file directory ``Web_app`` using ``cd <path>``.

**Run the FastAPI Server**:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

**Access the Video Stream**:
   - Open a web browser and navigate to `http://127.0.0.1:8001/`.
