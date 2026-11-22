"""Classic genetic algorithm for real-valued jump parameters."""

from dataclasses import dataclass
from random import Random
from statistics import mean, median


BOUNDS = ((0, 30), (3, 14), (-1.5, 1.5))
MUTATION_STEPS = (3, 1, 0.35)
CROSSOVER_RATE = 0.85
MUTATION_RATE = 0.15


@dataclass(frozen=True)
class Genome:
    a: float
    b: float
    c: float = 0

    @property
    def genes(self):
        return self.a, self.b, self.c

    def as_competitor(self, dino_id):
        return {"id": dino_id, "a": self.a, "b": self.b, "c": self.c}


def random_genome(rng):
    return Genome(*(rng.uniform(low, high) for low, high in BOUNDS))


def breed(population, fitness, elite_index, rng):
    """Keep one elite and fill the remaining slots by roulette and reproduction."""
    children = [population[elite_index]]
    weights = fitness if sum(fitness) > 0 else None
    while len(children) < len(population):
        first, second = rng.choices(population, weights=weights, k=2)
        offspring = (first, second)
        if rng.random() < CROSSOVER_RATE:
            cut = rng.randrange(1, len(BOUNDS))
            offspring = (
                Genome(*(first.genes[:cut] + second.genes[cut:])),
                Genome(*(second.genes[:cut] + first.genes[cut:])),
            )

        for child in offspring[:len(population) - len(children)]:
            genes = []
            for gene, (low, high), step in zip(child.genes, BOUNDS, MUTATION_STEPS):
                if rng.random() < MUTATION_RATE:
                    gene = max(low, min(high, gene + rng.uniform(-step, step)))
                genes.append(gene)
            children.append(Genome(*genes))
    return children


class Training:
    def __init__(self, population_size, generation_limit, seed):
        self.rng = Random(seed)
        self.seed = seed
        self.generation = 1
        self.generation_limit = generation_limit
        self.population = [random_genome(self.rng) for _ in range(population_size)]
        self.used_seeds = set()
        self.reference_seeds = [self.new_seed(), self.new_seed()]
        self.champion = None

    def new_seed(self):
        seed = self.rng.getrandbits(32)
        while seed in self.used_seeds:
            seed = self.rng.getrandbits(32)
        self.used_seeds.add(seed)
        return seed

    def next_tracks(self):
        return [*self.reference_seeds, self.new_seed()]

    def competitors(self):
        return [genome.as_competitor(index) for index, genome in enumerate(self.population, 1)]

    def complete_generation(self, tracks):
        fitness = [mean(results[index]["score"] for results in tracks.values())
                   for index in range(len(self.population))]
        reference = [mean(tracks[seed][index]["score"] for seed in self.reference_seeds)
                     for index in range(len(self.population))]
        wins = [sum(results[index]["outcome"] == "winner" for results in tracks.values())
                for index in range(len(self.population))]
        indices = range(len(self.population))
        elite = max(indices, key=lambda index: (fitness[index], wins[index], reference[index]))
        candidate = max(indices, key=lambda index: (reference[index], wins[index], fitness[index]))
        if self.champion is None or reference[candidate] > self.champion["referenceAverage"]:
            genome = self.population[candidate]
            self.champion = {
                "a": genome.a, "b": genome.b, "c": genome.c,
                "generation": self.generation, "referenceAverage": reference[candidate],
            }

        complete = self.generation == self.generation_limit
        report = {
            "generation": self.generation, "generations": self.generation_limit, "seed": self.seed,
            "best": fitness[elite], "median": median(fitness),
            "referenceBest": max(reference), "referenceMedian": median(reference),
            "elite": self.population[elite].as_competitor(elite + 1),
            "champion": self.champion, "complete": complete,
        }
        if not complete:
            self.population = breed(self.population, fitness, elite, self.rng)
            self.generation += 1
        return report
