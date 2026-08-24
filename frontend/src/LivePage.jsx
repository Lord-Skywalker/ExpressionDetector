import { useState, useEffect, useRef } from 'react';
import { detectLiveEmotion, checkMLWorkerStatus } from './api';

const EMOTION_COLORS = {
  happy:    '#68d391',
  neutral:  '#63b3ed',
  sad:      '#9f7aea',
  angry:    '#fc8181',
  fear:     '#f6ad55',
  surprise: '#4fd1c7',
  disgust:  '#f6e05e',
};

export default function LivePage() {
  const [active, setActive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [faces, setFaces] = useState([]);
  const [fps, setFps] = useState(0);
  const [backendState, setBackendState] = useState('Checking...');
  const [intervalMs, setIntervalMs] = useState(400); // 400ms interval defaults to ~2.5 FPS

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const loopRef = useRef(null);
  const lastTimeRef = useRef(Date.now());

  // Capture canvas is off-screen/hidden to capture frames at 640x480 for fast API transport
  const captureCanvasRef = useRef(null);

  // Set srcObject on video when mounted and start playback explicitly
  useEffect(() => {
    if (active && videoRef.current && streamRef.current) {
      const video = videoRef.current;
      video.srcObject = streamRef.current;
      video.play().catch(err => {
        console.error("Failed to start video playback:", err);
      });
    }
  }, [active]);

  // Ping backend status periodically
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const res = await checkMLWorkerStatus();
        if (res.status === 'ok') setBackendState('Online');
      } catch (err) {
        setBackendState('Waking Up (Takes ~10s)');
      }
    };
    checkStatus();
    const interval = setInterval(checkStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  // Starts webcam stream
  const startCamera = async () => {
    try {
      setLoading(true);
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: 'user' },
        audio: false
      });
      streamRef.current = stream;
      setActive(true);
      setLoading(false);
    } catch (err) {
      console.error("Camera access error:", err);
      alert("Failed to access webcam. Please check permissions.");
      setLoading(false);
    }
  };

  // Stops webcam stream
  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    if (loopRef.current) {
      clearTimeout(loopRef.current);
      loopRef.current = null;
    }
    setActive(false);
    setFaces([]);
    setFps(0);
    // Clear canvas overlay
    const canvas = canvasRef.current;
    if (canvas) {
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
  };

  // Triggers stop on unmount
  useEffect(() => {
    return () => stopCamera();
  }, []);

  // Frame detection loop
  useEffect(() => {
    if (!active) return;

    const processFrame = async () => {
      const video = videoRef.current;
      const captureCanvas = captureCanvasRef.current;
      
      if (!video || !captureCanvas || video.readyState < 2 || video.videoWidth === 0) {
        // Wait and schedule again if video data isn't ready
        loopRef.current = setTimeout(processFrame, intervalMs);
        return;
      }

      // Draw frame to hidden capture canvas at standard 640x480 resolution
      const ctxCapture = captureCanvas.getContext('2d');
      ctxCapture.drawImage(video, 0, 0, 640, 480);
      const dataUrl = captureCanvas.toDataURL('image/jpeg', 0.6); // compressed JPEG for speed

      try {
        const res = await detectLiveEmotion({ image: dataUrl });
        const detectedFaces = res.data.faces || [];
        setFaces(detectedFaces);

        // Update FPS counter
        const now = Date.now();
        const delta = now - lastTimeRef.current;
        lastTimeRef.current = now;
        setFps(Math.round(1000 / delta));

        // Draw bounding boxes on the overlay canvas
        drawOverlay(detectedFaces);
      } catch (err) {
        console.error("Inference request error:", err);
      }

      // Schedule next frame process
      loopRef.current = setTimeout(processFrame, intervalMs);
    };

    loopRef.current = setTimeout(processFrame, intervalMs);

    return () => {
      if (loopRef.current) {
        clearTimeout(loopRef.current);
      }
    };
  }, [active, intervalMs]);

  // Adjust canvas size to match the visible video layout size
  const drawOverlay = (detectedFaces) => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    // Set canvas dimensions matching current element client dimensions
    const width = video.clientWidth;
    const height = video.clientHeight;
    
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }

    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, width, height);

    // Compute scale coordinates (API works on 640x480)
    const scaleX = width / 640;
    const scaleY = height / 480;

    detectedFaces.forEach(f => {
      const [x, y, w, h] = f.box;
      const color = EMOTION_COLORS[f.emotion] || '#a855f7';

      // Draw bounding box
      ctx.strokeStyle = color;
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.roundRect(x * scaleX, y * scaleY, w * scaleX, h * scaleY, 6);
      ctx.stroke();

      // Draw label background banner
      ctx.fillStyle = color;
      const labelText = `${f.emotion.toUpperCase()} (${Math.round(f.score)}%)`;
      ctx.font = 'bold 11px JetBrains Mono, Inter, sans-serif';
      const textWidth = ctx.measureText(labelText).width;

      ctx.beginPath();
      ctx.roundRect(x * scaleX - 1.5, y * scaleY - 20, textWidth + 14, 20, [4, 4, 0, 0]);
      ctx.fill();

      // Draw label text
      ctx.fillStyle = '#0a0b10';
      ctx.fillText(labelText, x * scaleX + 7, y * scaleY - 6);
    });
  };

  // Derived statistics
  const totalFaces = faces.length;
  const dominantEmotion = faces.length 
    ? faces.reduce((acc, f) => {
        acc[f.emotion] = (acc[f.emotion] || 0) + 1;
        return acc;
      }, {})
    : null;

  const sceneEmotion = dominantEmotion
    ? Object.keys(dominantEmotion).reduce((a, b) => dominantEmotion[a] > dominantEmotion[b] ? a : b)
    : '—';

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 className="page-title">Live Cam Feed</h1>
          <p className="page-subtitle">Real-time audience facial emotion classification using ViT Model.</p>
        </div>
        <div>
          <span className={`badge`} style={{ fontSize: 12, padding: '6px 12px', marginRight: 12, background: backendState === 'Online' ? '#10b98122' : '#f59e0b22', color: backendState === 'Online' ? '#10b981' : '#f59e0b', border: '1px solid currentColor' }}>
            {backendState === 'Online' ? '🟢 Backend Online' : `🟡 Backend: ${backendState}`}
          </span>
          <span className={`badge ${active ? 'badge-success' : 'badge-danger'}`} style={{ fontSize: 12, padding: '6px 12px' }}>
            {active ? '● Live Active' : 'Camera Inactive'}
          </span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 24 }}>
        
        {/* Left: Video / Canvas Card */}
        <div className="card" style={{ padding: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column', minHeight: 460 }}>
          <div style={{ padding: '16px 24px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="card-title">Live Video Session</span>
            {active && (
              <span className="mono" style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                API Rate: {fps} FPS · Processing Speed: {intervalMs}ms
              </span>
            )}
          </div>
          
          <div style={{ flexGrow: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#07080c', position: 'relative' }}>
            {!active ? (
              <div style={{ textAlign: 'center', padding: 40 }}>
                <div style={{ fontSize: 48, marginBottom: 16 }}>📹</div>
                <h3 style={{ marginBottom: 8 }}>Camera Connection Inactive</h3>
                <p style={{ maxWidth: 360, margin: '0 auto 20px', fontSize: 13 }}>
                  Enable your webcam to start real-time emotion detection. Model classification runs automatically in backend.
                </p>
                <button className="btn btn-primary" onClick={startCamera} disabled={loading}>
                  {loading ? 'Starting cam...' : 'Start Webcam Stream'}
                </button>
              </div>
            ) : (
              <div style={{ position: 'relative', width: '100%', maxWidth: 640, height: '100%', display: 'flex', alignItems: 'center' }}>
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  style={{ width: '100%', height: 'auto', display: 'block', borderRadius: '0 0 var(--radius) var(--radius)' }}
                />
                <canvas
                  ref={canvasRef}
                  style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none' }}
                />
              </div>
            )}
          </div>
        </div>

        {/* Right: Controls & Live Stats Panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          
          {/* Controls Card */}
          <div className="card">
            <div className="card-header" style={{ paddingBottom: 12, marginBottom: 12 }}>
              <span className="card-title">Live Parameters</span>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <label className="text-muted" style={{ display: 'block', fontSize: 11, textTransform: 'uppercase', fontWeight: 600, marginBottom: 6 }}>
                  Refresh Interval
                </label>
                <select 
                  value={intervalMs} 
                  onChange={(e) => setIntervalMs(Number(e.target.value))}
                  style={{ width: '100%', padding: '6px 10px' }}
                  disabled={!active}
                >
                  <option value={250}>Turbo (250ms - 4 FPS)</option>
                  <option value={400}>Normal (400ms - 2.5 FPS)</option>
                  <option value={600}>Eco (600ms - 1.6 FPS)</option>
                  <option value={1000}>Safe (1000ms - 1 FPS)</option>
                </select>
              </div>

              {active && (
                <button className="btn btn-danger" style={{ width: '100%', marginTop: 8 }} onClick={stopCamera}>
                  Stop Webcam Feed
                </button>
              )}
            </div>
          </div>

          {/* Real-time statistics Panel */}
          <div className="card" style={{ flexGrow: 1 }}>
            <div className="card-header" style={{ paddingBottom: 12, marginBottom: 12 }}>
              <span className="card-title">Scene Stats</span>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
              <div>
                <span className="text-muted" style={{ display: 'block', fontSize: 11, textTransform: 'uppercase', fontWeight: 600 }}>
                  Audience Count
                </span>
                <span className="hero-number">{totalFaces}</span>
                <span style={{ fontSize: 12, display: 'block', color: 'var(--text-tertiary)', marginTop: -4 }}>
                  Faces currently in bounds
                </span>
              </div>

              <div>
                <span className="text-muted" style={{ display: 'block', fontSize: 11, textTransform: 'uppercase', fontWeight: 600, marginBottom: 4 }}>
                  Dominant Emotion
                </span>
                <span style={{ 
                  fontSize: 16, 
                  fontWeight: 700, 
                  color: EMOTION_COLORS[sceneEmotion] || 'var(--text-primary)',
                  fontFamily: 'var(--font-mono)' 
                }}>
                  {sceneEmotion.toUpperCase()}
                </span>
              </div>

              <div style={{ borderTop: '1px solid var(--border)', paddingTop: 14 }}>
                <span className="text-muted" style={{ display: 'block', fontSize: 11, textTransform: 'uppercase', fontWeight: 600, marginBottom: 8 }}>
                  Real-time Detections List
                </span>
                
                {faces.length === 0 ? (
                  <div style={{ fontSize: 12, color: 'var(--text-tertiary)', fontStyle: 'italic', padding: '10px 0' }}>
                    No faces detected in view...
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 160, overflowY: 'auto' }}>
                    {faces.map((f, i) => (
                      <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12.5 }}>
                        <span style={{ color: 'var(--text-secondary)' }}>Face #{i + 1}</span>
                        <span style={{ 
                          fontWeight: 600, 
                          color: EMOTION_COLORS[f.emotion], 
                          fontFamily: 'var(--font-mono)' 
                        }}>
                          {f.emotion} ({Math.round(f.score)}%)
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

        </div>

      </div>

      {/* Hidden 640x480 canvas used for frame capture */}
      <canvas 
        ref={captureCanvasRef} 
        width="640" 
        height="480" 
        style={{ display: 'none' }} 
      />
    </div>
  );
}
