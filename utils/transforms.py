from torchvision import transforms

def get_transforms():
    # --- PHASE 2: Aggressive Data Augmentation ---
    # These random changes are applied on-the-fly ONLY during training.
    # Every time the model sees an image, it will look slightly different.
    train_transform = transforms.Compose([
        transforms.Resize((48, 48)),            # Standardize size
        transforms.Grayscale(num_output_channels=3), # Standardize channels
        
        # 1. Spatial Augmentations
        transforms.RandomHorizontalFlip(p=0.5), # 50% chance to flip (mirrors reality)
        transforms.RandomRotation(15),          # Randomly tilt the head up to 15 degrees
        transforms.RandomAffine(degrees=0, translate=(0.1, 0.1)), # Shift the face slightly off-center
        
        # 2. Pixel-level Augmentations
        transforms.ColorJitter(brightness=0.2, contrast=0.2), # Simulate bad webcam lighting
        
        # Standard math conversions
        transforms.ToTensor(),
        transforms.Normalize((0.5,), (0.5,))
    ])

    # Validation/Test transforms remain STRICT.
    # We never randomly augment the validation data because we need a consistent, 
    # honest benchmark to calculate our true loss and accuracy.
    val_transform = transforms.Compose([
        transforms.Resize((48, 48)),
        transforms.Grayscale(num_output_channels=3),
        transforms.ToTensor(),
        transforms.Normalize((0.5,), (0.5,))
    ])

    return train_transform, val_transform