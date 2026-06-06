import torch
import torch.nn as nn
from torchvision import models

class TransferEmotionCNN(nn.Module):
    def __init__(self, num_classes=7):
        super(TransferEmotionCNN, self).__init__()
        
        # 1. Download the pre-trained ResNet18 brain
        print("Downloading ResNet18 weights...")
        self.resnet = models.resnet18(weights='DEFAULT')
        
        # 2. Chop off the final 1000-class layer
        num_ftrs = self.resnet.fc.in_features
        
        # 3. Glue on our new 7-Emotion Head
        self.resnet.fc = nn.Linear(num_ftrs, num_classes)

    def forward(self, x):
        return self.resnet(x)