# Smart Attendance System with Analytics

A modern facial recognition-based attendance management system with advanced analytics, reporting, and date-wise tracking features.

## Key Features

1. Face Recognition
   - Real-time face detection and recognition
   - Support for multiple photos per student
   - Duplicate entry prevention
   - Confidence threshold adjustment

2. Analytics Dashboard
   - Date-wise attendance tracking
   - Student-wise attendance history
   - Visual analytics with charts and graphs
   - Attendance percentage tracking
   - Monthly attendance trends

3. Reporting
   - Automated PDF report generation
   - Email integration for report sharing
   - Date range selection for reports
   - Custom report formatting

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/smart-attendance-system.git
cd smart-attendance-system
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the installation script:
```bash
python install.py
```

This will:
- Install required dependencies
- Set up directory structure
- Create desktop application shortcut
- Configure system settings

## Usage Guide

### Initial Setup

1. Launch the application:
   - From applications menu: "Smart Attendance System"
   - Or from terminal: `python face1.py`

2. Configure Email Settings (for reports):
   - Go to Settings tab
   - Enter teacher's email
   - Configure sender email (Gmail recommended)
   - Set up app password for email

### Creating Student Database

1. Prepare student photos:
   - Name format: firstname_lastname_number.jpg
   - Multiple photos per student recommended
   - Good lighting and clear face visibility
   - Supported formats: JPG, PNG

2. Create new dataset:
   - Go to Dataset Manager tab
   - Click "Create New Dataset"
   - Select photos folder
   - Add dataset name and description

### Taking Attendance

1. Load dataset from Dataset Manager
2. Click "Start Recognition" on main screen
3. Students will be automatically recognized and marked present
4. View real-time attendance list
5. Use "Stop Recognition" when done

### Analytics & Reports

1. View Analytics:
   - Go to Analytics tab
   - Select date from calendar
   - View attendance statistics
   - Explore different chart types
   - Track individual student attendance

2. Generate Reports:
   - Select date range
   - Click "Generate Report"
   - Choose report format
   - Email reports directly to teachers

## System Requirements

- Operating System: Windows 10/11, Linux, macOS
- Python 3.8 or higher
- Webcam for face recognition
- Minimum 4GB RAM recommended
- Internet connection for email features

## Directory Structure

```
smart-attendance-system/
├── encodings/           # Face encoding datasets
├── attendance_records/  # Daily attendance data
├── reports/            # Generated reports
├── icons/             # Application icons
└── classmates_photos/ # Student photo samples
```

## Troubleshooting

1. Camera Issues:
   - Check camera permissions
   - Ensure no other app is using camera
   - Try restarting application

2. Recognition Problems:
   - Add multiple photos per student
   - Ensure good lighting
   - Adjust recognition threshold

3. Email Issues:
   - Verify email settings
   - Check internet connection
   - Ensure app password is correct

## Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Support

For support, please:
1. Check documentation
2. Search existing issues
3. Create new issue with details
4. Contact development team

## Acknowledgments

- Face Recognition library
- OpenCV contributors
- PyQt5 community
- All contributors