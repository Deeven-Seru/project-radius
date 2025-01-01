"""generate_readme_images.py - Generates static SVG figures for README."""
import os, numpy as np
import matplotlib; matplotlib.use('Agg'); matplotlib.rcParams['svg.fonttype']='none'
import matplotlib.pyplot as plt
from PIL import Image

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
DATA = os.path.join(BASE,'data','dataset')
DOCS = os.path.join(BASE,'docs','images')
os.makedirs(DOCS, exist_ok=True)

frame = os.path.join(DATA,'frame_0000.bmp')
if os.path.exists(frame):
    img = np.array(Image.open(frame))
    plt.figure(figsize=(8,8), facecolor='black')
    plt.imshow(img, cmap='inferno'); plt.axis('off')
    plt.title("Simulated Shack-Hartmann Spot Field", color='white', pad=20, fontsize=16)
    plt.tight_layout()
    plt.savefig(os.path.join(DOCS,'wfs_spot_field_inferno.svg'), format='svg', facecolor='black', bbox_inches='tight')
    plt.close(); print("Generated: wfs_spot_field_inferno.svg")
