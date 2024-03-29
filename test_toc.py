from bs4 import BeautifulSoup
from ebooklib import epub
import ebooklib
import base64
from bs4 import BeautifulSoup


book = epub.read_epub("Hứa Tiên Chí.epub")
all_content = ""
image = book.get_items_of_type(ebooklib.ITEM_IMAGE)
content = book.get_items_of_type(ebooklib.ITEM_DOCUMENT)
for item in content:
    html_content = item.get_content().decode('utf-8')
    soup = BeautifulSoup(html_content, "html.parser")
    img_tags = soup.find_all("img")
    image_tags = soup.find_all("image")

    for img_tag in img_tags:
        for item in image:
            if item.get_type() == ebooklib.ITEM_IMAGE:
                if img_tag["src"] in item.get_name():
                    img_data = base64.b64encode(item.get_content()).decode('utf-8')
                    img_tag["src"] = f"data:image/lpg;base64,{img_data}"
                    break

    for image_tag in image_tags:
        for item in image:
            if item.get_type() == ebooklib.ITEM_IMAGE:
                if image_tag["xlink:href"] in item.get_name():
                    img_data = base64.b64encode(item.get_content()).decode('utf-8')
                    image_tag["xlink:href"] = f"data:image/jpg;base64,{img_data}"
                    break
    all_content += str(soup)
    with open("test.html", "a", encoding="utf-8") as file:
        file.write(all_content)
with open("test.html", "r", encoding="utf-8") as file:
    html_content = file.read()
    soup = BeautifulSoup(html_content, "html.parser")
    images = soup.find_all("image")
    with open("1.txt", "w", encoding="utf-8") as file:
        for image in images:
            file.write(image["xlink:href"] + "\n")
