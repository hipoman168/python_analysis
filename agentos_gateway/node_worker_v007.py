"""DAYONG Node-02 outbound claim worker v0.0.7. One-shot, no polling."""
import os, json, hashlib, socket, platform, datetime, httpx

def main():
    gateway=os.environ["CLOUD_GATEWAY_URL"].rstrip("/")
    token=os.environ["NODE_TOKEN"]
    node=os.getenv("NODE_ID","node-02")
    if not gateway.startswith("https://"): raise RuntimeError("HTTPS required")
    with httpx.Client(timeout=30,headers={"Authorization":"Bearer "+token}) as client:
        response=client.post(f"{gateway}/v1/nodes/{node}/claim")
        response.raise_for_status()
        job=response.json()
        task_id=job.get("task_id")
        if not task_id:
            print("NO_PENDING_JOB")
            return
        if job.get("skill")!="system_info":
            raise RuntimeError("Disallowed skill: "+str(job.get("skill")))
        payload={"node_id":node,"task_id":task_id,"skill_name":"system_info","agent_id":"D2-AKAI","result":{"hostname":socket.gethostname(),"system":platform.system(),"release":platform.release(),"python_version":platform.python_version(),"cpu_count":os.cpu_count()},"logs":["system_info completed"],"generated_at":datetime.datetime.now(datetime.timezone.utc).isoformat()}
        canonical=json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()
        sha256=hashlib.sha256(canonical).hexdigest()
        evidence={"payload":payload,"sha256":sha256,"size_bytes":len(canonical)}
        result=client.post(f"{gateway}/v1/nodes/{node}/result",json={"task_id":task_id,"status":"PASS","evidence":evidence})
        result.raise_for_status()
        print(json.dumps({"task_id":task_id,"sha256":sha256,"gateway_result":result.json()},ensure_ascii=False))

if __name__=="__main__":
    main()
