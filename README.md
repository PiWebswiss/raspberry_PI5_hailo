<h3 style="color: red;">🚧 Disclaimer: Working branche. Please do not use the code yet.</h3>

**note:**

   ```bash
   source ../../degirum_env/bin/activat
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

## Raspberry Pi 5 Running Hailo Model with a FastAPI Server 

I’m using a Raspberry Pi 5 with a Hailo AI chip to detect objects in a video and stream the results live to a web page. All processing is done locally on the device using a Raspberry Pi 5 with the Hailo8L AI accelerator

I've build a user-friendly, real-time video loop web application called **`Web_app`**, which performs object detection using a Hailo model on a Raspberry Pi 5.

I load all model, compiled for the Hailo-8L accelerator, using the [DeGirum SDK](https://github.com/DeGirum/hailo_examples).

If you find a mistake, feel free to drop a comment or open an issue on GitHub. Thanks!


## Video demonstration ``Wep_app``:

**In brief:**  
The browser capture camera frames and streams them to the server using WebRTC. The server runs object detection and streams the annotated video back to the user.

![alt text](Ressources/demo_web_app.gif)


## Demo 1 using Hailo Yolo11 nano model
![alt text](Ressources/demo-1.gif)

## Demo 2 using Hailo Yolo8 nano model
![alt text](Ressources/demo-2.gif)


## **Repository Structure**

The `HTTP` directory contains the **HTTP Streaming**: Streams the processed video frames to clients using the MJPEG format via FastAPI routes.

The `WebSocket` directory contains the **WebSocket Streaming**: Streams that processed video frames to clients using the WebSocket via FastAPI routes.

The `Webcam` directory contains the **Webcam Streaming**: Streams that processed video frames to clients using WebSocket via FastAPI routes.

The `Wep_app` directory contains **user-friendly, real-time video loop web application**


## **Functionality Overview**

1. **Initialize the AI Model**:  
   - Load the YOLOv8n/YOLOv11n Hailo model tailored for the Hailo8L device using the [DeGirum SDK](https://github.com/DeGirum/hailo_examples).  
   - Configure the model with appropriate parameters such as inference host address and device types using the [DeGirum SDK](https://github.com/DeGirum/hailo_examples).

2. **Process Video Input**:  
   - Open a video file or stream as the input source.  
   - Read frames sequentially, perform object detection inference on each frame, and overlay the detection results on **bounding boxes and labels** using [DeGirum SDK](https://github.com/DeGirum/hailo_examples).

3. **Stream Processed Video**:  
   - Serve the processed frames over HTTP or WebSocket using FastAPI.  
   - Implement an endpoint in order to view the real-time video stream with inference results.

   
## **Setting Up and Running the Application**

To set up and run the application:


1. **Install DeGirum SDK**:
   - Do the guided installation for [DeGirum SDK](https://github.com/DeGirum/hailo_examples).


2. **Activate the virtual environment**:
   ```bash
   source degirum_env/bin/activate
   ```

3. **Install requirements dependencies**
   ```bash
   pip install fastapi uvicorn degirum degirum_tools
   ```

4. **Clone my repo**:
   ```bash
   git clone https://github.com/PiWebswiss/raspberry_PI5_hailo.git
   cd raspberry_PI5_hailo
   ```

   >Then, go to the file directory `Webcam` ,``WebSocket`` or ``HTTP`` using ``cd <path>``.

5. **Run the FastAPI Server**:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

6. **Access the Video Stream**:
   - Open a web browser and navigate to `http://127.0.0.1:8001/` to view the AI-processed video stream.

## **Additional Notes**

- **Hardware Requirements**:  
  - A Raspberry Pi 5 with the Hailo8L AI accelerator.


