import os
import json
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import QVBoxLayout, QWidget

class AttendanceManager:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.attendance_dir = os.path.join(base_dir, 'attendance_records')
        self.analytics_dir = os.path.join(base_dir, 'attendance_analytics')
        os.makedirs(self.attendance_dir, exist_ok=True)
        os.makedirs(self.analytics_dir, exist_ok=True)

    def save_attendance(self, date, present_students, all_students):
        """Save attendance for a specific date"""
        date_str = date.strftime('%Y-%m-%d')
        attendance_file = os.path.join(self.attendance_dir, f'attendance_{date_str}.json')
        
        attendance_data = {
            'date': date_str,
            'present_students': list(present_students),
            'all_students': list(all_students),
            'absent_students': list(set(all_students) - set(present_students)),
            'total_students': len(all_students),
            'present_count': len(present_students),
            'attendance_percentage': (len(present_students) / len(all_students) * 100) if all_students else 0
        }
        
        with open(attendance_file, 'w') as f:
            json.dump(attendance_data, f, indent=4)

    def get_attendance(self, date):
        """Get attendance for a specific date"""
        date_str = date.strftime('%Y-%m-%d')
        attendance_file = os.path.join(self.attendance_dir, f'attendance_{date_str}.json')
        
        if os.path.exists(attendance_file):
            with open(attendance_file, 'r') as f:
                return json.load(f)
        return None

    def get_student_attendance_stats(self, student_name, start_date=None, end_date=None):
        """Get attendance statistics for a specific student"""
        attendance_files = os.listdir(self.attendance_dir)
        attendance_data = []
        
        # Convert string dates to datetime objects if they're strings
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        
        for file in attendance_files:
            if file.startswith('attendance_') and file.endswith('.json'):
                with open(os.path.join(self.attendance_dir, file), 'r') as f:
                    data = json.load(f)
                    date = datetime.strptime(data['date'], '%Y-%m-%d')
                    
                    if ((not start_date or date >= start_date) and 
                        (not end_date or date <= end_date)):
                        attendance_data.append({
                            'date': date,
                            'present': student_name in data['present_students']
                        })
        
        df = pd.DataFrame(attendance_data)
        if df.empty:
            return None
            
        stats = {
            'total_days': len(df),
            'days_present': df['present'].sum(),
            'days_absent': len(df) - df['present'].sum(),
            'attendance_percentage': (df['present'].sum() / len(df) * 100),
            'attendance_history': df.to_dict('records')
        }
        return stats

    def generate_attendance_charts(self, student_name=None, period=None, chart_type=None):
        """Generate attendance visualization charts
        
        Args:
            student_name (str, optional): Generate charts for specific student
            period (str, optional): Time period - 'week', 'month', 'semester'
            chart_type (str, optional): Specific chart type - 'distribution', 'trend'
        """
        if student_name:
            return self._generate_student_charts(student_name)
            
        if chart_type == "distribution":
            return self._generate_distribution_chart()
            
        # Get all attendance records
        attendance_files = sorted([f for f in os.listdir(self.attendance_dir) 
                                if f.startswith('attendance_') and f.endswith('.json')])
        
        data = []
        for file in attendance_files:
            with open(os.path.join(self.attendance_dir, file), 'r') as f:
                attendance = json.load(f)
                date = datetime.strptime(attendance['date'], '%Y-%m-%d')
                
                # Filter by period if specified
                if period == "week":
                    if (datetime.now() - date).days > 7:
                        continue
                elif period == "month":
                    if (datetime.now() - date).days > 30:
                        continue
                elif period == "semester":
                    if (datetime.now() - date).days > 180:
                        continue
                        
                data.append({
                    'date': date,
                    'attendance_percentage': attendance['attendance_percentage'],
                    'present_count': attendance['present_count'],
                    'total_students': attendance['total_students']
                })
                
        if not data:
            return None
            
        df = pd.DataFrame(data)
        
        # Create figure
        fig = plt.figure(figsize=(15, 6))
        
        # Daily Attendance Line Plot
        ax1 = plt.subplot(121)
        sns.lineplot(data=df, x='date', y='attendance_percentage', marker='o')
        plt.title('Attendance Trend')
        plt.xticks(rotation=45)
        plt.ylabel('Attendance %')
        
        # Stats Distribution
        ax2 = plt.subplot(122)
        if period:
            title = f"{period.capitalize()} Attendance Distribution"
        else:
            title = "Overall Attendance Distribution"
            
        sns.histplot(data=df, x='attendance_percentage', bins=20)
        plt.title(title)
        plt.xlabel('Attendance %')
        plt.ylabel('Frequency')
        
        plt.tight_layout()
        return fig
        
    def _generate_distribution_chart(self):
        """Generate attendance distribution charts"""
        attendance_files = os.listdir(self.attendance_dir)
        percentages = []
        
        for file in attendance_files:
            if file.startswith('attendance_') and file.endswith('.json'):
                with open(os.path.join(self.attendance_dir, file), 'r') as f:
                    data = json.load(f)
                    percentages.append(data['attendance_percentage'])
        
        if not percentages:
            return None
            
        fig = plt.figure(figsize=(10, 6))
        sns.histplot(percentages, bins=20, kde=True)
        plt.title('Attendance Distribution')
        plt.xlabel('Attendance Percentage')
        plt.ylabel('Frequency')
        
        return fig

    def _generate_student_charts(self, student_name):
        """Generate charts for individual student"""
        stats = self.get_student_attendance_stats(student_name)
        if not stats:
            return None

        # Create figure with subplots
        fig = plt.figure(figsize=(15, 5))
        
        # Attendance Pie Chart
        ax1 = plt.subplot(131)
        plt.pie([stats['days_present'], stats['days_absent']], 
                labels=['Present', 'Absent'],
                colors=['#34c759', '#ff3b30'],
                autopct='%1.1f%%')
        plt.title(f'Attendance Distribution for {student_name}')
        
        # Attendance Timeline
        ax2 = plt.subplot(132)
        df = pd.DataFrame(stats['attendance_history'])
        df['present'] = df['present'].astype(int)
        plt.plot(df['date'], df['present'], marker='o')
        plt.title('Attendance Timeline')
        plt.xticks(rotation=45)
        
        # Monthly Attendance Bar Chart
        ax3 = plt.subplot(133)
        df['month'] = df['date'].dt.strftime('%Y-%m')
        monthly = df.groupby('month')['present'].mean() * 100
        monthly.plot(kind='bar')
        plt.title('Monthly Attendance %')
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        return fig

    def _generate_overall_charts(self):
        """Generate overall attendance charts"""
        attendance_files = os.listdir(self.attendance_dir)
        data = []
        
        for file in attendance_files:
            if file.startswith('attendance_') and file.endswith('.json'):
                with open(os.path.join(self.attendance_dir, file), 'r') as f:
                    attendance = json.load(f)
                    data.append({
                        'date': datetime.strptime(attendance['date'], '%Y-%m-%d'),
                        'attendance_percentage': attendance['attendance_percentage'],
                        'present_count': attendance['present_count'],
                        'total_students': attendance['total_students'],
                        'absent_count': attendance['total_students'] - attendance['present_count']
                    })
        
        if not data:
            return None
            
        df = pd.DataFrame(data)
        df['weekday'] = df['date'].dt.strftime('%A')
        df['month'] = df['date'].dt.strftime('%Y-%m')
        
        # Create figure with subplots
        fig = plt.figure(figsize=(15, 10))
        
        # Daily Attendance Percentage
        ax1 = plt.subplot(231)
        sns.lineplot(data=df, x='date', y='attendance_percentage', marker='o')
        plt.title('Daily Attendance Percentage')
        plt.xticks(rotation=45)
        
        # Monthly Average Attendance
        ax2 = plt.subplot(232)
        monthly_avg = df.groupby('month')['attendance_percentage'].mean()
        monthly_avg.plot(kind='bar')
        plt.title('Monthly Average Attendance')
        plt.xticks(rotation=45)
        
        # Attendance Distribution
        ax3 = plt.subplot(233)
        sns.histplot(data=df, x='attendance_percentage', bins=10, color='#0071e3')
        plt.title('Attendance Distribution')
        plt.xlabel('Attendance Percentage')
        plt.ylabel('Frequency')
        
        # Day-wise Analysis
        ax4 = plt.subplot(234)
        weekday_avg = df.groupby('weekday')['attendance_percentage'].mean().reindex([
            'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'
        ])
        sns.barplot(x=weekday_avg.index, y=weekday_avg.values, palette='viridis')
        plt.title('Day-wise Average Attendance')
        plt.xticks(rotation=45)
        
        # Present vs Absent Trend
        ax5 = plt.subplot(235)
        plt.stackplot(df['date'], 
                     [df['present_count'], df['absent_count']], 
                     labels=['Present', 'Absent'],
                     colors=['#34c759', '#ff3b30'])
        plt.title('Present vs Absent Trend')
        plt.legend()
        plt.xticks(rotation=45)
        
        # Monthly Box Plot
        ax6 = plt.subplot(236)
        sns.boxplot(data=df, x='month', y='attendance_percentage')
        plt.title('Monthly Attendance Distribution')
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        return fig

    def clear_attendance(self, date):
        """Clear attendance records for a specific date"""
        date_str = date.strftime('%Y-%m-%d')
        attendance_file = os.path.join(self.attendance_dir, f'attendance_{date_str}.json')
        
        if os.path.exists(attendance_file):
            os.remove(attendance_file)
            return True
        return False

    def get_daily_attendance_counts(self, period="weekly"):
        """Get daily attendance counts for the specified period
        
        Args:
            period (str): 'weekly', 'monthly', or 'semester'
            
        Returns:
            tuple: (dates, counts) - Lists of dates and corresponding attendance counts
        """
        attendance_files = sorted([f for f in os.listdir(self.attendance_dir) 
                                if f.startswith('attendance_') and f.endswith('.json')])
        
        data = []
        for file in attendance_files:
            with open(os.path.join(self.attendance_dir, file), 'r') as f:
                attendance = json.load(f)
                date = datetime.strptime(attendance['date'], '%Y-%m-%d')
                
                # Filter by period
                days_diff = (datetime.now() - date).days
                if period == "weekly" and days_diff > 7:
                    continue
                elif period == "monthly" and days_diff > 30:
                    continue
                elif period == "semester" and days_diff > 180:
                    continue
                    
                data.append({
                    'date': date,
                    'count': attendance['present_count']
                })
        
        if not data:
            return [], []
            
        # Sort by date
        data.sort(key=lambda x: x['date'])
        
        # Split into separate lists
        dates = [d['date'] for d in data]
        counts = [d['count'] for d in data]
        
        return dates, counts

    def get_attendance_trend(self, period=None):
        """Get attendance trend data over a specified period
        
        Args:
            period (str): 'week', 'month', 'semester'
            
        Returns:
            dict: Dictionary containing dates and present counts
        """
        # Get all attendance records, sorted by date
        attendance_files = sorted([f for f in os.listdir(self.attendance_dir) 
                                if f.startswith('attendance_') and f.endswith('.json')])
        
        data = []
        for file in attendance_files:
            with open(os.path.join(self.attendance_dir, file), 'r') as f:
                attendance = json.load(f)
                date = datetime.strptime(attendance['date'], '%Y-%m-%d')
                
                # Filter by period if specified
                days_diff = (datetime.now() - date).days
                if period == "week" and days_diff > 7:
                    continue
                elif period == "month" and days_diff > 30:
                    continue
                elif period == "semester" and days_diff > 180:
                    continue
                    
                data.append({
                    'date': date,
                    'present_count': attendance['present_count']
                })
        
        if not data:
            return None
            
        # Sort by date
        data.sort(key=lambda x: x['date'])
        
        return {
            'dates': [d['date'] for d in data],
            'present_counts': [d['present_count'] for d in data]
        }

class AttendanceChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
    def update_chart(self, figure):
        """Update the chart display"""
        # Clear previous widgets
        for i in reversed(range(self.layout.count())): 
            self.layout.itemAt(i).widget().setParent(None)
            
        if figure:
            canvas = FigureCanvas(figure)
            self.layout.addWidget(canvas)
            
    def plot_attendance_pie(self, days_present, days_absent, title="Attendance Distribution"):
        """Plot a pie chart showing attendance distribution"""
        fig, ax = plt.subplots(figsize=(8, 6))
        plt.pie([days_present, days_absent],
                labels=['Present', 'Absent'],
                colors=['#34c759', '#ff3b30'],
                autopct='%1.1f%%')
        plt.title(title)
        self.update_chart(fig)
        
    def plot_attendance_trend(self, dates, counts, title="Attendance Trend"):
        """Plot a line chart showing attendance trend"""
        fig, ax = plt.subplots(figsize=(8, 6))
        plt.plot(dates, counts, marker='o')
        plt.title(title)
        plt.xticks(rotation=45)
        plt.ylabel('Present Count')
        plt.grid(True)
        plt.tight_layout()
        self.update_chart(fig)
