from unittest import mock

from django.core.files.base import ContentFile
from django.test import SimpleTestCase

from core.storage import SupabaseStorage


class FakeResp:
    def __init__(self, status=200, json=None, content=b"", headers=None):
        self.status_code, self._json, self.content, self.text = status, json or {}, content, ""
        self.headers = headers or {}

    def json(self):
        return self._json


class SupabaseStorageTests(SimpleTestCase):
    def make(self, public=True):
        return SupabaseStorage(bucket="tanpa-media", public=public, url="https://abc.supabase.co", key="service-key")

    def test_save_uploads_with_service_key_and_unique_name(self):
        st = self.make()
        with mock.patch.object(st.session, "post", return_value=FakeResp(200)) as post:
            name = st.save("gallery/photo.JPG", ContentFile(b"img", name="photo.JPG"))
        self.assertRegex(name, r"^gallery/photo-[0-9a-f]{10}\.jpg$")
        url, kwargs = post.call_args[0][0], post.call_args[1]
        self.assertEqual(url, f"https://abc.supabase.co/storage/v1/object/tanpa-media/{name}")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer service-key")
        self.assertEqual(kwargs["headers"]["Content-Type"], "image/jpeg")

    def test_public_url(self):
        self.assertEqual(
            self.make().url("gallery/a b.jpg"),
            "https://abc.supabase.co/storage/v1/object/public/tanpa-media/gallery/a%20b.jpg",
        )

    def test_private_url_is_signed(self):
        st = self.make(public=False)
        with mock.patch.object(st.session, "post", return_value=FakeResp(200, {"signedURL": "/object/sign/tanpa-media/x.pdf?token=t"})):
            self.assertEqual(st.url("x.pdf"), "https://abc.supabase.co/storage/v1/object/sign/tanpa-media/x.pdf?token=t")

    def test_upload_failure_raises(self):
        st = self.make()
        with mock.patch.object(st.session, "post", return_value=FakeResp(400)):
            with self.assertRaises(Exception):
                st.save("a.jpg", ContentFile(b"x", name="a.jpg"))

    def test_open_and_delete(self):
        st = self.make()
        with mock.patch.object(st.session, "get", return_value=FakeResp(200, content=b"data")):
            self.assertEqual(st.open("a.jpg").read(), b"data")
        with mock.patch.object(st.session, "delete") as delete:
            st.delete("a.jpg")
        self.assertEqual(delete.call_args[1]["json"], {"prefixes": ["a.jpg"]})
