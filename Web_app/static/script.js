// Get the canvas element from the HTML page
const canvas = document.getElementById("canvas");

// Get the 2D drawing context so we can draw on the canvas
const ctx = canvas.getContext("2d");

// Create a WebSocket connection to the server at /ws
const socket = new WebSocket("ws://" + location.host + "/ws");

// Set the WebSocket to receive binary data as Blob objects (images)
socket.binaryType = "blob";

// This function runs whenever a new message (video frame) is received from the WebSocket
socket.onmessage = async function(event) {
  // Convert the binary Blob data into an image bitmap (fast & efficient)
  const bitmap = await createImageBitmap(event.data);

  // Draw the image onto the canvas, filling the entire canvas area
  ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
};
