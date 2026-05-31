"""
MobileFaceNet-style lightweight embedding network.

This implementation follows the MobileFaceNet design pattern for face
verification: depthwise separable bottlenecks, a compact feature extractor,
global depthwise aggregation, and an embedding head. Unlike the previous
placeholder, this is a face-recognition architecture rather than a generic
MobileNetV2 classifier backbone with a random projection layer.
"""

import torch.nn as nn


def conv_bn(inp, oup, kernel_size, stride, padding, groups=1):
    return nn.Sequential(
        nn.Conv2d(inp, oup, kernel_size, stride, padding, groups=groups, bias=False),
        nn.BatchNorm2d(oup),
        nn.PReLU(oup),
    )


class DepthWise(nn.Module):
    def __init__(self, inp, oup, stride, expansion):
        super().__init__()
        hidden_dim = inp * expansion
        self.block = nn.Sequential(
            conv_bn(inp, hidden_dim, 1, 1, 0),
            conv_bn(hidden_dim, hidden_dim, 3, stride, 1, groups=hidden_dim),
            nn.Conv2d(hidden_dim, oup, 1, 1, 0, bias=False),
            nn.BatchNorm2d(oup),
        )
        self.use_residual = stride == 1 and inp == oup

    def forward(self, x):
        out = self.block(x)
        return x + out if self.use_residual else out


class Residual(nn.Module):
    def __init__(self, channels, num_blocks, expansion):
        super().__init__()
        self.blocks = nn.Sequential(
            *[DepthWise(channels, channels, stride=1, expansion=expansion) for _ in range(num_blocks)]
        )

    def forward(self, x):
        return self.blocks(x)


class MobileFaceNet(nn.Module):
    """Compact MobileFaceNet-style backbone for face embeddings."""

    def __init__(self, embedding_size=128, input_size=112, **_kwargs):
        super().__init__()
        if input_size != 112:
            raise ValueError("MobileFaceNet expects 112x112 aligned face crops.")

        self.features = nn.Sequential(
            conv_bn(3, 64, 3, 2, 1),
            conv_bn(64, 64, 3, 1, 1, groups=64),
            DepthWise(64, 64, stride=2, expansion=2),
            Residual(64, num_blocks=4, expansion=2),
            DepthWise(64, 128, stride=2, expansion=4),
            Residual(128, num_blocks=6, expansion=2),
            DepthWise(128, 128, stride=2, expansion=4),
            Residual(128, num_blocks=2, expansion=2),
            conv_bn(128, 512, 1, 1, 0),
        )
        self.global_depthwise = nn.Sequential(
            nn.Conv2d(512, 512, kernel_size=7, groups=512, bias=False),
            nn.BatchNorm2d(512),
        )
        self.embedding = nn.Sequential(
            nn.Flatten(),
            nn.Linear(512, embedding_size, bias=False),
            nn.BatchNorm1d(embedding_size),
        )

    def forward(self, x):
        x = self.features(x)
        x = self.global_depthwise(x)
        return self.embedding(x)
