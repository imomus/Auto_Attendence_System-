import sys
import os
import shutil
import subprocess

def create_desktop_entry():
    """Create desktop entry for the application"""
    home = os.path.expanduser("~")
    desktop_file = os.path.join(home, ".local/share/applications/smart-attendance.desktop")
    
    icon_path = os.path.abspath("icons/app_icon.png")
    exec_path = os.path.abspath("smart_attendance")
    
    entry_content = f"""[Desktop Entry]
Name=Smart Attendance System
Comment=Face Recognition Based Attendance System
Exec={exec_path}
Icon={icon_path}
Terminal=false
Type=Application
Categories=Education;Office;
"""
    
    os.makedirs(os.path.dirname(desktop_file), exist_ok=True)
    with open(desktop_file, 'w') as f:
        f.write(entry_content)
    
    # Make the desktop entry executable
    os.chmod(desktop_file, 0o755)

def build_application():
    """Build the application using PyInstaller"""
    spec_content = """# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['face1.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('icons/*', 'icons'),
        ('encodings', 'encodings'),
        ('attendance_records', 'attendance_records'),
        ('attendance_analytics', 'attendance_analytics')
    ],
    hiddenimports=['cv2', 'face_recognition', 'numpy', 'pandas', 'matplotlib', 'seaborn'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='smart_attendance',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icons/app_icon.ico'
)
"""
    
    # Create icons directory and add icon
    os.makedirs("icons", exist_ok=True)
    # Note: You need to add an icon file named app_icon.png and app_icon.ico in the icons directory
    
    # Write PyInstaller spec file
    with open("smart_attendance.spec", 'w') as f:
        f.write(spec_content)
    
    # Run PyInstaller
    subprocess.run(["pyinstaller", "smart_attendance.spec"], check=True)

def main():
    # Install dependencies
    print("Installing dependencies...")
    subprocess.run(["pip", "install", "-r", "requirements.txt"], check=True)
    
    # Build application
    print("Building application...")
    build_application()
    
    # Create desktop entry
    print("Creating desktop entry...")
    create_desktop_entry()
    
    print("Installation complete! You can now launch Smart Attendance System from your applications menu.")

if __name__ == "__main__":
    main()
