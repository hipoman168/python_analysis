"""Offline API contract tests. Never touch the live Render gateway."""
import hashlib
import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


class GatewayContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = patch.dict(os.environ, {
            "GATEWAY_DB": str(Path(self.tmp.name) / "test.db"),
            "NODE_TOKEN": "unit-node-token",
            "ADMIN_TOKEN": "unit-admin-token",
            "D2_READ_TOKEN": "unit-d2-read-token",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        sys.modules.pop("agentos_gateway.gateway", None)
        self.gateway = importlib.import_module("agentos_gateway.gateway")
        self.client = TestClient(self.gateway.app)

    def auth(self, token):
        return {"Authorization": "Bearer " + token}

    def test_health_and_auth(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.client.post("/v1/jobs", json={"task_id": "auth-test"}).status_code, 401)
        self.assertEqual(self.client.get("/v1/jobs/nope").status_code, 401)

    def test_roundtrip_and_scoped_read(self):
        task = "ci-contract-001"
        created = self.client.post("/v1/jobs", headers=self.auth("unit-admin-token"),
                                   json={"task_id": task, "node_id": "node-02", "skill": "system_info"})
        self.assertEqual(created.status_code, 200, created.text)
        claimed = self.client.post("/v1/nodes/node-02/claim", headers=self.auth("unit-node-token"))
        self.assertEqual(claimed.json()["task_id"], task)
        payload = {"task_id": task, "node_id": "node-02", "skill_name": "system_info"}
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
        evidence = {"payload": payload, "sha256": hashlib.sha256(canonical).hexdigest(),
                    "size_bytes": len(canonical)}
        result = self.client.post("/v1/nodes/node-02/result", headers=self.auth("unit-node-token"),
                                  json={"task_id": task, "status": "PASS", "evidence": evidence})
        self.assertEqual(result.status_code, 200, result.text)
        read = self.client.get(f"/v1/jobs/{task}/evidence", headers=self.auth("unit-d2-read-token"))
        self.assertEqual(read.status_code, 200, read.text)
        self.assertEqual(read.json(), evidence)
        self.assertEqual(self.client.get(f"/v1/jobs/{task}/evidence").status_code, 401)

    def test_reject_bad_hash_and_disallowed_skill(self):
        rejected = self.client.post("/v1/jobs", headers=self.auth("unit-admin-token"),
                                    json={"task_id": "unsafe", "skill": "shell"})
        self.assertEqual(rejected.status_code, 403)
        self.client.post("/v1/jobs", headers=self.auth("unit-admin-token"),
                         json={"task_id": "bad-hash", "node_id": "node-01"})
        self.client.post("/v1/nodes/node-01/claim", headers=self.auth("unit-node-token"))
        rejected = self.client.post("/v1/nodes/node-01/result", headers=self.auth("unit-node-token"),
                                    json={"task_id": "bad-hash", "status": "PASS",
                                          "evidence": {"payload": {"task_id": "bad-hash", "node_id": "node-01"}, "sha256": "0" * 64}})
        self.assertEqual(rejected.status_code, 400)


if __name__ == "__main__":
    unittest.main()
