"""
CARLA Vision System - U-Net & Bounding Box Detection
Complete implementation in a single file
"""

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import numpy as np
import cv2
from scipy import ndimage


# ============================================================================
# U-NET MODEL
# ============================================================================

class UNet:
    """U-Net architecture for semantic segmentation"""
    
    def __init__(self, input_shape=(256, 256, 3), num_classes=13):
        self.input_shape = input_shape
        self.num_classes = num_classes
        self.model = self._build_model()
    
    def _conv_block(self, inputs, filters, kernel_size=3, activation='relu'):
        x = layers.Conv2D(filters, kernel_size, padding='same')(inputs)
        x = layers.BatchNormalization()(x)
        x = layers.Activation(activation)(x)
        return x
    
    def _encoder_block(self, inputs, filters):
        x = self._conv_block(inputs, filters)
        x = self._conv_block(x, filters)
        pool = layers.MaxPooling2D(pool_size=(2, 2))(x)
        return x, pool
    
    def _decoder_block(self, inputs, skip_features, filters):
        x = layers.Conv2DTranspose(filters, (2, 2), strides=2, padding='same')(inputs)
        x = layers.Concatenate()([x, skip_features])
        x = self._conv_block(x, filters)
        x = self._conv_block(x, filters)
        return x
    
    def _build_model(self):
        inputs = layers.Input(shape=self.input_shape)
        
        # Encoder
        s1, p1 = self._encoder_block(inputs, 64)
        s2, p2 = self._encoder_block(p1, 128)
        s3, p3 = self._encoder_block(p2, 256)
        s4, p4 = self._encoder_block(p3, 512)
        
        # Bottleneck
        b = self._conv_block(p4, 1024)
        b = self._conv_block(b, 1024)
        
        # Decoder
        d1 = self._decoder_block(b, s4, 512)
        d2 = self._decoder_block(d1, s3, 256)
        d3 = self._decoder_block(d2, s2, 128)
        d4 = self._decoder_block(d3, s1, 64)
        
        outputs = layers.Conv2D(self.num_classes, 1, activation='softmax', padding='same')(d4)
        
        return keras.Model(inputs=inputs, outputs=outputs, name='U-Net')
    
    def compile_model(self, learning_rate=0.001):
        self.model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy', tf.keras.metrics.MeanIoU(num_classes=self.num_classes)]
        )
    
    def predict(self, images, verbose=0):
        return self.model.predict(images, verbose=verbose)
    
    def train(self, train_dataset, validation_dataset, epochs=50):
        return self.model.fit(train_dataset, validation_data=validation_dataset, epochs=epochs)
    
    def save(self, filepath):
        self.model.save_weights(filepath)
    
    def load(self, filepath):
        self.model.load_weights(filepath)


# ============================================================================
# BOUNDING BOX DETECTION
# ============================================================================

class BoundingBoxDetector:
    """Extract bounding boxes from segmentation masks"""
    
    def __init__(self):
        self.vehicle_id = 13
        self.person_id = 12
        self.traffic_light_id = 7
        self.traffic_sign_id = 8
        
        self.classes_to_detect = {
            self.vehicle_id: 'Vehicle',
            self.person_id: 'Person',
            self.traffic_light_id: 'Traffic Light',
            self.traffic_sign_id: 'Traffic Sign'
        }
    
    def extract_bboxes(self, segmentation_mask, min_area=100):
        detections = []
        
        for class_id, class_name in self.classes_to_detect.items():
            binary_mask = (segmentation_mask == class_id).astype(np.uint8)
            labeled_mask, num_features = ndimage.label(binary_mask)
            
            for region_id in range(1, num_features + 1):
                region_mask = (labeled_mask == region_id)
                area = np.sum(region_mask)
                
                if area < min_area:
                    continue
                
                coords = np.argwhere(region_mask)
                y1, x1 = coords.min(axis=0)
                y2, x2 = coords.max(axis=0)
                
                bbox_area = (x2 - x1) * (y2 - y1)
                confidence = area / bbox_area if bbox_area > 0 else 0
                
                detections.append({
                    'class': class_name,
                    'class_id': class_id,
                    'bbox': [int(x1), int(y1), int(x2), int(y2)],
                    'confidence': float(confidence),
                    'area': int(area)
                })
        
        return detections
    
    def non_max_suppression(self, detections, iou_threshold=0.5):
        if len(detections) == 0:
            return []
        
        class_groups = {}
        for det in detections:
            class_name = det['class']
            if class_name not in class_groups:
                class_groups[class_name] = []
            class_groups[class_name].append(det)
        
        filtered_detections = []
        
        for class_name, group in class_groups.items():
            group = sorted(group, key=lambda x: x['confidence'], reverse=True)
            
            keep = []
            while group:
                best = group.pop(0)
                keep.append(best)
                group = [det for det in group 
                        if self._calculate_iou(best['bbox'], det['bbox']) < iou_threshold]
            
            filtered_detections.extend(keep)
        
        return filtered_detections
    
    def _calculate_iou(self, box1, box2):
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2
        
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        if x2_i < x1_i or y2_i < y1_i:
            return 0.0
        
        intersection = (x2_i - x1_i) * (y2_i - y1_i)
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def draw_bboxes(self, image, detections, thickness=2):
        img_copy = image.copy()
        
        colors = {
            'Vehicle': (0, 255, 0),
            'Person': (255, 0, 0),
            'Traffic Light': (0, 165, 255),
            'Traffic Sign': (0, 255, 255)
        }
        
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            color = colors.get(det['class'], (255, 255, 255))
            
            cv2.rectangle(img_copy, (x1, y1), (x2, y2), color, thickness)
            
            label = f"{det['class']}: {det['confidence']:.2f}"
            (text_width, text_height), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
            )
            
            cv2.rectangle(img_copy, (x1, y1 - text_height - 5), 
                         (x1 + text_width, y1), color, -1)
            cv2.putText(img_copy, label, (x1, y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
        return img_copy


# ============================================================================
# OBJECT TRACKER
# ============================================================================

class ObjectTracker:
    """Simple object tracker across frames"""
    
    def __init__(self, max_age=5):
        self.tracks = []
        self.next_id = 0
        self.max_age = max_age
    
    def update(self, detections):
        if len(self.tracks) == 0:
            for det in detections:
                self.tracks.append({
                    'id': self.next_id,
                    'detection': det,
                    'age': 0
                })
                self.next_id += 1
            return self.tracks
        
        matched_tracks = []
        unmatched_detections = list(detections)
        
        for track in self.tracks:
            track['age'] += 1
            best_iou = 0
            best_det = None
            best_idx = -1
            
            for idx, det in enumerate(unmatched_detections):
                if det['class'] != track['detection']['class']:
                    continue
                
                iou = self._calculate_iou(track['detection']['bbox'], det['bbox'])
                if iou > best_iou:
                    best_iou = iou
                    best_det = det
                    best_idx = idx
            
            if best_iou > 0.3:
                track['detection'] = best_det
                track['age'] = 0
                matched_tracks.append(track)
                unmatched_detections.pop(best_idx)
        
        for det in unmatched_detections:
            matched_tracks.append({
                'id': self.next_id,
                'detection': det,
                'age': 0
            })
            self.next_id += 1
        
        self.tracks = [t for t in matched_tracks if t['age'] < self.max_age]
        return self.tracks
    
    def _calculate_iou(self, box1, box2):
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2
        
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        if x2_i < x1_i or y2_i < y1_i:
            return 0.0
        
        intersection = (x2_i - x1_i) * (y2_i - y1_i)
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0


# ============================================================================
# CARLA SEGMENTATION COLORS
# ============================================================================

CARLA_COLORS = {
    0: (0, 0, 0),        # Unlabeled
    1: (128, 64, 128),   # Road
    2: (244, 35, 232),   # Sidewalk
    3: (70, 70, 70),     # Building
    4: (102, 102, 156),  # Wall
    5: (190, 153, 153),  # Fence
    6: (153, 153, 153),  # Pole
    7: (250, 170, 30),   # Traffic light
    8: (220, 220, 0),    # Traffic sign
    9: (107, 142, 35),   # Vegetation
    10: (152, 251, 152), # Terrain
    11: (70, 130, 180),  # Sky
    12: (220, 20, 60),   # Person
    13: (0, 0, 142),     # Vehicle
}


def visualize_prediction(image, prediction):
    """Convert prediction to RGB visualization"""
    predicted_mask = np.argmax(prediction, axis=-1)
    h, w = predicted_mask.shape
    color_mask = np.zeros((h, w, 3), dtype=np.uint8)
    
    for class_id, color in CARLA_COLORS.items():
        color_mask[predicted_mask == class_id] = color
    
    blended = (0.6 * image + 0.4 * color_mask).astype(np.uint8)
    return blended, color_mask


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    print("Creating U-Net model...")
    unet = UNet(input_shape=(256, 256, 3), num_classes=13)
    unet.compile_model()
    print(f"Model created with {unet.model.count_params():,} parameters")
    
    print("\nTesting bounding box detector...")
    detector = BoundingBoxDetector()
    tracker = ObjectTracker()
    
    # Create dummy segmentation mask
    mask = np.zeros((256, 256), dtype=np.uint8)
    mask[50:100, 50:150] = 13  # Vehicle
    mask[120:180, 80:140] = 12  # Person
    
    detections = detector.extract_bboxes(mask, min_area=50)
    detections = detector.non_max_suppression(detections)
    
    print(f"\nFound {len(detections)} objects:")
    for det in detections:
        print(f"  - {det['class']}: confidence={det['confidence']:.2f}")
    
    tracks = tracker.update(detections)
    print(f"\nTracking {len(tracks)} objects")
    
    print("\n✓ All systems operational!")
