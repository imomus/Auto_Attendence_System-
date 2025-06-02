import sys
import cv2
import face_recognition
import numpy as np
import os
import pickle
import shutil
import json
from datetime import datetime
import threading
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from reportlab.pdfgen import canvas
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QWidget, QTableWidget, QTableWidgetItem,
                            QHeaderView, QFileDialog, QLineEdit, QMessageBox, QFrame,
                            QStatusBar, QTabWidget, QGroupBox, QFormLayout, QComboBox,
                            QListWidget, QListWidgetItem, QSplitter, QTextEdit, QCheckBox,
                            QProgressBar, QDialog, QDialogButtonBox, QScrollArea, QSizePolicy,
                            QCalendarWidget)
from PyQt5.QtGui import QImage, QPixmap, QFont, QIcon, QColor, QPalette
from PyQt5.QtCore import Qt, QTimer, pyqtSlot, QThread, pyqtSignal, QDate
from attendance_manager import AttendanceManager, AttendanceChartWidget


# Thread class for face recognition to prevent GUI freezing
class FaceRecognitionThread(QThread):
    update_frame = pyqtSignal(np.ndarray, list, list, list)
    update_attendance = pyqtSignal(str, str)
    
    def __init__(self, known_face_encodings, known_face_names, threshold=0.45):
        super().__init__()
        self.known_face_encodings = known_face_encodings
        self.known_face_names = known_face_names
        self.threshold = threshold
        self.running = False
        self.video_capture = None
        
    def run(self):
        try:
            self.running = True
            self.video_capture = cv2.VideoCapture(0)
            
            if not self.video_capture.isOpened():
                print("Error: Could not open camera")
                return
                
            while self.running:
                ret, frame = self.video_capture.read()
                if not ret:
                    print("Error: Could not read frame")
                    continue
                    
                try:
                    # Process at smaller scale for performance
                    small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
                    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                    
                    # Find faces
                    face_locations = face_recognition.face_locations(rgb_small_frame)
                    face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
                    
                    # Scale face locations back to original size
                    face_locations_original = [(top * 2, right * 2, bottom * 2, left * 2) 
                                           for top, right, bottom, left in face_locations]
                    
                    recognized_names = []
                    
                    for face_encoding in face_encodings:
                        name = "Unknown"
                        if len(self.known_face_encodings) > 0:
                            face_distances = face_recognition.face_distance(
                                self.known_face_encodings, face_encoding
                            )
                            best_match_index = np.argmin(face_distances)
                            
                            if face_distances[best_match_index] < self.threshold:
                                name = self.known_face_names[best_match_index]
                                # Signal to update attendance
                                self.update_attendance.emit(
                                    name, 
                                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                )
                        
                        recognized_names.append(name)
                    
                    # Update the frame
                    self.update_frame.emit(frame, face_locations_original, recognized_names, face_encodings)
                    
                except Exception as e:
                    print(f"Error processing frame: {e}")
                    continue
                    
        except Exception as e:
            print(f"Camera error: {e}")
        finally:
            self.cleanup()
    
    def stop(self):
        self.running = False
        self.cleanup()
        self.wait()
    
    def cleanup(self):
        """Clean up camera resources"""
        if self.video_capture is not None:
            self.video_capture.release()
            self.video_capture = None


# Thread class for loading student data
class LoadStudentsThread(QThread):
    finished = pyqtSignal(list, list, int)
    progress = pyqtSignal(str)
    
    def __init__(self, directory):
        super().__init__()
        self.directory = directory
        
    def run(self):
        known_face_encodings = []
        known_face_names = []
        students_encodings = {}
        loaded_count = 0
        
        self.progress.emit("Starting to load student images...")
        
        for filename in os.listdir(self.directory):
            if filename.endswith(".jpg") or filename.endswith(".png"):
                try:
                    name = "_".join(filename.split("_")[:-1])  # Extract student name before underscore number
                    img_path = os.path.join(self.directory, filename)
                    
                    self.progress.emit(f"Processing image: {filename}")
                    
                    # Use OpenCV first (faster loading)
                    img = cv2.imread(img_path)
                    if img is None:
                        self.progress.emit(f"Couldn't read image: {filename}")
                        continue
                        
                    # Convert for face_recognition
                    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    encodings = face_recognition.face_encodings(rgb_img)
                    
                    if encodings:  # Ensure at least one encoding exists
                        if name in students_encodings:
                            students_encodings[name].append(encodings[0])
                        else:
                            students_encodings[name] = [encodings[0]]
                        loaded_count += 1
                        self.progress.emit(f"Successfully processed {name}")
                except Exception as e:
                    self.progress.emit(f"Error processing {filename}: {str(e)}")
        
        # Average encodings for each student
        for name, encodings in students_encodings.items():
            known_face_encodings.append(np.mean(encodings, axis=0))
            known_face_names.append(name)
            
        self.finished.emit(known_face_encodings, known_face_names, loaded_count)


# Dialog for creating new encoding sets
class CreateEncodingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Encoding Set")
        self.setMinimumSize(600, 400)  # Larger minimum size
        self.resize(700, 500)  # Default size
        
        # Enable resizing
        self.setSizeGripEnabled(True)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        
        # Main layout with margins
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Create a scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(15)
        
        # Instructions with better styling
        info_label = QLabel("Create a new face encoding dataset from a folder of images.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("""
            color: #666;
            font-style: italic;
            margin-bottom: 10px;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 8px;
            border: 1px solid #dee2e6;
        """)
        layout.addWidget(info_label)
        
        # Form group with border
        form_group = QGroupBox("Dataset Information")
        form_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #d2d2d7;
                border-radius: 8px;
                margin-top: 15px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px;
            }
        """)
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(15)
        
        # Name input with better styling
        self.name_input = QLineEdit()
        self.name_input.setMinimumHeight(40)
        self.name_input.setPlaceholderText("e.g., Class_2024_Spring, Department_Staff")
        self.name_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #d2d2d7;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #0071e3;
            }
        """)
        form_layout.addRow("Dataset Name:", self.name_input)
        
        # Description input with better styling
        self.description_input = QTextEdit()
        self.description_input.setMinimumHeight(100)
        self.description_input.setPlaceholderText("Optional: Describe this dataset (e.g., Computer Science Class 2024)")
        self.description_input.setStyleSheet("""
            QTextEdit {
                border: 2px solid #d2d2d7;
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
                background-color: white;
            }
            QTextEdit:focus {
                border-color: #0071e3;
            }
        """)
        form_layout.addRow("Description:", self.description_input)
        
        layout.addWidget(form_group)
        
        # Directory selection with border and better styling
        dir_group = QGroupBox("Image Directory")
        dir_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #d2d2d7;
                border-radius: 8px;
                margin-top: 15px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px;
            }
        """)
        dir_layout = QVBoxLayout(dir_group)
        
        self.dir_label = QLabel("No directory selected")
        self.dir_label.setStyleSheet("""
            color: #666;
            font-style: italic;
            border: 1px dashed #ccc;
            padding: 15px;
            border-radius: 8px;
            background-color: white;
        """)
        self.select_dir_button = QPushButton("Select Image Folder")
        self.select_dir_button.setMinimumHeight(40)
        self.select_dir_button.clicked.connect(self.select_directory)
        
        dir_layout.addWidget(self.dir_label)
        dir_layout.addWidget(self.select_dir_button)
        layout.addWidget(dir_group)
        
        # Instructions for image naming with better styling
        naming_group = QGroupBox("Image Naming Instructions")
        naming_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #d2d2d7;
                border-radius: 8px;
                margin-top: 15px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px;
            }
        """)
        naming_layout = QVBoxLayout(naming_group)
        
        naming_info = QLabel("""
        • Use format: 'StudentName_1.jpg', 'StudentName_2.jpg', etc.
        • Multiple images per person improve recognition accuracy
        • Supported formats: JPG, PNG
        • Face should be clearly visible in images
        • Good lighting conditions recommended
        """)
        naming_info.setWordWrap(True)
        naming_info.setStyleSheet("""
            padding: 15px;
            background-color: #f0f8ff;
            border-radius: 8px;
            border: 1px solid #b3d7ff;
        """)
        naming_layout.addWidget(naming_info)
        layout.addWidget(naming_group)
        
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        
        # Buttons with better styling
        button_layout = QHBoxLayout()
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.setStyleSheet("""
            QPushButton {
                min-width: 100px;
                min-height: 40px;
            }
        """)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        button_layout.addWidget(buttons)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        self.selected_directory = None
    
    def select_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Select Image Directory", "", QFileDialog.ShowDirsOnly
        )
        if directory:
            self.selected_directory = directory
            self.dir_label.setText(f"Selected: {os.path.basename(directory)}")
            self.dir_label.setStyleSheet("""
                color: #007acc;
                font-weight: bold;
                border: 2px solid #007acc;
                padding: 15px;
                border-radius: 8px;
                background-color: #f8f9fa;
            """)
    
    def accept(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Missing Name", "Please enter a name for the encoding dataset.")
            return
        if not self.selected_directory:
            QMessageBox.warning(self, "Missing Directory", "Please select a directory containing images.")
            return
        super().accept()
    
    def get_data(self):
        return {
            'name': self.name_input.text().strip(),
            'description': self.description_input.toPlainText().strip(),
            'directory': self.selected_directory
        }


# Enhanced Attendance System with Encoding Management
class AttendanceSystem(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Initialize directories
        self.encodings_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'encodings')
        self.attendance_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'attendance_records')
        os.makedirs(self.encodings_directory, exist_ok=True)
        os.makedirs(self.attendance_directory, exist_ok=True)
        
        # Initialize attendance manager
        self.attendance_manager = AttendanceManager(os.path.dirname(os.path.abspath(__file__)))
        
        # Initialize email settings
        self.teacher_email = ""
        self.sender_email = ""
        self.app_password = ""
        
        # Initialize attendance data
        self.present_students = {}
        self.known_face_encodings = []
        self.known_face_names = []
        self.camera_active = False
        
        # Load email settings
        self.load_email_settings()
        
        # Set window properties
        self.setWindowTitle("Smart Attendance System with Encoding Management")
        self.setGeometry(100, 100, 1400, 900)
        # Enable window resizing
        self.setMinimumSize(1000, 700)  # Minimum window size
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Apply Apple-like styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f7;
            }
            QLabel {
                font-family: 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif;
                color: #1d1d1f;
                font-size: 16px;
            }
            QPushButton {
                background-color: #0071e3;
                color: white;
                border-radius: 10px;
                padding: 14px 28px;
                font-weight: bold;
                border: none;
                min-height: 24px;
                font-size: 16px;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #0077ed;
                transform: translateY(-1px);
            }
            QPushButton:pressed {
                background-color: #0068d1;
                transform: translateY(0px);
            }
            QPushButton:disabled {
                background-color: #a1a1a6;
            }
            QPushButton.secondary {
                background-color: #8e8e93;
            }
            QPushButton.secondary:hover {
                background-color: #98989d;
            }
            QPushButton.danger {
                background-color: #ff3b30;
            }
            QPushButton.danger:hover {
                background-color: #ff4d42;
            }
            QPushButton.success {
                background-color: #34c759;
            }
            QPushButton.success:hover {
                background-color: #30d158;
            }
            QTableWidget {
                border: 1px solid #d2d2d7;
                border-radius: 8px;
                alternate-background-color: #f5f5f7;
                gridline-color: #d2d2d7;
            }
            QListWidget {
                border: 1px solid #d2d2d7;
                border-radius: 8px;
                alternate-background-color: #f5f5f7;
                selection-background-color: #0071e3;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #e5e5e7;
            }
            QListWidget::item:selected {
                background-color: #0071e3;
                color: white;
            }
            QHeaderView::section {
                background-color: #f5f5f7;
                padding: 10px;
                font-weight: bold;
                border: none;
                border-bottom: 2px solid #d2d2d7;
            }
            QTabWidget::pane {
                border: 1px solid #d2d2d7;
                border-radius: 8px;
                padding: 5px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #e8e8ed;
                padding: 12px 24px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 3px solid #0071e3;
            }
            QGroupBox {
                border: 2px solid #d2d2d7;
                border-radius: 10px;
                margin-top: 15px;
                padding-top: 20px;
                font-weight: bold;
                font-size: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px;
                background-color: #f5f5f7;
            }
            QLineEdit {
                border: 2px solid #d2d2d7;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #0071e3;
            }
            QComboBox {
                border: 2px solid #d2d2d7;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
            }
            QTextEdit {
                border: 2px solid #d2d2d7;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
            }
            QProgressBar {
                border: 2px solid #d2d2d7;
                border-radius: 8px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #0071e3;
                border-radius: 6px;
            }
        """)
        
        # Set up the main UI
        self.setup_ui()
        
        # Load available encoding sets
        self.refresh_encoding_sets()
        
        self.statusBar().showMessage("Ready. Create or load an encoding dataset to begin face recognition.")
    
    def setup_ui(self):
        # Main widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Header with modern styling
        header_layout = QHBoxLayout()
        logo_label = QLabel("🎯")
        logo_label.setFont(QFont("Arial", 28))
        title_label = QLabel("Smart Attendance System")
        title_label.setFont(QFont("SF Pro Display", 26, QFont.Bold))
        title_label.setStyleSheet("color: #0071e3;")
        
        # Add Analytics Button in header
        self.analytics_button = QPushButton("📊 View Analytics")
        self.analytics_button.clicked.connect(self.show_analytics)
        self.analytics_button.setStyleSheet("""
            QPushButton {
                background-color: #34c759;
                padding: 10px 20px;
                border-radius: 8px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #30d158;
            }
        """)
        
        header_layout.addWidget(logo_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.analytics_button)
        
        main_layout.addLayout(header_layout)
        
        # Create tab widget
        tab_widget = QTabWidget()
        
        # Tab 1: Face Recognition
        recognition_tab = QWidget()
        recognition_layout = QVBoxLayout(recognition_tab)
        
        # Main content area
        content_layout = QHBoxLayout()
        
        # Left panel: Camera feed
        camera_group = QGroupBox("📹 Live Camera Feed")
        camera_layout = QVBoxLayout(camera_group)
        
        self.camera_label = QLabel()
        self.camera_label.setFixedSize(640, 480)  # Fixed size instead of min/max
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setStyleSheet("""
            border: 3px solid #d2d2d7; 
            border-radius: 12px; 
            background-color: #1d1d1f; 
            color: white;
            font-size: 16px;
        """)
        self.camera_label.setText("📷\nCamera feed will appear here\nLoad an encoding dataset first")
        
        camera_layout.addWidget(self.camera_label, 0, Qt.AlignCenter)  # Center align the camera feed
        
        camera_buttons_layout = QHBoxLayout()
        camera_buttons_layout.setSpacing(20)  # Add space between buttons
        camera_buttons_layout.setContentsMargins(10, 20, 10, 20)  # Add padding around buttons
        
        # Calculate button width based on camera width
        button_width = (640 - 20) // 2  # Camera width minus spacing, divided by 2
        
        self.start_button = QPushButton("🚀 Start Recognition")
        self.start_button.clicked.connect(self.toggle_camera)
        self.start_button.setEnabled(False)
        self.start_button.setFixedSize(button_width, 50)  # Fixed width matching camera
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #34c759;
                color: white;
                border: none;
                border-radius: 25px;
                padding: 10px 30px;
                font-size: 16px;
                font-weight: bold;
                transition: all 0.3s;
            }
            QPushButton:hover {
                background-color: #30d158;
                transform: translateY(-2px);
                box-shadow: 0 4px 10px rgba(52, 199, 89, 0.3);
            }
            QPushButton:pressed {
                background-color: #2cc54e;
                transform: translateY(1px);
                box-shadow: 0 2px 5px rgba(52, 199, 89, 0.2);
            }
            QPushButton:disabled {
                background-color: #8e8e93;
                box-shadow: none;
            }
        """)
        
        self.stop_button = QPushButton("⏹️ Stop Recognition")
        self.stop_button.clicked.connect(self.toggle_camera)
        self.stop_button.setEnabled(False)
        self.stop_button.setFixedSize(button_width, 50)  # Fixed width matching camera
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #ff3b30;
                color: white;
                border: none;
                border-radius: 25px;
                padding: 10px 30px;
                font-size: 16px;
                font-weight: bold;
                transition: all 0.3s;
            }
            QPushButton:hover {
                background-color: #ff4d42;
                transform: translateY(-2px);
                box-shadow: 0 4px 10px rgba(255, 59, 48, 0.3);
            }
            QPushButton:pressed {
                background-color: #ff3226;
                transform: translateY(1px);
                box-shadow: 0 2px 5px rgba(255, 59, 48, 0.2);
            }
            QPushButton:disabled {
                background-color: #8e8e93;
                box-shadow: none;
            }
        """)
        
        camera_buttons_layout.addStretch(1)  # Add flexible space before buttons
        camera_buttons_layout.addWidget(self.start_button)
        camera_buttons_layout.addWidget(self.stop_button)
        camera_buttons_layout.addStretch(1)  # Add flexible space after buttons
        camera_layout.addLayout(camera_buttons_layout)
        
        # Right panel: Attendance List
        attendance_group = QGroupBox("📋 Today's Attendance")
        attendance_layout = QVBoxLayout(attendance_group)
        
        # Attendance statistics
        stats_layout = QHBoxLayout()
        self.total_students_label = QLabel("Total Students: 0")
        self.present_count_label = QLabel("Present: 0")
        self.absent_count_label = QLabel("Absent: 0")
        
        stats_layout.addWidget(self.total_students_label)
        stats_layout.addWidget(self.present_count_label)
        stats_layout.addWidget(self.absent_count_label)
        stats_layout.addStretch()
        attendance_layout.addLayout(stats_layout)
        
        self.attendance_table = QTableWidget(0, 2)
        self.attendance_table.setHorizontalHeaderLabels(["👤 Student Name", "🕒 Check-in Time"])
        self.attendance_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.attendance_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.attendance_table.setAlternatingRowColors(True)
        
        attendance_layout.addWidget(self.attendance_table)
        
        attendance_buttons_layout = QHBoxLayout()
        self.clear_attendance_button = QPushButton("🗑️ Clear All")
        self.clear_attendance_button.clicked.connect(self.clear_attendance)
        self.clear_attendance_button.setProperty("class", "secondary")
        self.clear_attendance_button.setStyleSheet("QPushButton { background-color: #8e8e93; }")
        
        self.generate_report_button = QPushButton("📄 Generate Report")
        self.generate_report_button.clicked.connect(self.generate_report)
        self.generate_report_button.setEnabled(False)
        
        self.send_email_button = QPushButton("📧 Send Email")
        self.send_email_button.clicked.connect(self.send_email)
        self.send_email_button.setEnabled(False)
        
        attendance_buttons_layout.addWidget(self.clear_attendance_button)
        attendance_buttons_layout.addWidget(self.generate_report_button)
        attendance_buttons_layout.addWidget(self.send_email_button)
        attendance_layout.addLayout(attendance_buttons_layout)
        
        # Add both panels to content layout
        content_layout.addWidget(camera_group, 60)
        content_layout.addWidget(attendance_group, 40)
        
        recognition_layout.addLayout(content_layout)
        
        # Bottom panel: Current Encoding Set Info
        current_set_group = QGroupBox("📂 Current Dataset")
        current_set_layout = QHBoxLayout(current_set_group)
        
        status_layout = QVBoxLayout()
        self.current_set_label = QLabel("No encoding dataset loaded")
        self.current_set_label.setStyleSheet("color: #8e8e93; font-style: italic; font-size: 14px;")
        
        self.status_indicator = QLabel("⚫ Not Ready")
        self.status_indicator.setStyleSheet("color: #ff3b30; font-weight: bold; font-size: 16px;")
        status_layout.addWidget(self.current_set_label)
        status_layout.addWidget(self.status_indicator)
        current_set_layout.addLayout(status_layout)
        
        self.load_different_button = QPushButton("📁 Load Different Dataset")
        self.load_different_button.clicked.connect(lambda: tab_widget.setCurrentIndex(1))
        self.load_different_button.setProperty("class", "secondary")
        self.load_different_button.setStyleSheet("QPushButton { background-color: #8e8e93; }")
        
        current_set_layout.addWidget(self.current_set_label)
        current_set_layout.addStretch()
        current_set_layout.addWidget(self.load_different_button)
        
        recognition_layout.addWidget(current_set_group)
        
        # Add tab to tab widget
        tab_widget.addTab(recognition_tab, "🎯 Face Recognition")
        
        
        # Tab 2: Encoding Management (Enhanced)
        encoding_tab = QWidget()
        encoding_layout = QVBoxLayout(encoding_tab)
        
        # Title with instructions
        encoding_header_layout = QVBoxLayout()
        encoding_title = QLabel("🧠 Face Encoding Dataset Management")
        encoding_title.setFont(QFont("SF Pro Display", 20, QFont.Bold))
        encoding_title.setStyleSheet("color: #0071e3; margin-bottom: 10px;")
        
        instruction_label = QLabel("Create and manage face encoding datasets for different classes or groups. Each dataset can contain multiple students.")
        instruction_label.setWordWrap(True)
        instruction_label.setStyleSheet("color: #666; font-style: italic; margin-bottom: 20px;")
        
        encoding_header_layout.addWidget(encoding_title)
        encoding_header_layout.addWidget(instruction_label)
        encoding_layout.addLayout(encoding_header_layout)
        
        # Split layout for ety encoding sets and details
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side: Encoding sets list with enhanced UI
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        sets_group = QGroupBox("💾 Available Datasets")
        sets_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #d2d2d7;
                border-radius: 8px;
                margin-top: 15px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px;
            }
        """)
        sets_layout = QVBoxLayout(sets_group)
        
        # Quick action buttons at the top
        quick_actions_layout = QHBoxLayout()
        self.create_set_button = QPushButton("➕ Create New Dataset")
        self.create_set_button.clicked.connect(self.create_new_encoding_set)
        self.create_set_button.setStyleSheet("QPushButton { background-color: #34c759; } QPushButton:hover { background-color: #30d158; }")
        
        self.refresh_button = QPushButton("🔄 Refresh")
        self.refresh_button.clicked.connect(self.refresh_encoding_sets)
        self.refresh_button.setProperty("class", "secondary")
        self.refresh_button.setStyleSheet("QPushButton { background-color: #8e8e93; }")
        
        quick_actions_layout.addWidget(self.create_set_button)
        quick_actions_layout.addWidget(self.refresh_button)
        sets_layout.addLayout(quick_actions_layout)
        
        self.encoding_sets_list = QListWidget()
        self.encoding_sets_list.itemClicked.connect(self.on_encoding_set_selected)
        self.encoding_sets_list.setMinimumHeight(200)
        sets_layout.addWidget(self.encoding_sets_list)
        
        # Action buttons for selected dataset
        sets_buttons_layout = QHBoxLayout()
        
        self.load_set_button = QPushButton("📂 Load Selected")
        self.load_set_button.clicked.connect(self.load_selected_encoding_set)
        self.load_set_button.setEnabled(False)
        
        self.delete_set_button = QPushButton("🗑️ Delete Selected")
        self.delete_set_button.clicked.connect(self.delete_selected_encoding_set)
        self.delete_set_button.setEnabled(False)
        self.delete_set_button.setStyleSheet("QPushButton { background-color: #ff3b30; } QPushButton:hover { background-color: #ff4d42; }")
        
        sets_buttons_layout.addWidget(self.load_set_button)
        sets_buttons_layout.addWidget(self.delete_set_button)
        
        sets_layout.addLayout(sets_buttons_layout)
        left_layout.addWidget(sets_group)
        
        # Right side: Encoding set details with enhanced display
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        details_group = QGroupBox("📊 Dataset Information")
        details_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #d2d2d7;
                border-radius: 8px;
                margin-top: 15px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px;
            }
        """)
        details_layout = QVBoxLayout(details_group)
        
        # Scrollable details area
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(180)
        self.details_text.setStyleSheet("background-color: #f8f9fa; border: 1px solid #dee2e6;")
        scroll_layout.addWidget(self.details_text)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        details_layout.addWidget(scroll_area)
        
        # Students in selected set with search
        students_group = QGroupBox("👥 Students in Dataset")
        students_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #d2d2d7;
                border-radius: 8px;
                margin-top: 15px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px;
            }
        """)
        students_layout = QVBoxLayout(students_group)
        
        # Search functionality
        search_layout = QHBoxLayout()
        search_label = QLabel("🔍 Search:")
        self.student_search = QLineEdit()
        self.student_search.setPlaceholderText("Type to search students...")
        self.student_search.textChanged.connect(self.filter_students)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.student_search)
        students_layout.addLayout(search_layout)
        
        self.students_list = QListWidget()
        self.students_list.setMinimumHeight(150)
        students_layout.addWidget(self.students_list)
        
        # Student count label
        self.student_count_label = QLabel("Total: 0 students")
        self.student_count_label.setStyleSheet("color: #666; font-style: italic;")
        students_layout.addWidget(self.student_count_label)
        
        details_layout.addWidget(students_group)
        right_layout.addWidget(details_group)
        
        # Progress bar for operations
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("margin: 10px 0;")
        right_layout.addWidget(self.progress_bar)
        
        # Progress label
        self.progress_label = QLabel()
        self.progress_label.setVisible(False)
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setStyleSheet("color: #0071e3; font-weight: bold;")
        right_layout.addWidget(self.progress_label)
        
        # Add widgets to splitter
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([350, 450])
        
        encoding_layout.addWidget(splitter)
        
        # Add tab to tab widget
        tab_widget.addTab(encoding_tab, "🧠 Dataset Manager")
        
        # Tab 3: Settings (Enhanced)
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        
        settings_title = QLabel("⚙️ System Settings")
        settings_title.setFont(QFont("SF Pro Display", 20, QFont.Bold))
        settings_title.setStyleSheet("color: #0071e3; margin-bottom: 20px;")
        settings_layout.addWidget(settings_title)
        
        # Email Settings
        email_group = QGroupBox("📧 Email Configuration")
        email_form = QFormLayout(email_group)
        
        self.teacher_email_input = QLineEdit(self.teacher_email)
        self.sender_email_input = QLineEdit(self.sender_email)
        self.app_password_input = QLineEdit()
        self.app_password_input.setEchoMode(QLineEdit.Password)
        self.app_password_input.setText(self.app_password)
        
        email_form.addRow("📮 Teacher's Email:", self.teacher_email_input)
        email_form.addRow("📤 Sender Email:", self.sender_email_input)
        email_form.addRow("🔐 App Password:", self.app_password_input)
        
        # Email info label
        email_info = QLabel("💡 For Gmail: Use App Password (not regular password)\nGo to Google Account → Security → App passwords")
        email_info.setWordWrap(True)
        email_info.setStyleSheet("color: #666; font-style: italic; background-color: #f0f8ff; padding: 10px; border-radius: 5px; margin: 10px 0;")
        email_form.addRow(email_info)
        
        # Save email settings button
        save_email_button = QPushButton("💾 Save Email Settings")
        save_email_button.clicked.connect(self.save_email_settings)
        email_form.addRow(save_email_button)
        
        settings_layout.addWidget(email_group)
        
        # Recognition Settings
        recognition_group = QGroupBox("🎯 Recognition Settings")
        recognition_form = QFormLayout(recognition_group)
        
        self.threshold_input = QLineEdit("0.45")
        self.threshold_input.setPlaceholderText("0.0 to 1.0 (lower = more strict)")
        recognition_form.addRow("🎚️ Recognition Threshold:", self.threshold_input)
        
        self.duplicate_prevention = QCheckBox("Prevent duplicate entries (same person within 30 seconds)")
        self.duplicate_prevention.setChecked(True)
        recognition_form.addRow(self.duplicate_prevention)
        
        settings_layout.addWidget(recognition_group)
        
        # System Info
        system_group = QGroupBox("ℹ️ System Information")
        system_layout = QVBoxLayout(system_group)
        
        system_info = QLabel(f"""
        📊 Current Status:
        • OpenCV Version: {cv2.__version__}
        • Face Recognition Library: Available
        • Camera Status: {'Available' if cv2.VideoCapture(0).isOpened() else 'Not Available'}
        • Encodings Directory: {os.path.abspath(self.encodings_directory)}
        """)
        system_info.setStyleSheet("background-color: #f8f9fa; padding: 15px; border-radius: 8px; font-family: monospace;")
        system_layout.addWidget(system_info)
        
        settings_layout.addWidget(system_group)
        settings_layout.addStretch()
        
        # Add tab to tab widget
        tab_widget.addTab(settings_tab, "⚙️ Settings")
        
        # Add tab widget to main layout
        main_layout.addWidget(tab_widget)
        
        # Status bar
        self.statusBar().setStyleSheet("background-color: #f5f5f7; color: #1d1d1f; font-weight: bold;")
    
    def send_email(self):
        """Send attendance report via email with improved error handling"""
        if not self.present_students:
            QMessageBox.warning(self, "No Data", "No attendance data to send.")
            return
        
        if not all([self.teacher_email, self.sender_email, self.app_password]):
            QMessageBox.warning(self, "Email Settings", "Please configure email settings first.")
            return
        
        try:
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.teacher_email
            msg['Subject'] = f"Attendance Report - {datetime.now().strftime('%Y-%m-%d')}"
            
            # Calculate statistics
            total_students = len(set(self.known_face_names))
            present_count = len(self.present_students)
            absent_count = total_students - present_count
            attendance_rate = (present_count / total_students * 100) if total_students > 0 else 0
            
            # Create email body
            body = f"""
            Attendance Report
            Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            
            Statistics:
            - Total Students: {total_students}
            - Present: {present_count} ({attendance_rate:.1f}%)
            - Absent: {absent_count}
            
            Present Students:
            """
            
            for name, time in sorted(self.present_students.items()):
                body += f"• {name} - {time}\n"
            
            # Add absent students
            absent_students = set(self.known_face_names) - set(self.present_students.keys())
            if absent_students:
                body += "\nAbsent Students:\n"
                for name in sorted(absent_students):
                    body += f"• {name}\n"
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Connect to SMTP server with error handling and timeout
            try:
                server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
                server.starttls()
                server.login(self.sender_email, self.app_password)
                server.send_message(msg)
                server.quit()
                
                QMessageBox.information(self, "Success", f"Attendance report sent to {self.teacher_email}")
                
            except smtplib.SMTPAuthenticationError:
                QMessageBox.critical(self, "Authentication Error", 
                    "Failed to authenticate with email server. Please check your email and app password.")
            except smtplib.SMTPException as e:
                QMessageBox.critical(self, "SMTP Error", 
                    f"An error occurred while sending email: {str(e)}")
            except TimeoutError:
                QMessageBox.critical(self, "Timeout Error", 
                    "Connection to email server timed out. Please check your internet connection.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to send email: {str(e)}")

    def save_email_settings(self):
        """Save email configuration settings with improved error handling"""
        try:
            config = {
                'teacher_email': self.teacher_email_input.text().strip(),
                'sender_email': self.sender_email_input.text().strip(),
                'app_password': self.app_password_input.text()
            }
            
            # Validate email addresses
            if not all(self._validate_email(email) for email in [config['teacher_email'], config['sender_email']]):
                QMessageBox.warning(self, "Invalid Email", "Please enter valid email addresses.")
                return
            
            # Create backup of existing config
            if os.path.exists('email_config.json'):
                shutil.copy2('email_config.json', 'email_config.json.bak')
            
            # Save new config
            with open('email_config.json', 'w') as f:
                json.dump(config, f, indent=4)
            
            # Update instance variables
            self.teacher_email = config['teacher_email']
            self.sender_email = config['sender_email']
            self.app_password = config['app_password']
            
            QMessageBox.information(self, "Settings Saved", "Email settings have been saved successfully!")
            
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save settings: {str(e)}")
            # Restore backup if it exists
            if os.path.exists('email_config.json.bak'):
                shutil.copy2('email_config.json.bak', 'email_config.json')

    def load_email_settings(self):
        """Load email configuration with improved error handling"""
        try:
            if os.path.exists('email_config.json'):
                with open('email_config.json', 'r') as f:
                    config = json.load(f)
                    self.teacher_email = config.get('teacher_email', '')
                    self.sender_email = config.get('sender_email', '')
                    self.app_password = config.get('app_password', '')
        except Exception as e:
            print(f"Error loading email settings: {e}")
            # Use default empty values
            self.teacher_email = ""
            self.sender_email = ""
            self.app_password = ""

    def _validate_email(self, email):
        """Validate email address format"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def refresh_encoding_sets(self):
        """Refresh the list of available encoding datasets"""
        self.encoding_sets_list.clear()
        
        if not os.path.exists(self.encodings_directory):
            return
        
        # Look for encoding files in the directory
        for item in os.listdir(self.encodings_directory):
            item_path = os.path.join(self.encodings_directory, item)
            if os.path.isdir(item_path):
                encoding_file = os.path.join(item_path, 'encodings.pkl')
                info_file = os.path.join(item_path, 'info.json')
                
                if os.path.exists(encoding_file):
                    try:
                        list_item = QListWidgetItem(f"📁 {item}")
                        
                        # Add metadata if available
                        if os.path.exists(info_file):
                            with open(info_file, 'r') as f:
                                info = json.load(f)
                                student_count = info.get('student_count', 0)
                                list_item.setText(f"📁 {item} ({student_count} students)")
                        
                        list_item.setData(Qt.UserRole, item_path)
                        self.encoding_sets_list.addItem(list_item)
                    except Exception as e:
                        print(f"Error loading dataset {item}: {e}")
                        
        # Update UI state
        has_items = self.encoding_sets_list.count() > 0
        if not has_items:
            self.encoding_sets_list.addItem("No encoding datasets found")
    
    def on_encoding_set_selected(self, item):
        """Handle selection of an encoding dataset"""
        if not item:
            return
        
        dataset_path = item.data(Qt.UserRole)
        self.load_set_button.setEnabled(True)
        self.delete_set_button.setEnabled(True)
        
        # Load and display dataset information
        info_file = os.path.join(dataset_path, 'info.json')
        encoding_file = os.path.join(dataset_path, 'encodings.pkl')
        
        details_text = f"📂 Dataset: {os.path.basename(dataset_path)}\n"
        details_text += f"📍 Location: {dataset_path}\n\n"
        
        if os.path.exists(info_file):
            try:
                with open(info_file, 'r') as f:
                    info = json.load(f)
                    details_text += f"📝 Description: {info.get('description', 'No description')}\n"
                    details_text += f"📅 Created: {info.get('created_date', 'Unknown')}\n"
                    details_text += f"👥 Students: {info.get('student_count', 0)}\n"
                    details_text += f"🖼️ Images Processed: {info.get('images_processed', 0)}\n"
            except:
                details_text += "⚠️ Could not load dataset information\n"
        
        # Check encoding file
        if os.path.exists(encoding_file):
            try:
                file_size = os.path.getsize(encoding_file)
                details_text += f"💾 Encoding File Size: {file_size /1024:.1f} KB\n"
            except:
                pass
        
        self.details_text.setText(details_text)
        
        # Load and display student list
        self.load_student_list(dataset_path)
    
    def load_student_list(self, dataset_path):
        """Load and display the list of students in the selected dataset"""
        self.students_list.clear()
        
        encoding_file = os.path.join(dataset_path, 'encodings.pkl')
        
        if os.path.exists(encoding_file):
            try:
                with open(encoding_file, 'rb') as f:
                    data = pickle.load(f)
                    names = data.get('names', [])
                    
                    for name in sorted(set(names)):  # Remove duplicates and sort
                        count = names.count(name)
                        item = QListWidgetItem(f"👤 {name} ({count} encoding{'s' if count > 1 else ''})")
                        self.students_list.addItem(item)
                    
                    self.student_count_label.setText(f"Total: {len(set(names))} students")
            except Exception as e:
                self.students_list.addItem(QListWidgetItem(f"⚠️ Error loading student data: {str(e)}"))
                self.student_count_label.setText("Total: 0 students")
        else:
            self.students_list.addItem(QListWidgetItem("⚠️ No encoding data found"))
            self.student_count_label.setText("Total: 0 students")
    
    def filter_students(self, text):
        """Filter the student list based on search text"""
        for i in range(self.students_list.count()):
            item = self.students_list.item(i)
            if text.lower() in item.text().lower():
                item.setHidden(False)
            else:
                item.setHidden(True)
    
    def create_new_encoding_set(self):
        """Create a new face encoding dataset"""
        dialog = CreateEncodingDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            self.process_new_encoding_set(data)
    
    def process_new_encoding_set(self, data):
        """Process the creation of a new encoding dataset"""
        dataset_name = data['name']
        description = data['description']
        source_directory = data['directory']
        
        # Create dataset directory
        dataset_path = os.path.join(self.encodings_directory, dataset_name)
        
        if os.path.exists(dataset_path):
            reply = QMessageBox.question(self, "Dataset Exists", 
                                       f"Dataset '{dataset_name}' already exists. Overwrite?",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
        
        os.makedirs(dataset_path, exist_ok=True)
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_label.setText("Creating encoding dataset...")
        
        # Create and start the loading thread
        self.load_thread = LoadStudentsThread(source_directory)
        self.load_thread.progress.connect(self.update_progress)
        self.load_thread.finished.connect(lambda encodings, names, count: self.save_encoding_set(
            dataset_path, dataset_name, description, encodings, names, count, source_directory))
        self.load_thread.start()
    
    def update_progress(self, message):
        """Update the progress label with current operation"""
        self.progress_label.setText(message)
        QApplication.processEvents()  # Keep UI responsive
    
    def save_encoding_set(self, dataset_path, name, description, encodings, names, count, source_dir):
        """Save the processed encoding dataset"""
        try:
            # Save encodings
            encoding_file = os.path.join(dataset_path, 'encodings.pkl')
            with open(encoding_file, 'wb') as f:
                pickle.dump({'encodings': encodings, 'names': names}, f)
            
            # Save dataset info
            info_file = os.path.join(dataset_path, 'info.json')
            info_data = {
                'name': name,
                'description': description,
                'created_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'student_count': len(set(names)),
                'images_processed': count,
                'source_directory': source_dir
            }
            
            with open(info_file, 'w') as f:
                json.dump(info_data, f, indent=4)
            
            # Hide progress and refresh list
            self.progress_bar.setVisible(False)
            self.progress_label.setVisible(False)
            self.refresh_encoding_sets()
            
            QMessageBox.information(self, "Success", 
                                  f"Dataset '{name}' created successfully!\n"
                                  f"Processed {count} images for {len(set(names))} students.")
            
        except Exception as e:
            self.progress_bar.setVisible(False)
            self.progress_label.setVisible(False)
            QMessageBox.critical(self, "Error", f"Failed to save dataset: {str(e)}")
    
    def load_selected_encoding_set(self):
        """Load the selected encoding dataset for face recognition"""
        current_item = self.encoding_sets_list.currentItem()
        if not current_item:
            return
        
        dataset_path = current_item.data(Qt.UserRole)
        encoding_file = os.path.join(dataset_path, 'encodings.pkl')
        
        try:
            with open(encoding_file, 'rb') as f:
                data = pickle.load(f)
                self.known_face_encodings = data['encodings']
                self.known_face_names = data['names']
            
            # Update UI
            self.current_encoding_set = os.path.basename(dataset_path)
            self.current_set_label.setText(f"Loaded: {self.current_encoding_set} ({len(set(self.known_face_names))} students)")
            self.current_set_label.setStyleSheet("color: #34c759; font-weight: bold; font-size: 14px;")
            
            # Enable recognition controls
            self.start_button.setEnabled(True)
            self.generate_report_button.setEnabled(True)
            self.send_email_button.setEnabled(True)
            
            # Update status
            self.status_indicator.setText("🟢 Ready for Recognition")
            self.status_indicator.setStyleSheet("color: #34c759; font-weight: bold; font-size: 16px;")
            
            # Update statistics
            self.update_statistics();
            
            self.statusBar().showMessage(f"Dataset '{self.current_encoding_set}' loaded successfully. Ready for face recognition.");
            
            QMessageBox.information(self, "Dataset Loaded", 
                                  f"Successfully loaded '{self.current_encoding_set}' with {len(set(self.known_face_names))} students.")
            
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load dataset: {str(e)}")
    
    def delete_selected_encoding_set(self):
        """Delete the selected encoding dataset"""
        current_item = self.encoding_sets_list.currentItem()
        if not current_item:
            return
        
        dataset_name = current_item.text().replace("📁 ", "").split(" (")[0]
        dataset_path = current_item.data(Qt.UserRole)
        
        reply = QMessageBox.question(self, "Confirm Deletion", 
                                   f"Are you sure you want to delete dataset '{dataset_name}'?\n"
                                   f"This action cannot be undone.",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                import shutil
                shutil.rmtree(dataset_path)
                self.refresh_encoding_sets()
                self.details_text.clear()
                self.students_list.clear()
                self.student_count_label.setText("Total: 0 students")
                
                # If this was the current dataset, reset
                if self.current_encoding_set == dataset_name:
                    self.known_face_encodings = []
                    self.known_face_names = []
                    self.current_encoding_set = None
                    self.current_set_label.setText("No encoding dataset loaded")
                    self.current_set_label.setStyleSheet("color: #8e8e93; font-style: italic; font-size: 14px;")
                    self.start_button.setEnabled(False)
                    self.status_indicator.setText("⚫ Not Ready")
                    self.status_indicator.setStyleSheet("color: #ff3b30; font-weight: bold; font-size: 16px;")
                
                QMessageBox.information(self, "Deleted", f"Dataset '{dataset_name}' has been deleted.")
                
            except Exception as e:
                QMessageBox.critical(self, "Delete Error", f"Failed to delete dataset: {str(e)}")
    
    def toggle_camera(self):
        """Toggle camera on/off for face recognition"""
        if not self.camera_active:
            self.start_recognition()
        else:
            self.stop_recognition()
    
    def start_recognition(self):
        """Start face recognition"""
        if not self.known_face_encodings:
            QMessageBox.warning(self, "No Dataset", "Please load an encoding dataset first.")
            return
        
        # Get threshold from settings
        try:
            threshold = float(self.threshold_input.text())
            if not 0.0 <= threshold <= 1.0:
                raise ValueError()
        except:
            threshold = 0.45
            self.threshold_input.setText("0.45")
        
        # Start recognition thread
        self.face_recognition_thread = FaceRecognitionThread(
            self.known_face_encodings, 
            self.known_face_names, 
            threshold
        )
        self.face_recognition_thread.update_frame.connect(self.update_camera_display)
        self.face_recognition_thread.update_attendance.connect(self.update_attendance_record)
        self.face_recognition_thread.start()
        
        # Update UI
        self.camera_active = True
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.statusBar().showMessage("Face recognition active. Point camera at students.")
        
        # Update status indicator
        self.status_indicator.setText("🔴 Recognition Active")
        self.status_indicator.setStyleSheet("color: #ff3b30; font-weight: bold; font-size: 16px;")
    
    def stop_recognition(self):
        """Stop face recognition"""
        if self.face_recognition_thread:
            self.face_recognition_thread.stop()
            self.face_recognition_thread = None
        
        # Update UI
        self.camera_active = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        # Clear camera display
        self.camera_label.clear()
        self.camera_label.setText("📷\nCamera stopped\nClick 'Start Recognition' to resume")
        
        self.statusBar().showMessage("Face recognition stopped.")
        
        # Update status indicator
        self.status_indicator.setText("🟢 Ready for Recognition")
        self.status_indicator.setStyleSheet("color: #34c759; font-weight: bold; font-size: 16px;")
    
    def update_camera_display(self, frame, face_locations, names, encodings):
        """Update the camera display with detected faces"""
        # Draw rectangles and names on detected faces
        for (top, right, bottom, left), name in zip(face_locations, names):
            # Choose color based on recognition status
            color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)  # Green for known, red for unknown
            
            # Draw rectangle around face
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            
            # Draw label background
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
            
            # Draw name text
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, name, (left + 6, bottom - 6), font, 0.6, (255, 255, 255), 1)
        
        # Convert frame to Qt format and display
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        # Scale image to fit label
        pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = pixmap.scaled(self.camera_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.camera_label.setPixmap(scaled_pixmap)
    
    def update_attendance_record(self, name, timestamp):
        """Update attendance record for a recognized student"""
        if not self.duplicate_prevention.isChecked() or \
           name not in self.present_students or \
           (datetime.now() - datetime.strptime(self.present_students[name], "%Y-%m-%d %H:%M:%S")).seconds > 30:
            
            self.present_students[name] = timestamp
            self.refresh_attendance_table()
            
            # Save attendance to database
            self.attendance_manager.save_attendance(
                datetime.now(),
                list(self.present_students.keys()),
                self.known_face_names
            )
            
            # Update analytics if tab exists
            if hasattr(self, 'analytics_tab'):
                self.analytics_tab.update_student_list(self.known_face_names)
                self.analytics_tab.update_chart()
            
            # Update statistics
            self.update_statistics()
    
    def refresh_attendance_table(self):
        """Refresh the attendance table display"""
        self.attendance_table.setRowCount(len(self.present_students))
        
        for row, (name, time) in enumerate(sorted(self.present_students.items())):
            self.attendance_table.setItem(row, 0, QTableWidgetItem(name))
            self.attendance_table.setItem(row, 1, QTableWidgetItem(time))
    
    def update_statistics(self):
        """Update attendance statistics"""
        total_students = len(set(self.known_face_names)) if self.known_face_names else 0
        present_count = len(self.present_students)
        absent_count = total_students - present_count
        
        self.total_students_label.setText(f"Total Students: {total_students}")
        self.present_count_label.setText(f"Present: {present_count}")
        self.absent_count_label.setText(f"Absent: {absent_count}")
        
        # Style based on attendance rate
        if total_students > 0:
            attendance_rate = present_count / total_students
            if attendance_rate >= 0.8:
                style = "color: #34c759; font-weight: bold;"
            elif attendance_rate >= 0.6:
                style = "color: #ff9500; font-weight: bold;"
            else:
                style = "color: #ff3b30; font-weight: bold;"
            
            self.present_count_label.setStyleSheet(style)
    
    def clear_attendance(self):
        """Clear all attendance records"""
        reply = QMessageBox.question(self, "Clear Attendance", 
                                   "Are you sure you want to clear all attendance records?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Clear in-memory data
            self.present_students.clear()
            self.refresh_attendance_table()
            self.update_statistics()
            
            # Clear saved record for today
            if self.attendance_manager.clear_attendance(datetime.now()):
                self.statusBar().showMessage("Attendance records cleared.")
            else:
                self.statusBar().showMessage("No attendance records found for today.")
    
    def generate_report(self):
        """Generate a PDF attendance report"""
        if not self.present_students:
            QMessageBox.warning(self, "No Data", "No attendance data to generate report.")
            return
        
        # Get save location
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Attendance Report", 
            f"attendance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            "PDF Files (*.pdf)"
        )
        
        if not filename:
            return
        
        try:
            # Create PDF
            c = canvas.Canvas(filename)
            
            # Header
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, 800, "ATTENDANCE REPORT")
            
            c.setFont("Helvetica", 12)
            c.drawString(50, 780, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            c.drawString(50, 760, f"Dataset: {self.current_encoding_set or 'Unknown'}")
            
            # Statistics
            c.drawString(50, 720, f"Total Students: {len(set(self.known_face_names))}")
            c.drawString(50, 700, f"Present: {len(self.present_students)}")
            c.drawString(50, 680, f"Absent: {len(set(self.known_face_names)) - len(self.present_students)}")
            
            # Present students
            c.setFont("Helvetica-Bold", 14)
            c.drawString(50, 640, "PRESENT STUDENTS:")
            
            c.setFont("Helvetica", 10)
            y_position = 620
            
            for name, time in sorted(self.present_students.items()):
                c.drawString(70, y_position, f"• {name} - {time}")
                y_position -= 20
                
                if y_position < 50:  # New page if needed
                    c.showPage()
                    y_position = 800
            
            # Absent students
            if self.known_face_names:
                absent_students = set(self.known_face_names) - set(self.present_students.keys())
                
                if absent_students:
                    if y_position < 200:  # New page if needed
                        c.showPage()
                        y_position = 800
                    
                    c.setFont("Helvetica-Bold", 14)
                    c.drawString(50, y_position, "ABSENT STUDENTS:")
                    y_position -= 20
                    
                    c.setFont("Helvetica", 10)
                    for name in sorted(absent_students):
                        c.drawString(70, y_position, f"• {name}")
                        y_position -= 20
                        
                        if y_position < 50:  # New page if needed
                            c.showPage()
                            y_position = 800
            
            c.save()
            
            QMessageBox.information(self, "Report Generated", f"Attendance report saved to:\n{filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "Report Error", f"Failed to generate report: {str(e)}")
    
    def send_email(self):
        """Send attendance report via email with improved error handling"""
        if not self.present_students:
            QMessageBox.warning(self, "No Data", "No attendance data to send.")
            return
        
        if not all([self.teacher_email, self.sender_email, self.app_password]):
            QMessageBox.warning(self, "Email Settings", "Please configure email settings first.")
            return
        
        try:
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.teacher_email
            msg['Subject'] = f"Attendance Report - {datetime.now().strftime('%Y-%m-%d')}"
            
            # Calculate statistics
            total_students = len(set(self.known_face_names))
            present_count = len(self.present_students)
            absent_count = total_students - present_count
            attendance_rate = (present_count / total_students * 100) if total_students > 0 else 0
            
            # Create email body
            body = f"""
            Attendance Report
            Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            
            Statistics:
            - Total Students: {total_students}
            - Present: {present_count} ({attendance_rate:.1f}%)
            - Absent: {absent_count}
            
            Present Students:
            """
            
            for name, time in sorted(self.present_students.items()):
                body += f"• {name} - {time}\n"
            
            # Add absent students
            absent_students = set(self.known_face_names) - set(self.present_students.keys())
            if absent_students:
                body += "\nAbsent Students:\n"
                for name in sorted(absent_students):
                    body += f"• {name}\n"
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Connect to SMTP server with error handling and timeout
            try:
                server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
                server.starttls()
                server.login(self.sender_email, self.app_password)
                server.send_message(msg)
                server.quit()
                
                QMessageBox.information(self, "Success", f"Attendance report sent to {self.teacher_email}")
                
            except smtplib.SMTPAuthenticationError:
                QMessageBox.critical(self, "Authentication Error", 
                    "Failed to authenticate with email server. Please check your email and app password.")
            except smtplib.SMTPException as e:
                QMessageBox.critical(self, "SMTP Error", 
                    f"An error occurred while sending email: {str(e)}")
            except TimeoutError:
                QMessageBox.critical(self, "Timeout Error", 
                    "Connection to email server timed out. Please check your internet connection.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to send email: {str(e)}")
    
    def closeEvent(self, event):
        """Handle application close event"""
        if self.face_recognition_thread:
            self.face_recognition_thread.stop()
        event.accept()

    def show_analytics(self):
        """Show the analytics window"""
        from analytics_ui import AnalyticsWindow
        self.analytics_window = AnalyticsWindow(self.attendance_manager, self)
        self.analytics_window.show()


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Smart Attendance System")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("Education Tech Solutions")
    
    # Create and show main window
    window = AttendanceSystem()
    window.show()
    
    # Load email settings
    window.load_email_settings()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()