import tkinter as tk
from tkinter import scrolledtext


def load_html_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        html_content = file.read()
    return html_content

def display_html_content(html_content):
    root = tk.Tk()
    root.title("HTML Viewer")

    text = scrolledtext.ScrolledText(root, width=100, height=30, wrap=tk.WORD)
    text.insert(tk.INSERT, html_content)
    text.pack(expand=True, fill=tk.BOTH)

    root.mainloop()

if __name__ == "__main__":
    file_path = "test.html"
    html_content = load_html_file(file_path)
    display_html_content(html_content)
