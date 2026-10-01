"""Opt-in real stdio tests using generic preparation, with technical fixture decisions."""
import argparse
import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mcp_sentry_gateway.core import approve, inspect, capture, digest, canon
from mcp_sentry_gateway.onboarding import prepare_codex
from mcp_sentry_gateway.operator import decide
from mcp_sentry_gateway.preparation import separated
from mcp_sentry_gateway.review import ensure_pending, submit_verdict


class Client:
    def __init__(self, manifest, store):
        self.store = store
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
        self.started = time.perf_counter()
        self.process = subprocess.Popen([sys.executable,"-m","mcp_sentry_gateway.gateway","--interface","execution",
            "--manifest",str(manifest),"--store",str(store)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,text=True,encoding="utf-8",env=environment)
        self.output = queue.Queue()
        self.thread = threading.Thread(target=self.read,daemon=True)
        self.thread.start()
        self.number = 0

    def read(self):
        for line in self.process.stdout: self.output.put(line)
        self.output.put(None)

    def request(self, method, params):
        self.number += 1
        self.process.stdin.write(json.dumps({"jsonrpc":"2.0","id":self.number,"method":method,"params":params})+'\n')
        self.process.stdin.flush()
        line = self.output.get(timeout=240)
        if line is None: raise RuntimeError("gateway ended before response")
        response = json.loads(line)
        assert response.get("id")==self.number,response
        return response

    def initialize(self):
        result = self.request("initialize",{"protocolVersion":"2025-06-18","capabilities":{},
            "clientInfo":{"name":"sentry-technical-smoke","version":"1"}})
        self.process.stdin.write('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
        self.process.stdin.flush()
        self.request("tools/list",{})
        return result, time.perf_counter()-self.started

    def close(self):
        self.process.stdin.close()
        try: self.process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.process.kill();self.process.wait()
        self.thread.join(timeout=1)
        self.process.stdout.close()


def run(scenario, plan_path, lab):
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    root = Path(plan["project_root"])
    lab.mkdir(parents=True,exist_ok=False)
    config = lab/"config";config.mkdir()
    data = lab/"data";data.mkdir()
    manifest,store = config/"manifest.json",lab/"state"
    command = list(plan["command"])
    names = []
    if scenario=="memory":
        os.environ["MEMORY_FILE_PATH"] = str(data/"memory.jsonl")
        names = ["MEMORY_FILE_PATH"]
        calls = [("create_entities",{"entities":[{"name":"SentryFixture","entityType":"technical-test","observations":["fictitious"]}]}),
                 ("read_graph",{})]
    elif scenario=="filesystem":
        (data/"input.txt").write_text("fictitious generic sentry",encoding="utf-8")
        command.append(str(data))
        calls = [("read_text_file",{"path":str(data/"input.txt")})]
    else:
        git = os.environ["GIT_PYTHON_GIT_EXECUTABLE"]
        subprocess.run([git,"init",str(data)],check=True,capture_output=True)
        (data/"input.txt").write_text("fictitious",encoding="utf-8")
        names = ["PATH","GIT_PYTHON_GIT_EXECUTABLE"]
        command += ["--repository",str(data)]
        calls = [("git_status",{"repo_path":str(data)})]
    separated(root,store,[data])
    prepare_codex(SimpleNamespace(name="generic",project_root=root,inspect_root=plan["inspect_roots"],
        manifest=manifest,store=store,fragment=config/"codex.toml",backend_command=command,passthrough_name=names))
    approve(manifest,store)
    baseline_hash = digest(canon(capture(manifest)))
    entry_index = 2 if command[1]=="-B" else 1
    entry = root/command[entry_index]
    original = entry.read_bytes()
    results = []

    def exchange(expected):
        client = Client(manifest,store)
        try:
            _,ready = client.initialize()
            request_started = time.perf_counter()
            response = client.request("tools/call",{"name":calls[0][0],"arguments":calls[0][1]})
            first_duration = time.perf_counter()-request_started
            total = time.perf_counter()-client.started
            lifecycle = json.loads((store/"relatorios-de-seguranca/backend-lifecycle-current.json").read_text())
            copied_path = None
            if expected:
                assert not response["result"].get("isError"),response
                assert lifecycle["spawn_attempts"]==1,lifecycle
                copies = list((store/"copias-verificadas").iterdir())
                assert len(copies)==1,copies
                copied_path = copies[0]/entry.relative_to(root)
                assert copied_path.read_bytes()==entry.read_bytes()
                for method,params in calls[1:]:
                    response = client.request("tools/call",{"name":method,"arguments":params})
                expected_text = {"memory":"SentryFixture","filesystem":"fictitious generic sentry","git":"input.txt"}[scenario]
                assert expected_text in json.dumps(response),response
            else:
                assert lifecycle["spawn_attempts"]==0,lifecycle
                assert response["result"]["structuredContent"]["status"]=="security_review_required",response
            results.append({"expected_success":expected,"ready_seconds":round(ready,3),
                "first_call_seconds":round(first_duration,3),"start_to_first_result_seconds":round(total,3),
                "verified_entry":str(copied_path),"lifecycle":lifecycle,"response":response})
        finally:client.close()

    try:
        exchange(True)
        # Persistence is mutable external data; it must not change integrity.
        assert inspect(manifest,store)["status"]=="unchanged"
        entry.write_bytes(original+(b"\n# technical fixture update\n" if entry.suffix==".py" else b"\n// technical fixture update\n"))
        exchange(False)
        record,_=ensure_pending(manifest,store)
        submit_verdict(manifest,store,{"review_id":record["review_id"],"reviewed_hash":record["dossier"]["current_hash"],
            "dossier_hash":record["dossier"]["dossier_hash"],"policy_version":record["policy_version"],
            "decision":"allow","justification":"Technical fixture: appended comment; not an AI assessment","risks":[]})
        decide(manifest,store,"accept",input_fn=lambda:"ACEITAR",output=lambda _:None)
        exchange(True)
    finally:entry.write_bytes(original)
    report={"scenario":scenario,"package":plan.get("package"),"version":plan.get("version"),
        "preparation":"generic prepare_codex; no server profile", "sentry_sources_hash":digest(b''.join(
            p.name.encode()+b'\0'+p.read_bytes() for p in sorted((Path(__file__).resolve().parents[1]/"mcp_sentry_gateway").glob('*.py')))),
        "baseline_hash":baseline_hash,"protected_files":len(capture(manifest)["files"])-1,"results":results,
        "qualification":"real stdio technical client; controlled comment/assessment/operator input, no AI or desktop client"}
    (lab/"result.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!='results'},ensure_ascii=False,indent=2))
    print(json.dumps([{k:v for k,v in r.items() if k not in {'response','lifecycle'}} for r in results],indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario",choices=("memory","filesystem","git"),required=True)
    parser.add_argument("--plan",type=Path,required=True)
    parser.add_argument("--lab",type=Path,required=True)
    args=parser.parse_args()
    run(args.scenario,args.plan.resolve(),args.lab.resolve())
