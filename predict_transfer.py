import cv2
import torch
import torch.nn.functional as F
from PIL import Image
import os
import sys
import datetime
from model_transfer import TransferEmotionCNN
from utils import get_transforms

def predict_emotion_auto(target_image_name):
    input_folder = "test_images"
    debug_folder = "debug_crops"
    
    for folder in [input_folder, debug_folder]:
        if not os.path.exists(folder):
            os.makedirs(folder)

    if os.path.exists(target_image_name):
        image_path = target_image_name
    elif os.path.exists(os.path.join(input_folder, target_image_name)):
        image_path = os.path.join(input_folder, target_image_name)
    else:
        print(f"\n[!] ERROR: Could not find '{target_image_name}'.")
        return

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # --- CHANGE 1: Load the ResNet weights ---
    model_path = "saved_models/resnet_emotion_model.pth"

    if not os.path.exists(model_path):
        print(f"Error: Could not find trained model at {model_path}")
        return

    # --- CHANGE 2: Boot up the ResNet Architecture ---
    model = TransferEmotionCNN(num_classes=7).to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()

    _, val_transform = get_transforms()
    emotion_dict = {0: 'Angry', 1: 'Disgust', 2: 'Fear', 3: 'Happy', 4: 'Neutral', 5: 'Sad', 6: 'Surprise'}

    print(f"\n[1] Loading raw image from: '{image_path}'")
    img_cv = cv2.imread(image_path)
    if img_cv is None:
        print("Error loading image.")
        return

    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    print("[2] Scanning for human faces...")
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=3, minSize=(20, 20))

    if len(faces) == 0:
        print("\n[!] ERROR: No face detected in the image!")
        return

    (x, y, w, h) = faces[0]
    print(f"[3] Face locked at coordinates: X:{x}, Y:{y}")
    
    cropped_face_cv = img_cv[y:y+h, x:x+w]

    base_name = os.path.splitext(os.path.basename(image_path))[0]
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_filename = f"{debug_folder}/resnet_{base_name}_crop_{timestamp}.jpg"

    cv2.imwrite(debug_filename, cropped_face_cv)
    print(f"[4] Saved verification crop to: '{debug_filename}'")

    cropped_face_rgb = cv2.cvtColor(cropped_face_cv, cv2.COLOR_BGR2RGB)
    img_pil = Image.fromarray(cropped_face_rgb)
    img_tensor = val_transform(img_pil).unsqueeze(0).to(device)

    print(f"[5] ResNet is analyzing geometric features on {device}...")
    with torch.no_grad():
        outputs = model(img_tensor)
        probabilities = F.softmax(outputs, dim=1)
        prediction = torch.argmax(probabilities, dim=1).item()
        confidence = probabilities[0][prediction].item() * 100

    predicted_emotion = emotion_dict[prediction]
    print("\n" + "="*40)
    print(f" RESNET PREDICTION: {predicted_emotion.upper()}")
    print(f" CONFIDENCE:        {confidence:.2f}%")
    print("="*40)

    print("\nDetailed Breakdown:")
    for i, prob in enumerate(probabilities[0]):
        print(f" - {emotion_dict[i]}: {prob.item()*100:.2f}%")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "me.jpg"
    predict_emotion_auto(target)