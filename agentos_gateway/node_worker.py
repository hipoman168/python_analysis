"""Run on Node-02; outbound HTTPS only, no inbound listener."""
import os, json, hashlib, socket, platform, datetime, httpx
GATEWAY=os.environ['CLOUD_GATEWAY_URL'].rstrip('/')
TOKEN=os.environ['NODE_TOKEN']
NODE=os.getenv('NODE_ID','node-02')

def once():
    headers={'Authorization':'Bearer '+TOKEN}
    with httpx.Client(timeout=20,headers=headers) as client:
        response=client.post(f'{GATEWAY}/v1/nodes/{NODE}/claim')
        response.raise_for_status()
        job=response.json()
        if not job.get('task_id'): return False
        if job['skill']!='system_info': raise RuntimeError('Disallowed skill')
        payload={'node_id':NODE,'task_id':job['task_id'],'skill_name':'system_info','agent_id':'node-worker','result':{'hostname':socket.gethostname(),'system':platform.system(),'python_version':platform.python_version()},'logs':['system_info completed'],'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
        digest=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
        evidence={'payload':payload,'sha256':digest}
        response=client.post(f'{GATEWAY}/v1/nodes/{NODE}/result',json={'task_id':job['task_id'],'status':'PASS','evidence':evidence})
        response.raise_for_status()
        print(json.dumps(response.json()))
        return True

if __name__=='__main__':
    once()
