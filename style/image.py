import torch
import numpy as np
import math
import torchvision.transforms as t
from collections import namedtuple
import PIL

from style.random import white_noise

vgg_mean = torch.tensor([0.485, 0.456, 0.406])
vgg_std = torch.tensor([0.229, 0.224, 0.225])

def to_torch(x):
    if hasattr(x, '__array__'):
        x = np.asarray(x)
    return t.ToTensor()(x).unsqueeze(0)

def to_np(x):
    if isinstance(x, PIL.Image.Image):
        x = np.array(x, dtype=np.float32) / 255.0
        if x.ndim == 2:
            x = np.expand_dims(x, -1)
    elif isinstance(x, torch.Tensor):
        x = x.detach().cpu().squeeze().numpy()
        if x.ndim == 2:
            x = np.expand_dims(x, 0)
        x = np.transpose(x, (1,2,0))
    else:
        x = np.asarray(x)
    return x

def to_image(x):
    return to_np(x).view(Image)

def to_pil(x):    
    if isinstance(x, (np.ndarray, np.generic)):
        x = (x*255).astype(np.uint8)
        x = t.ToPILImage()(x)
    elif isinstance(x, torch.Tensor):
        x = to_pil(to_np(x))    
    elif hasattr(x, '__array__'):
        x = to_pil(to_np(x))    
    return x

def open(fname):
    return to_image(to_np(PIL.Image.open(fname).convert('RGB')))

def new_random_white(shape, mean=None, sigma=1e-2):
    if mean is None:
        mean = np.array([0.5,0.5,0.5]).reshape(1,1,3)
    elif isinstance(mean, (np.ndarray, np.generic)):
        mean = mean.mean((0,1), keepdims=True)

    img = np.clip(mean + white_noise(shape, sigma), 0, 1).astype(np.float32)
    return to_image(img)

def save(fname, x):
    to_pil(x).save(fname)

BILINEAR = PIL.Image.BILINEAR
NEAREST = PIL.Image.NEAREST

def pyramid_scale_factors(nlevels=3):
    return [0.5**l for l in range(nlevels)][::-1]

def borderless_view(x, border):    
    b = border
    if b > 0:
        if isinstance(x, torch.Tensor):
            return x[...,b:-b, b:-b]
        else:
            return x[b:-b, b:-b]
    else:
        return x

Border = namedtuple('Border', 'tl t tr r br b bl l ft fr fb fl')

def border_elements(x, b):    

    if isinstance(x, torch.Tensor):
        h, w = x.shape[-2:]
        
        return Border(
            tl=x[...,:b, :b],
            t=x[...,:b, b:-b],
            tr=x[...,:b, -b:],
            r=x[...,b:-b, -b:],
            br=x[...,-b:, -b:],
            b=x[...,-b:, b:-b],
            bl=x[...,-b:, :b],
            l=x[...,b:-b, :b],
            ft=x[...,:b, :],
            fr=x[...,-b:],
            fb=x[...,-b:, :],
            fl=x[...,:b],
        )
    else:
        # assume numpy
        h, w = x.shape[:2]
        
        return Border(
            tl=x[:b, :b],
            t=x[:b, b:-b],
            tr=x[:b, -b:],
            r=x[b:-b, -b:],
            br=x[-b:, -b:],
            b=x[-b:, b:-b],
            bl=x[-b:, :b],
            l=x[b:-b, :b],
            ft=x[:b, :],
            fr=x[:,-b:],
            fb=x[-b:, :],
            fl=x[:,:b],
        )

class Image(np.ndarray):
    def __new__(cls, *args, **kwargs):        
        return super(Image, cls).__new__(cls, *args, **kwargs)

    def __init__(self, *args, **kwargs):
        pass

    def __array_finalize__(self, obj):
        pass

    def save(self, fname):
        to_pil(self).save(fname)
    
    def show(self):
        to_pil(self).show()

    def _repr_png_(self):
        return to_pil(self)._repr_png_()

    def resize(self, shape, resample=BILINEAR):
        if self.shape[:2] == shape:
            return self
        else:
            return to_image(to_pil(self).resize(shape[::-1], resample))

    def rotate(self, degree, resample=BILINEAR, expand=True):
        return to_image(to_pil(self).rotate(degree, resample=resample, expand=True))

    def scale_by(self, factor, resample=BILINEAR):
        if not isinstance(factor, tuple):
            factor = (factor, factor)
        
        h,w = self.data.shape[:2]
        newhw = (int(math.ceil(h*factor[0])), int(math.ceil(w*factor[1])))
        return self.resize(newhw, resample=resample)
    
    def up(self, repeat=1, resample=BILINEAR):        
        return self.scale_by(2**repeat)
    
    def down(self, repeat=1, resample=BILINEAR):
        return self.scale_by(0.5**repeat)
    
    def scale_to(self, shape, resample=BILINEAR):
        if not isinstance(shape, tuple):
            shape = (shape, shape)
        
        return self.resize(shape[:2], resample=resample)
                
    def scale_short_to(self, size, resample=BILINEAR):
        return self._scale_side_to(np.argmin, size, resample)
        
    def scale_long_to(self, size, resample=BILINEAR):
        return self._scale_side_to(np.argmax, size, resample)        
    
    def _scale_side_to(self, fnc, size, resample=BILINEAR):
        hw = self.data.shape[:2]
        
        idx = fnc(hw)
        otherx = (idx + 1) % 2
        f = size / hw[idx]
        
        newhw = [0,0]
        newhw[idx] = size
        newhw[otherx] = int(math.ceil(hw[otherx]*f))
        
        return self.resize(newhw, resample=resample)