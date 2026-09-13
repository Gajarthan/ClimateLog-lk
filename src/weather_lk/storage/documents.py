"""Content-addressed original bytes and source discovery metadata."""

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path


class DocumentStore:
    def __init__(self, database, data_dir):
        self.database = database
        self.data_dir = Path(data_dir)

    def archive(self, content, kind="pdf", source_url=None):
        if kind not in ("pdf", "legacy_json"):
            raise ValueError("Unsupported source document kind")
        digest = hashlib.sha256(content).hexdigest()
        suffix = ".pdf" if kind == "pdf" else ".json"
        relative = f"raw/{digest[:2]}/{digest}{suffix}"
        target = self.data_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                raise RuntimeError("Archived source bytes failed integrity validation")
        else:
            fd, temporary = tempfile.mkstemp(dir=target.parent, suffix=".part")
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, target)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        with self.database.transaction() as connection:
            existing = connection.execute(
                "SELECT sources FROM documents WHERE hash=?", (digest,)
            ).fetchone()
            sources = json.loads(existing["sources"]) if existing else []
            if source_url and source_url not in sources:
                sources.append(source_url)
            connection.execute(
                "INSERT INTO documents(hash,kind,raw_path,sources,fetched_at) VALUES(?,?,?,?,?) ON CONFLICT(hash) DO UPDATE SET sources=excluded.sources",
                (digest, kind, relative, json.dumps(sources), time.time()),
            )
        return self.get(digest)

    def get(self, digest):
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM documents WHERE hash=?", (digest,)
            ).fetchone()
        if row is None:
            raise KeyError(digest)
        result = dict(row)
        result["sources"] = json.loads(result["sources"])
        return result

    def pending(self, parser_version, failed_only=False):
        query = "SELECT d.* FROM documents d WHERE kind='pdf' AND NOT EXISTS (SELECT 1 FROM parse_attempts a WHERE a.document_hash=d.hash AND a.parser_version=? AND a.status IN ('succeeded','needs_review') AND EXISTS (SELECT 1 FROM observations o WHERE o.attempt_id=a.id))"
        if failed_only:
            query += " AND EXISTS (SELECT 1 FROM parse_attempts a WHERE a.document_hash=d.hash AND a.status IN ('retryable_failure','needs_review'))"
        with self.database.connect() as connection:
            return [
                dict(row)
                for row in connection.execute(
                    query + " ORDER BY fetched_at,hash", (parser_version,)
                )
            ]

    def path(self, document):
        target = (self.data_dir / document["raw_path"]).resolve()
        if not target.is_relative_to(self.data_dir.resolve()):
            raise ValueError("Raw document path is outside the data directory")
        return target
