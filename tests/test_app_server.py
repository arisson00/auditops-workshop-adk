"""Testes dos limites de proteção do servidor web (auditorias simultâneas, pedidos por IP e tamanho do corpo)."""

import json
import os
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch

import app_server
from audit_ops.schemas import AuditReport


class TestServerLimits(unittest.TestCase):

    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), app_server.AuditOpsRequestHandler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        # Sem credenciais: a auditoria roda em modo demonstração, sem chamar o Gemini
        env_patch = patch.dict(os.environ, {"PATH": os.environ.get("PATH", "")}, clear=True)
        env_patch.start()
        self.addCleanup(env_patch.stop)

    def _post(self, path, body, ip="203.0.113.7"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        req = urllib.request.Request(
            self.base + path, data=data, method="POST",
            headers={"Content-Type": "application/json", "X-Forwarded-For": f"1.2.3.4, {ip}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                return res.status, json.loads(res.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_rate_limit_per_ip_blocks_after_limit(self):
        with patch.object(app_server, "AUDIT_LIMITER", app_server.RateLimiter(2, 3600)), \
             patch.object(app_server.ORCHESTRATOR, "execute_audit", return_value=AuditReport()):
            statuses = [self._post("/api/audit", {"contract_text": "x"})[0] for _ in range(3)]
            other_ip, _ = self._post("/api/audit", {"contract_text": "x"}, ip="198.51.100.9")
        self.assertEqual(statuses, [200, 200, 429])
        self.assertEqual(other_ip, 200, "o limite é por IP real, não global")

    def test_spoofed_forwarded_for_does_not_bypass_limit(self):
        limiter = app_server.RateLimiter(1, 3600)
        with patch.object(app_server, "AUDIT_LIMITER", limiter), \
             patch.object(app_server.ORCHESTRATOR, "execute_audit", return_value=AuditReport()):
            first, _ = self._post("/api/audit", {"contract_text": "x"})
            # O cliente muda o primeiro item do cabeçalho; o último (IP real) continua o mesmo
            req = urllib.request.Request(
                self.base + "/api/audit", data=b'{"contract_text": "x"}', method="POST",
                headers={"X-Forwarded-For": "9.9.9.9, 203.0.113.7"},
            )
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req, timeout=30)
        self.assertEqual(first, 200)
        self.assertEqual(ctx.exception.code, 429)

    def test_concurrent_audits_are_capped(self):
        release = threading.Event()

        def slow_audit(**kwargs):
            release.wait(10)
            return AuditReport()

        results = []
        with patch.object(app_server, "AUDIT_SLOTS", threading.BoundedSemaphore(1)), \
             patch.object(app_server, "AUDIT_LIMITER", app_server.RateLimiter(100, 3600)), \
             patch.object(app_server.ORCHESTRATOR, "execute_audit", side_effect=slow_audit):
            first = threading.Thread(target=lambda: results.append(self._post("/api/audit", {"contract_text": "x"})))
            first.start()
            time.sleep(0.3)
            status, body = self._post("/api/audit", {"contract_text": "y"}, ip="198.51.100.9")
            release.set()
            first.join(10)
        self.assertEqual(status, 429)
        self.assertIn("auditorias em andamento", body["error"])
        self.assertEqual(results[0][0], 200)

    def test_oversized_body_is_rejected(self):
        with patch.object(app_server, "MAX_BODY_BYTES", 1024):
            status, body = self._post("/api/upload_document", b"{" + b" " * 4096 + b"}")
        self.assertEqual(status, 413)
        self.assertIn("grande demais", body["error"])

    def test_chat_uses_report_of_its_own_contract(self):
        reports = {"contrato A": AuditReport(contract_title="A"), "contrato B": AuditReport(contract_title="B")}
        seen = []

        def fake_chat(question, report, contract_text):
            seen.append(report.contract_title if report else None)
            return {"answer": "ok"}

        with patch.object(app_server, "AUDIT_LIMITER", app_server.RateLimiter(100, 3600)), \
             patch.object(app_server.ORCHESTRATOR, "execute_audit",
                          side_effect=lambda contract_text, **kw: reports[contract_text]), \
             patch.object(app_server.ORCHESTRATOR, "ask_insight_assistant", side_effect=fake_chat):
            self._post("/api/audit", {"contract_text": "contrato A"})
            self._post("/api/audit", {"contract_text": "contrato B"}, ip="198.51.100.9")
            self._post("/api/chat", {"question": "Qual o foro?", "contract_text": "contrato A"})
            self._post("/api/chat", {"question": "Qual o foro?", "contract_text": "contrato nunca auditado"})
        self.assertEqual(seen, ["A", None])

    def test_chat_rate_limit(self):
        with patch.object(app_server, "CHAT_LIMITER", app_server.RateLimiter(1, 3600)):
            first, _ = self._post("/api/chat", {"question": "Quem são as partes?", "contract_text": "x"})
            second, body = self._post("/api/chat", {"question": "E o foro?", "contract_text": "x"})
        self.assertEqual(first, 200)
        self.assertEqual(second, 429)
        self.assertIn("perguntas por hora", body["error"])


if __name__ == "__main__":
    unittest.main()
