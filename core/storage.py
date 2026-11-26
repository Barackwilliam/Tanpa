"""Django storage backend for Supabase Storage (REST API).

Files go to a Supabase bucket using the service-role key, which stays on the server.
- public bucket  -> permanent public URLs (gallery, news, leaders, member photos)
- private bucket -> short-lived signed URLs (payment slips)

Create both buckets in Supabase -> Storage (mark the media bucket as *Public*).
"""

import mimetypes
import posixpath
import uuid
from urllib.parse import quote

import requests
from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible


class SupabaseStorageError(Exception):
    pass


@deconstructible
class SupabaseStorage(Storage):
    def __init__(self, bucket=None, public=True, url=None, key=None, signed_url_ttl=3600):
        self.bucket = bucket or settings.SUPABASE_PUBLIC_BUCKET
        self.public = public
        self.base = (url or settings.SUPABASE_URL).rstrip("/") + "/storage/v1"
        self.key = key or settings.SUPABASE_SERVICE_ROLE_KEY
        self.signed_url_ttl = signed_url_ttl
        self.session = requests.Session()

    # -- helpers ---------------------------------------------------------------
    def _headers(self, **extra):
        return {"Authorization": f"Bearer {self.key}", "apikey": self.key, **extra}

    @staticmethod
    def _clean(name):
        return posixpath.normpath(str(name).replace("\\", "/")).lstrip("/")

    def _object_url(self, name):
        return f"{self.base}/object/{self.bucket}/{quote(self._clean(name))}"

    # -- Storage API -------------------------------------------------------------
    def _save(self, name, content):
        name = self._clean(name)
        content.seek(0) if hasattr(content, "seek") else None
        data = content.read()
        ctype = getattr(content, "content_type", None) or mimetypes.guess_type(name)[0] or "application/octet-stream"
        resp = self.session.post(
            self._object_url(name),
            data=data,
            headers=self._headers(**{"Content-Type": ctype, "x-upsert": "true", "cache-control": "max-age=31536000"}),
            timeout=60,
        )
        if resp.status_code not in (200, 201):
            raise SupabaseStorageError(f"Upload of {name} failed ({resp.status_code}): {resp.text[:300]}")
        return name

    def _open(self, name, mode="rb"):
        resp = self.session.get(self._object_url(name), headers=self._headers(), timeout=60)
        if resp.status_code != 200:
            raise FileNotFoundError(f"{name} not found in bucket {self.bucket} ({resp.status_code})")
        f = ContentFile(resp.content, name=name)
        return f

    def delete(self, name):
        if not name:
            return
        self.session.delete(
            f"{self.base}/object/{self.bucket}",
            json={"prefixes": [self._clean(name)]},
            headers=self._headers(),
            timeout=30,
        )

    def exists(self, name):
        # Names are made unique in get_available_name, so overwrites can't happen.
        return False

    def get_available_name(self, name, max_length=None):
        name = self._clean(name)
        directory, filename = posixpath.split(name)
        stem, ext = posixpath.splitext(filename)
        stem = stem[: 60]
        unique = f"{stem}-{uuid.uuid4().hex[:10]}{ext.lower()}"
        return posixpath.join(directory, unique) if directory else unique

    def size(self, name):
        resp = self.session.head(self._object_url(name), headers=self._headers(), timeout=30)
        return int(resp.headers.get("content-length", 0))

    def url(self, name):
        name = self._clean(name)
        if self.public:
            return f"{self.base}/object/public/{self.bucket}/{quote(name)}"
        cache_key = f"sb-signed:{self.bucket}:{name}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        resp = self.session.post(
            f"{self.base}/object/sign/{self.bucket}/{quote(name)}",
            json={"expiresIn": self.signed_url_ttl},
            headers=self._headers(),
            timeout=30,
        )
        if resp.status_code != 200:
            return ""
        signed = resp.json().get("signedURL") or resp.json().get("signedUrl") or ""
        full = f"{self.base}{signed}" if signed.startswith("/") else signed
        cache.set(cache_key, full, max(self.signed_url_ttl - 120, 60))
        return full


def private_storage():
    from django.core.files.storage import storages

    return storages["private"]
