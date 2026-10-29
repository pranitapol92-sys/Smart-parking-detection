from ultralytics import YOLO
import cv2

# Load YOLO model
model = YOLO("yolo11n.pt")

# Open camera
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Camera open nahi zala!")
    exit()

print("Camera started. Press Q to exit.")

while True:

    ret, frame = cap.read()

    if not ret:
        print("Camera frame nahi milala.")
        break

    # AI vehicle detection
    results = model(frame)

    # Display detection results
    annotated_frame = results[0].plot()

    cv2.imshow(
        "AI Vehicle Detection",
        annotated_frame
    )

    # Press Q to close
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()