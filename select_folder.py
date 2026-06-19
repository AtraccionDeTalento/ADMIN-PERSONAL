import tkinter as tk
from tkinter import filedialog
import os

def select():
    """Abre un diálogo nativo de Windows de forma independiente."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    folder = filedialog.askdirectory()
    root.destroy()
    if folder:
        print(os.path.normpath(folder))

if __name__ == "__main__":
    select()
