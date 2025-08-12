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

// When the user clicks the Start button
startBtn.addEventListener('click', () => {
  // Open a WebSocket connection to the server
  socket = new WebSocket("ws://" + location.host + "/ws");
  socket.binaryType = "blob"; // Expect binary data (images) from server

  // When connection is successfully opened
  socket.onopen = () => {
    canvas.style.display = 'block'; // Show the canvas
    startBtn.disabled = true;       // Disable Start button
    stopBtn.disabled = false;       // Enable Stop button
  };

  // When an image blob is received from the server
  socket.onmessage = async function(event) {
    const bitmap = await createImageBitmap(event.data); // Decode image
    ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height); // Draw on canvas
  };

  // If there's a WebSocket error safely stop the stream
  socket.onerror = () => {
    stopStream();
  };
});

// When the user clicks the Stop button
stopBtn.addEventListener('click', () => {
  stopStream();
});

// Function to stop the video stream and reset UI
function stopStream() {
  if (socket) {
    socket.close();  // This triggers WebSocketDisconnect on the server
    socket = null;   // Clear socket reference
  }
  canvas.style.display = 'none'; // Hide the canvas
  startBtn.disabled = false;     // Re-enable Start button
  stopBtn.disabled = true;       // Disable Stop button
}


