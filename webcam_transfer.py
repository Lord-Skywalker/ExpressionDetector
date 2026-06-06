import cv2
import torch
import torch.nn.functional as F
from PIL import Image
import os
import datetime

# --- CHANGE 1: Import the ResNet Architecture ---
from model_transfer import TransferEmotionCNN
from utils import get_transforms

def run_live_webcam():
    print("Booting up the Heavyweight ResNet AI...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    save_folder = "emotion_collection"
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)

    # --- CHANGE 2: Point to the ResNet Weights ---
    model_path = "saved_models/resnet_emotion_model.pth"
    if not os.path.exists(model_path):
        print(f"\n[!] ERROR: Could not find '{model_path}'. Did you finish training?")
        return

    # --- CHANGE 3: Initialize the ResNet Brain ---
    model = TransferEmotionCNN(num_classes=7).to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()

    _, val_transform = get_transforms()
    emotion_dict = {0: 'Angry', 1: 'Disgust', 2: 'Fear', 3: 'Happy', 4: 'Neutral', 5: 'Sad', 6: 'Surprise'}

    # Load OpenCV Face Hunter (Using the highly sensitive parameters)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    cap = cv2.VideoCapture(0)
    print("\n====================================")
    print(" RESNET LIVE FEED STARTED!")
    print("------------------------------------")
    print(" CONTROLS:")
    print(" [S] - Save a Snapshot")
    print(" [Q] - Quit the Application")
    print("====================================")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab camera frame. Exiting...")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=3, minSize=(30, 30))

        current_top_emotion = "NoFace"

        for (x, y, w, h) in faces:
            # Draw the bounding box
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cropped_face = frame[y:y+h, x:x+w]
            
            try:
                # Format for ResNet (RGB & Tensor)
                cropped_face_rgb = cv2.cvtColor(cropped_face, cv2.COLOR_BGR2RGB)
                img_pil = Image.fromarray(cropped_face_rgb)
                img_tensor = val_transform(img_pil).unsqueeze(0).to(device)
                
                # ResNet Inference
                with torch.no_grad():
                    outputs = model(img_tensor)
                    probabilities = F.softmax(outputs, dim=1)
                    prediction = torch.argmax(probabilities, dim=1).item()
                    confidence = probabilities[0][prediction].item() * 100
                
                current_top_emotion = emotion_dict[prediction]
                label = f"{current_top_emotion.upper()} ({confidence:.1f}%)"
                
                # Write the label
                cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            except Exception as e:
                pass

        # Updated Window Title
        cv2.imshow('ResNet18 Emotion AI - Live', frame)

        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'): 
            break
        elif key == ord('s'): 
            # Updated Snapshot Naming logic to specify it was taken by ResNet
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{save_folder}/resnet_{current_top_emotion}_{timestamp}.jpg"
            cv2.imwrite(filename, frame)
            print(f"[!] SNAPSHOT SAVED: {filename}")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    run_live_webcam()