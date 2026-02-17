"""
CARLA Vision System - Complete Integration
U-Net + Bounding Boxes + Web Server in one file
Usage: python carla_app.py
Then open: http://localhost:5000
"""

from flask import Flask, jsonify, Response, send_file
from flask_cors import CORS
import cv2
import numpy as np
import base64
import threading
import time
import queue
from pathlib import Path

from carla_vision import UNet, BoundingBoxDetector, ObjectTracker, visualize_prediction


# ============================================================================
# MOCK CARLA DATA GENERATOR
# ============================================================================

class MockCARLADataLoader:
    """Generate synthetic CARLA-like data for testing"""
    
    def __init__(self, width=256, height=256):
        self.width = width
        self.height = height
        self.frame_count = 0
    
    def get_frame(self):
        """Generate synthetic frame"""
        # Create RGB image
        rgb_image = np.random.randint(0, 255, (self.height, self.width, 3), dtype=np.uint8)
        
        # Sky (top 60%)
        rgb_image[:int(self.height*0.6), :] = [70, 130, 180]
        
        # Road (bottom 40%)
        rgb_image[int(self.height*0.6):, :] = [80, 80, 80]
        
        # Create segmentation mask
        seg_mask = np.ones((self.height, self.width), dtype=np.uint8) * 11  # Sky
        seg_mask[int(self.height*0.6):, :] = 1  # Road
        
        # Add moving vehicle
        if self.frame_count % 40 < 30:
            x = int(self.width * 0.3 + (self.frame_count % 40) * 8)
            y = int(self.height * 0.5)
            
            # Ensure vehicle stays in bounds
            if x + 80 < self.width and y + 60 < self.height:
                seg_mask[y:y+60, x:x+80] = 13  # Vehicle
                rgb_image[y:y+60, x:x+80] = [50, 100, 200]
        
        # Add random pedestrian
        if self.frame_count % 60 < 40:
            x = int(self.width * 0.6)
            y = int(self.height * 0.55)
            if x + 30 < self.width and y + 50 < self.height:
                seg_mask[y:y+50, x:x+30] = 12  # Person
                rgb_image[y:y+50, x:x+30] = [200, 100, 50]
        
        self.frame_count += 1
        time.sleep(0.033)  # ~30 FPS
        
        return rgb_image, seg_mask


# ============================================================================
# VISION SYSTEM SERVER
# ============================================================================

class VisionSystemServer:
    """Backend for web visualization"""
    
    def __init__(self):
        print("Initializing U-Net model...")
        self.unet = UNet(input_shape=(256, 256, 3), num_classes=13)
        self.unet.compile_model()
        
        print("Initializing detectors...")
        self.bbox_detector = BoundingBoxDetector()
        self.tracker = ObjectTracker()
        
        print("Starting CARLA simulator...")
        self.carla = MockCARLADataLoader(256, 256)
        
        self.current_frame = None
        self.current_detections = []
        self.stats = {
            'frame_count': 0,
            'total_detections': 0,
            'fps': 0,
            'active_tracks': 0
        }
        
        self.running = False
        self.lock = threading.Lock()
    
    def start(self):
        """Start processing loop"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._process_loop, daemon=True)
            self.thread.start()
            print("✓ Vision system started")
    
    def stop(self):
        """Stop processing"""
        self.running = False
        print("✓ Vision system stopped")
    
    def _process_loop(self):
        """Main processing loop"""
        last_time = time.time()
        
        while self.running:
            try:
                # Get frame from CARLA
                rgb_image, seg_mask = self.carla.get_frame()
                
                # Predict segmentation with U-Net
                img_normalized = np.array([rgb_image.astype(np.float32) / 255.0])
                prediction = self.unet.predict(img_normalized, verbose=0)[0]
                predicted_mask = np.argmax(prediction, axis=-1)
                
                # Extract bounding boxes
                detections = self.bbox_detector.extract_bboxes(predicted_mask, min_area=100)
                detections = self.bbox_detector.non_max_suppression(detections)
                
                # Track objects
                tracks = self.tracker.update(detections)
                
                # Visualize
                vis_blend, vis_mask = visualize_prediction(rgb_image, prediction)
                vis_bbox = self.bbox_detector.draw_bboxes(rgb_image, detections)
                
                # Calculate FPS
                current_time = time.time()
                fps = 1.0 / (current_time - last_time) if current_time > last_time else 0
                last_time = current_time
                
                # Update state
                with self.lock:
                    self.current_frame = {
                        'rgb': rgb_image,
                        'segmentation': vis_mask,
                        'bbox': vis_bbox,
                        'blend': vis_blend
                    }
                    self.current_detections = detections
                    self.stats['frame_count'] += 1
                    self.stats['total_detections'] += len(detections)
                    self.stats['fps'] = fps
                    self.stats['active_tracks'] = len(tracks)
                
            except Exception as e:
                print(f"Error in processing loop: {e}")
                time.sleep(0.1)
    
    def get_frame_data(self):
        """Get current frame data as JSON"""
        with self.lock:
            if self.current_frame is None:
                return None
            
            return {
                'rgb': self._encode_image(self.current_frame['rgb']),
                'segmentation': self._encode_image(self.current_frame['segmentation']),
                'bbox': self._encode_image(self.current_frame['bbox']),
                'blend': self._encode_image(self.current_frame['blend']),
                'detections': self.current_detections,
                'stats': self.stats.copy()
            }
    
    def _encode_image(self, image):
        """Encode image to base64"""
        _, buffer = cv2.imencode('.jpg', cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        return base64.b64encode(buffer).decode('utf-8')


# ============================================================================
# FLASK WEB SERVER
# ============================================================================

app = Flask(__name__)
CORS(app)

# Global server instance
vision_server = VisionSystemServer()


@app.route('/')
def index():
    """Serve main HTML page"""
    html_path = Path(__file__).parent / 'carla_web.html'
    if html_path.exists():
        return send_file(html_path)
    else:
        return """
        <html><body>
        <h1>CARLA Vision System</h1>
        <p>Error: carla_web.html not found in the same directory.</p>
        <p>Please ensure carla_web.html is in the same folder as this script.</p>
        </body></html>
        """, 404


@app.route('/api/start', methods=['POST'])
def start_processing():
    """Start processing"""
    vision_server.start()
    return jsonify({'status': 'started'})


@app.route('/api/stop', methods=['POST'])
def stop_processing():
    """Stop processing"""
    vision_server.stop()
    return jsonify({'status': 'stopped'})


@app.route('/api/frame')
def get_frame():
    """Get current frame data"""
    data = vision_server.get_frame_data()
    if data is None:
        return jsonify({'error': 'No frame available'}), 404
    return jsonify(data)


@app.route('/api/stats')
def get_stats():
    """Get statistics"""
    with vision_server.lock:
        return jsonify(vision_server.stats)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("CARLA Vision System - U-Net + Bounding Box Detection")
    print("=" * 60)
    print("\nStarting server...")
    
    # Auto-start vision processing
    vision_server.start()
    
    print("\n✓ Server ready!")
    print("Open in browser: http://localhost:5000")
    print("Press Ctrl+C to stop\n")
    
    # Run Flask app
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        vision_server.stop()
        print("✓ Goodbye!")
