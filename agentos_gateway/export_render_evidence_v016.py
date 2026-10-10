"""One-shot authenticated export of AgentOS jobs/Evidence from legacy Render Gateway.
Read-only. Never deploy or restart the legacy Gateway. Never commit raw exports to Git.
Run from an authorized node holding ADMIN_TOKEN or D2_READ_TOKEN.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone
import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", action="append", required=True)
    parser.add_argument("--output-dir", default="agentos-render-rescue")
    args = parser.parse_args()
    base = os.getenv("CLOUD_GATEWAY_URL", "https://dayong-agentos-gateway.onrender.com").rstrip("/")
    if not base.startswith("https://"):
        raise SystemExit("HTTPS required")
    token = os.getenv("ADMIN_TOKEN") or os.getenv("D2_READ_TOKEN")
    if not token:
        raise SystemExit("ADMIN_TOKEN or D2_READ_TOKEN is required; no credentials stored")
    dest = Path(args.output_dir)
    dest.mkdir(parents=True, exist_ok=True)
    manifest = {"exported_at": datetime.now(timezone.utc).isoformat(),
                "gateway": base, "records": []}
    with httpx.Client(timeout=45, headers={"Authorization": "Bearer " + token}) as client:
        for task_id in args.task_id:
            if not task_id or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for ch in task_id):
                raise SystemExit("Invalid task id")
            entry = {"task_id": task_id}
            for kind, endpoint in (("job", f"/v1/jobs/{task_id}"),
                                   ("evidence", f"/v1/jobs/{task_id}/evidence")):
                response = client.get(base + endpoint)
                entry[kind + "_http_status"] = response.status_code
                if response.status_code != 200:
                    entry[kind + "_error"] = response.text[:160]
                    continue
                raw = response.content
                filename = f"{task_id}-{kind}.json"
                target = dest / filename
                tmp = target.with_suffix(".json.tmp")
                tmp.write_bytes(raw)
                tmp.replace(target)
                entry[kind + "_file"] = filename
                entry[kind + "_response_sha256"] = hashlib.sha256(raw).hexdigest()
                entry[kind + "_response_bytes"] = len(raw)
                if kind == "evidence":
                    data = response.json()
                    payload = data.get("payload")
                    if isinstance(payload, dict):
                        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                                               separators=(",", ":")).encode("utf-8")
                        computed = hashlib.sha256(canonical).hexdigest()
                        entry["canonical_payload_sha256"] = computed
                        entry["canonical_payload_bytes"] = len(canonical)
                        entry["canonical_sha256_matches"] = computed == data.get("sha256")
            manifest["records"].append(entry)
    target = dest / "manifest.json"
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
