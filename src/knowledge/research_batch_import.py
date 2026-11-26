"""Download, classify and commit an individual research document."""

from hashlib import sha256
from math import ceil
from os import name as os_name
from pathlib import Path
from shutil import which
from subprocess import DEVNULL, PIPE, Popen, TimeoutExpired
from time import monotonic
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup
from filelock import FileLock, Timeout

from src.core.kb_importer import import_uploaded_document, parse_document_bytes
from src.core.network_policy import validate_url
from src.core.process_env import process_environment

from .config import knowledge_config
from .download import download_document
from .files import KnowledgeFiles
from .research_classification import classify, policy
from .research_metadata import category_id, record


def _native_pdf(url, check, deadline):
    executable = which("curl.exe" if os_name == "nt" else "curl")
    if not executable:
        raise ValueError("Install curl to retrieve this provider's original PDF")
    target, addresses = validate_url(url, resolve=True)
    if target.scheme != "https" or not addresses or not all(ip.is_global for ip in addresses):
        raise ValueError("The original PDF must use a public HTTPS address")
    check()
    remaining = deadline - monotonic()
    if remaining <= 0:
        raise TimeoutError("Document download deadline exceeded")
    address = str(addresses[0])
    if addresses[0].version == 6:
        address = f"[{address}]"
    size_limit = knowledge_config()["max_upload_bytes"]
    command = [
        executable,
        "--disable",
        "--silent",
        "--fail",
        "--globoff",
        "--noproxy",
        "*",
        "--proto",
        "=https",
        "--resolve",
        f"{target.hostname}:{target.port or 443}:{address}",
        "--max-time",
        str(ceil(remaining)),
        "--max-filesize",
        str(size_limit),
        "--write-out",
        "%{http_code}",
        "--url",
        url,
    ]
    with Popen(command, stdout=PIPE, stderr=DEVNULL, stdin=DEVNULL, env=process_environment("document")) as child:
        try:
            while True:
                check()
                remaining = deadline - monotonic()
                if remaining <= 0:
                    raise TimeoutError("Document download deadline exceeded")
                try:
                    output, _ = child.communicate(timeout=min(0.25, remaining))
                    break
                except TimeoutExpired:
                    continue
        finally:
            if child.poll() is None:
                child.kill()
    contents, status = output[:-3], output[-3:]
    if child.returncode or status != b"200" or len(contents) > size_limit:
        raise ValueError("Could not retrieve the original PDF")
    return contents


def _download(item, check):
    address = item.get("landing_url") or item["url"]
    if not address:
        raise ValueError("No full-text URL")
    if item["kind"] == "paper":
        parts = urlsplit(address)
        for rule in knowledge_config()["paper_download_rules"]:
            if parts.hostname in rule["hosts"] and parts.path.startswith(rule["from_path"]):
                address = urlunsplit(
                    ("https", parts.netloc, parts.path.replace(rule["from_path"], rule["to_path"], 1), "", "")
                )
                break
    deadline = monotonic() + policy()["limits"]["download_seconds"]
    filename, contents, final = download_document(address, check=check, deadline=deadline)
    if Path(filename).suffix.lower() in {".html", ".htm"}:
        soup = BeautifulSoup(contents, "html.parser")
        candidate = soup.find("meta", attrs={"name": "citation_pdf_url"})
        link = soup.find("link", attrs={"type": "application/pdf"})
        if not link and item.get("landing_url"):
            selector = policy()["full_text_selectors"].get(item["provider"])
            link = soup.select_one(selector) if selector else None
        url = candidate.get("content") if candidate else link.get("href") if link else None
        if not isinstance(url, str) or not url:
            raise ValueError("No downloadable full text")
        filename, contents, final = download_document(urljoin(final, url), check=check, deadline=deadline)
        if Path(filename).suffix.lower() in {".html", ".htm"}:
            raise ValueError("Full-text link returned a web page")
    if Path(filename).suffix.lower() == ".pdf" and not contents[:1024].lstrip().startswith(b"%PDF-"):
        if urlsplit(final).hostname in policy()["native_pdf_hosts"]:
            contents = _native_pdf(final, check, deadline)
        if not contents[:1024].lstrip().startswith(b"%PDF-"):
            raise ValueError("The source responded without a PDF document")
    return filename, contents


def ingest(repo, item, settings, check, stage):
    library = settings["library"]
    source = f"research:{item['kind']}:{item['key']}"
    directory = KnowledgeFiles(repo).directory(library)
    directory.mkdir(parents=True, exist_ok=True)
    lock = FileLock(str(directory / ".research-ingest.lock"))
    while True:
        check()
        try:
            lock.acquire(timeout=0.25)
            break
        except Timeout:
            continue
    try:
        scoped = "d.library_name=? AND d.attachment_session='' AND d.status='ready'"
        existing = repo.db.query_one(
            f"SELECT d.id FROM kb_documents d WHERE {scoped} AND d.source=?", (library, source)
        )
        if existing:
            return "duplicate", existing["id"], ""
        stage("downloading")
        filename, content = _download(item, check)
        digest = sha256(content).hexdigest()
        existing = repo.db.query_one(
            f"SELECT d.id FROM kb_documents d JOIN kb_research_metadata m ON d.id=m.doc_id "
            f"WHERE {scoped} AND m.content_hash=?",
            (library, digest),
        )
        if existing:
            return "duplicate", existing["id"], ""
        check()
        stage("parsing")
        parsed = parse_document_bytes(filename, content)
        check()
        stage("classifying")
        mode, reason = settings["mode"], ""
        try:
            topic, score, version = classify(
                "\n\n".join((item["title"], item["abstract"], parsed["content"])), mode, settings.get("model_id")
            )
        except InterruptedError:
            raise
        except Exception as exc:
            topic, score, version, reason = "", 0.0, "", type(exc).__name__
        check()
        stage("saving")
        with repo.db.transaction():
            row = import_uploaded_document(
                filename=filename,
                content_bytes=content,
                parsed_document=parsed,
                title=item["title"],
                library=library,
                chunk_chars=settings.get("chunk_chars"),
                source=source,
                category_id=category_id(repo, topic),
                repo=repo,
                doc_type="论文" if item["kind"] == "paper" else "研报",
            )
            record(
                repo,
                row["doc_id"],
                item,
                topic,
                digest,
                {
                    "mode": mode,
                    "model": version,
                    "score": score,
                    "taxonomy": policy()["version"],
                    "reason": reason,
                    "provider": item["provider"],
                    "published": item["published"],
                },
            )
        return ("imported" if topic else "review"), row["doc_id"], reason
    finally:
        lock.release()
