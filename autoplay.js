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

    async function getRound() {
        if (location.protocol === 'file:') return previewRound;

        const response = await fetch('./rodada', { cache: 'no-store' });
        if (response.status === 404) return previewRound;
        if (!response.ok) throw new Error(`GET /rodada: HTTP ${response.status}`);
        return response.json();
    }

    async function sendResults(roundId, results) {
        status.textContent = 'Enviando resultados ao Python…';
        try {
            const response = await fetch('./resultados', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ roundId, results })
            });
            if (!response.ok) throw new Error(`POST /resultados: HTTP ${response.status}`);
            status.textContent = 'Disputa encerrada. O Python recebeu os resultados.';
        } catch (error) {
            status.textContent = 'Disputa encerrada. Falha ao enviar os resultados ao Python.';
            console.error(error);
        }
    }

    function startRound(round) {
        const competitors = round.competitors.map(({ id, a, b }, index) => ({
            id,
            color: colors[index % colors.length],
            shouldJump(distance, speed, onGround) {
                return onGround && distance <= a + b * speed;
            }
        }));
        const entries = new Map();
        let remaining = competitors.length;

        for (const { id, color } of competitors) {
            const entry = document.createElement('li');
            const badge = document.createElement('span');
            badge.className = 'race-badge';
            badge.style.backgroundColor = color;
            badge.textContent = id;
            badge.setAttribute('aria-label', `Dino ${id}`);

            const result = document.createElement('span');
            result.className = 'race-result';
            result.textContent = 'Na pista';
            entry.append(badge, result);
            standings.append(entry);
            entries.set(id, result);
        }

        function showStatus() {
            if (remaining === 0) {
                status.textContent = 'Disputa encerrada';
            } else if (remaining === 1) {
                status.textContent = '1 Dino na pista';
            } else {
                status.textContent = `${remaining} Dinos na pista`;
            }
        }

        const formatScore = new Intl.NumberFormat('pt-BR');
        showStatus();
        new Runner('.interstitial-wrapper', undefined, {
            competitors,
            timeLimitMs: round.timeLimitMs,
            onResult({ id, score, outcome }) {
                const result = entries.get(id);
                const label = outcome === 'collision' ? 'Eliminado' : 'Tempo limite';
                result.textContent = `${label} · ${formatScore.format(score)} pts`;
                if (outcome === 'collision') {
                    result.parentElement.classList.add('eliminated');
                }
                remaining--;
                showStatus();
                console.info(`Dino ${id} · Pontuação final:`, score);
            },
            onFinish(results) {
                if (round.id !== null) void sendResults(round.id, results);
            }
        });
    }

    getRound().then(startRound).catch(error => {
        status.textContent = 'Falha ao carregar a rodada.';
        console.error(error);
    });
})();
