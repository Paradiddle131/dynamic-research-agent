from urllib.parse import urlparse
import html2text
def convert_to_md(html: str, base_url: str = None) -> str:
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.body_width = 0
    if base_url:
        try:
            parsed_url = urlparse(base_url)
            if parsed_url.scheme and parsed_url.netloc:
                 h.baseurl = f"{parsed_url.scheme}://{parsed_url.netloc}"
            else:
                 pass
        except ValueError:
             pass
    try:
        markdown = h.handle(html)
        return markdown
    except Exception as e:
        print(f"Error converting HTML to Markdown: {e}")
        return html
