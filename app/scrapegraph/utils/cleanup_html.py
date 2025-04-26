import re
from bs4 import BeautifulSoup, Comment
def minify_html_regex(html_content: str) -> str:
    html_content = re.sub(r"<!--.*?-->", "", html_content, flags=re.DOTALL)
    html_content = re.sub(r">\\s+<", "><", html_content)
    html_content = re.sub(r"\\s+", " ", html_content)
    return html_content.strip()
def cleanup_html(html_content: str) -> str:
    soup = BeautifulSoup(html_content, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    cleaned_html = str(soup)
    minimized_html = minify_html_regex(cleaned_html)
    return minimized_html
def reduce_html(html_content: str, reduction_level: int = 0) -> str:
    minified = minify_html_regex(html_content)
    if reduction_level == 0:
        return minified
    soup = BeautifulSoup(minified, "lxml")
    if reduction_level >= 1:
        attrs_to_keep = ["href", "src"]
        for tag in soup.find_all(True):
            tag.attrs = {k: v for k, v in tag.attrs.items() if k in attrs_to_keep}
    return str(soup)
