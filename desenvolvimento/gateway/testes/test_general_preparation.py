import json
import contextlib
import io
import shutil
import sys
import unittest
from unittest import mock
from pathlib import Path
from types import SimpleNamespace

import test_gateway_universal as fixtures
from mcp_sentry_gateway.core import SentryError, approve, inspect
from mcp_sentry_gateway.gateway import StdioGateway
from mcp_sentry_gateway.onboarding import prepare_codex
from mcp_sentry_gateway.operator import decide
from mcp_sentry_gateway.review import ensure_pending, submit_verdict
from mcp_sentry_gateway.materialize import launcher_spec, materialize
from mcp_sentry_gateway.preparation import separated
from mcp_sentry_gateway.preparation import main as preparation_main


NODE_SOURCE = '''const readline = require('node:readline');
for await (const line of readline.createInterface({input:process.stdin})) {
 const r=JSON.parse(line); if (!('id' in r)) continue;
 let result;
 if(r.method==='initialize') result={protocolVersion:'2025-06-18',capabilities:{tools:{}},serverInfo:{name:'fixture',version:'1'}};
 else if(r.method==='tools/list') result={tools:[{name:'echo',description:'Echo a value',inputSchema:{type:'object',properties:{value:{type:'string'}},required:['value']}}]};
 else result={content:[{type:'text',text:process.cwd()+'|'+r.params.arguments.value}]};
 console.log(JSON.stringify({jsonrpc:'2.0',id:r.id,result}));
}
'''


class GeneralTests(unittest.TestCase):
    setUp = fixtures.UniversalGatewayTests.setUp
    save_manifest = fixtures.UniversalGatewayTests.save_manifest
    request = staticmethod(fixtures.UniversalGatewayTests.request)

    def allow(self):
        record, _ = ensure_pending(self.manifest, self.state)
        submit_verdict(self.manifest, self.state, {
            "review_id": record["review_id"], "reviewed_hash": record["dossier"]["current_hash"],
            "dossier_hash": record["dossier"]["dossier_hash"], "policy_version": record["policy_version"],
            "decision": "allow", "justification": "Technical fixture, not AI assessment", "risks": []})

    def call(self):
        gateway = StdioGateway(self.manifest, self.state, interface="execution")
        self.addCleanup(gateway.backend.close)
        response = gateway.handle(self.request(1, "tools/call", {"name": "echo", "arguments": {"value": "ok"}}))
        return gateway, response

    def prepare(self, command, roots):
        self.manifest.unlink()
        return prepare_codex(SimpleNamespace(name="generic", project_root=self.project, inspect_root=roots,
            manifest=self.manifest, store=self.state, fragment=self.config/"codex.toml",
            backend_command=command, passthrough_name=[]))

    def test_dist_info_replacement_preserves_baseline_and_requires_two_decisions(self):
        old = self.project / "anything-1.dist-info"
        old.mkdir()
        (old/"METADATA").write_text("Version: 1\n")
        self.manifest_data["inspect_roots"].append(old.name)
        self.save_manifest()
        approve(self.manifest, self.state)
        baseline_bytes = (self.state/"versao-aprovada.json").read_bytes()
        shutil.rmtree(old)
        new = self.project / "anything-2.dist-info"
        new.mkdir()
        (new/"METADATA").write_text("Version: 2\n")
        result = inspect(self.manifest, self.state)
        self.assertEqual(result["dossier"]["coverage"]["missing_current"], [old.name])
        self.assertIn((old.name+"/METADATA", "removed"), [(c["path"],c["kind"]) for c in result["dossier"]["changes"]])
        gateway, _ = self.call()
        self.assertEqual(gateway.backend.lifecycle.snapshot()["spawn_attempts"], 0)
        self.manifest_data["inspect_roots"] = ["server.py", new.name]
        self.save_manifest()
        result = inspect(self.manifest, self.state)
        self.assertIn((new.name+"/METADATA", "added"), [(c["path"],c["kind"]) for c in result["dossier"]["changes"]])
        self.assertEqual(result["dossier"]["coverage"]["removed_roots"], [old.name])
        self.assertEqual((self.state/"versao-aprovada.json").read_bytes(), baseline_bytes)
        self.allow()
        with self.assertRaisesRegex(SentryError, "envelope"):
            decide(self.manifest,self.state,"accept",input_fn=lambda:"ACEITAR",output=lambda _:None)
        decide(self.manifest,self.state,"envelope",input_fn=lambda:"PROMOVER",output=lambda _:None)
        gateway, _ = self.call()
        self.assertEqual(gateway.backend.lifecycle.snapshot()["spawn_attempts"], 0)
        decide(self.manifest,self.state,"accept",input_fn=lambda:"ACEITAR",output=lambda _:None)
        gateway, response = self.call()
        self.assertEqual(response["result"]["content"][0]["text"],"ok")
        self.assertEqual(inspect(self.manifest,self.state)["status"],"unchanged")

    def test_add_remove_files_and_coverage(self):
        (self.project/"keep.json").write_text('{}')
        self.manifest_data["inspect_roots"] = ["."]
        self.save_manifest()
        approve(self.manifest,self.state)
        (self.project/"keep.json").unlink()
        (self.project/"added.py").write_text('# added')
        changes = inspect(self.manifest,self.state)["dossier"]["changes"]
        self.assertEqual({(c["path"],c["kind"]) for c in changes}, {("keep.json","removed"),("added.py","added")})

    def test_generic_python_absolute_script_becomes_local(self):
        self.prepare([sys.executable,str(self.project/"server.py")],["server.py"])
        self.assertEqual(json.loads(self.manifest.read_text())["configuration"]["command"][1],"server.py")
        approve(self.manifest,self.state)
        gateway,response = self.call()
        self.assertEqual(response["result"]["content"][0]["text"],"ok")
        self.assertTrue((gateway.backend.copy_root/"server.py").is_file())

    def test_generic_python_module(self):
        package = self.project/"unrelated"
        package.mkdir()
        (package/"__init__.py").write_text('')
        (package/"__main__.py").write_text(fixtures.SERVER_SOURCE)
        self.prepare([sys.executable,"-m","unrelated"],["unrelated"])
        approve(self.manifest,self.state)
        gateway,response = self.call()
        self.assertEqual(response["result"]["content"][0]["text"],"ok")
        self.assertTrue((gateway.backend.copy_root/"unrelated/__main__.py").is_file())

    def test_generic_node_entry_runs_in_copy(self):
        node = shutil.which("node")
        if not node: self.skipTest("Node.js unavailable")
        # Top-level await requires ESM; fixture explicitly imports its local helper.
        (self.project/"server.mjs").write_text(NODE_SOURCE.replace("const readline = require('node:readline');", "import readline from 'node:readline';"))
        self.prepare([node,str(self.project/"server.mjs")],["server.mjs"])
        approve(self.manifest,self.state)
        gateway,response = self.call()
        self.assertIn(str(gateway.backend.copy_root),response["result"]["content"][0]["text"])
        gateway.backend.close()
        (self.project/"server.mjs").write_text('// changed\n'+(self.project/"server.mjs").read_text())
        gateway,_ = self.call()
        self.assertEqual(gateway.backend.lifecycle.snapshot()["spawn_attempts"],0)
        self.allow()
        decide(self.manifest,self.state,"accept",input_fn=lambda:"ACEITAR",output=lambda _:None)
        gateway,response = self.call()
        self.assertIn("|ok",response["result"]["content"][0]["text"])

    def test_uncopied_absolute_original_entry_is_rejected(self):
        self.manifest_data["configuration"]["command"] = [sys.executable,str(self.project/"server.py")]
        self.save_manifest()
        approve(self.manifest,self.state)
        gateway,response = self.call()
        self.assertEqual(gateway.backend.lifecycle.snapshot()["spawn_attempts"],0)
        self.assertIn("dentro do código protegido",json.dumps(response,ensure_ascii=False))

    def test_launcher_conversion_specs(self):
        for command in (["npx","-y","@scope/server@1.2.3","data"],
                        ["cmd","/c","npx","--package","@scope/server@1.2.3","server","data"]):
            parsed = launcher_spec(command)
            self.assertEqual((parsed["package"],parsed["version"],parsed["args"]),("@scope/server","1.2.3",["data"]))
        parsed = launcher_spec(["uvx","--from","distribution==2.1.0","mcp-command","--arg"])
        self.assertEqual((parsed["package"],parsed["binary"]),("distribution","mcp-command"))
        self.assertEqual(launcher_spec(["uvx","server@2.1.0"])["version"],"2.1.0")
        self.assertEqual(launcher_spec(["npx","server"],"1.2.3")["version"],"1.2.3")
        for command in (["npx","server@latest"],["uvx","server"],["npx","-c","echo x"]):
            with self.assertRaises(SentryError): launcher_spec(command)

    def test_materialization_converts_bin_not_package_manager(self):
        node = shutil.which("node")
        if not node: self.skipTest("Node unavailable")
        destination = self.temp/"installed"
        def installer(command):
            package = destination/"node_modules/unrelated"
            package.mkdir(parents=True)
            (package/"package.json").write_text(json.dumps({"name":"unrelated","version":"1.2.3","bin":{"mcp-other":"entry.js"}}))
            (package/"entry.js").write_text('// fixture')
            (destination/"package.json").write_text('{}')
            (destination/"package-lock.json").write_text('{}')
            return ''
        with mock.patch("mcp_sentry_gateway.materialize.run_checked",side_effect=installer):
            result = materialize(launcher_spec(["npx","unrelated@1.2.3"]),destination,node)
        self.assertEqual(Path(result["command"][0]).name.lower(),"node.exe" if sys.platform=="win32" else "node")
        self.assertEqual(result["command"][1],"node_modules/unrelated/entry.js")
        self.assertTrue((destination/"launch.json").is_file())
        with self.assertRaisesRegex(SentryError,"já existe"):
            materialize(launcher_spec(["npx","unrelated@1.2.3"]),destination,node)

    def test_data_and_state_are_separate(self):
        with self.assertRaisesRegex(SentryError,"separadas"):
            separated(self.project,self.state,[self.project])

    def test_envelope_decision_is_bound_to_displayed_code(self):
        approve(self.manifest,self.state)
        self.manifest_data["configuration"]["passthrough_names"]=["SOME_VAR"]
        self.save_manifest()
        self.allow()
        def mutation():
            (self.project/"server.py").write_text(fixtures.SERVER_SOURCE+'\n# changed during prompt')
            return "PROMOVER"
        with self.assertRaisesRegex(SentryError,"mudou"):
            decide(self.manifest,self.state,"envelope",input_fn=mutation,output=lambda _:None)

    def test_mutation_after_inspection_is_still_blocked_before_spawn(self):
        approve(self.manifest,self.state)
        gateway = StdioGateway(self.manifest,self.state,interface="execution")
        self.addCleanup(gateway.backend.close)
        copy_and_spawn = gateway.backend._copy_and_spawn
        def mutation(expected_hash):
            (self.project/"server.py").write_text(fixtures.SERVER_SOURCE+'\n# mutation after inspection')
            return copy_and_spawn(expected_hash)
        with mock.patch.object(gateway.backend,"_copy_and_spawn",side_effect=mutation):
            response = gateway.handle(self.request(1,"tools/call",{"name":"echo","arguments":{"value":"ok"}}))
        self.assertEqual(gateway.backend.lifecycle.snapshot()["spawn_attempts"],0)
        self.assertIn("estado mudou antes",json.dumps(response,ensure_ascii=False))

    def test_plan_cli_is_generic_and_does_not_approve(self):
        self.manifest.unlink()
        plan=self.config/"launch.json"
        plan.write_text(json.dumps({"project_root":str(self.project),"inspect_roots":["server.py"],
            "command":[sys.executable,"server.py"],"package":"unrelated","version":"1"}))
        with mock.patch("builtins.input",return_value="DESCOBRIR"),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(preparation_main(["--plan",str(plan),"--name","anything",
                "--manifest",str(self.manifest),"--store",str(self.state),"--fragment",str(self.config/"fragment.toml")]),0)
        self.assertTrue(self.manifest.exists())
        self.assertFalse((self.state/"versao-aprovada.json").exists())

    def test_local_modules_and_configuration_are_copied_for_discovery_and_execution(self):
        (self.project/"helper.py").write_text("import json\nfrom pathlib import Path\nVALUE=json.loads(Path('config.json').read_text())['greeting']\n")
        (self.project/"config.json").write_text('{"greeting":"local-"}')
        source="from helper import VALUE\n"+fixtures.SERVER_SOURCE.replace('os.environ.get("SERVER_GREETING", "") + value','VALUE + value')
        (self.project/"server.py").write_text(source)
        self.prepare([sys.executable,"server.py"],["server.py","helper.py","config.json"])
        approve(self.manifest,self.state)
        gateway,response=self.call()
        self.assertEqual(response["result"]["content"][0]["text"],"local-ok")
        self.assertTrue((gateway.backend.copy_root/"helper.py").is_file())
        self.assertTrue((gateway.backend.copy_root/"config.json").is_file())
