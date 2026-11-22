(function () {
    'use strict';

    const previewRound = {
        id: null,
        timeLimitMs: Infinity,
        competitors: [
            { id: 1, a: 8, b: 8 },
            { id: 2, a: 16, b: 4 },
            { id: 3, a: 14, b: 9 },
            { id: 4, a: 3, b: 4 }
        ]
    };
    const colors = ['#1d4ed8', '#b91c1c', '#047857', '#7e22ce'];
    const status = document.getElementById('autoplay-status');
    const standings = document.getElementById('race-standings');
    const seedLink = document.getElementById('race-seed');
    const evaluateLink = document.getElementById('race-evaluate');
    const formatScore = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 });

    function getPreviewRound() {
        const requested = new URLSearchParams(location.search).get('sementes');
        const seed = requested === null ? Math.floor(Math.random() * 2 ** 32) : Number(requested);
        if (!Number.isInteger(seed) || seed < 0 || seed >= 2 ** 32 || requested?.trim() === '') {
            throw new Error('Informe uma semente inteira entre 0 e 4294967295.');
        }
        return { ...previewRound, seeds: [seed] };
    }

    async function getRound() {
        if (location.protocol === 'file:') return getPreviewRound();

        const response = await fetch('./rodada' + location.search, { cache: 'no-store' });
        if (response.status === 404) return getPreviewRound();
        if (!response.ok) throw new Error(`GET /rodada: HTTP ${response.status}`);
        return response.json();
    }

    async function sendResults(roundId, seed, results) {
        status.textContent = 'Enviando resultados ao Python…';
        try {
            const response = await fetch('./resultados', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ roundId, seed, results })
            });
            if (!response.ok) throw new Error(`POST /resultados: HTTP ${response.status}`);
            return await response.json();
        } catch (error) {
            status.textContent = 'Disputa encerrada. Falha ao enviar os resultados ao Python.';
            console.error(error);
            return null;
        }
    }

    async function runEvaluation(evaluation) {
        const competitors = evaluation.competitors.map(({ id, a, b }, index) => ({
            id,
            color: colors[index % colors.length],
            shouldJump(distance, speed, onGround) {
                return onGround && distance <= a + b * speed;
            }
        }));
        const entries = new Map();
        let runner;

        for (const { id, color } of competitors) {
            const entry = document.createElement('li');
            const badge = document.createElement('span');
            badge.className = 'race-badge';
            badge.style.backgroundColor = color;
            badge.textContent = id;
            badge.setAttribute('aria-label', `Dino ${id}`);

            const result = document.createElement('span');
            result.className = 'race-result';
            entry.append(badge, result);
            standings.append(entry);
            entries.set(id, result);
        }

        const trackCount = evaluation.seeds.length;
        seedLink.href = '?sementes=' + evaluation.seeds.join(',');
        seedLink.title = trackCount === 1 ? 'Repetir esta pista' : 'Repetir esta avaliação';
        seedLink.hidden = false;
        evaluateLink.hidden = evaluation.id === null;

        for (const [index, seed] of evaluation.seeds.entries()) {
            seedLink.textContent = trackCount === 1 ? `Semente ${seed} · Repetir` :
                `Pista ${index + 1}/${trackCount} · semente ${seed} · Repetir`;
            let remaining = competitors.length;
            for (const result of entries.values()) {
                result.textContent = 'Na pista';
                result.parentElement.classList.remove('eliminated');
            }
            showRaceStatus(remaining);

            const results = await new Promise(resolve => {
                const race = {
                    competitors,
                    seed,
                    timeLimitMs: evaluation.timeLimitMs,
                    onResult({ id, score, outcome }) {
                        const result = entries.get(id);
                        const label = outcome === 'collision' ? 'Eliminado' : 'Tempo limite';
                        result.textContent = `${label} · ${formatScore.format(score)} pts`;
                        if (outcome === 'collision') {
                            result.parentElement.classList.add('eliminated');
                        }
                        showRaceStatus(--remaining);
                        console.info(`Dino ${id} · Pontuação final:`, score);
                    },
                    onFinish: resolve
                };
                if (runner) {
                    runner.startRace(race);
                } else {
                    runner = new Runner('.interstitial-wrapper', undefined, race);
                }
            });

            if (evaluation.id === null) return;
            const response = await sendResults(evaluation.id, seed, results);
            if (!response) return;
            if (trackCount === 1) {
                status.textContent = 'Disputa encerrada. O Python recebeu os resultados.';
            } else if (response.averages) {
                for (const { id, average } of response.averages) {
                    const result = entries.get(id);
                    result.textContent = `Média · ${formatScore.format(average)} pts`;
                    result.parentElement.classList.remove('eliminated');
                }
                status.textContent = `Avaliação concluída · ${trackCount} pistas`;
            }
        }
    }

    function showRaceStatus(remaining) {
        if (remaining === 0) {
            status.textContent = 'Disputa encerrada';
        } else if (remaining === 1) {
            status.textContent = '1 Dino na pista';
        } else {
            status.textContent = `${remaining} Dinos na pista`;
        }
    }

    getRound().then(runEvaluation).catch(error => {
        status.textContent = 'Falha ao carregar a rodada.';
        console.error(error);
    });
})();
