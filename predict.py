import cv2
import torch
import torch.nn.functional as F
from PIL import Image
import os
import sys
import datetime
from model import EmotionCNN
from utils import get_transforms

def predict_emotion_auto(target_image_name):
    # ==========================================
    # --- FOLDER ORGANIZATION & SETUP ---
    # ==========================================
    # 1. Ensure our clean directory structure exists
    input_folder = "test_images"
    debug_folder = "debug_crops"
    
    for folder in [input_folder, debug_folder]:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"[*] Created new directory: '{folder}/'")

    # 2. Smart Path Resolution
    # Check if the user typed the exact path, OR if it's sitting inside our test_images folder
    if os.path.exists(target_image_name):
        image_path = target_image_name
    elif os.path.exists(os.path.join(input_folder, target_image_name)):
        image_path = os.path.join(input_folder, target_image_name)
    else:
        print(f"\n[!] ERROR: Could not find '{target_image_name}'.")
        print(f"    Please drop the image into the '{input_folder}/' folder and try again.")
        return

    # 3. Setup Device & Load AI
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model_path = "saved_models/emotion_model.pth"

    if not os.path.exists(model_path):
        print(f"Error: Could not find trained model at {model_path}")
        return

    model = EmotionCNN(num_classes=7).to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()

    _, val_transform = get_transforms()
    emotion_dict = {0: 'Angry', 1: 'Disgust', 2: 'Fear', 3: 'Happy', 4: 'Neutral', 5: 'Sad', 6: 'Surprise'}

    # ==========================================
    # --- STAGE 1: THE AUTO-CROPPER (OPENCV) ---
    # ==========================================
    print(f"\n[1] Loading raw image from: '{image_path}'")
    img_cv = cv2.imread(image_path)
    
    if img_cv is None:
        print(f"Error: Could not load the image. File might be corrupted.")
        return

    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    print("[2] Scanning for human faces...")
    # *** THE UPDATED BOUNCER PARAMETERS ***
    # scaleFactor=1.05 and minNeighbors=3 make it highly sensitive to catch tough faces
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=3, minSize=(20, 20))

    if len(faces) == 0:
        print("\n[!] ERROR: No face detected in the image!")
        print("    The face might be too dark, turned away, or obscured.")
        return

    (x, y, w, h) = faces[0]
    print(f"[3] Face locked at coordinates: X:{x}, Y:{y}")
    
    cropped_face_cv = img_cv[y:y+h, x:x+w]

    # Dynamically name and save the debug crop into its dedicated folder
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_filename = f"{debug_folder}/{base_name}_crop_{timestamp}.jpg"

    cv2.imwrite(debug_filename, cropped_face_cv)
    print(f"[4] Saved verification crop to: '{debug_filename}'")

    # ==========================================
    # --- STAGE 2: THE PREDICTOR (PYTORCH) ---
    # ==========================================
    cropped_face_rgb = cv2.cvtColor(cropped_face_cv, cv2.COLOR_BGR2RGB)
    img_pil = Image.fromarray(cropped_face_rgb)

    img_tensor = val_transform(img_pil).unsqueeze(0).to(device)

    print(f"[5] Analyzing geometric features on {device}...")
    with torch.no_grad():
        outputs = model(img_tensor)
        probabilities = F.softmax(outputs, dim=1)
        prediction = torch.argmax(probabilities, dim=1).item()
        confidence = probabilities[0][prediction].item() * 100

    predicted_emotion = emotion_dict[prediction]
    print("\n" + "="*40)
    print(f" PREDICTED EMOTION: {predicted_emotion.upper()}")
    print(f" CONFIDENCE:        {confidence:.2f}%")
    print("="*40)

    print("\nDetailed Breakdown:")
    for i, prob in enumerate(probabilities[0]):
        print(f" - {emotion_dict[i]}: {prob.item()*100:.2f}%")

if __name__ == "__main__":
    # Default to a placeholder name if the user forgets to type one
    target = sys.argv[1] if len(sys.argv) > 1 else "me.jpg"
    predict_emotion_auto(target)