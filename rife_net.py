"""RIFE v4.25 frame interpolation, used to draw the join of a seamless loop.

Network code from HolyWu/vs-rife (MIT License, Copyright (c) 2021 HolyWu),
itself based on hzwer/Practical-RIFE (MIT).  Weights: flownet_v4.25.pkl from
https://github.com/HolyWu/vs-rife/releases/download/model/flownet_v4.25.pkl

Only PyTorch and Pillow are needed; no VapourSynth.  Runs on CUDA when
available (Modal GPU), otherwise on the CPU (slow, fine for tests).
"""
from __future__ import annotations

import math

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image

WEIGHTS_URL = "https://github.com/HolyWu/vs-rife/releases/download/model/flownet_v4.25.pkl"
_MODULO = 64


def warp(ten_input, ten_flow, ten_flow_div, backwarp_grid):
    dtype = ten_input.dtype
    ten_input = ten_input.to(torch.float)
    ten_flow = ten_flow.to(torch.float)
    ten_flow = torch.cat([ten_flow[:, 0:1] / ten_flow_div[0], ten_flow[:, 1:2] / ten_flow_div[1]], 1)
    grid = (backwarp_grid + ten_flow).permute(0, 2, 3, 1)
    return F.grid_sample(input=ten_input, grid=grid, mode="bilinear", padding_mode="border",
                         align_corners=True).to(dtype)


def conv(in_planes, out_planes, kernel_size=3, stride=1, padding=1, dilation=1):
    return nn.Sequential(
        nn.Conv2d(in_planes, out_planes, kernel_size=kernel_size, stride=stride, padding=padding,
                  dilation=dilation, bias=True),
        nn.LeakyReLU(0.2, True),
    )


class Head(nn.Module):
    def __init__(self):
        super().__init__()
        self.cnn0 = nn.Conv2d(3, 16, 3, 2, 1)
        self.cnn1 = nn.Conv2d(16, 16, 3, 1, 1)
        self.cnn2 = nn.Conv2d(16, 16, 3, 1, 1)
        self.cnn3 = nn.ConvTranspose2d(16, 4, 4, 2, 1)
        self.relu = nn.LeakyReLU(0.2, True)

    def forward(self, x):
        x = x.clamp(0.0, 1.0)
        x = self.relu(self.cnn0(x))
        x = self.relu(self.cnn1(x))
        x = self.relu(self.cnn2(x))
        return self.cnn3(x)


class ResConv(nn.Module):
    def __init__(self, c, dilation=1):
        super().__init__()
        self.conv = nn.Conv2d(c, c, 3, 1, dilation, dilation=dilation, groups=1)
        self.beta = nn.Parameter(torch.ones((1, c, 1, 1)), requires_grad=True)
        self.relu = nn.LeakyReLU(0.2, True)

    def forward(self, x):
        return self.relu(self.conv(x) * self.beta + x)


class IFBlock(nn.Module):
    def __init__(self, in_planes, c=64):
        super().__init__()
        self.conv0 = nn.Sequential(conv(in_planes, c // 2, 3, 2, 1), conv(c // 2, c, 3, 2, 1))
        self.convblock = nn.Sequential(*[ResConv(c) for _ in range(8)])
        self.lastconv = nn.Sequential(nn.ConvTranspose2d(c, 4 * 13, 4, 2, 1), nn.PixelShuffle(2))

    def forward(self, x, flow=None, scale=1):
        x = F.interpolate(x, scale_factor=1.0 / scale, mode="bilinear")
        if flow is not None:
            flow = F.interpolate(flow, scale_factor=1.0 / scale, mode="bilinear") / scale
            x = torch.cat((x, flow), 1)
        feat = self.convblock(self.conv0(x))
        tmp = F.interpolate(self.lastconv(feat), scale_factor=scale, mode="bilinear")
        return tmp[:, :4] * scale, tmp[:, 4:5], tmp[:, 5:]


class IFNet(nn.Module):
    def __init__(self, scale=1):
        super().__init__()
        self.block0 = IFBlock(7 + 8, c=192)
        self.block1 = IFBlock(8 + 4 + 8 + 8, c=128)
        self.block2 = IFBlock(8 + 4 + 8 + 8, c=96)
        self.block3 = IFBlock(8 + 4 + 8 + 8, c=64)
        self.block4 = IFBlock(8 + 4 + 8 + 8, c=32)
        self.encode = Head()
        self.scale_list = [16 / scale, 8 / scale, 4 / scale, 2 / scale, 1 / scale]

    def forward(self, img0, img1, timestep, ten_flow_div, backwarp_grid, f0, f1):
        img0, img1 = img0.clamp(0.0, 1.0), img1.clamp(0.0, 1.0)
        warped_img0, warped_img1 = img0, img1
        flow = mask = feat = None
        blocks = [self.block0, self.block1, self.block2, self.block3, self.block4]
        for i in range(5):
            if flow is None:
                flow, mask, feat = blocks[i](torch.cat((img0, img1, f0, f1, timestep), 1), None,
                                             scale=self.scale_list[i])
            else:
                wf0 = warp(f0, flow[:, :2], ten_flow_div, backwarp_grid)
                wf1 = warp(f1, flow[:, 2:4], ten_flow_div, backwarp_grid)
                fd, mask, feat = blocks[i](
                    torch.cat((warped_img0, warped_img1, wf0, wf1, timestep, mask, feat), 1),
                    flow, scale=self.scale_list[i])
                flow = flow + fd
            warped_img0 = warp(img0, flow[:, :2], ten_flow_div, backwarp_grid)
            warped_img1 = warp(img1, flow[:, 2:4], ten_flow_div, backwarp_grid)
        mask = torch.sigmoid(mask)
        return warped_img0 * mask + warped_img1 * (1 - mask)


class Interpolator:
    """Load once, then call ``between(a, b, count)`` for each join."""

    def __init__(self, weights_path: str, device: str | None = None):
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self.dtype = torch.float16 if self.device.type == "cuda" else torch.float32
        state = torch.load(weights_path, map_location="cpu")
        state = {k.replace("module.", ""): v for k, v in state.items() if "module." in k}
        self.net = IFNet()
        self.net.load_state_dict(state, strict=False)
        self.net.encode.load_state_dict({k.replace("encode.", ""): v for k, v in state.items() if k.startswith("encode.")})
        self.net.eval().to(self.device, self.dtype)

    def _tensor(self, image: Image.Image, pw: int, ph: int) -> torch.Tensor:
        arr = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
        ten = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)
        ten = F.pad(ten, (0, pw - arr.shape[1], 0, ph - arr.shape[0]))
        return ten.to(self.device, self.dtype)

    def at(self, a: Image.Image, b: Image.Image, t: float) -> Image.Image:
        """One frame at position t between a (t=0) and b (t=1)."""
        return self.between(a, b, 1, times=[t])[0]

    @torch.inference_mode()
    def between(self, a: Image.Image, b: Image.Image, count: int, times: list[float] | None = None) -> list[Image.Image]:
        """``count`` new frames evenly spaced between a (t=0) and b (t=1)."""
        w, h = a.size
        pw, ph = math.ceil(w / _MODULO) * _MODULO, math.ceil(h / _MODULO) * _MODULO
        img0, img1 = self._tensor(a, pw, ph), self._tensor(b.resize(a.size), pw, ph)
        ten_flow_div = torch.tensor([(pw - 1.0) / 2.0, (ph - 1.0) / 2.0], dtype=torch.float, device=self.device)
        hor = torch.linspace(-1.0, 1.0, pw, dtype=torch.float, device=self.device).view(1, 1, 1, pw).expand(-1, -1, ph, -1)
        ver = torch.linspace(-1.0, 1.0, ph, dtype=torch.float, device=self.device).view(1, 1, ph, 1).expand(-1, -1, -1, pw)
        grid = torch.cat([hor, ver], 1)
        f0, f1 = self.net.encode(img0), self.net.encode(img1)
        frames = []
        for t in times or [(k + 1) / (count + 1) for k in range(count)]:
            timestep = torch.full([1, 1, ph, pw], t, dtype=self.dtype, device=self.device)
            out = self.net(img0, img1, timestep, ten_flow_div, grid, f0, f1)[0, :, :h, :w]
            arr = (out.float().clamp(0, 1).permute(1, 2, 0).cpu().numpy() * 255.0).round().astype(np.uint8)
            frames.append(Image.fromarray(arr, "RGB"))
        return frames
