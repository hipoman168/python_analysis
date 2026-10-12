"""Worker sandbox: tests use only temporary directories and no network calls."""
import json
import os
from pathlib import Path

import pytest

from agentos_gateway.node_inbox_worker import (
    digest_text, safe_target, trusted_code_root, validate_code, write_code,
    evidence, save_evidence,
)


def job(text, path):
    return {"message_id":"PATCH-"+"a"*32,"node_id":"node-02","channel":"code",
            "content":text,"content_sha":digest_text(text),"target_file":path}


def test_verified_write(tmp_path):
    policy={"code_inbox_root":str(tmp_path)}
    original='print("你好")\n'
    result=write_code(job(original,"sample/program.py"),policy)
    written=Path(result["target_file"])
    assert written.read_text(encoding="utf-8")==original
    assert result["on_disk_sha256"]==digest_text(original)
    assert all(result["checks"].values())
    with pytest.raises(PermissionError,match="already exists"):
        write_code(job(original,"sample/program.py"),policy)


@pytest.mark.parametrize("target",[
    "../evil.py","sub/../evil.py","C:/evil.py","/etc/evil.py",
    "sub//evil.py","NUL.py","sub/.env","a/.git/pre.py",
    "run.ps1","trailing./t.py",
])
def test_refuse_bad_paths(tmp_path,target):
    with pytest.raises(PermissionError):
        safe_target(tmp_path,target)


def test_content_and_syntax_safety(tmp_path):
    for content in ["def bad(:\n pass", "x = 1\nsecret='abcdefghijklmno'"]:
        with pytest.raises((PermissionError,SyntaxError)):
            write_code(job(content,"reject.py"),{"code_inbox_root":str(tmp_path)})
    assert not (tmp_path/"reject.py").exists()
    with pytest.raises(ValueError):
        write_code({**job("pass\n","sha.py"),"content_sha":"0"*64},
                   {"code_inbox_root":str(tmp_path)})


def test_json_roundtrip_and_evidence(tmp_path):
    s='{"value": "台灣"}\n'
    result=write_code(job(s,"ok.json"),{"code_inbox_root":str(tmp_path)})
    assert json.loads(Path(result["target_file"]).read_text(encoding="utf-8"))["value"]=="台灣"
    ev=evidence({"message_id":"PATCH-"+"a"*32, "outcome":"PASS"})
    p=save_evidence(ev,tmp_path/"evidence")
    assert json.loads(p.read_text(encoding="utf-8"))["sha256"]==ev["sha256"]
    with pytest.raises(FileExistsError):
        save_evidence(ev,tmp_path/"evidence")


def test_symlink_escape(tmp_path):
    inside=tmp_path/"inside"
    outside=tmp_path/"outside"
    inside.mkdir();outside.mkdir()
    link=inside/"external"
    try:
        link.symlink_to(outside,target_is_directory=True)
    except (OSError,NotImplementedError):
        pytest.skip("symlinks unavailable to test user")
    with pytest.raises(PermissionError):
        safe_target(inside,"external/hack.py")
