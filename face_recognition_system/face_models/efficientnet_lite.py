"""
EfficientNet-Lite0 — Adapted as face recognition backbone.

Paper:  EfficientNet: Rethinking Model Scaling for CNNs (arXiv:1905.11946)
        Lite variant removes Squeeze-and-Excitation and uses ReLU6.

Uses timm's EfficientNet-Lite0 as a backbone,
replaces the classifier head with a face embedding layer.

Input:  112×112 RGB face crop
Output: 512-dimensional embedding vector
Params: ~3.4 M
"""

import torch
import torch.nn as nn
import timm


class EfficientNetLite0Face(nn.Module):
    """
    EfficientNet-Lite0 adapted for face recognition.

    The Lite variant is designed for mobile/edge deployment:
        - No Squeeze-and-Excitation blocks
        - ReLU6 instead of Swish
        - Fixed input resolution support
    """

    def __init__(self, embedding_size=512, pretrained=False):
        super().__init__()

        # Load EfficientNet-Lite0 backbone (no classifier)
        self.backbone = timm.create_model(
            'efficientnet_lite0',
            pretrained=pretrained,
            num_classes=0,           # remove classifier
            global_pool='avg',       # keep global average pooling
        )

        # Get the feature dimension from the backbone
        with torch.no_grad():
            dummy = torch.randn(1, 3, 112, 112)
            feat_dim = self.backbone(dummy).shape[-1]

        # Embedding head
        self.embedding = nn.Sequential(
            nn.Linear(feat_dim, embedding_size, bias=False),
            nn.BatchNorm1d(embedding_size),
        )

    def forward(self, x):
        x = self.backbone(x)
        x = self.embedding(x)
        return x
