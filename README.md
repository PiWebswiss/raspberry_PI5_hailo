## Raspberry Pi 5 Running Hailo Model with a FastAPI Server 

 I’m using a Raspberry Pi 5 with a Hailo AI chip to detect objects in a video and stream the results live to a web page. All processing is done locally on the device using a Raspberry Pi 5 with the Hailo8L AI accelerator

I'm still in development, so the HTML UI is not finished yet. I’ve only set it up for quick prototyping.

I'm still testing whether WebSocket is faster than HTTP with the MJPEG format.

## Screenshot of a Video Stream via WebSocket
![alt text](Ressources/Screenshot.png)

I load the YOLOv8 model tailored for the Hailo8L device using the [DeGirum SDK](https://github.com/DeGirum/hailo_examples).

## Demo 1 using Hailo Yolo8 nano model
![alt text](Ressources/demo-1.gif)

## Demo 2 using Hailo Yolo11 nano model
![alt text](Ressources/demo-2.gif)


## **Repository Structure**

The `HTTP` directory contains the **HTTP Streaming**: Streams the processed video frames to clients using the MJPEG format via FastAPI routes.


The `WebSocket` directory contains the **WebSocket Streaming**: Streams that processed video frames to clients using the WebSocket via FastAPI routes.


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

2. **Clone my repo**:
   ```bash
   git clone https://github.com/PiWebswiss/raspberry_PI5_hailo.git
   ```

2. **Activate the virtual environment**:
   ```bash
   source degirum_env/bin/activate
   ```
   Then, go to the file directory ``WebSocket`` or ``HTTP`` using ``cd <path>``.

2. **Run the FastAPI Server**:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

3. **Access the Video Stream**:
   - Open a web browser and navigate to `http://127.0.0.1:8001/` to view the AI-processed video stream.

## **Additional Notes**

- **Hardware Requirements**:  
  - A Raspberry Pi 5 with the Hailo8L AI accelerator.


