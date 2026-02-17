"""
CARLA Perception Stack with UKF + Vision System
Complete Integration: Sensor Fusion + Vision + Web Server
"""

import carla
import numpy as np
import time
import json
import asyncio
import websockets
import struct
from collections import deque
from scipy.linalg import cholesky
from datetime import datetime
import threading
import queue
import os
import base64
import http.server
import random
import socketserver
import cv2
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from scipy import ndimage
from flask import Flask, jsonify, Response, send_file
from flask_cors import CORS
from pathlib import Path


# ============================================================================
# U-NET MODEL FOR SEMANTIC SEGMENTATION
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
        
        s1, p1 = self._encoder_block(inputs, 64)
        s2, p2 = self._encoder_block(p1, 128)
        s3, p3 = self._encoder_block(p2, 256)
        s4, p4 = self._encoder_block(p3, 512)
        
        b = self._conv_block(p4, 1024)
        b = self._conv_block(b, 1024)
        
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


HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CARLA Perception System - Professional Dashboard</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #0a0e27;
            color: #e0e0e0;
            padding: 20px;
            min-height: 100vh;
        }

        .container {
            max-width: 1600px;
            margin: 0 auto;
        }

        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(102, 126, 234, 0.4);
        }

        header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }

        header p {
            font-size: 1.1em;
            opacity: 0.95;
        }

        .main-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }

        .card {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            backdrop-filter: blur(10px);
        }

        .card h2 {
            font-size: 1.3em;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
            color: #667eea;
            border-bottom: 2px solid rgba(102, 126, 234, 0.3);
            padding-bottom: 10px;
        }

        .vision-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }

        .image-container {
            position: relative;
            background: #000;
            border-radius: 10px;
            overflow: hidden;
            aspect-ratio: 1;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .image-container img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }

        .image-overlay {
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(0, 0, 0, 0.85);
            padding: 8px 15px;
            border-radius: 6px;
            font-size: 0.9em;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .status-dot {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #4CAF50;
            box-shadow: 0 0 10px #4CAF50;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }

        .stat-card {
            background: rgba(102, 126, 234, 0.1);
            border-left: 4px solid #667eea;
            padding: 20px;
            border-radius: 10px;
            transition: all 0.3s;
        }

        .stat-card:hover {
            background: rgba(102, 126, 234, 0.2);
            transform: translateY(-2px);
        }

        .stat-label {
            font-size: 0.9em;
            opacity: 0.8;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }

        .stat-value {
            font-size: 2.2em;
            font-weight: bold;
            color: #667eea;
        }

        .stat-unit {
            font-size: 0.8em;
            opacity: 0.7;
            margin-left: 5px;
        }

        .detections-container {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 10px;
            padding: 15px;
            max-height: 400px;
            overflow-y: auto;
        }

        .detection-item {
            background: rgba(102, 126, 234, 0.12);
            padding: 12px 15px;
            margin-bottom: 10px;
            border-radius: 8px;
            border-left: 3px solid #667eea;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.2s;
        }

        .detection-item:hover {
            background: rgba(102, 126, 234, 0.2);
            transform: translateX(5px);
        }

        .detection-info {
            flex: 1;
        }

        .detection-label {
            font-weight: 600;
            margin-bottom: 5px;
        }

        .detection-coords {
            font-size: 0.85em;
            opacity: 0.7;
            font-family: monospace;
        }

        .detection-badge {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
            text-transform: uppercase;
            margin-left: 15px;
        }

        .badge-vehicle { background: #4CAF50; color: white; }
        .badge-person { background: #2196F3; color: white; }
        .badge-traffic-light { background: #FF9800; color: white; }
        .badge-traffic-sign { background: #FFC107; color: #000; }

        .sensor-data {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-top: 15px;
        }

        .sensor-item {
            background: rgba(0, 0, 0, 0.2);
            padding: 12px;
            border-radius: 8px;
            border-left: 2px solid #764ba2;
        }

        .sensor-label {
            font-size: 0.85em;
            opacity: 0.8;
            margin-bottom: 5px;
        }

        .sensor-value {
            font-size: 1.1em;
            font-weight: bold;
            font-family: monospace;
            color: #667eea;
        }

        .controls {
            display: flex;
            gap: 15px;
            margin-top: 20px;
        }

        button {
            flex: 1;
            padding: 14px 20px;
            font-size: 1em;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .btn-start {
            background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
            color: white;
        }

        .btn-start:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(76, 175, 80, 0.4);
        }

        .btn-stop {
            background: linear-gradient(135deg, #f44336 0%, #da190b 100%);
            color: white;
        }

        .btn-stop:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(244, 67, 54, 0.4);
        }

        .legend {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-top: 15px;
        }

        .legend-item {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 0.9em;
        }

        .color-box {
            width: 20px;
            height: 20px;
            border-radius: 4px;
            border: 1px solid rgba(255, 255, 255, 0.3);
        }

        ::-webkit-scrollbar {
            width: 8px;
        }

        ::-webkit-scrollbar-track {
            background: rgba(0, 0, 0, 0.2);
            border-radius: 10px;
        }

        ::-webkit-scrollbar-thumb {
            background: rgba(102, 126, 234, 0.4);
            border-radius: 10px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: rgba(102, 126, 234, 0.6);
        }

        .loading {
            text-align: center;
            padding: 40px;
            opacity: 0.7;
        }

        .no-data {
            text-align: center;
            padding: 30px;
            opacity: 0.6;
            color: #999;
        }

        @media (max-width: 1200px) {
            .main-grid {
                grid-template-columns: 1fr;
            }
            
            .vision-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🚗 CARLA Perception System</h1>
            <p>Real-time Sensor Fusion + Vision + Object Detection</p>
        </header>

        <div class="main-grid">
            <!-- Vision Panel -->
            <div>
                <div class="card">
                    <h2>📷 Vision Pipeline</h2>
                    <div class="vision-grid">
                        <div class="image-container">
                            <img id="rgbImage" src="data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/2wBDAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAhEAACAQMEAgMBAQAAAAAAAAABAgADBBEhEjFBUWEicf/EABUBAQEAAAAAAAAAAAAAAAAAAAMF/8QAGhEAAgIDAAAAAAAAAAAAAAAAAAECEgMRkf/aAAwDAQACEQMRAD8AltJaxQIlrFBYi2iMRaI0BaLRaABYi0BaLRaABYi0BaLRaABYi0BaLRaABYi0BaLRaABYi0BaLRaD/9k=" alt="RGB">
                            <div class="image-overlay">
                                <span class="status-dot"></span>
                                RGB Camera
                            </div>
                        </div>
                        <div class="image-container">
                            <img id="bboxImage" src="data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/2wBDAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAhEAACAQMEAgMBAQAAAAAAAAABAgADBBEhEjFBUWEicf/EABUBAQEAAAAAAAAAAAAAAAAAAAMF/8QAGhEAAgIDAAAAAAAAAAAAAAAAAAECEgMRkf/aAAwDAQACEQMRAD8AltJaxQIlrFBYi2iMRaI0BaLRaABYi0BaLRaABYi0BaLRaABYi0BaLRaABYi0BaLRaABYi0BaLRaD/9k=" alt="Detections">
                            <div class="image-overlay">
                                Objects: <span id="objectCount">0</span>
                            </div>
                        </div>
                        <div class="image-container">
                            <img id="segImage" src="data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/2wBDAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAhEAACAQMEAgMBAQAAAAAAAAABAgADBBEhEjFBUWEicf/EABUBAQEAAAAAAAAAAAAAAAAAAAMF/8QAGhEAAgIDAAAAAAAAAAAAAAAAAAECEgMRkf/aAAwDAQACEQMRAD8AltJaxQIlrFBYi2iMRaI0BaLRaABYi0BaLRaABYi0BaLRaABYi0BaLRaABYi0BaLRaABYi0BaLRaABYi0BaLRaD/9k=" alt="Segmentation">
                            <div class="image-overlay">
                                FPS: <span id="fpsValue">0</span>
                            </div>
                        </div>
                        <div class="image-container">
                            <img id="lidarImage" src="data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/2wBDAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAhEAACAQMEAgMBAQAAAAAAAAABAgADBBEhEjFBUWEicf/EABUBAQEAAAAAAAAAAAAAAAAAAAMF/8QAGhEAAgIDAAAAAAAAAAAAAAAAAAECEgMRkf/aAAwDAQACEQMRAD8AltJaxQIlrFBYi2iMRaI0BaLRaABYi0BaLRaABYi0BaLRaABYi0BaLRaABYi0BaLRaABYi0BaLRaABYi0BaLRaD/9k=" alt="LiDAR">
                            <div class="image-overlay">
                                Points: <span id="lidarCount">0</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="legend" style="margin-top: 15px;">
                        <div class="legend-item">
                            <div class="color-box" style="background: rgb(0,0,142);"></div>
                            <span>Vehicle</span>
                        </div>
                        <div class="legend-item">
                            <div class="color-box" style="background: rgb(220,20,60);"></div>
                            <span>Person</span>
                        </div>
                        <div class="legend-item">
                            <div class="color-box" style="background: rgb(250,170,30);"></div>
                            <span>Traffic Light</span>
                        </div>
                        <div class="legend-item">
                            <div class="color-box" style="background: rgb(220,220,0);"></div>
                            <span>Traffic Sign</span>
                        </div>
                    </div>
                </div>

                <!-- Detections List -->
                <div class="card" style="margin-top: 20px;">
                    <h2>📋 Detected Objects</h2>
                    <div class="detections-container" id="detectionsList">
                        <div class="no-data">Waiting for detections...</div>
                    </div>
                </div>
            </div>

            <!-- Right Panel -->
            <div>
                <!-- Statistics -->
                <div class="card">
                    <h2>📊 Statistics</h2>
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-label">FPS</div>
                            <div class="stat-value">
                                <span id="fpsStats">0</span>
                                <span class="stat-unit">fps</span>
                            </div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Frames</div>
                            <div class="stat-value" id="frameCount">0</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">LiDAR Points</div>
                            <div class="stat-value" id="lidarCountStat">0</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Tracked Objects</div>
                            <div class="stat-value" id="trackedCount">0</div>
                        </div>
                    </div>
                </div>

                <!-- Sensor Data -->
                <div class="card" style="margin-top: 20px;">
                    <h2>🛰️ Sensor Data</h2>
                    <div class="sensor-data">
                        <div class="sensor-item">
                            <div class="sensor-label">GPS Latitude</div>
                            <div class="sensor-value" id="gpsLat">--</div>
                        </div>
                        <div class="sensor-item">
                            <div class="sensor-label">GPS Longitude</div>
                            <div class="sensor-value" id="gpsLon">--</div>
                        </div>
                        <div class="sensor-item">
                            <div class="sensor-label">Altitude</div>
                            <div class="sensor-value" id="gpsAlt">--</div>
                        </div>
                        <div class="sensor-item">
                            <div class="sensor-label">Radar Points</div>
                            <div class="sensor-value" id="radarCount">0</div>
                        </div>
                    </div>
                </div>

                <!-- UKF State -->
                <div class="card" style="margin-top: 20px;">
                    <h2>🔮 UKF Fusion State</h2>
                    <div class="sensor-data">
                        <div class="sensor-item">
                            <div class="sensor-label">Position X</div>
                            <div class="sensor-value" id="poseX">0.00</div>
                        </div>
                        <div class="sensor-item">
                            <div class="sensor-label">Position Y</div>
                            <div class="sensor-value" id="poseY">0.00</div>
                        </div>
                        <div class="sensor-item">
                            <div class="sensor-label">Position Z</div>
                            <div class="sensor-value" id="poseZ">0.00</div>
                        </div>
                        <div class="sensor-item">
                            <div class="sensor-label">Velocity</div>
                            <div class="sensor-value" id="velocity">0.00 m/s</div>
                        </div>
                    </div>
                </div>

                <!-- Controls -->
                <div class="card" style="margin-top: 20px;">
                    <h2>🎮 Controls</h2>
                    <div class="controls">
                        <button class="btn-start" onclick="startSystem()">▶ Start</button>
                        <button class="btn-stop" onclick="stopSystem()">⏹ Stop</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let isRunning = false;
        let updateInterval = null;
        let fpsHistory = [];

        async function startSystem() {
            try {
                const response = await fetch('/api/start', { method: 'POST' });
                const data = await response.json();
                
                if (data.status === 'started') {
                    isRunning = true;
                    console.log('✓ System started');
                    startUpdates();
                }
            } catch (error) {
                console.error('Error starting:', error);
                alert('Failed to start system');
            }
        }

        async function stopSystem() {
            try {
                const response = await fetch('/api/stop', { method: 'POST' });
                isRunning = false;
                if (updateInterval) clearInterval(updateInterval);
            } catch (error) {
                console.error('Error stopping:', error);
            }
        }

        function startUpdates() {
            if (updateInterval) clearInterval(updateInterval);
            updateInterval = setInterval(updateFrame, 100);
        }

        async function updateFrame() {
            if (!isRunning) return;

            try {
                const response = await fetch('/api/frame');
                if (!response.ok) return;
                
                const data = await response.json();
                
                // Update images
                if (data.rgb) document.getElementById('rgbImage').src = 'data:image/jpeg;base64,' + data.rgb;
                if (data.segmentation) document.getElementById('segImage').src = 'data:image/jpeg;base64,' + data.segmentation;
                if (data.bbox) document.getElementById('bboxImage').src = 'data:image/jpeg;base64,' + data.bbox;
                
                // Update stats
                document.getElementById('fpsStats').textContent = data.stats.fps.toFixed(1);
                document.getElementById('frameCount').textContent = data.stats.frame_count;
                document.getElementById('lidarCountStat').textContent = data.stats.lidar_points;
                document.getElementById('trackedCount').textContent = data.stats.active_tracks;
                document.getElementById('fpsValue').textContent = data.stats.fps.toFixed(1);
                document.getElementById('objectCount').textContent = data.detections.length;
                
                // Update detections
                updateDetectionsList(data.detections);
                
            } catch (error) {
                console.error('Error updating:', error);
            }
        }

        function updateDetectionsList(detections) {
            const list = document.getElementById('detectionsList');
            
            if (!detections || detections.length === 0) {
                list.innerHTML = '<div class="no-data">No detections</div>';
                return;
            }
            
            const getBadgeClass = (cls) => 'badge-' + cls.toLowerCase().replace(/\\s+/g, '-');
            
            list.innerHTML = detections.map((det, idx) => \`
                <div class="detection-item">
                    <div class="detection-info">
                        <div class="detection-label">Detection #\${idx + 1}: \${det.class}</div>
                        <div class="detection-coords">
                            Bbox: [\${det.bbox.map(v => v.toFixed(0)).join(', ')}]
                        </div>
                    </div>
                    <div class="detection-badge \${getBadgeClass(det.class)}">
                        \${(det.confidence * 100).toFixed(1)}%
                    </div>
                </div>
            \`).join('');
        }

        // WebSocket for sensor data
        const ws = new WebSocket('ws://localhost:8765');
        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            
            if (msg.type === 'gps') {
                document.getElementById('gpsLat').textContent = msg.latitude.toFixed(6);
                document.getElementById('gpsLon').textContent = msg.longitude.toFixed(6);
                document.getElementById('gpsAlt').textContent = msg.altitude.toFixed(2) + ' m';
            } else if (msg.type === 'pose') {
                const p = msg.position;
                document.getElementById('poseX').textContent = p.x.toFixed(2);
                document.getElementById('poseY').textContent = p.y.toFixed(2);
                document.getElementById('poseZ').textContent = p.z.toFixed(2);
                const vel = Math.sqrt(p.vx ** 2 + p.vy ** 2 + p.vz ** 2);
                document.getElementById('velocity').textContent = vel.toFixed(2) + ' m/s';
            } else if (msg.type === 'radar') {
                document.getElementById('radarCount').textContent = msg.count;
            } else if (msg.type === 'lidar') {
                const binary = atob(msg.data);
                const bytes = new Uint8Array(binary.length);
                for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
                const positions = new Float32Array(bytes.buffer);
                document.getElementById('lidarCount').textContent = (positions.length / 4).toFixed(0);
            }
        };

        window.addEventListener('load', () => {
            console.log('✓ Dashboard loaded');
            setTimeout(() => startSystem(), 1000);
        });
    </script>
</body>
</html>
"""


class UnscentedKalmanFilter:
    """Unscented Kalman Filter for sensor fusion"""
    
    def __init__(self, dim_x=10, dim_z=6):
        self.dim_x = dim_x
        self.dim_z = dim_z
        
        self.x = np.zeros(dim_x)
        self.P = np.eye(dim_x) * 10.0
        
        self.Q = np.eye(dim_x)
        self.Q[0:3, 0:3] *= 0.1
        self.Q[3:6, 3:6] *= 0.5
        self.Q[6:9, 6:9] *= 0.01
        self.Q[9, 9] *= 0.05
        
        self.R = np.eye(dim_z)
        self.R[0:3, 0:3] *= 2.0
        self.R[3:6, 3:6] *= 0.5
        
        self.alpha = 0.001
        self.beta = 2.0
        self.kappa = 0.0
        self.lambda_ = self.alpha**2 * (self.dim_x + self.kappa) - self.dim_x
        
        self.Wm, self.Wc = self._calculate_weights()
        
    def _calculate_weights(self):
        n = self.dim_x
        lambda_ = self.lambda_
        
        Wm = np.zeros(2 * n + 1)
        Wc = np.zeros(2 * n + 1)
        
        Wm[0] = lambda_ / (n + lambda_)
        Wc[0] = lambda_ / (n + lambda_) + (1 - self.alpha**2 + self.beta)
        
        for i in range(1, 2 * n + 1):
            Wm[i] = 1.0 / (2 * (n + lambda_))
            Wc[i] = 1.0 / (2 * (n + lambda_))
            
        return Wm, Wc
    
    def _generate_sigma_points(self):
        n = self.dim_x
        lambda_ = self.lambda_
        
        sigma_points = np.zeros((2 * n + 1, n))
        sigma_points[0] = self.x
        
        try:
            U = cholesky((n + lambda_) * self.P)
        except np.linalg.LinAlgError:
            U = np.linalg.cholesky((n + lambda_) * (self.P + np.eye(n) * 1e-6))
        
        for i in range(n):
            sigma_points[i + 1] = self.x + U[i]
            sigma_points[n + i + 1] = self.x - U[i]
            
        return sigma_points
    
    def _state_transition(self, x, dt):
        x_new = x.copy()
        x_new[0] += x[3] * dt
        x_new[1] += x[4] * dt
        x_new[2] += x[5] * dt
        x_new[8] += x[9] * dt
        x_new[8] = np.arctan2(np.sin(x_new[8]), np.cos(x_new[8]))
        return x_new
    
    def _measurement_function(self, x):
        return x[[0, 1, 2, 3, 4, 5]]
    
    def predict(self, dt):
        sigma_points = self._generate_sigma_points()
        sigma_points_pred = np.array([self._state_transition(sp, dt) for sp in sigma_points])
        
        self.x = np.sum(self.Wm[:, np.newaxis] * sigma_points_pred, axis=0)
        
        diff = sigma_points_pred - self.x
        self.P = self.Q.copy()
        for i in range(len(self.Wc)):
            self.P += self.Wc[i] * np.outer(diff[i], diff[i])
    
    def update(self, z, R=None):
        if R is None:
            R = self.R
            
        sigma_points = self._generate_sigma_points()
        sigma_points_meas = np.array([self._measurement_function(sp) for sp in sigma_points])
        
        z_pred = np.sum(self.Wm[:, np.newaxis] * sigma_points_meas, axis=0)
        
        diff_z = sigma_points_meas - z_pred
        Pzz = R.copy()
        for i in range(len(self.Wc)):
            Pzz += self.Wc[i] * np.outer(diff_z[i], diff_z[i])
        
        diff_x = sigma_points - self.x
        Pxz = np.zeros((self.dim_x, self.dim_z))
        for i in range(len(self.Wc)):
            Pxz += self.Wc[i] * np.outer(diff_x[i], diff_z[i])
        
        K = Pxz @ np.linalg.inv(Pzz)
        
        innovation = z - z_pred
        self.x += K @ innovation
        self.P -= K @ Pzz @ K.T


class DataWebSocketServer:
    """Simple WebSocket server for data transmission"""
    
    def __init__(self, host='0.0.0.0', port=8765):
        self.host = host
        self.port = port
        self.clients = set()
        
    async def register_client(self, websocket):
        self.clients.add(websocket)
        print(f"✅ Web client connected! Total: {len(self.clients)}")
        
    async def unregister_client(self, websocket):
        self.clients.discard(websocket)
        print(f"Client disconnected. Total: {len(self.clients)}")
    
    async def handle_client(self, websocket):
        """Handle client connection"""
        await self.register_client(websocket)
        try:
            async for message in websocket:
                pass  # Handle incoming if needed
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister_client(websocket)
    
    async def send_message(self, message):
        """Send message to all clients"""
        if not self.clients:
            return
        
        msg_json = json.dumps(message)
        
        # Send to all clients
        disconnected = set()
        for client in self.clients:
            try:
                await client.send(msg_json)
            except:
                disconnected.add(client)
        
        # Remove disconnected clients
        self.clients -= disconnected
    
    async def start(self):
        """Start server"""
        async with websockets.serve(self.handle_client, self.host, self.port):
            print(f"🌐 WebSocket: ws://localhost:{self.port}")
            await asyncio.Future()


class PerceptionStack:
    """Main perception stack with vision and UKF"""
    
    def __init__(self, carla_host='localhost', carla_port=2000):
        self.client = None
        self.world = None
        self.vehicle = None
        self.sensors = {}
        self.spawned_actors = []  # Track spawned actors for cleanup
        
        self.carla_host = carla_host
        self.carla_port = carla_port
        
        self.ukf = UnscentedKalmanFilter()
        self.last_time = time.time()
        
        self.data_ws = DataWebSocketServer()
        self.loop = None
        
        # Vision components
        print("📡 Initializing vision components...")
        self.unet = UNet(input_shape=(256, 256, 3), num_classes=13)
        self.unet.compile_model()
        self.bbox_detector = BoundingBoxDetector()
        self.tracker = ObjectTracker()
        
        self.current_frame = None
        self.current_detections = []
        self.vision_lock = threading.Lock()
        
        self.gps_origin = None
        self.data_count = {'lidar': 0, 'radar': 0, 'gps': 0, 'imu': 0, 'camera': 0}
        
        # LiDAR and Radar buffers
        self.latest_lidar_points = None
        self.latest_radar_objects = None
        
        # Stats
        self.stats = {
            'frame_count': 0,
            'fps': 0,
            'lidar_points': 0,
            'active_tracks': 0
        }
        self.fps_history = deque(maxlen=30)
        
    def connect_to_carla(self):
        """Connect to CARLA"""
        try:
            self.client = carla.Client(self.carla_host, self.carla_port)
            self.client.set_timeout(30.0)
            self.world = self.client.get_world()
            print(f'✅ Connected to CARLA: {self.client.get_server_version()}')
            return True
        except Exception as e:
            print(f'❌ CARLA connection failed: {e}')
            return False
    
    def spawn_vehicle(self):
        """Spawn vehicle with camera following"""
        blueprint_library = self.world.get_blueprint_library()
        
        vehicle_blueprints = blueprint_library.filter('vehicle.tesla.model3')
        if not vehicle_blueprints:
            vehicle_bp = blueprint_library.filter('vehicle.*')[0]
        else:
            vehicle_bp = vehicle_blueprints[0]
        
        spawn_points = self.world.get_map().get_spawn_points()
        if not spawn_points:
            print("❌ No spawn points!")
            return False
        
        # Try multiple spawn points
        for i in range(min(5, len(spawn_points))):
            try:
                spawn_point = spawn_points[i]
                self.vehicle = self.world.spawn_actor(vehicle_bp, spawn_point)
                print(f'✅ Vehicle spawned at point {i}')
                break
            except Exception as e:
                if i == 4:
                    print(f"❌ Failed to spawn: {e}")
                    return False
        
        self.vehicle.set_autopilot(True)
        print('✅ Autopilot enabled')
        
        # Position camera
        time.sleep(0.5)
        spectator = self.world.get_spectator()
        transform = self.vehicle.get_transform()
        spectator.set_transform(carla.Transform(
            transform.location + carla.Location(x=-8, z=4),
            carla.Rotation(pitch=-15, yaw=transform.rotation.yaw)
        ))
        print('✅ Camera positioned')
        
        return True
    
    def setup_sensors(self):
        """Setup sensors"""
        bp_lib = self.world.get_blueprint_library()
        
        # RGB Camera
        camera_bp = bp_lib.find('sensor.camera.rgb')
        camera_bp.set_attribute('image_size_x', '256')
        camera_bp.set_attribute('image_size_y', '256')
        camera_bp.set_attribute('fov', '90')
        camera_transform = carla.Transform(carla.Location(x=0.5, z=1.8))
        self.sensors['camera'] = self.world.spawn_actor(
            camera_bp, camera_transform, attach_to=self.vehicle
        )
        self.sensors['camera'].listen(self.camera_callback)
        
        # LiDAR
        lidar_bp = bp_lib.find('sensor.lidar.ray_cast')
        lidar_bp.set_attribute('channels', '32')
        lidar_bp.set_attribute('points_per_second', '280000')
        lidar_bp.set_attribute('rotation_frequency', '10')
        lidar_bp.set_attribute('range', '50')
        lidar_transform = carla.Transform(carla.Location(z=2.4))
        self.sensors['lidar'] = self.world.spawn_actor(
            lidar_bp, lidar_transform, attach_to=self.vehicle
        )
        self.sensors['lidar'].listen(self.lidar_callback)
        
        # Radar
        radar_bp = bp_lib.find('sensor.other.radar')
        radar_bp.set_attribute('horizontal_fov', '30')
        radar_bp.set_attribute('range', '100')
        radar_transform = carla.Transform(carla.Location(x=2.0, z=1.0))
        self.sensors['radar'] = self.world.spawn_actor(
            radar_bp, radar_transform, attach_to=self.vehicle
        )
        self.sensors['radar'].listen(self.radar_callback)
        
        # GPS
        gps_bp = bp_lib.find('sensor.other.gnss')
        gps_transform = carla.Transform()
        self.sensors['gps'] = self.world.spawn_actor(
            gps_bp, gps_transform, attach_to=self.vehicle
        )
        self.sensors['gps'].listen(self.gps_callback)
        
        # IMU
        imu_bp = bp_lib.find('sensor.other.imu')
        imu_transform = carla.Transform()
        self.sensors['imu'] = self.world.spawn_actor(
            imu_bp, imu_transform, attach_to=self.vehicle
        )
        self.sensors['imu'].listen(self.imu_callback)
        
        print('✅ All sensors active')
        
        # Spawn surrounding actors for realistic testing (reduced for faster startup)
        print('\n🌍 Spawning traffic for sensor testing...')
        self.spawn_actors(num_vehicles=3, num_pedestrians=2)
    
    def spawn_actors(self, num_vehicles=3, num_pedestrians=2):
        """Spawn surrounding vehicles and pedestrians for sensor testing."""
        try:
            world = self.client.get_world()
            blueprint_library = world.get_blueprint_library()

            # Get spawn points
            spawn_points = world.get_map().get_spawn_points()
            if len(spawn_points) < 1:
                print("❌ No spawn points available")
                return
            
            # Get ego vehicle location for proximity-based spawning
            ego_location = self.vehicle.get_location()
            
            # Filter spawn points to be near the ego vehicle for camera visibility
            nearby_spawn_points = [sp for sp in spawn_points if ego_location.distance(sp.location) < 100]
            if len(nearby_spawn_points) < num_vehicles + num_pedestrians:
                print("⚠️  Limited nearby spawn points, using all available")
                nearby_spawn_points = spawn_points[:max(num_vehicles + num_pedestrians, len(spawn_points))]

            # Spawn vehicles with autopilot
            vehicle_blueprints = blueprint_library.filter('vehicle.*')
            vehicle_blueprints = [bp for bp in vehicle_blueprints if bp.get_attribute('number_of_wheels') == 4]

            print(f"🚗 Spawning {num_vehicles} vehicles (bulk, proximity-based)...")
            # Try to obtain traffic manager port
            try:
                tm = self.client.get_trafficmanager()
                tm_port = tm.get_port()
            except Exception:
                tm = None
                tm_port = None
            for i in range(num_vehicles):
                try:
                    bp = random.choice(vehicle_blueprints)
                    bp.set_attribute('role_name', f'vehicle_{i}')

                    # Try to spawn without collisions, retry a few times with small jitter
                    vehicle = None
                    for attempt in range(6):
                        # Use nearby spawn points for camera visibility
                        spawn_point = random.choice(nearby_spawn_points if nearby_spawn_points else spawn_points)
                        # jitter location slightly to avoid occupied points, especially toward camera field of view
                        jitter_x = random.uniform(-3.0, 8.0)  # Forward/backward (forward for visibility)
                        jitter_y = random.uniform(-2.0, 2.0)  # Left/right
                        jitter = carla.Location(x=jitter_x, y=jitter_y, z=0.0)
                        jittered = carla.Transform(spawn_point.location + jitter, spawn_point.rotation)
                        vehicle = world.try_spawn_actor(bp, jittered)
                        if vehicle is not None:
                            break
                    if vehicle is None:
                        print(f"  ✗ No free spawn for vehicle {i+1} after retries, skipping")
                        continue

                    # Enable autopilot
                    try:
                        if tm_port is not None:
                            vehicle.set_autopilot(True, tm_port)
                        else:
                            vehicle.set_autopilot(True)
                    except Exception:
                        try:
                            vehicle.set_autopilot(True)
                        except Exception:
                            pass
                    self.spawned_actors.append(vehicle)
                    print(f"  ✓ Vehicle {i+1} spawned: {vehicle.type_id}")
                except Exception as e:
                    print(f"  ✗ Failed to spawn vehicle {i+1}: {e}")
                finally:
                    time.sleep(0.02)

            # Spawn pedestrians with AI controller
            pedestrian_blueprints = blueprint_library.filter('walker.pedestrian.*')
            walker_controller_bp = blueprint_library.find('controller.ai.walker')
            print(f"🚶 Spawning {num_pedestrians} pedestrians (bulk)...")

            for i in range(num_pedestrians):
                try:
                    bp = random.choice(pedestrian_blueprints)
                    # jitter spawn locations for walkers too
                    pedestrian = None
                    for attempt in range(6):
                        spawn_point = random.choice(spawn_points)
                        jitter = carla.Location(x=random.uniform(-1.0, 1.0), y=random.uniform(-1.0, 1.0), z=0.0)
                        jittered = carla.Transform(spawn_point.location + jitter, spawn_point.rotation)
                        pedestrian = world.try_spawn_actor(bp, jittered)
                        if pedestrian is not None:
                            break
                    if pedestrian is None:
                        print(f"  ✗ No free spawn for pedestrian {i+1} after retries, skipping")
                        continue
                    self.spawned_actors.append(pedestrian)

                    # Spawn AI controller for pedestrian if available
                    controller = None
                    try:
                        controller = world.try_spawn_actor(walker_controller_bp, carla.Transform(), pedestrian)
                    except Exception:
                        controller = None
                    if controller is None:
                        try:
                            controller = world.try_spawn_actor(walker_controller_bp, carla.Transform())
                        except Exception:
                            controller = None
                    if controller is not None:
                        self.spawned_actors.append(controller)
                        try:
                            controller.start()
                            controller.go_to_location(random.choice(spawn_points).location)
                        except Exception:
                            pass
                    print(f"  ✓ Pedestrian {i+1} spawned")
                except Exception as e:
                    print(f"  ✗ Failed to spawn pedestrian {i+1}: {e}")
                finally:
                    time.sleep(0.01)

            print(f"✅ Spawn attempt finished; total actors tracked: {len(self.spawned_actors)}")

        except Exception as e:
            print(f"❌ Error spawning actors: {e}")
    
    def camera_callback(self, camera_data):
        """Process camera feed with U-Net and bounding boxes"""
        try:
            self.data_count['camera'] += 1
            
            # Check for NULL frames
            if camera_data.raw_data is None or len(camera_data.raw_data) == 0:
                self.data_count['null_frames'] = self.data_count.get('null_frames', 0) + 1
                if self.data_count['camera'] % 30 == 0:
                    print(f"⚠️  NULL frame #{self.data_count['camera']} | Total nulls: {self.data_count['null_frames']}")
                return
            
            if self.data_count['camera'] % 10 == 1:
                print(f"📸 Camera frame #{self.data_count['camera']} received (shape: {camera_data.width}x{camera_data.height})")
            
            # Convert to numpy array
            array = np.frombuffer(camera_data.raw_data, dtype=np.uint8)
            array = array.reshape((camera_data.height, camera_data.width, 4))
            rgb_image = array[:, :, :3]
            
            detections = []
            vis_bbox = rgb_image.copy()
            vis_mask = rgb_image.copy()
            
            # Try U-Net prediction if available
            try:
                # Resize if needed
                if rgb_image.shape != (256, 256, 3):
                    rgb_resized = cv2.resize(rgb_image, (256, 256))
                else:
                    rgb_resized = rgb_image
                
                # Predict segmentation
                img_normalized = np.array([rgb_resized.astype(np.float32) / 255.0])
                prediction = self.unet.predict(img_normalized, verbose=0)[0]
                predicted_mask = np.argmax(prediction, axis=-1)
                
                # Extract bounding boxes
                detections = self.bbox_detector.extract_bboxes(predicted_mask, min_area=50)
                detections = self.bbox_detector.non_max_suppression(detections)
                
                # Log detection stats periodically
                if self.data_count['camera'] % 30 == 1:
                    unique_classes = len(np.unique(predicted_mask))
                    print(f"🎯 Frame {self.data_count['camera']}: {len(detections)} detections | {unique_classes} unique classes")
                
                # Visualize
                vis_blend, vis_mask = visualize_prediction(rgb_resized, prediction)
                vis_bbox = self.bbox_detector.draw_bboxes(rgb_resized, detections)
            except Exception as e:
                print(f"⚠️  U-Net processing error at frame {self.data_count['camera']}: {e}")
                detections = []
                vis_bbox = rgb_image.copy()
                vis_mask = rgb_image.copy()
            
            # Track objects
            tracks = self.tracker.update(detections)
            
            # Store for web interface
            with self.vision_lock:
                self.current_frame = {
                    'rgb': rgb_image,
                    'segmentation': vis_mask,
                    'bbox': vis_bbox,
                    'blend': vis_bbox
                }
                self.current_detections = detections
                self.stats['active_tracks'] = len(tracks)
                self.stats['frame_count'] += 1
                
                # Calculate FPS
                current_time = time.time()
                if hasattr(self, 'last_camera_time'):
                    dt = current_time - self.last_camera_time
                    if dt > 0:
                        fps = 1.0 / dt
                        self.fps_history.append(fps)
                        self.stats['fps'] = np.mean(list(self.fps_history))
                self.last_camera_time = current_time
                # Broadcast layered frame + sensors over WebSocket for external clients (e.g., Foxglove)
                try:
                    if self.loop:
                        message = {
                            'topic': 'layered_frame',
                            'rgb': self._encode_image(self.current_frame['rgb']),
                            'segmentation': self._encode_image(self.current_frame['segmentation']),
                            'bbox': self._encode_image(self.current_frame['bbox']),
                            'detections': self.current_detections,
                            'stats': self.stats.copy()
                        }

                        # Attach LiDAR and Radar if available (hex encoded bytes)
                        if getattr(self, 'latest_lidar_points', None) is not None:
                            points_to_send = self.latest_lidar_points[::5]
                            message['lidarPoints'] = points_to_send.tobytes().hex()
                        if getattr(self, 'latest_radar_objects', None) is not None:
                            message['radarObjects'] = self.latest_radar_objects.tobytes().hex()

                        asyncio.run_coroutine_threadsafe(
                            self.data_ws.send_message(message),
                            self.loop
                        )
                except Exception:
                    pass
                
        except Exception as e:
            print(f"❌ Camera error: {e}")
    
    def lidar_callback(self, lidar_data):
        """Process LiDAR"""
        try:
            self.data_count['lidar'] += 1
        
            points = np.frombuffer(lidar_data.raw_data, dtype=np.float32)
            points = points.reshape(-1, 4)
            
            self.stats['lidar_points'] = len(points)
        
            # Store full points for visualization
            with self.vision_lock:
                self.latest_lidar_points = points.copy()
            
            # Downsample for web viz
            points_ds = points[::5]
        
            # Send to web viz
            if self.loop:
                message = {
                    'type': 'lidar',
                    'data': base64.b64encode(points_ds.tobytes()).decode('ascii')
                }
                asyncio.run_coroutine_threadsafe(
                    self.data_ws.send_message(message),
                    self.loop
                )
                
        except Exception as e:
            print(f"❌ LiDAR error: {e}")
    
    def radar_callback(self, radar_data):
        """Process Radar"""
        self.data_count['radar'] += 1
        
        # Extract radar detections for visualization
        radar_points = []
        for detection in radar_data:
            # Convert radar coordinates to world coordinates
            # Radar uses spherical coordinates: depth, azimuth, altitude
            depth = detection.depth
            azimuth = detection.azimuth
            altitude = detection.altitude
            
            # Convert to Cartesian coordinates
            x = depth * np.cos(altitude) * np.cos(azimuth)
            y = depth * np.cos(altitude) * np.sin(azimuth)
            z = depth * np.sin(altitude)
            
            radar_points.append([x, y, z, detection.velocity])
        
        # Store for visualization
        if radar_points:
            with self.vision_lock:
                self.latest_radar_objects = np.array(radar_points, dtype=np.float32)
        
        # Send radar data to web viz
        if self.loop and radar_points:
            radar_array = np.array(radar_points, dtype=np.float32)
            message = {
                'type': 'radar',
                'data': base64.b64encode(radar_array.tobytes()).decode('ascii'),
                'count': len(radar_points)
            }
            asyncio.run_coroutine_threadsafe(
                self.data_ws.send_message(message),
                self.loop
            )
        
        # Use for UKF
        velocities = [d.velocity for d in radar_data]
        if velocities:
            avg_velocity = np.mean(velocities)
            self.update_ukf_with_radar(avg_velocity)
    
    def gps_callback(self, gps_data):
        """Process GPS"""
        try:
            self.data_count['gps'] += 1
            
            if self.gps_origin is None:
                self.gps_origin = (gps_data.latitude, gps_data.longitude, gps_data.altitude)
                print(f"📍 GPS origin: {self.gps_origin}")
            
            # Send to web viz
            if self.loop:
                message = {
                    'type': 'gps',
                    'latitude': gps_data.latitude,
                    'longitude': gps_data.longitude,
                    'altitude': gps_data.altitude
                }
                asyncio.run_coroutine_threadsafe(
                    self.data_ws.send_message(message),
                    self.loop
                )
            
            self.update_ukf_with_gps(gps_data)
            
        except Exception as e:
            print(f"GPS error: {e}")
    
    def imu_callback(self, imu_data):
        """Process IMU"""
        self.data_count['imu'] += 1
        
        current_time = time.time()
        dt = current_time - self.last_time
        self.last_time = current_time
        
        if 0 < dt < 1.0:
            self.ukf.predict(dt)
            self.ukf.x[9] = imu_data.gyroscope.z
    
    def update_ukf_with_gps(self, gps_data):
        """Update UKF with GPS"""
        if self.gps_origin is None:
            return
        
        x = (gps_data.longitude - self.gps_origin[1]) * 111320.0 * np.cos(np.radians(self.gps_origin[0]))
        y = (gps_data.latitude - self.gps_origin[0]) * 110540.0
        z = gps_data.altitude - self.gps_origin[2]
        
        measurement = np.array([x, y, z, self.ukf.x[3], self.ukf.x[4], self.ukf.x[5]])
        
        R_gps = np.eye(6)
        R_gps[0:3, 0:3] *= 2.0
        R_gps[3:6, 3:6] *= 10.0
        
        self.ukf.update(measurement, R=R_gps)
        self.publish_fused_state()
    
    def update_ukf_with_radar(self, velocity):
        """Update UKF with radar"""
        measurement = np.array([
            self.ukf.x[0], self.ukf.x[1], self.ukf.x[2],
            velocity, 0.0, 0.0
        ])
        
        R_radar = np.eye(6)
        R_radar[0:3, 0:3] *= 100.0
        R_radar[3:6, 3:6] *= 0.5
        
        self.ukf.update(measurement, R=R_radar)
    
    def publish_fused_state(self):
        """Publish fused pose"""
        try:
            # Send to web viz
            if self.loop:
                message = {
                    'type': 'pose',
                    'position': {
                        'x': float(self.ukf.x[0]),
                        'y': float(self.ukf.x[1]),
                        'z': float(self.ukf.x[2])
                    }
                }
                asyncio.run_coroutine_threadsafe(
                    self.data_ws.send_message(message),
                    self.loop
                )
                
        except Exception as e:
            print(f"Pose error: {e}")
    
    def update_spectator(self):
        """Update camera"""
        if self.vehicle:
            spectator = self.world.get_spectator()
            transform = self.vehicle.get_transform()
            spectator.set_transform(carla.Transform(
                transform.location + carla.Location(x=-8, z=4),
                carla.Rotation(pitch=-15, yaw=transform.rotation.yaw)
            ))
    
    def get_frame_data(self):
        """Get current frame data for web interface"""
        with self.vision_lock:
            if self.current_frame is None:
                return None
            
            # Calculate unique segmentation classes for stats
            seg_image = self.current_frame['segmentation']
            unique_classes = len(np.unique(cv2.cvtColor(seg_image, cv2.COLOR_RGB2GRAY))) if seg_image is not None else 0
            
            frame_data = {
                'rgb': self._encode_image(self.current_frame['rgb']),
                'segmentation': self._encode_image(self.current_frame['segmentation']),
                'bbox': self._encode_image(self.current_frame['bbox']),
                'detections': self.current_detections,
                'unique_classes': unique_classes,
                'stats': self.stats.copy()
            }
            
            # Include LiDAR points if available
            if self.latest_lidar_points is not None:
                # Downsample points for web transfer
                points_to_send = self.latest_lidar_points[::5]
                frame_data['lidarPoints'] = points_to_send.tobytes().hex()
            
            # Include Radar objects if available
            if self.latest_radar_objects is not None:
                frame_data['radarObjects'] = self.latest_radar_objects.tobytes().hex()
            
            return frame_data
    
    def _encode_image(self, image):
        """Encode image to base64"""
        _, buffer = cv2.imencode('.jpg', cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        return base64.b64encode(buffer).decode('utf-8')
    
    def cleanup(self):
        """Cleanup"""
        print("\n🧹 Cleaning up...")
        for sensor in self.sensors.values():
            if sensor:
                sensor.destroy()
        if self.vehicle:
            self.vehicle.destroy()
        print("✅ Cleanup done")


# ============================================================================
# FLASK WEB SERVER
# ============================================================================

app = Flask(__name__)
CORS(app)

# Global perception instance
perception_instance = None


@app.route('/')
def index():
    """Serve main HTML page"""
    return HTML_CONTENT


@app.route('/api/start', methods=['POST'])
def start_processing():
    """Start processing"""
    return jsonify({'status': 'started'})


@app.route('/api/stop', methods=['POST'])
def stop_processing():
    """Stop processing"""
    return jsonify({'status': 'stopped'})


@app.route('/api/frame')
def get_frame():
    """Get current frame data"""
    if perception_instance is None:
        return jsonify({'error': 'System not ready'}), 503
    
    data = perception_instance.get_frame_data()
    if data is None:
        return jsonify({'error': 'No frame available'}), 404
    return jsonify(data)


@app.route('/api/stats')
def get_stats():
    """Get statistics"""
    if perception_instance is None:
        return jsonify({'error': 'System not ready'}), 503
    
    return jsonify(perception_instance.stats)


@app.route('/api/health')
def health_check():
    """Health check endpoint for diagnostics"""
    if perception_instance is None:
        return jsonify({
            'status': 'error',
            'message': 'Perception system not initialized'
        }), 503
    
    return jsonify({
        'status': 'ok',
        'carla_connected': perception_instance.world is not None,
        'vehicle_spawned': perception_instance.vehicle is not None,
        'sensors_active': len(perception_instance.sensors),
        'camera_frames': perception_instance.data_count.get('camera', 0),
        'lidar_frames': perception_instance.data_count.get('lidar', 0),
        'radar_frames': perception_instance.data_count.get('radar', 0),
        'spawned_actors': len(perception_instance.spawned_actors),
        'current_fps': perception_instance.stats.get('fps', 0)
    })


async def run_data_ws(perception):
    """Run data WebSocket server"""
    await perception.data_ws.start()


def main():
    """Main"""
    global perception_instance
    
    print("=" * 60)
    print("🚗 CARLA Perception Stack with UKF + Vision System")
    print("=" * 60)
    
    perception_instance = PerceptionStack()
    
    print("\n[1/5] Connecting to CARLA...")
    if not perception_instance.connect_to_carla():
        print("\n❌ Start CARLA first: CarlaUE4.exe")
        return
    
    print("[2/5] Spawning vehicle...")
    if not perception_instance.spawn_vehicle():
        return
    
    time.sleep(1)
    
    print("[3/5] Setting up sensors...")
    perception_instance.setup_sensors()
    
    print("[4/5] Starting servers...")
    
    # Start WebSocket server in thread
    def run_server():
        perception_instance.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(perception_instance.loop)
        perception_instance.loop.run_until_complete(run_data_ws(perception_instance))
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Start Flask server in thread
    def run_flask():
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    time.sleep(2)
    
    print("\n" + "=" * 60)
    print("✅ SYSTEM READY!")
    print("=" * 60)
    print("🌐 Web Dashboard: http://localhost:5000")
    print("🌐 WebSocket: ws://localhost:8765")
    print("\n📊 Data Streams:")
    print("   • Camera - RGB + Segmentation + BBoxes")
    print("   • LiDAR - Point cloud")
    print("   • Radar - Detections")
    print("   • GPS - Position data")
    print("   • UKF - Fused pose estimate")
    print("\n⌨️  Press Ctrl+C to stop")
    print("=" * 60 + "\n")
    
    try:
        while True:
            perception_instance.update_spectator()
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n")
        perception_instance.cleanup()


if __name__ == '__main__':
    main()