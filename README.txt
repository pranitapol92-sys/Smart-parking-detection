SMART PARKING DETECTION - FINAL READY PROJECT
================================================

1. Install Python 3.10-3.12 if possible for the smoothest YOLO setup.
2. Open Command Prompt in this folder.
3. Run:
   python -m pip install -r requirements.txt
4. Run:
   python main.py

LOGIN
-----
Username: admin
Password: admin123

FILES
-----
main.py                         Main application
parking.db                      Created automatically on first run
parking_background_clean.png    Project background
requirements.txt                Required packages
README.txt                      Instructions

FEATURES
--------
- Login
- Customer registration
- Vehicle registration
- Parking slot management (20 slots)
- Vehicle search
- Parking entry / exit
- AI vehicle detection using YOLO
- Parking history
- Payment / billing
- Payment history
- Parking report
- Notifications
- Feedback
- Settings
- Help / About
- Automatic next-page navigation after major forms

IMPORTANT
---------
Keep parking_background_clean.png in the same folder as main.py.
The application creates parking.db automatically.
If YOLO/camera is unavailable, the rest of the GUI and database features still work.

BACKGROUND IMAGE
----------------
The supplied Smart Parking image is used as the SAME background for:
Login, Dashboard, Customer Registration, Vehicle Registration,
Parking Slot Management, Parking Detection, Payment/Billing,
History, Feedback, Settings and other project forms.
Keep parking_background_clean.png in the same folder as main.py.
