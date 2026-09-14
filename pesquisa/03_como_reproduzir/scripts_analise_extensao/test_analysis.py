from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from . import analyze


class AnalysisTests(unittest.TestCase):
    def test_inputs_and_global_reconstruction(self):
        data = analyze.analyze()
        overall = data["metric_rows"][0]
        costs = data["cost_rows"][0]
        self.assertEqual((450, 900, 5, 23), (overall["pairs"], overall["primary_units"], overall["r3_diagnostics"], overall["terminal_failures"]))
        self.assertEqual((905, "5.14043240", "5.80164740"), (costs["attempts"], costs["cost_observed_usd"], costs["cost_accounted_usd"]))

    def test_topology_by_position(self):
        data = analyze.analyze()
        rows = {(r["position_id"], r["condition"]): r for r in data["metric_rows"]}
        for position in analyze.POSITIONS:
            self.assertEqual((150, 300), (rows[position, "ALL"]["pairs"], rows[position, "ALL"]["primary_units"]))
            self.assertEqual((60, 60, 30), tuple(rows[position, condition]["pairs"] for condition in analyze.CONDITIONS))
        actions = {}
        for row in data["action_rows"]:
            key = (row["position_id"], row["condition"])
            actions.setdefault(key, []).append(row)
        for rows_for_group in actions.values():
            self.assertEqual(int(rows_for_group[0]["denominator_primary_units"]), sum(int(row["count"]) for row in rows_for_group))

    def test_materialization_is_deterministic_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "analysis"
            analyze.materialize(output)
            first = {p.name: p.read_bytes() for p in output.iterdir()}
            ledger = {line.split("\t")[1]: line.split("\t")[0] for line in (output / "sha256.tsv").read_text(encoding="utf-8").splitlines()}
            self.assertEqual(6, len(ledger))
            self.assertTrue(all(hashlib.sha256((output / name).read_bytes()).hexdigest() == digest for name, digest in ledger.items()))
            with self.assertRaisesRegex(analyze.AnalysisError, "saída já existe"):
                analyze.materialize(output)
            second = Path(temporary) / "second"
            analyze.materialize(second)
            self.assertEqual(first, {p.name: p.read_bytes() for p in second.iterdir()})

    def test_tampered_input_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            ledger = Path(temporary) / "ledger.tsv"
            ledger.write_text(analyze.LEDGER.read_text(encoding="utf-8").replace("3bdd", "0000", 1), encoding="utf-8")
            with mock.patch.object(analyze, "LEDGER", ledger):
                with self.assertRaisesRegex(analyze.AnalysisError, "hash do ledger"):
                    analyze.validate_inputs()

    def test_coherently_rehashed_evidence_and_ledger_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "inputs"
            root.mkdir()
            for name in analyze.FILES:
                (root / name).write_bytes((analyze.INPUT / name).read_bytes())
            target = root / "authorization.json"
            target.write_bytes(target.read_bytes() + b" ")
            ledger = Path(temporary) / "ledger.tsv"
            ledger.write_text("".join(
                f"{hashlib.sha256((root / name).read_bytes()).hexdigest()}\t{name}\n"
                for name in analyze.FILES
            ), encoding="utf-8")
            with mock.patch.object(analyze, "INPUT", root), mock.patch.object(analyze, "LEDGER", ledger):
                with self.assertRaisesRegex(analyze.AnalysisError, "hash do ledger"):
                    analyze.validate_inputs()

    def test_summary_disclaims_causality(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "analysis"
            analyze.materialize(output)
            summary = json.loads((output / "resumo_analitico.json").read_text(encoding="utf-8"))
            self.assertIs(summary["causal_superiority_claimed"], False)

    def test_manifest_pins_complete_analyzer_source_set(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "analysis"
            analyze.materialize(output)
            manifest = json.loads((output / "manifesto_analise.json").read_text(encoding="utf-8"))
            self.assertEqual(
                {
                    "tools/m2_3_extensao_multimodelo_analysis_v1/__init__.py",
                    "tools/m2_3_extensao_multimodelo_analysis_v1/analyze.py",
                    "tools/m2_3_extensao_multimodelo_analysis_v1/test_analysis.py",
                },
                set(manifest["analyzer_sources_sha256"]),
            )

    def test_non_finite_json_and_causal_contract_are_rejected(self):
        with self.assertRaisesRegex(analyze.AnalysisError, "constante JSON"):
            analyze.loads('{"value": NaN}')
        with tempfile.TemporaryDirectory() as temporary:
            contract = json.loads(analyze.CONTRACT.read_text(encoding="utf-8"))
            contract["model_or_provider_superiority_is_causal"] = True
            path = Path(temporary) / "contract.json"
            path.write_text(json.dumps(contract), encoding="utf-8")
            with mock.patch.object(analyze, "CONTRACT", path):
                with self.assertRaisesRegex(analyze.AnalysisError, "hash do contrato"):
                    analyze.validate_inputs()

    def test_noncausal_contract_invariant_change_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            contract = json.loads(analyze.CONTRACT.read_text(encoding="utf-8"))
            contract["denominators"]["terminal_failures_remain_in_denominator"] = False
            path = Path(temporary) / "contract.json"
            path.write_text(json.dumps(contract), encoding="utf-8")
            with mock.patch.object(analyze, "CONTRACT", path), mock.patch.object(analyze, "EXPECTED_CONTRACT_SHA256", hashlib.sha256(path.read_bytes()).hexdigest()):
                with self.assertRaisesRegex(analyze.AnalysisError, "contrato analítico inválido"):
                    analyze.validate_inputs()

    def test_contract_comparison_rejects_python_numeric_equivalences(self):
        variants = []
        false_as_zero = json.loads(analyze.CONTRACT.read_text(encoding="utf-8"))
        false_as_zero["model_or_provider_superiority_is_causal"] = 0
        variants.append(false_as_zero)
        int_as_float = json.loads(analyze.CONTRACT.read_text(encoding="utf-8"))
        int_as_float["denominators"]["total"]["pairs"] = 450.0
        variants.append(int_as_float)
        for contract in variants:
            with self.subTest(contract=contract):
                with tempfile.TemporaryDirectory() as temporary:
                    path = Path(temporary) / "contract.json"
                    path.write_text(json.dumps(contract), encoding="utf-8")
                    with mock.patch.object(analyze, "CONTRACT", path), mock.patch.object(analyze, "EXPECTED_CONTRACT_SHA256", hashlib.sha256(path.read_bytes()).hexdigest()):
                        with self.assertRaisesRegex(analyze.AnalysisError, "contrato analítico inválido"):
                            analyze.validate_inputs()


if __name__ == "__main__":
    unittest.main()
