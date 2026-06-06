import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision.datasets import ImageFolder
from model_transfer import TransferEmotionCNN
from utils import get_transforms
import os

def train_model():
    # 1. Setup Device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on: {device}")

    # 2. Load Transforms and Data
    train_transform, val_transform = get_transforms()
    
    if not os.path.exists('dataset/train') or not os.path.exists('dataset/val'):
        print("Error: Ensure both 'dataset/train' and 'dataset/val' folders exist.")
        return

    train_dataset = ImageFolder(root='dataset/train', transform=train_transform)
    val_dataset = ImageFolder(root='dataset/val', transform=val_transform)

    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)

    # 3. Initialize the ResNet Transfer Model
    model = TransferEmotionCNN(num_classes=7).to(device)
    
    # ISOLATED SAVE PATH: We use a new name so your custom model is totally safe
    model_path = "saved_models/resnet_emotion_model.pth"
    
    if os.path.exists(model_path):
        try:
            print("Loading existing ResNet weights...")
            model.load_state_dict(torch.load(model_path, map_location=device))
            print("Success: Resuming from previous state.")
        except Exception as e:
            print(f"Starting fresh: {e}")
    
    # Phase 3: Class Weights
    class_weights = torch.tensor([1.0, 5.0, 1.0, 0.5, 1.0, 1.0, 1.0]).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    
    optimizer = optim.Adam(model.parameters(), lr=0.0001)
    
    # Phase 1: Scheduler (Now we will feed it the VALIDATION loss instead of training loss)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', patience=3, factor=0.5)

    if not os.path.exists('saved_models'):
        os.makedirs('saved_models')

    # 4. Training Loop with Validation Integration
    epochs = 20
    best_val_loss = float('inf') # Set the initial best score to infinity
    print("Starting Transfer Learning training...")
    
    for epoch in range(epochs):
        # --- TRAINING PHASE ---
        model.train() # Tell the model it is allowed to learn
        running_loss = 0.0
        
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            
            outputs = model(images)
            loss = criterion(outputs, labels)
            
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item()
            
        avg_train_loss = running_loss / len(train_loader)

        # --- VALIDATION PHASE ---
        model.eval() # Tell the model to STOP learning (Test mode)
        val_running_loss = 0.0
        
        with torch.no_grad(): # Turn off memory-heavy gradient calculations
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device)
                
                outputs = model(images)
                loss = criterion(outputs, labels)
                val_running_loss += loss.item()
                
        avg_val_loss = val_running_loss / len(val_loader)
        current_lr = optimizer.param_groups[0]['lr']
        
        print(f"Epoch [{epoch+1}/{epochs}] | Train Loss: {avg_train_loss:.4f} | Val Loss: {avg_val_loss:.4f} | LR: {current_lr}")
        
        # Step the scheduler based on the REAL-WORLD test score, not the practice test
        scheduler.step(avg_val_loss)

        # --- SAVE THE BEST MODEL ---
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            torch.save(model.state_dict(), model_path)
            print(f" --> New best model found! Saved to {model_path}")

    print("Training complete! Your Heavyweight ResNet model is ready for deployment.")

if __name__ == "__main__":
    train_model()