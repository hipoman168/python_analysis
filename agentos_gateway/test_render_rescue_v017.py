"""Offline regression tests for Render rescue exporter, no network or credentials."""
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import httpx

from agentos_gateway import export_render_evidence_v016 as rescue


class RescueTests(unittest.TestCase):
    def test_export_and_hash_verification(self):
        task = "E2E-761c9e6e"
        payload = {"task_id": task, "node_id": "node-02", "result": {"ok": True}}
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
        evidence = {"payload": payload, "sha256": hashlib.sha256(canonical).hexdigest(),
                    "size_bytes": len(canonical)}
        job = {"task_id": task, "node_id": "node-02", "status": "COMPLETED", "evidence": evidence}
        calls = []
        def handler(request):
            calls.append(str(request.url))
            if request.url.path.endswith("/evidence"):
                return httpx.Response(200, json=evidence)
            return httpx.Response(200, json=job)
        original_client = rescue.httpx.Client
        def client(*args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            return original_client(*args, **kwargs)
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"D2_READ_TOKEN": "offline-test", "ADMIN_TOKEN": "",
                                          "CLOUD_GATEWAY_URL": "https://example.invalid"}), \
                 patch.object(sys, "argv", ["rescue", "--task-id", task, "--output-dir", directory]), \
                 patch.object(rescue.httpx, "Client", side_effect=client):
                rescue.main()
            manifest = json.loads((Path(directory) / "manifest.json").read_text(encoding="utf-8"))
            record = manifest["records"][0]
            self.assertTrue(record["canonical_sha256_matches"])
            self.assertEqual(record["canonical_payload_sha256"], evidence["sha256"])
            self.assertEqual(record["job_http_status"], 200)
            self.assertEqual(record["evidence_http_status"], 200)
            self.assertEqual(len(calls), 2)
            self.assertEqual(json.loads((Path(directory) / (task + "-evidence.json")).read_bytes()), evidence)


if __name__ == "__main__":
    unittest.main()
