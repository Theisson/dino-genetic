import argparse
import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from random import sample
from statistics import mean
from threading import Lock
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
PUBLIC_FILES = {"index.html", "index.css", "index.js", "autoplay.js"}
TIME_LIMIT_MS = 30_000
SEED_COUNT = 2**32
MAX_TRACKS = 20
COMPETITORS = [
    {"id": 1, "a": 8, "b": 8},
    {"id": 2, "a": 16, "b": 4},
    {"id": 3, "a": 14, "b": 9},
    {"id": 4, "a": 0, "b": 0},
]
COMPETITOR_IDS = {competitor["id"] for competitor in COMPETITORS}


def choose_seeds(query):
    params = parse_qs(query, keep_blank_values=True)
    if "sementes" in params:
        try:
            seeds = [int(value) for value in params["sementes"][0].split(",")]
        except ValueError:
            raise ValueError("Informe as sementes como inteiros separados por vírgula.") from None
        if not 1 <= len(seeds) <= MAX_TRACKS:
            raise ValueError(f"Informe de 1 a {MAX_TRACKS} sementes.")
        if len(set(seeds)) != len(seeds) or any(not 0 <= seed < SEED_COUNT for seed in seeds):
            raise ValueError(f"As sementes devem ser distintas e estar entre 0 e {SEED_COUNT - 1}.")
        return seeds

    try:
        count = int(params.get("pistas", ["1"])[0])
    except ValueError:
        raise ValueError("Informe um número inteiro de pistas.") from None
    if not 1 <= count <= MAX_TRACKS:
        raise ValueError(f"Escolha de 1 a {MAX_TRACKS} pistas.")
    return sample(range(SEED_COUNT), count)


def parse_results(payload):
    if not isinstance(payload, dict):
        raise ValueError("Envie um objeto JSON com roundId e results.")

    round_id = payload.get("roundId")
    seed = payload.get("seed")
    results = payload.get("results")
    if not isinstance(round_id, str) or not isinstance(results, list):
        raise ValueError("Informe o ID da rodada e a lista de resultados.")
    if seed is not None and type(seed) is not int:
        raise ValueError("A semente deve ser um inteiro.")

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

    return round_id, seed, [by_id[dino_id] for dino_id in sorted(by_id)]


class RaceServer(ThreadingHTTPServer):
    def __init__(self, address):
        self.rounds = {}
        self.round_lock = Lock()
        super().__init__(address, RaceHandler)

    def start_round(self, seeds):
        round_id = uuid4().hex
        with self.round_lock:
            self.rounds[round_id] = dict.fromkeys(seeds)
        return {
            "id": round_id, "timeLimitMs": TIME_LIMIT_MS, "competitors": COMPETITORS, "seeds": seeds
        }

    def record_results(self, round_id, seed, results):
        with self.round_lock:
            tracks = self.rounds.get(round_id)
            if tracks is None:
                return HTTPStatus.NOT_FOUND, {"error": "Rodada desconhecida."}

            if seed is None and len(tracks) == 1:
                seed = next(iter(tracks))
            if seed not in tracks:
                return HTTPStatus.BAD_REQUEST, {"error": "A semente deve pertencer à rodada."}

            previous = tracks[seed]
            if previous is None:
                tracks[seed] = results
                report = json.dumps({"roundId": round_id, "seed": seed, "results": results})
                print(f"Resultados recebidos: {report}", flush=True)
            elif previous != results:
                return HTTPStatus.CONFLICT, {"error": "A pista já tem outros resultados."}

            response = {"roundId": round_id, "seed": seed}
            if all(scores is not None for scores in tracks.values()):
                response["averages"] = [
                    {"id": dino_id, "average": mean(scores[index]["score"] for scores in tracks.values())}
                    for index, dino_id in enumerate(sorted(COMPETITOR_IDS))
                ]
                if previous is None and len(tracks) > 1:
                    report = json.dumps({"roundId": round_id, "seeds": list(tracks),
                                         "averages": response["averages"]})
                    print(f"Avaliação concluída: {report}", flush=True)

        return HTTPStatus.OK, response


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
        request = urlsplit(self.path)
        if request.path == "/rodada":
            try:
                seeds = choose_seeds(request.query)
            except ValueError as error:
                self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
                return
            self.send_json(HTTPStatus.OK, self.server.start_round(seeds))
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
            round_id, seed, results = parse_results(payload)
        except ValueError as error:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return

        status, response = self.server.record_results(round_id, seed, results)
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
