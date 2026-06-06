import cv2
import torch
import torch.nn.functional as F
from PIL import Image
import os
import datetime
from model import EmotionCNN
from utils import get_transforms

def run_live_webcam():
    print("Booting up the AI...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # --- SETUP FOLDERS ---
    save_folder = "emotion_collection"
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)
        print(f"[*] Created new directory: '{save_folder}/' for snapshots.")

    # --- 1. LOAD THE BRAIN (PyTorch) ---
    model_path = "saved_models/emotion_model.pth"
    if not os.path.exists(model_path):
        print(f"\n[!] ERROR: Could not find '{model_path}'.")
        return

    model = EmotionCNN(num_classes=7).to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()

    _, val_transform = get_transforms()
    emotion_dict = {0: 'Angry', 1: 'Disgust', 2: 'Fear', 3: 'Happy', 4: 'Neutral', 5: 'Sad', 6: 'Surprise'}

    # --- 2. LOAD THE EYES (OpenCV) ---
    # We use the slightly loosened parameters here too so it catches your face easily!
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    # --- 3. TURN ON THE CAMERA ---
    cap = cv2.VideoCapture(0) # '0' is your default laptop camera
    print("\n====================================")
    print(" LIVE FEED STARTED!")
    print("------------------------------------")
    print(" CONTROLS:")
    print(" [S] - Save a Snapshot")
    print(" [Q] - Quit the Application")
    print("====================================")

    while True:
        # Grab a single frame of video
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab camera frame. Exiting...")
            break

        # Convert to grayscale for the face hunter
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Hunt for faces in this specific frame
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=3, minSize=(30, 30))

        current_top_emotion = "NoFace"

        # Loop through every face it finds
        for (x, y, w, h) in faces:
            # Draw a green bounding box around the face
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            # Crop the face out
            cropped_face = frame[y:y+h, x:x+w]
            
            try:
                # Translate OpenCV (BGR) to PyTorch (RGB & Tensor)
                cropped_face_rgb = cv2.cvtColor(cropped_face, cv2.COLOR_BGR2RGB)
                img_pil = Image.fromarray(cropped_face_rgb)
                img_tensor = val_transform(img_pil).unsqueeze(0).to(device)
                
                # Make the prediction
                with torch.no_grad():
                    outputs = model(img_tensor)
                    probabilities = F.softmax(outputs, dim=1)
                    prediction = torch.argmax(probabilities, dim=1).item()
                    confidence = probabilities[0][prediction].item() * 100
                
                # Create the text label
                current_top_emotion = emotion_dict[prediction]
                label = f"{current_top_emotion.upper()} ({confidence:.1f}%)"
                
                # Write the label right above the bounding box
                cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            except Exception as e:
                pass

        # Show the final video frame on your screen
        cv2.imshow('Emotion AI', frame)

        # --- KEYBOARD CONTROLS ---
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'): # Quit
            break
        elif key == ord('s'): # Save Snapshot
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{save_folder}/{current_top_emotion}_{timestamp}.jpg"
            cv2.imwrite(filename, frame)
            print(f"[!] SNAPSHOT SAVED: {filename}")

    # Clean up and turn off the camera light
    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    run_live_webcam()