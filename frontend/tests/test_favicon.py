from pathlib import Path
from xml.etree import ElementTree


FRONTEND_ROOT = Path(__file__).resolve().parents[1]
FAVICON_PATH = FRONTEND_ROOT / "public" / "favicon.svg"
INDEX_PATH = FRONTEND_ROOT / "index.html"


def test_index_declares_svg_favicon() -> None:
    index = INDEX_PATH.read_text(encoding="utf-8")

    assert '<link rel="icon" type="image/svg+xml" href="/favicon.svg" />' in index


def test_favicon_is_safe_standalone_svg() -> None:
    assert FAVICON_PATH.is_file()

    root = ElementTree.parse(FAVICON_PATH).getroot()
    local_name = root.tag.rsplit("}", 1)[-1]
    forbidden = {"script", "image", "foreignObject", "use"}
    element_names = {element.tag.rsplit("}", 1)[-1] for element in root.iter()}
    linked_attributes = {
        attribute.rsplit("}", 1)[-1]
        for element in root.iter()
        for attribute in element.attrib
        if attribute.rsplit("}", 1)[-1] == "href"
    }
    source = FAVICON_PATH.read_text(encoding="utf-8")

    assert local_name == "svg"
    assert root.attrib["viewBox"] == "0 0 64 64"
    assert forbidden.isdisjoint(element_names)
    assert not linked_attributes
    assert "#07111f" in source
    assert "#22d3b6" in source
