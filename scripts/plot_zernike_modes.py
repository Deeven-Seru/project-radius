"""plot_zernike_modes.py - Renders a 4x5 grid of first 20 Zernike mode surfaces."""
import numpy as np, matplotlib.pyplot as plt, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__),'..'))
from src.zernike_simulator import zernike

DOCS = os.path.join(os.path.dirname(__file__),'..','docs','images')
os.makedirs(DOCS, exist_ok=True)
rho=np.linspace(0,1,80); theta=np.linspace(0,2*np.pi,80)
RHO,THETA=np.meshgrid(rho,theta); X=RHO*np.cos(THETA); Y=RHO*np.sin(THETA)
NAMES=['Piston','Tip','Tilt','Defocus','Astig 45','Astig 0','Coma V','Coma H',
       'Trefoil V','Trefoil H','Sph. Aber.','Sec. Astig V','Sec. Astig H',
       'Sec. Coma V','Sec. Coma H','Tetrafoil V','Tetrafoil H','Z18','Z19','Z20']
fig,axes=plt.subplots(4,5,figsize=(15,12),facecolor='black')
for j,ax in enumerate(axes.flat,start=1):
    Z=zernike(j,RHO,THETA); ax.pcolormesh(X,Y,Z,cmap='RdBu_r',shading='auto')
    ax.set_aspect('equal'); ax.axis('off'); ax.set_facecolor('black')
    ax.set_title(f"Z{j}: {NAMES[j-1]}",color='white',fontsize=8)
plt.suptitle('First 20 Zernike Modes',color='white',fontsize=14)
plt.tight_layout()
plt.savefig(os.path.join(DOCS,'zernike_modes_grid.png'),dpi=120,bbox_inches='tight',facecolor='black')
plt.close(); print("Saved: zernike_modes_grid.png")
