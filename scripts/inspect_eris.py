import aotpy
system = aotpy.AOSystem.read_from_file("data/ERIS_NGS.fits")

print(f"System: {system.name}")
print(f"Number of WFS: {len(system.wavefront_sensors)}")
for i, wfs in enumerate(system.wavefront_sensors):
    print(f"WFS {i}:")
    print(f"  Measurements shape: {wfs.measurements.data.shape if wfs.measurements else 'None'}")
    print(f"  Detector frame shape: {wfs.detector.frame.data.shape if wfs.detector and wfs.detector.frame else 'None'}")

print(f"Number of Mirrors: {len(system.mirrors)}")
for i, m in enumerate(system.mirrors):
    print(f"Mirror {i}:")
    print(f"  Commands shape: {m.commands.data.shape if m.commands else 'None'}")

if hasattr(system, 'aberrations') and system.aberrations:
    print(f"Aberrations: {len(system.aberrations)}")
else:
    print("No aberrations found.")
