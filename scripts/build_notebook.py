"""build_notebook.py - Renders all theory notebooks to HTML in docs/."""
import subprocess, os, glob
NB  = os.path.join(os.path.dirname(__file__),'..','notebooks')
OUT = os.path.join(os.path.dirname(__file__),'..','docs')
os.makedirs(OUT, exist_ok=True)
for nb in sorted(glob.glob(os.path.join(NB,'*.ipynb'))):
    print(f"Executing {os.path.basename(nb)}...")
    subprocess.run(['jupyter','nbconvert','--to','html','--execute',nb,'--output-dir',OUT],check=False)
print("Done.")
