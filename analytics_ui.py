from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QComboBox, QMainWindow, QGroupBox, QCalendarWidget,
                            QFrame, QTextEdit, QPushButton, QScrollArea, QSplitter)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from attendance_manager import AttendanceChartWidget
import matplotlib.pyplot as plt

class AnalyticsWindow(QMainWindow):
    def __init__(self, attendance_manager, parent=None):
        super().__init__(parent)
        self.attendance_manager = attendance_manager
        self.setWindowTitle("Attendance Analytics")
        self.setMinimumSize(1200, 800)  # Increased window size
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)  # Changed to horizontal layout
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Left Panel: Calendar and Controls
        left_panel = QWidget()
        left_panel.setFixedWidth(400)  # Fixed width for left panel
        left_panel.setStyleSheet("background-color: #f5f5f7;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(20)
        left_layout.setContentsMargins(20, 20, 20, 20)
        
        # Calendar widget
        calendar_group = QGroupBox("📅 Select Date Range")
        calendar_group.setStyleSheet("""
            QGroupBox {
                font-size: 22px;
                font-weight: bold;
                border: 2px solid #d2d2d7;
                border-radius: 12px;
                margin-top: 16px;
                padding: 20px;
                background-color: Black;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 0 10px;
                color: #1d1d1f;
            }
        """)
        calendar_layout = QVBoxLayout(calendar_group)
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.calendar.setHorizontalHeaderFormat(QCalendarWidget.SingleLetterDayNames)
        self.calendar.clicked.connect(self.update_analytics)
        calendar_layout.addWidget(self.calendar)
        left_layout.addWidget(calendar_group)
        
        # Controls section
        controls_group = QGroupBox("🔄 View Controls")
        controls_layout = QVBoxLayout(controls_group)
        
        # Student selection
        student_layout = QVBoxLayout()
        student_label = QLabel("Select Student:")
        student_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 5px;")
        self.student_selector = QComboBox()
        self.student_selector.setMinimumHeight(40)
        self.student_selector.currentTextChanged.connect(self.update_analytics)
        
        student_layout.addWidget(student_label)
        student_layout.addWidget(self.student_selector)
        controls_layout.addLayout(student_layout)
        
        # Period selection
        period_layout = QVBoxLayout()
        period_label = QLabel("View Period:")
        period_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 5px;")
        self.period_selector = QComboBox()
        self.period_selector.setMinimumHeight(40)
        self.period_selector.addItems(["Weekly", "Monthly", "Semester"])
        self.period_selector.currentTextChanged.connect(self.update_analytics)
        
        period_layout.addWidget(period_label)
        period_layout.addWidget(self.period_selector)
        controls_layout.addLayout(period_layout)
        
        left_layout.addWidget(controls_group)
        left_layout.addStretch()
        
        # Right Panel: Stats and Charts
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(20)
        right_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("📊 Attendance Analytics Dashboard")
        header.setFont(QFont("SF Pro Display", 28, QFont.Bold))
        header.setStyleSheet("color: #0071e3; margin-bottom: 20px;")
        right_layout.addWidget(header)
        
        # Statistics cards in a grid
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(10)
        self.stat_cards = {}
        self.stat_cards["total"] = self._create_stat_card("Total Students", "0")
        self.stat_cards["present"] = self._create_stat_card("Present", "0", "#34c759")
        self.stat_cards["absent"] = self._create_stat_card("Absent", "0", "#ff3b30")
        self.stat_cards["percentage"] = self._create_stat_card("Attendance Rate", "0%", "#0071e3")
        
        for card in self.stat_cards.values():
            stats_layout.addWidget(card)
        right_layout.addLayout(stats_layout)
        
        # Charts area with increased size
        charts_group = QGroupBox("📊 Attendance Visualization")
        charts_layout = QVBoxLayout(charts_group)
        charts_split = QSplitter(Qt.Horizontal)
        charts_split.setStyleSheet("QSplitter::handle { background-color: #d2d2d7; }")
        
        # Left: Pie chart
        pie_group = QGroupBox("Student Attendance Distribution")
        pie_layout = QVBoxLayout(pie_group)
        self.pie_chart = AttendanceChartWidget()
        self.pie_chart.setMinimumSize(400, 300)
        pie_layout.addWidget(self.pie_chart)
        charts_split.addWidget(pie_group)
        
        # Right: Trend chart
        trend_group = QGroupBox("Overall Attendance Trend")
        trend_layout = QVBoxLayout(trend_group)
        self.trend_chart = AttendanceChartWidget()
        self.trend_chart.setMinimumSize(400, 300)
        trend_layout.addWidget(self.trend_chart)
        charts_split.addWidget(trend_group)
        
        charts_layout.addWidget(charts_split)
        charts_group.setLayout(charts_layout)
        right_layout.addWidget(charts_group)
        
        # Add panels to main layout
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)
        
        # Apply styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f7;
            }
            QGroupBox {
                font-size: 18px;
                font-weight: bold;
                border: 2px solid #d2d2d7;
                border-radius: 12px;
                margin-top: 16px;
                padding: 20px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 0 10px;
                color: #1d1d1f;
            }
            QComboBox {
                border: 2px solid #d2d2d7;
                border-radius: 8px;
                padding: 8px;
                min-width: 200px;
                background-color: white;
                font-size: 14px;
            }
            QLabel {
                font-size: 14px;
            }
        """)
        
        # Initialize data
        self.update_analytics()
    
    def _create_stat_card(self, title, value, color="#1d1d1f"):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 2px solid #d2d2d7;
                border-radius: 12px;
                padding: 15px;
                min-width: 200px;
                min-height: 100px;
            }}
            QLabel {{
                color: {color};
            }}
        """)
        
        layout = QVBoxLayout(card)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("SF Pro Display", 12))
        title_label.setStyleSheet("color: #666;")
        
        value_label = QLabel(value)
        value_label.setFont(QFont("SF Pro Display", 24, QFont.Bold))
        value_label.setObjectName("value_label")  # Set object name for finding later
        
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.setAlignment(Qt.AlignCenter)
        
        return card
    
    def update_analytics(self):
        """Update all analytics components"""
        from datetime import datetime, timedelta
        
        selected_date = self.calendar.selectedDate()
        period = self.period_selector.currentText()
        selected_student = self.student_selector.currentText()
        
        # Get attendance data
        stats = self.attendance_manager.get_attendance(selected_date.toPyDate())
        if not stats:
            return
            
        # Update statistics cards
        total = stats.get('total_students', 0)
        present = stats.get('present_count', 0)
        absent = total - present
        percentage = (present / total * 100) if total > 0 else 0
        
        # Update stat cards
        self.stat_cards["total"].findChild(QLabel, "value_label").setText(str(total))
        self.stat_cards["present"].findChild(QLabel, "value_label").setText(str(present))
        self.stat_cards["absent"].findChild(QLabel, "value_label").setText(str(absent))
        self.stat_cards["percentage"].findChild(QLabel, "value_label").setText(f"{percentage:.1f}%")
        
        # Update student selector if needed
        current_students = set(self.student_selector.itemText(i) for i in range(self.student_selector.count()))
        if stats.get('all_students') and set(stats['all_students']) != current_students:
            self.student_selector.clear()
            self.student_selector.addItems(sorted(stats['all_students']))
            
        # Update pie chart for selected student
        if selected_student:
            # Calculate date range based on period
            end_date = datetime.now()
            if period == "Weekly":
                start_date = end_date - timedelta(days=7)
            elif period == "Monthly":
                start_date = end_date - timedelta(days=30)
            elif period == "Semester":
                start_date = end_date - timedelta(days=180)
            else:
                start_date = None

            student_stats = self.attendance_manager.get_student_attendance_stats(
                selected_student,
                start_date.strftime('%Y-%m-%d') if start_date else None,
                end_date.strftime('%Y-%m-%d')
            )
            if student_stats:
                self.pie_chart.plot_attendance_pie(
                    student_stats['days_present'],
                    student_stats['days_absent'],
                    title=f"{selected_student}'s Attendance"
                )
        
        # Update trend chart based on period
        period_map = {
            "Weekly": "week",
            "Monthly": "month",
            "Semester": "semester"
        }
        trend_data = self.attendance_manager.get_attendance_trend(
            period=period_map.get(period, "week")
        )
        if trend_data:
            self.trend_chart.plot_attendance_trend(
                trend_data['dates'],
                trend_data['present_counts'],
                title=f"{period} Attendance Trend"
            )
    
    def update_student_stats(self):
        student = self.student_selector.currentText()
        if student:
            stats = self.attendance_manager.get_student_attendance_stats(student)
            if stats:
                details = f"""
                Student: {student}
                Total Days: {stats['total_days']}
                Days Present: {stats['days_present']}
                Days Absent: {stats['days_absent']}
                Attendance Rate: {stats['attendance_percentage']:.1f}%
                """
                self.student_stats.setText(details)
                # Update student-specific charts

class AnalyticsTab(QWidget):
    def __init__(self, attendance_manager, parent=None):
        super().__init__(parent)
        self.attendance_manager = attendance_manager
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("📊 Attendance Analytics")
        header.setFont(QFont("SF Pro Display", 20, QFont.Bold))
        header.setStyleSheet("color: #0071e3; margin-bottom: 20px;")
        layout.addWidget(header)
        
        # Calendar
        calendar_group = QGroupBox("📅 Select Date")
        calendar_layout = QVBoxLayout(calendar_group)
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setStyleSheet("""
            QCalendarWidget {
                background-color: white;
                border: 2px solid #d2d2d7;
                border-radius: 8px;
            }
            QCalendarWidget QToolButton {
                color: #1d1d1f;
                background-color: transparent;
                border: 2px solid transparent;
                border-radius: 4px;
                padding: 4px;
            }
            QCalendarWidget QToolButton:hover {
                background-color: #e8e8ed;
            }
            QCalendarWidget QMenu {
                background-color: white;
                border: 1px solid #d2d2d7;
                border-radius: 4px;
            }
            QCalendarWidget QSpinBox {
                background-color: white;
                border: 1px solid #d2d2d7;
                border-radius: 4px;
                padding: 3px;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #f5f5f7;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
            QCalendarWidget QWidget { alternate-background-color: #fafafa; }
        """)
        calendar_layout.addWidget(self.calendar)
        layout.addWidget(calendar_group)
        
        # Content Split
        content = QSplitter(Qt.Horizontal)
        
        # Left: Stats
        stats_group = QGroupBox("📈 Statistics")
        stats_layout = QVBoxLayout(stats_group)
        
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 2px solid #d2d2d7;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
            }
        """)
        stats_layout.addWidget(self.stats_text)
        
        student_layout = QHBoxLayout()
        self.student_selector = QComboBox()
        self.student_selector.setStyleSheet("""
            QComboBox {
                border: 2px solid #d2d2d7;
                border-radius: 8px;
                padding: 8px;
                min-width: 200px;
            }
            QComboBox::drop-down {
                border: none;
                border-left: 2px solid #d2d2d7;
                padding: 0 8px;
            }
            QComboBox::down-arrow {
                image: url(icons/down-arrow.png);
            }
        """)
        
        self.view_student_btn = QPushButton("View Student Stats")
        self.view_student_btn.setStyleSheet("""
            QPushButton {
                background-color: #0071e3;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0077ed;
            }
            QPushButton:pressed {
                background-color: #0068d1;
            }
        """)
        
        student_layout.addWidget(QLabel("Select Student:"))
        student_layout.addWidget(self.student_selector)
        student_layout.addWidget(self.view_student_btn)
        stats_layout.addLayout(student_layout)
        
        content.addWidget(stats_group)
        
        # Right: Charts
        charts_group = QGroupBox("📊 Visualizations")
        charts_layout = QVBoxLayout(charts_group)
        
        self.chart_widget = AttendanceChartWidget()
        charts_layout.addWidget(self.chart_widget)
        
        chart_controls = QHBoxLayout()
        self.chart_type = QComboBox()
        self.chart_type.addItems([
            "Overall Attendance",
            "Student History",
            "Monthly Trends"
        ])
        self.chart_type.setStyleSheet("""
            QComboBox {
                border: 2px solid #d2d2d7;
                border-radius: 8px;
                padding: 8px;
                min-width: 150px;
            }
        """)
        chart_controls.addWidget(QLabel("Chart Type:"))
        chart_controls.addWidget(self.chart_type)
        charts_layout.addLayout(chart_controls)
        
        content.addWidget(charts_group)
        
        # Set default sizes
        content.setSizes([400, 600])
        layout.addWidget(content)
        
        # Connect signals
        self.calendar.clicked.connect(self.on_date_selected)
        self.view_student_btn.clicked.connect(self.on_view_student)
        self.chart_type.currentTextChanged.connect(self.update_chart)
        
    def on_date_selected(self, date):
        """Handle date selection"""
        attendance = self.attendance_manager.get_attendance(date.toPyDate())
        if attendance:
            stats = f"""📅 Date: {attendance['date']}

📊 Summary:
• Total Students: {attendance['total_students']}
• Present: {attendance['present_count']}
• Absent: {len(attendance['absent_students'])}
• Attendance Rate: {attendance['attendance_percentage']:.1f}%

✅ Present Students:
{', '.join(attendance['present_students'])}

❌ Absent Students:
{', '.join(attendance['absent_students'])}"""
            self.stats_text.setText(stats)
        else:
            self.stats_text.setText("No attendance data for selected date")
    
    def on_view_student(self):
        """Show selected student's statistics"""
        student = self.student_selector.currentText()
        if student:
            stats = self.attendance_manager.get_student_attendance_stats(student)
            if stats:
                text = f"""👤 Student: {student}

📊 Attendance Summary:
• Total Days: {stats['total_days']}
• Days Present: {stats['days_present']}
• Days Absent: {stats['days_absent']}
• Attendance Rate: {stats['attendance_percentage']:.1f}%"""
                self.stats_text.setText(text)
                self.update_chart("Student History")
            else:
                self.stats_text.setText("No attendance data for selected student")
    
    def update_chart(self, chart_type=None):
        """Update the displayed chart"""
        if chart_type == "Student History":
            student = self.student_selector.currentText()
            if student:
                figure = self.attendance_manager.generate_attendance_charts(student)
                self.chart_widget.update_chart(figure)
        else:
            figure = self.attendance_manager.generate_attendance_charts()
            self.chart_widget.update_chart(figure)
    
    def update_student_list(self, students):
        """Update the student selector dropdown"""
        self.student_selector.clear()
        self.student_selector.addItems(sorted(students))