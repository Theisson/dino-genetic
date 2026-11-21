import argparse
import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import urlsplit
from uuid import uuid4


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
PUBLIC_FILES = {"index.html", "index.css", "index.js", "autoplay.js"}
TIME_LIMIT_MS = 30_000
COMPETITORS = [
    {"id": 1, "a": 8, "b": 8},
    {"id": 2, "a": 16, "b": 4},
    {"id": 3, "a": 14, "b": 9},
    {"id": 4, "a": 0, "b": 0},
]
COMPETITOR_IDS = {competitor["id"] for competitor in COMPETITORS}


def parse_results(payload):
    if not isinstance(payload, dict):
        raise ValueError("Envie um objeto JSON com roundId e results.")

    round_id = payload.get("roundId")
    results = payload.get("results")
    if not isinstance(round_id, str) or not isinstance(results, list):
        raise ValueError("Informe o ID da rodada e a lista de resultados.")

    by_id = {}
    for result in results:
        if not isinstance(result, dict):
            raise ValueError("Cada resultado deve ser um objeto.")

        dino_id = result.get("id")
        score = result.get("score")
        outcome = result.get("outcome")
        if type(dino_id) is not int or dino_id not in COMPETITOR_IDS or dino_id in by_id:
            raise ValueError("Cada Dino da rodada deve aparecer uma única vez.")
        if type(score) is not int or score < 0:
            raise ValueError("A pontuação deve ser um inteiro não negativo.")
        if outcome not in ("collision", "time_limit"):
            raise ValueError("Informe como o Dino terminou a rodada.")

        by_id[dino_id] = {"id": dino_id, "score": score, "outcome": outcome}

    if by_id.keys() != COMPETITOR_IDS:
        raise ValueError("Envie as pontuações de todos os Dinos da rodada.")

    return round_id, [by_id[dino_id] for dino_id in sorted(by_id)]


class RaceServer(ThreadingHTTPServer):
    def __init__(self, address):
        self.rounds = {}
        self.round_lock = Lock()
        super().__init__(address, RaceHandler)

    def start_round(self):
        round_id = uuid4().hex
        with self.round_lock:
            self.rounds[round_id] = None
        return {"id": round_id, "timeLimitMs": TIME_LIMIT_MS, "competitors": COMPETITORS}

    def record_results(self, round_id, results):
        with self.round_lock:
            if round_id not in self.rounds:
                return HTTPStatus.NOT_FOUND, {"error": "Rodada desconhecida."}

            previous = self.rounds[round_id]
            if previous is None:
                self.rounds[round_id] = results
                report = json.dumps({"roundId": round_id, "results": results})
                print(f"Resultados recebidos: {report}", flush=True)
            elif previous != results:
                return HTTPStatus.CONFLICT, {"error": "A rodada já tem outros resultados."}

        return HTTPStatus.OK, {"roundId": round_id}


class RaceHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_head(self):
        if urlsplit(self.path).path == "/":
            self.path = "/index.html"
        path = Path(self.translate_path(self.path)).resolve()
        if (path.parent == ROOT and path.name in PUBLIC_FILES) or (
            ASSETS in path.parents and path.is_file()
        ):
            return super().send_head()

        self.send_error(HTTPStatus.NOT_FOUND)
        return None

    def do_GET(self):
        if urlsplit(self.path).path == "/rodada":
            self.send_json(HTTPStatus.OK, self.server.start_round())
        else:
            super().do_GET()

    def do_POST(self):
        if urlsplit(self.path).path != "/resultados":
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Rota desconhecida."})
            return

        if self.headers.get_content_type() != "application/json":
            self.send_json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": "Envie JSON."})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 64_000:
                raise ValueError("Tamanho do corpo da requisição inválido.")
            payload = json.loads(self.rfile.read(length))
            round_id, results = parse_results(payload)
        except ValueError as error:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return

        status, response = self.server.record_results(round_id, results)
        self.send_json(status, response)


def main():
    parser = argparse.ArgumentParser(description="Servidor local do Dino Genetic.")
    parser.add_argument("--port", type=int, default=8000, help="Porta HTTP (padrão: 8000).")
    args = parser.parse_args()

    with RaceServer(("127.0.0.1", args.port)) as server:
        print(f"Abra http://127.0.0.1:{server.server_port} no navegador.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
