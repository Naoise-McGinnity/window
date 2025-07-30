import os

folder = r"C:\Users\pmcgi\OneDrive\Documents\GitHub\window\assets\wide angle"
folders = [f for f in os.listdir(folder)]
names = ["playeridle", "playeridle", "jumpidleleft", "jumpidleright", "jumpleft", "jumpright", "left", "right"]
for i, sub in enumerate(folders):
    subfolder = os.path.join(folder, sub)
    files = [f for f in os.listdir(subfolder) if f.lower().endswith(".png")]
    files.sort()
    for j, filename in enumerate(files):
        new_name = f"{names[i]}{j}.png"
        src = os.path.join(subfolder, filename)
        dst = os.path.join(subfolder, new_name)
        os.rename(src, dst)
        print(f"Renamed {filename} -> {new_name}")