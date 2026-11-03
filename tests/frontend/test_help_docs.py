import os
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import pytest
import yaml
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
from mkdocs.config import load_config

from src.core.config import Settings
from src.help_docs import ensure_help_docs_site, help_docs_iframe_html
from src.help_docs.builder import _needs_rebuild
from src.help_docs.links import handbook_markdown
from src.help_docs.mount import mount_help_docs


def test_help_docs_builds_mkdocs_site(tmp_path):
    settings = Settings(help_docs_site_dir=tmp_path / "help_site", help_docs_auto_build=True)

    status = ensure_help_docs_site(settings)

    assert status.mounted is True
    assert status.built is True
    assert status.fallback is False
    assert status.index_path.exists()
    content = status.index_path.read_text(encoding="utf-8")
    assert "AIQuant智投帮助中心" in content
    assert "使用文档" in content and "原理文档" in content
    assert not (status.site_dir / "audit").exists()

    app = FastAPI()
    mount_help_docs(app, settings)
    with TestClient(app) as client:
        for route in ("/usage/backtest/", "/principles/backtest_metrics/", "/quick_start/", "/help/ai_workspace/"):
            response = client.get(settings.help_docs_mount_path + route)
            assert response.status_code == 200
        image = client.get(settings.help_docs_mount_path + "/usage/assets/screenshots/07-backtest-charts.jpg")
        assert image.status_code == 200 and image.headers["content-type"].startswith("image/jpeg")
        for asset in (
            "css/base.css",
            "js/base.js",
            "webfonts/fa-solid-900.woff2",
            "usage/assets/handbook.css",
            "usage/assets/handbook-search.js",
        ):
            assert client.get(settings.help_docs_mount_path + "/" + asset).status_code == 200
        assert any(
            row["location"].startswith("usage/ai_workspace/")
            for row in client.get(settings.help_docs_mount_path + "/search/search_index.json").json()["docs"]
        )


def test_help_docs_iframe_uses_configured_mount_path():
    html = help_docs_iframe_html("/custom-help")

    assert "src='/custom-help/'" in html
    assert "loading='lazy'" in html
    assert "新窗口打开" in html


def test_handbook_images_trigger_rebuild_but_archived_evidence_does_not(tmp_path):
    source = tmp_path / "docs"
    source.mkdir()
    config = tmp_path / "mkdocs.yml"
    config.write_text("extra:\n  help_source_roots: [usage, principles]\n", encoding="utf-8")
    index = tmp_path / "index.html"
    index.write_text("built", encoding="utf-8")
    image = source / "usage" / "assets" / "screen.jpg"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"image")
    archive = source / "audit" / "report.md"
    archive.parent.mkdir()
    archive.write_text("history", encoding="utf-8")
    for path in (config, image):
        os.utime(path, (100, 100))
    os.utime(index, (200, 200))
    os.utime(archive, (300, 300))
    assert not _needs_rebuild(source, config, index)
    os.utime(image, (300, 300))
    assert _needs_rebuild(source, config, index)


def test_learning_reader_resolves_images_and_crosslinks_without_rewriting_external_links(tmp_path):
    settings = Settings(project_root=tmp_path, help_docs_mount_path="/custom-help")
    source = tmp_path / "docs" / "usage" / "guide.md"
    content = "![screen](assets/screen.jpg) [principle](../principles/README.md) [web](https://example.com/a)"
    rendered = handbook_markdown(content, source, settings)
    assert "![screen](/custom-help/usage/assets/screen.jpg)" in rendered
    assert "[principle](/custom-help/principles/)" in rendered
    assert "[web](https://example.com/a)" in rendered
    outside = "[source](../../../outside.md) [root](../..)"
    assert handbook_markdown(outside, source, settings) == outside


def test_learning_catalog_prioritizes_two_document_categories():
    from src.frontend.service.foundation import _learning_entries
    from src.frontend.service.strategy import StrategyServiceMixin

    entries = _learning_entries()
    usage = [entry for entry in entries if entry["path"].startswith("docs/usage/")]
    principles = [entry for entry in entries if entry["path"].startswith("docs/principles/")]
    assert usage and principles
    assert all(entry["category_key"] == "usage" for entry in usage)
    assert all(entry["category_key"] == "principles" for entry in principles)
    assert all(not Path(entry["path"]).name.startswith("task") for entry in entries)
    assert [group["category_key"] for group in StrategyServiceMixin().learning_tree()[:2]] == ["usage", "principles"]
    path = Path("mkdocs.platform.yml") if Path("mkdocs.platform.yml").is_file() else Path("mkdocs.yml")
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert config["docs_dir"] == "docs"


class _PageResources(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls: list[str] = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        key = "href" if tag in {"a", "link"} else "src" if tag in {"img", "script"} else ""
        if key and attributes.get(key):
            self.urls.append(attributes[key])


def test_publication_template_resolves_source_relative_to_its_config(tmp_path):
    configuration = load_config(config_file="egs/mkdocs.publish.example.yaml", site_dir=str(tmp_path / "public"))
    assert Path(configuration.docs_dir).resolve() == (Path.cwd() / "docs").resolve()
    assert configuration.site_url == "https://example.com/aiquant/"
    assert configuration.nav is not None
    assert configuration.nav[1].get("使用文档")


@pytest.mark.parametrize("prefix", ["/", "/aiquant/", "/project/docs/"])
def test_static_handbook_publishes_under_root_and_nested_prefixes(tmp_path, prefix):
    settings = Settings(help_docs_site_dir=tmp_path / "published", help_docs_auto_build=True)
    status = ensure_help_docs_site(settings)
    assert status.built and not status.fallback
    app = FastAPI()
    app.mount(prefix.rstrip("/"), StaticFiles(directory=status.site_dir, html=True))
    targets = set()
    with TestClient(app) as client:
        for route in ("", "usage/documentation_publish/", "usage/backtest/", "principles/", "quick_start/"):
            response = client.get(prefix + route)
            assert response.status_code == 200
            resources = _PageResources()
            resources.feed(response.text)
            for value in resources.urls:
                url = urlsplit(urljoin(str(response.url), value))
                if url.netloc != "testserver":
                    continue
                assert url.path.startswith(prefix)
                targets.add(url.path + ("?" + url.query if url.query else ""))
        for target in targets:
            assert client.get(target).status_code == 200, target
        index = client.get(prefix + "search/search_index.json").json()
        assert any(row["location"].startswith("usage/documentation_publish/") for row in index["docs"])
        script = prefix + "usage/assets/handbook-search.js?v=20261022"
        assert urljoin("http://testserver" + script, "../../search/search_index.json") == (
            "http://testserver" + prefix + "search/search_index.json"
        )
