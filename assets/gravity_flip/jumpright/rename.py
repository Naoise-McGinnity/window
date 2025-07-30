import os

folder = r"C:\Users\pmcgi\OneDrive\Documents\GitHub\window\assets\gravity_flip\jumpright"
files = [f for f in os.listdir(folder) if f.lower().endswith('.png')]
files.sort()
print(files)

for i, filename in enumerate(files):
    new_name = f"jumpright{i}.png"
    src = os.path.join(folder, filename)
    dst = os.path.join(folder, new_name)
    os.rename(src, dst)
    print(f"Renamed {filename} -> {new_name}")