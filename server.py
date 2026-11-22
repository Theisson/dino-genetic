import argparse
import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from random import getrandbits, sample
from statistics import mean
from threading import Lock
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from genetic import Training


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
BEST_MODEL = ROOT / "best.json"
PUBLIC_FILES = {"index.html", "index.css", "index.js", "autoplay.js"}
SEED_COUNT = 2**32
MAX_TRACKS = 20
SCORE_LIMIT = 5_000
VALIDATION_TRACKS = 5
REGRESSION_SEED = 2132847803
COMPETITORS = [
    {"id": 1, "a": 8, "b": 8},
    {"id": 2, "a": 16, "b": 4},
    {"id": 3, "a": 14, "b": 9},
    {"id": 4, "a": 0, "b": 0},
]


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
        if type(dino_id) is not int or dino_id < 1 or dino_id in by_id:
            raise ValueError("Cada Dino da rodada deve aparecer uma única vez.")
        if type(score) is not int or score < 0:
            raise ValueError("A pontuação deve ser um inteiro não negativo.")
        if outcome not in ("collision", "time_limit", "winner", "tie", "score_limit"):
            raise ValueError("Informe como o Dino terminou a rodada.")

        by_id[dino_id] = {"id": dino_id, "score": score, "outcome": outcome}

    return round_id, seed, [by_id[dino_id] for dino_id in sorted(by_id)]


def save_best_model(training):
    model = {
        **training.champion,
        "trainingSeed": training.seed,
        "trainingSeeds": sorted(training.used_seeds),
    }
    temporary = BEST_MODEL.with_name(f".best-{uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8")
        temporary.replace(BEST_MODEL)
    finally:
        temporary.unlink(missing_ok=True)


def read_best_model():
    model = json.loads(BEST_MODEL.read_text(encoding="utf-8"))
    if not isinstance(model, dict):
        raise ValueError("Modelo inválido.")

    model.setdefault("c", 0)
    for key in ("a", "b", "c"):
        value = model.get(key)
        if type(value) not in (int, float) or not -1000 <= value <= 1000:
            raise ValueError("Genes inválidos.")

    seeds = model.get("trainingSeeds")
    if not isinstance(seeds, list) or not seeds or any(
        type(seed) is not int or not 0 <= seed < SEED_COUNT for seed in seeds
    ):
        raise ValueError("Sementes de treino inválidas.")
    return model


class RaceServer(ThreadingHTTPServer):
    def __init__(self, address, population_size=12, generation_limit=10):
        self.rounds = {}
        self.round_lock = Lock()
        self.population_size = population_size
        self.generation_limit = generation_limit
        super().__init__(address, RaceHandler)

    def start_round(self, seeds):
        with self.round_lock:
            return self.register_round(seeds)

    def start_training(self, seed):
        training = Training(self.population_size, self.generation_limit, seed)
        print(f"Semente do treino: {seed}", flush=True)
        with self.round_lock:
            return self.register_round(training.next_tracks(), training)

    def start_validation(self):
        model = read_best_model()
        excluded = {*model["trainingSeeds"], REGRESSION_SEED}
        seeds = []
        while len(seeds) < VALIDATION_TRACKS:
            seed = getrandbits(32)
            if seed not in excluded:
                seeds.append(seed)
                excluded.add(seed)

        with self.round_lock:
            return self.register_round(seeds, validation_model=model)

    def register_round(self, seeds, training=None, validation_model=None):
        round_id = uuid4().hex
        if validation_model is not None:
            competitors = [
                {
                    "id": 1, "a": validation_model["a"], "b": validation_model["b"],
                    "c": validation_model["c"], "label": "Dino treinado",
                },
                {"id": 2, "a": 8, "b": 8, "label": "Regra 8, 8"},
                {"id": 3, "a": 14, "b": 9, "label": "Regra 14, 9"},
            ]
        else:
            competitors = training.competitors() if training else COMPETITORS
        self.rounds[round_id] = {
            "tracks": dict.fromkeys(seeds),
            "ids": {competitor["id"] for competitor in competitors},
            "training": training,
            "validation": validation_model is not None,
            "summary": {},
        }
        response = {"id": round_id, "timeLimitMs": None, "competitors": competitors, "seeds": seeds}
        if training:
            response["training"] = {
                "generation": training.generation, "generations": training.generation_limit,
                "seed": training.seed, "scoreLimit": SCORE_LIMIT,
            }
        elif validation_model is not None:
            response["validation"] = {"scoreLimit": SCORE_LIMIT}
        return response

    def record_results(self, round_id, seed, results):
        with self.round_lock:
            evaluation = self.rounds.get(round_id)
            if evaluation is None:
                return HTTPStatus.NOT_FOUND, {"error": "Rodada desconhecida."}

            tracks = evaluation["tracks"]
            if {result["id"] for result in results} != evaluation["ids"]:
                return HTTPStatus.BAD_REQUEST, {"error": "Envie as pontuações de todos os Dinos da rodada."}
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

            summary = evaluation["summary"]
            if previous is None and all(scores is not None for scores in tracks.values()):
                summary["averages"] = [
                    {"id": dino_id, "average": mean(scores[index]["score"] for scores in tracks.values())}
                    for index, dino_id in enumerate(sorted(evaluation["ids"]))
                ]
                if evaluation["validation"]:
                    for index, result in enumerate(summary["averages"]):
                        scores = [track[index]["score"] for track in tracks.values()]
                        result["worst"] = min(scores)
                        result["reachedGoal"] = sum(score >= SCORE_LIMIT for score in scores)
                if len(tracks) > 1:
                    report = {"roundId": round_id, "seeds": list(tracks), "averages": summary["averages"]}
                    label = "Validação" if evaluation["validation"] else "Avaliação"
                    print(f"{label} concluída: {json.dumps(report)}", flush=True)

                training = evaluation["training"]
                if training:
                    summary["training"] = training.complete_generation(tracks)
                    print(f"Geração concluída: {json.dumps(summary['training'])}", flush=True)
                    if summary["training"]["complete"]:
                        try:
                            save_best_model(training)
                        except OSError as error:
                            summary["training"]["saved"] = False
                            print(f"Falha ao salvar best.json: {error}", flush=True)
                        else:
                            summary["training"]["saved"] = True
                    else:
                        summary["nextRound"] = self.register_round(training.next_tracks(), training)

            return HTTPStatus.OK, {"roundId": round_id, "seed": seed, **summary}


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
        elif request.path == "/treino":
            try:
                params = parse_qs(request.query, keep_blank_values=True)
                seed = int(params["sementetreino"][0]) if "sementetreino" in params else getrandbits(32)
                if not 0 <= seed < SEED_COUNT:
                    raise ValueError
            except ValueError:
                self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Informe uma semente de treino de 32 bits."})
                return
            self.send_json(HTTPStatus.OK, self.server.start_training(seed))
        elif request.path == "/validacao":
            try:
                validation = self.server.start_validation()
            except FileNotFoundError:
                self.send_json(HTTPStatus.CONFLICT, {
                    "error": "Conclua um treino para salvar um Dino antes de validar."
                })
            except (OSError, ValueError):
                self.send_json(HTTPStatus.CONFLICT, {
                    "error": "Não foi possível ler best.json. Conclua um treino para gerar outro."
                })
            else:
                self.send_json(HTTPStatus.OK, validation)
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
    parser.add_argument("--populacao", type=int, default=12, help="Dinos por geração (padrão: 12).")
    parser.add_argument("--geracoes", type=int, default=10, help="Gerações por treino (padrão: 10).")
    args = parser.parse_args()
    if not 2 <= args.populacao <= 24 or args.geracoes < 1:
        parser.error("Use de 2 a 24 Dinos e pelo menos uma geração.")

    with RaceServer(("127.0.0.1", args.port), args.populacao, args.geracoes) as server:
        print(f"Abra http://127.0.0.1:{server.server_port} no navegador.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
