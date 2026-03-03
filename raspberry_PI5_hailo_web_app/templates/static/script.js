// sources:
// https://github.com/PiWebswiss/raspberry_PI5_hailo/blob/web-app/WebSocket/main.py
// https://chatgpt.com/share/6838291d-cdf4-800e-af62-9ae145e8e58f
// https://chatgpt.com/share/68383000-066c-800e-8ae4-a21eb074307d


// Get reference to the canvas and its drawing context
const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");

// Declare socket variable (WebSocket will be initialized on start)
let socket = null;

// Helper function to easily select DOM elements
const $ = s => document.querySelector(s);
const startBtn = $('#startBtn');
const stopBtn = $('#stopBtn');
const personsNowEl = $('#personsNow');
const uniquePersonsEl = $('#uniquePersons');
const streamStatusEl = $('#streamStatus');

// Update the status text and optional color state in one place.
function setStatus(text, statusClass = '') {
  streamStatusEl.textContent = text;
  streamStatusEl.classList.remove('connected', 'error');
  if (statusClass) {
    streamStatusEl.classList.add(statusClass);
  }
}

// Apply server stats to the dashboard cards if fields are present.
function updateStats(payload) {
  if (typeof payload.persons_now === 'number') {
    personsNowEl.textContent = payload.persons_now;
  }
  if (typeof payload.unique_persons === 'number') {
    uniquePersonsEl.textContent = payload.unique_persons;
  }
}

// Reset displayed stats when stream is closed/stopped.
function resetStats() {
  personsNowEl.textContent = '0';
  uniquePersonsEl.textContent = '0';
}

// When the user clicks the Start button
startBtn.addEventListener('click', () => {
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
    return;
  }

  // Start each session with fresh counters.
  resetStats();

  // Open a WebSocket connection to the server
  socket = new WebSocket("ws://" + location.host + "/ws");
  // Binary messages from backend are JPEG frames.
  socket.binaryType = "blob";

  // When connection is successfully opened
  socket.onopen = () => {
    canvas.style.display = 'block'; // Show the canvas
    startBtn.disabled = true;       // Disable Start button
    stopBtn.disabled = false;       // Enable Stop button
    setStatus('Streaming', 'connected');
  };

  // Receive both JSON stats and binary image frames
  socket.onmessage = async function(event) {
    // Text messages carry stats payloads.
    if (typeof event.data === 'string') {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === 'stats') {
          updateStats(payload);
        }
      } catch {
        // Ignore malformed text messages.
      }
      return;
    }

    // Non-text message is a video frame blob.
    const bitmap = await createImageBitmap(event.data); // Decode image
    ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height); // Draw on canvas
  };

  // Keep all stop/reset UI logic centralized in one close handler.
  socket.onclose = () => {
    socket = null;
    canvas.style.display = 'none';
    startBtn.disabled = false;
    stopBtn.disabled = true;
    personsNowEl.textContent = '0';
    // Final unique count remains visible in the "UNIQUE PERSONS" card.
    setStatus('Stream stopped');
  };

  // If there's a WebSocket error safely stop the stream
  socket.onerror = () => {
    setStatus('Stream error', 'error');
  };
});

// When the user clicks the Stop button
stopBtn.addEventListener('click', () => {
  stopStream();
});

// Function to stop the video stream and reset UI
function stopStream() {
  if (socket) {
    // Graceful close triggers the backend loop to exit.
    socket.close();
  }
}
