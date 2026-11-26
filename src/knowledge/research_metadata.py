"""Publication facets and stable two-level research categories."""

import json
import unicodedata

from src.core.repository import Repository
from src.core.timeutil import utc_now_iso

from .config import library_name
from .research_catalog import publication_year
from .research_classification import policy, topics


def category_id(repo, topic):
    labels: tuple[str, ...]
    if topic:
        group, leaf = topics()[topic]
        labels = (group[0], leaf[0])
    else:
        labels = ("待审核",)
    parent = 0
    for label in labels:
        row = repo.db.query_one(
            "SELECT id FROM kb_categories WHERE name=? AND parent_id=? ORDER BY id LIMIT 1", (label, parent)
        )
        now = utc_now_iso()
        parent = (
            row
            or repo.insert("kb_categories", {"name": label, "parent_id": parent, "created_at": now, "updated_at": now})
        )["id"]
    return parent


def record(repo, doc_id, item, topic, digest, classification):
    year = publication_year(item["published"])
    repo.db.execute(
        """INSERT INTO kb_research_metadata(doc_id,published_year,topic,metadata,content_hash)
                       VALUES(?,?,?,?,?)""",
        (doc_id, year, topic, json.dumps(classification, ensure_ascii=False), digest),
    )
    institutions = item.get("institutions") or []
    if isinstance(institutions, str):
        institutions = [institutions]
    for value in institutions[: policy()["limits"]["institutions_per_document"]]:
        name = " ".join(unicodedata.normalize("NFKC", str(value)).split())[:250]
        if name:
            repo.db.execute(
                "INSERT OR IGNORE INTO kb_research_institutions VALUES(?,?,?)", (doc_id, name.casefold(), name)
            )


def documents(library, year=None, institution=None, topic=None, doc_type=None, page=1):
    clauses = ["d.library_name=?", "d.attachment_session=''", "d.status='ready'"]
    params: list[str | int] = [library_name(library)]
    if year == "unknown":
        clauses.append("m.published_year IS NULL")
    elif year:
        clauses.append("m.published_year=?")
        params.append(int(year))
    if institution == "unknown":
        clauses.append("NOT EXISTS (SELECT 1 FROM kb_research_institutions i WHERE i.doc_id=d.id)")
    elif institution:
        clauses.append("EXISTS (SELECT 1 FROM kb_research_institutions i WHERE i.doc_id=d.id AND i.normalized=?)")
        params.append(str(institution))
    if topic == "review":
        clauses.append("m.topic=''")
    elif isinstance(topic, str) and topic.startswith("group:"):
        group = policy()["categories"].get(topic.removeprefix("group:"))
        keys = list(group["topics"]) if group else []
        if not keys:
            raise ValueError("Unknown research group")
        clauses.append(f"m.topic IN ({','.join('?' for _ in keys)})")
        params.extend(keys)
    elif topic:
        clauses.append("m.topic=?")
        params.append(str(topic))
    if doc_type:
        clauses.append("d.doc_type=?")
        params.append(doc_type)
    size = policy()["limits"]["page_size"]
    return Repository().db.query(
        f"""SELECT d.id AS doc_id,d.title,d.doc_type,d.library_name,m.published_year,
            COALESCE((SELECT group_concat(i.name, ' / ') FROM kb_research_institutions i
                      WHERE i.doc_id=d.id), '') AS institutions,
            p.name AS category,c.name AS topic,d.source,d.updated_at
            FROM kb_documents d LEFT JOIN kb_research_metadata m ON m.doc_id=d.id
            LEFT JOIN kb_categories c ON c.id=d.category_id LEFT JOIN kb_categories p ON p.id=c.parent_id
            WHERE {" AND ".join(clauses)} ORDER BY d.id DESC LIMIT ? OFFSET ?""",
        (*params, size, (max(1, int(page or 1)) - 1) * size),
    )


def facets(library):
    repo = Repository()
    name = library_name(library)
    scope = "d.library_name=? AND d.attachment_session='' AND d.status='ready'"
    years = repo.db.query(
        f"SELECT DISTINCT m.published_year AS year FROM kb_documents d JOIN kb_research_metadata m ON m.doc_id=d.id "
        f"WHERE {scope} AND m.published_year IS NOT NULL ORDER BY year DESC",
        (name,),
    )
    institutions = repo.db.query(
        f"SELECT i.normalized,MIN(i.name) AS name FROM kb_documents d JOIN kb_research_institutions i ON i.doc_id=d.id "
        f"WHERE {scope} GROUP BY i.normalized ORDER BY name",
        (name,),
    )
    categories = repo.db.query(
        f"SELECT DISTINCT c.id,c.name,p.name AS parent,p.id AS parent_id FROM kb_documents d "
        f"JOIN kb_categories c ON c.id=d.category_id LEFT JOIN kb_categories p ON p.id=c.parent_id "
        f"WHERE {scope} ORDER BY p.name,c.name",
        (name,),
    )
    return years, institutions, categories


def reclassify(library, doc_id, topic):
    if topic and topic not in topics():
        raise ValueError("Unknown research category")
    repo = Repository()
    row = repo.get("kb_documents", int(doc_id))
    if row["library_name"] != library_name(library) or row["attachment_session"]:
        raise ValueError("Document is outside the selected library")
    with repo.db.transaction():
        changed = repo.db.execute("UPDATE kb_research_metadata SET topic=?,manual=1 WHERE doc_id=?", (topic, doc_id))
        if not changed.rowcount:
            raise ValueError("This document has no research classification")
        repo.update("kb_documents", int(doc_id), {"category_id": category_id(repo, topic), "updated_at": utc_now_iso()})
