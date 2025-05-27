// Helpers
const $ = s => document.querySelector(s);
const startBtn  = $('#startBtn');
const stopBtn   = $('#stopBtn');
const img       = $('#streamImg');

// Start streaming
startBtn.addEventListener('click', () => {
  img.src = '/video_feed?cb=';
  img.style.display = 'block';
  startBtn.disabled = true;
  stopBtn.disabled  = false;
});

// Stop streaming
stopBtn.addEventListener('click', () => {
  img.src = '';
  img.style.display = 'none';
  startBtn.disabled = false;
  stopBtn.disabled  = true;
});
