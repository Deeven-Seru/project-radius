"""generate_rotating_gifs.py - Rotating 3D GIFs with labeled axes for README."""
import os, numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from scipy.ndimage import gaussian_filter

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)),'..')
DATA = os.path.join(BASE,'data','dataset')
DOCS = os.path.join(BASE,'docs','images')
os.makedirs(DOCS, exist_ok=True)

def style(ax, xl, yl, zl, title):
    ax.set_xlabel(xl,color='white',labelpad=10,fontsize=9)
    ax.set_ylabel(yl,color='white',labelpad=10,fontsize=9)
    ax.set_zlabel(zl,color='white',labelpad=10,fontsize=9)
    ax.set_title(title,color='white',pad=12,fontsize=11,fontweight='bold')
    for a in (ax.xaxis,ax.yaxis,ax.zaxis):
        a.set_pane_color((0.05,0.05,0.05,1.0))
        a._axinfo['grid']['color']=(0.3,0.3,0.3,0.5)
    ax.tick_params(axis='x',colors='white',labelsize=7)
    ax.tick_params(axis='y',colors='white',labelsize=7)
    ax.tick_params(axis='z',colors='white',labelsize=7)

x = np.linspace(-1,1,21); X,Y = np.meshgrid(x,x)
valid = np.sqrt(X**2+Y**2) <= 1.0

dm_path = os.path.join(DATA,'dm_coupling.csv')
gt_path = os.path.join(DATA,'ground_truth.csv')
if os.path.exists(dm_path) and os.path.exists(gt_path):
    dm=np.loadtxt(dm_path,delimiter=','); gt=np.loadtxt(gt_path,delimiter=',')
    acts=dm@gt[5]; Z=np.zeros_like(X); idx=0
    for i in range(21):
        for j in range(21):
            if valid[i,j] and idx<len(acts): Z[i,j]=acts[idx]; idx+=1
    Z=gaussian_filter(Z,sigma=1.0)
    fig=plt.figure(figsize=(8,6),facecolor='#0a0a0a'); ax=fig.add_subplot(111,projection='3d')
    ax.set_facecolor('#0a0a0a'); ax.set_zlim(Z.min()-0.1,Z.max()+0.1); ax.set_xlim(-1,1); ax.set_ylim(-1,1)
    s=ax.plot_surface(X,Y,Z,cmap='viridis',edgecolor='none',alpha=0.92)
    cb=fig.colorbar(s,ax=ax,shrink=0.5,aspect=12,pad=0.12)
    cb.set_label('Stroke [normalised]',color='white',fontsize=8)
    plt.setp(cb.ax.yaxis.get_ticklabels(),color='white')
    style(ax,'Pupil X [normalised]','Pupil Y [normalised]','Stroke [normalised]','DM Actuator Surface (357 actuators)')
    plt.tight_layout()
    ani=FuncAnimation(fig,lambda f:[ax.view_init(elev=28,azim=f)],frames=np.arange(0,360,3),blit=False)
    ani.save(os.path.join(DOCS,'dm_actuator_surface.gif'),writer=PillowWriter(fps=6))
    plt.close(); print("Generated: dm_actuator_surface.gif")

Zp=X**2-Y**2+(3*(X**2+Y**2)-2)*X; Zp[~valid]=np.nan
fig=plt.figure(figsize=(8,6),facecolor='#0a0a0a'); ax=fig.add_subplot(111,projection='3d')
ax.set_facecolor('#0a0a0a'); ax.set_zlim(np.nanmin(Zp)-0.1,np.nanmax(Zp)+0.1); ax.set_xlim(-1,1); ax.set_ylim(-1,1)
s=ax.plot_surface(X,Y,Zp,cmap='plasma',edgecolor='none',alpha=0.92)
cb=fig.colorbar(s,ax=ax,shrink=0.5,aspect=12,pad=0.12)
cb.set_label('Phase [rad]',color='white',fontsize=8)
plt.setp(cb.ax.yaxis.get_ticklabels(),color='white')
style(ax,'Pupil X [normalised]','Pupil Y [normalised]','Phase [rad]','Zernike Phase Reconstruction')
plt.tight_layout()
ani=FuncAnimation(fig,lambda f:[ax.view_init(elev=28,azim=f)],frames=np.arange(0,360,3),blit=False)
ani.save(os.path.join(DOCS,'reconstruction_3d.gif'),writer=PillowWriter(fps=6))
plt.close(); print("Generated: reconstruction_3d.gif")
