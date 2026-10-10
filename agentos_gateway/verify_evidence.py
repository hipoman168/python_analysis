import json,hashlib,re,sys
def verify(e):
    p=e.get("payload")
    if not isinstance(p,dict): return False
    digest=hashlib.sha256(json.dumps(p,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
    return bool(re.fullmatch(r"[0-9a-f]{64}",str(e.get("sha256","")))) and digest==e["sha256"] and p.get("node_id")=="node-02" and p.get("skill_name")=="system_info"
if __name__=="__main__":
    with open(sys.argv[1],encoding="utf-8") as f: e=json.load(f)
    valid=verify(e)
    print("PASS" if valid else "FAIL")
    sys.exit(0 if valid else 1)
