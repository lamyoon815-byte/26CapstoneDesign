"""Run: python -B -m unittest scripts.test_personal_color -v"""
import sys
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from sqlmodel import create_engine
import backend.main as main
from backend.services.personal_color import MAX_IMAGE_BYTES, image_format

REAL_CLIENT = httpx.Client
PAYLOAD = {"season": "autumn", "season_ko": "가을웜", "season_full": "autumn-warm", "confidence": "low"}


class PersonalColorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.engine = create_engine(
            "sqlite:///" + (Path(self.tmp.name) / "test.db").as_posix(),
            connect_args={"check_same_thread": False},
        )
        self.originals = []
        for name, module in list(sys.modules.items()):
            if name.startswith("backend.") and hasattr(module, "engine"):
                self.originals.append((module, module.engine))
                module.engine = self.engine
        self.client = TestClient(main.app)
        self.client.__enter__()
        for email in ("a@example.com", "b@example.com"):
            response = self.client.post("/api/auth/signup", json={
                "email": email, "password": "Test-pass-123", "name": "Test",
            })
            self.assertEqual(response.status_code, 201)

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.engine.dispose()
        for module, engine in self.originals:
            module.engine = engine
        self.tmp.cleanup()

    def login(self, email="a@example.com"):
        self.assertEqual(self.client.post("/api/auth/login", json={
            "email": email, "password": "Test-pass-123",
        }).status_code, 200)

    def upload(self, handler, data=b"\x89PNG\r\n\x1a\nmock", **kwargs):
        def factory(**options):
            self.assertEqual(options["timeout"].read, 120)
            return REAL_CLIENT(transport=httpx.MockTransport(handler), **options)
        with patch("backend.services.personal_color.httpx.Client", side_effect=factory):
            return self.client.post("/api/me/personal-color", files={
                "file": ("private-name.png", data, "image/png"),
            }, **kwargs)

    def test_diagnosis_flow_and_failures(self):
        url = "/api/me/personal-color"
        self.assertEqual(self.client.get(url).status_code, 401)
        self.assertEqual(self.upload(lambda r: self.fail("must not call AI")).status_code, 401)
        self.login()
        self.assertEqual(self.client.get(url).json(), {"result": None})
        self.assertEqual(self.client.post(url).status_code, 422)

        def success(request):
            self.assertEqual(str(request.url), "https://personal-color-api-nqrx.onrender.com/predict")
            self.assertEqual(request.method, "POST")
            body = request.read()
            self.assertIn(b'name="file"', body)
            self.assertNotIn(b"private-name", body)
            self.assertNotIn("cookie", request.headers)
            return httpx.Response(200, json=PAYLOAD)

        response = self.upload(success)
        self.assertEqual(response.status_code, 200, response.text)
        saved = response.json()
        self.assertEqual(saved["tone"], "autumn_warm")
        self.assertEqual(saved["confidence_level"], "low")
        self.assertIsNone(saved["confidence"])
        self.assertIsNotNone(datetime.fromisoformat(saved["diagnosed_at"]).tzinfo)
        self.assertEqual(self.client.get(url).json()["result"], saved)
        self.assertEqual(response.headers["cache-control"], "no-store")

        for data, status in [(b"", 400), (b"not image", 415), (b"x" * (MAX_IMAGE_BYTES + 1), 413)]:
            r = self.upload(lambda req: self.fail("invalid upload reached AI"), data=data)
            self.assertEqual(r.status_code, status)
            self.assertEqual(set(r.json()), {"code", "message"})
        for status, expected in [(422, 422), (500, 502), (429, 503), (302, 502)]:
            self.assertEqual(self.upload(lambda r: httpx.Response(status)).status_code, expected)
        for payload in [[], {}, {**PAYLOAD, "confidence": 0.8}, {**PAYLOAD, "season_full": "winter-cool"}]:
            self.assertEqual(self.upload(lambda r: httpx.Response(200, json=payload)).status_code, 502)
        self.assertEqual(self.upload(lambda r: httpx.Response(200, text="not JSON")).status_code, 502)
        for error, expected in [(httpx.ReadTimeout, 504), (httpx.ConnectError, 502)]:
            def failing(request):
                raise error("test", request=request)
            self.assertEqual(self.upload(failing).status_code, expected)
        self.assertEqual(self.client.get(url).json()["result"], saved)
        self.assertEqual(self.upload(success, headers={"origin": "https://other.example"}).status_code, 403)

        self.login("b@example.com")
        self.assertEqual(self.client.get(url).json(), {"result": None})
        self.login()
        # Restart app lifecycle using the same temporary SQLite file.
        self.client.__exit__(None, None, None)
        self.client = TestClient(main.app)
        self.client.__enter__()
        self.login()
        self.assertEqual(self.client.get(url).json()["result"], saved)
        new = {"season": "winter", "season_ko": "겨울쿨", "season_full": "winter-cool", "confidence": "high"}
        r = self.upload(lambda req: httpx.Response(200, json=new))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.client.get(url).json()["result"]["tone"], "winter_cool")
        for path in ["/api/me/profile", "/api/me/recommendations", "/api/me/cart/warnings", "/api/products"]:
            self.assertEqual(self.client.get(path).status_code, 200, path)
        self.assertIn(url, self.client.get("/openapi.json").json()["paths"])

    def test_supported_signatures(self):
        for data, ext in [(b"\xff\xd8\xffmock", "jpg"), (b"\x89PNG\r\n\x1a\nmock", "png"), (b"RIFF1234WEBPmock", "webp"), (b"BMmock", "bmp")]:
            self.assertEqual(image_format(data)[0], ext)


if __name__ == "__main__":
    unittest.main()
