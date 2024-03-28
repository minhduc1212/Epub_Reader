from bs4 import BeautifulSoup
from ebooklib import epub
import ebooklib
import base64


"""book = epub.read_epub("E:/T/TC/Quỷ Bí Chi Chủ (Tác Giả Mực Thích Lặn Nước).epub")
documents = book.get_items_of_type(ebooklib.ITEM_DOCUMENT)
for item in documents:
    print(item.get_content().decode("utf-8"))"""


book = epub.read_epub("E:/T/TC/Quỷ Bí Chi Chủ (Tác Giả Mực Thích Lặn Nước).epub")
all_content = ""
img_tags = []
image_tags = []

for item in book.get_items():
    if item.get_type() == ebooklib.ITEM_DOCUMENT:
        html_content = item.get_content().decode('utf-8')
        all_content += html_content
        
soup = BeautifulSoup(all_content, "html.parser")
img_tags.extend(soup.find_all("img"))
image_tags.extend(soup.find_all("image"))

for img_tag in img_tags:
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_IMAGE:
            if img_tag["src"] in item.get_name():
                img_data = base64.b64encode(item.get_content()).decode('utf-8')
                img_tag["src"] = f"data:image/jpeg;base64,{img_data}"
                break

for image_tag in image_tags:
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_IMAGE:
            if image_tag["xlink:href"] in item.get_name():
                img_data = base64.b64encode(item.get_content()).decode('utf-8')
                image_tag["xlink:href"] = f"data:image/jpeg;base64,{img_data}"
                break

content = str(soup)
with open("test.html", "w", encoding="utf-8") as f:
    f.write(content)