"""
Copyright (C) 2019 NVIDIA Corporation.  All rights reserved.
Licensed under the CC BY-NC-SA 4.0 license
(https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode).
"""
import os.path
from PIL import Image
import glob

import torch.utils.data as data
import torch
import torchvision
import numpy as np
import random
from PIL import ImageFilter, ImageOps


def default_loader(path):
    return Image.open(path).convert('RGB')


class Dataset(data.Dataset):
    def __init__(self, root, image_size, transform=None, loader=default_loader, train=True, return_paths=False):
        super(Dataset, self).__init__()
        self.root = root
        print(root)
        if train:
            self.im_list = glob.glob(os.path.join(self.root, 'train', '*/*.jpg'))
            self.class_dir = glob.glob(os.path.join(self.root, 'train', '*'))
        else:
            self.im_list = glob.glob(os.path.join(self.root, 'test', '*/*.jpg'))
            self.class_dir = glob.glob(os.path.join(self.root, 'test', '*'))

        self.transform = transform
        self.loader = loader

        self.imgs = [(im_path, self.class_dir.index(os.path.dirname(im_path))) for
                     im_path in self.im_list]
        random.shuffle(self.imgs)

        self.return_paths = return_paths
        self.train = train
        self.image_size = image_size

        print('Seceed loading dataset!')

    def __getitem__(self, index):
        img_path, label = self.imgs[index]
        target_height, target_width = self.image_size, self.image_size

        # image and its flipped image
        seg_path = img_path.replace('.jpg', '.png')
        img = self.loader(img_path)
        seg = Image.open(seg_path)
        W, H = img.size

        if self.train:
            if random.uniform(0, 1) < 0.5:
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
                seg = seg.transpose(Image.FLIP_LEFT_RIGHT)

            h = random.randint(int(0.90 * H), int(0.99 * H))
            w = random.randint(int(0.90 * W), int(0.99 * W))
            left = random.randint(0, W-w)
            upper = random.randint(0, H-h)
            right = random.randint(w - left, W)
            lower = random.randint(h - upper, H)
            img = img.crop((left, upper, right, lower))
            seg = seg.crop((left, upper, right, lower))

        W, H = img.size
        desired_size = max(W, H)
        delta_w = desired_size - W
        delta_h = desired_size - H
        padding = (delta_w//2, delta_h//2, delta_w-(delta_w//2), delta_h-(delta_h//2))
        img = ImageOps.expand(img, padding)
        seg = ImageOps.expand(seg, padding)

        img = img.resize((target_height, target_width))
        seg = seg.resize((target_height, target_width))
        seg = seg.point(lambda p: p > 160 and 255)
        edge = seg.filter(ImageFilter.FIND_EDGES)
        edge = edge.filter(ImageFilter.SMOOTH_MORE)
        edge = edge.point(lambda p: p > 20 and 255)
        edge = torchvision.transforms.functional.to_tensor(edge).max(0, True)[0]

        from torchvision.utils import save_image
        img = torchvision.transforms.functional.to_tensor(img)
        #save_image(img, 'img1.png')
        seg = torchvision.transforms.functional.to_tensor(seg)[0].unsqueeze(0)
        #save_image(seg, 'imgS1.png')
        img = img * seg + torch.ones_like(img) * (1 - seg)
        #save_image(img, 'imgR1.png')

        rgbs = torch.cat([img, seg], dim=0)

        data= {'images': rgbs, 'path': img_path, 'label': label,
               'edge': edge}

        return {'data': data}

    def __len__(self):
        return len(self.imgs)
