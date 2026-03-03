# Modified code from https://github.com/PiWebswiss/raspberry_PI5_hailo/blob/web-app/WebSocket/main.py
import time
import cv2
import degirum as dg
from pathlib import Path
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.websockets import WebSocketState
import asyncio
import json
import math


# Load Hailo model
model = dg.load_model(
    model_name="yolo11n_coco--640x640_quant_hailort_multidevice_1", 
    inference_host_address="@local",
    zoo_url="degirum/hailo", 
    token="",
    device_type="HAILORT/HAILO8L",
)

# FastAPI setup
# Help : https://chatgpt.com/c/683ebaec-e754-800e-b3db-77546297fbce
BASE_DIR = Path(__file__).resolve().parent
app = FastAPI()
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "templates" / "static")),
    name="static",
)

PERSON_LABEL = "person"
MIN_PERSON_SCORE = 0.30
MAX_MATCH_DISTANCE_PX = 90
MAX_TRACK_MISSES = 45


def _parse_detections(inf_result):
    """Return inference detections as a list of dicts."""
    # Depending on postprocessor configuration, results can be a list or a JSON string.
    detections = getattr(inf_result, "results", [])
    if isinstance(detections, str):
        try:
            # Convert JSON text to Python list so downstream code is consistent.
            detections = json.loads(detections)
        except json.JSONDecodeError:
            # Fail safe: malformed payload means no detections for this frame.
            return []
    if not isinstance(detections, list):
        # Any unsupported format is treated as empty detections.
        return []
    return detections


def _extract_person_centers(inf_result):
    """Extract center points for `person` detections from inference results."""
    person_centers = []
    for det in _parse_detections(inf_result):
        if not isinstance(det, dict):
            continue

        # Normalize label text to avoid case/spacing mismatches.
        label = str(det.get("label", "")).strip().lower()
        score = float(det.get("score", 0.0))
        bbox = det.get("bbox")
        # Keep only confident person detections.
        if label != PERSON_LABEL or score < MIN_PERSON_SCORE:
            continue
        # Expected bbox format: [x1, y1, x2, y2].
        if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            continue

        try:
            x1, y1, x2, y2 = [float(v) for v in bbox]
        except (TypeError, ValueError):
            continue

        # Use bbox center as a lightweight tracking point for this person.
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        person_centers.append((cx, cy))
    return person_centers

# Routes for index page
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})



# WebSocket endpoint for real-time video streaming
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Initialize camera
    cap = cv2.VideoCapture(0)

    # Check that the camera is accessible
    # Code from : https://chatgpt.com/share/683867a8-db8c-800e-ae13-1b2fcdfee4ee
    if not cap.isOpened():
        print("⚠️  No camera detected!")
        # Reject WebSocket with proper close code
        await websocket.close(code=1003)  # 1003 = unsupported data 
        return

    # Set camera resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    prev_frame_time = time.time()
    # `tracks` stores active person tracks: {track_id: {"center": (x, y), "misses": n}}.
    tracks = {}
    # Monotonic counter used to assign unique IDs to newly seen people.
    next_track_id = 0
    # Track IDs already counted at least once in the unique counter.
    counted_track_ids = set()
    unique_person_count = 0

    print("✅  Camera initialized, starting stream...")

    # Accept the WebSocket connection
    await websocket.accept()

    try:
        while True:
            # Read a frame from the camera in a background thread
            # Code from: https://chatgpt.com/share/683867a8-db8c-800e-ae13-1b2fcdfee4ee
            # off-load the heavy work, keep the server responsive, get the result when it’s ready
            ret, frame = await asyncio.to_thread(cap.read)
            if not ret:
                break  # Stop if the camera failed

            # Run inference on the frame (also off the main async thread)
            # off-load the heavy work, keep the server responsive, get the result when it’s ready
            inf = await asyncio.to_thread(model, frame)
            frm = inf.image_overlay

            # Keep track IDs stable across frames to avoid counting the same person repeatedly.
            person_centers = _extract_person_centers(inf)
            # Start by assuming all existing tracks are unmatched this frame.
            unmatched_track_ids = set(tracks.keys())
            # Track IDs visible in this frame (used for "Persons now").
            visible_track_ids = set()

            for center in person_centers:
                # Find the nearest existing track within distance threshold.
                best_track_id = None
                best_distance = float("inf")
                for track_id in unmatched_track_ids:
                    track_center = tracks[track_id]["center"]
                    distance = math.dist(center, track_center)
                    if distance < best_distance and distance <= MAX_MATCH_DISTANCE_PX:
                        best_track_id = track_id
                        best_distance = distance

                if best_track_id is None:
                    # No nearby track: create a new person track.
                    best_track_id = next_track_id
                    next_track_id += 1
                    tracks[best_track_id] = {"center": center, "misses": 0}
                else:
                    # Existing track matched: update its latest center and reset miss counter.
                    tracks[best_track_id]["center"] = center
                    tracks[best_track_id]["misses"] = 0
                    unmatched_track_ids.remove(best_track_id)

                visible_track_ids.add(best_track_id)
                # Increment unique count only once per track ID.
                if best_track_id not in counted_track_ids:
                    counted_track_ids.add(best_track_id)
                    unique_person_count += 1

            for track_id in list(unmatched_track_ids):
                # Tracks not seen this frame get a miss penalty.
                tracks[track_id]["misses"] += 1
                if tracks[track_id]["misses"] > MAX_TRACK_MISSES:
                    # Drop stale tracks to keep memory bounded and avoid wrong re-associations.
                    del tracks[track_id]

            # Draw FPS on the frame.
            now = time.time()
            fps = 1 / max(now - prev_frame_time, 1e-6)
            prev_frame_time = now
            cv2.putText(
                frm, f"FPS: {fps:.0f}", (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA
            )

            # Frontend-readable stats sent as JSON text in the same WebSocket stream.
            stats_payload = {
                "type": "stats",
                "persons_now": len(visible_track_ids),
                "unique_persons": unique_person_count,
            }

            # Code from: https://chatgpt.com/share/68383000-066c-800e-8ae4-a21eb074307d
            # Encode the annotated frame as JPEG
            success, jpg = cv2.imencode('.jpg', frm)
            if not success:
                continue  # Skip this frame if encoding fails

            # Try to send the JPEG over WebSocket
            # Code from: https://chatgpt.com/share/68383000-066c-800e-8ae4-a21eb074307d
            try:
                # Send stats first (text), then the annotated frame (binary JPEG).
                await websocket.send_text(json.dumps(stats_payload))
                await websocket.send_bytes(jpg.tobytes())
            except Exception:
                # If the client disconnected or network error → exit loop
                print("⚠️  Streaming stopped")
                break

    finally:
        # Always release the camera
        cap.release()

        # Gracefully close the WebSocket if it's still open
        if websocket.application_state == WebSocketState.CONNECTED:
            await websocket.close()
