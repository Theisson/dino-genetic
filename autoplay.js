(function () {
    'use strict';

    const competitors = [
        { id: 1, a: 8, b: 8, color: '#1d4ed8' },
        { id: 2, a: 16, b: 4, color: '#b91c1c' },
        { id: 3, a: 14, b: 9, color: '#047857' },
        { id: 4, a: 3, b: 4, color: '#7e22ce' }
    ].map(({ id, a, b, color }) => ({
        id,
        color,
        shouldJump(distance, speed, onGround) {
            return onGround && distance <= a + b * speed;
        }
    }));
    const status = document.getElementById('autoplay-status');
    const standings = document.getElementById('race-standings');
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

    showStatus();
    const formatScore = new Intl.NumberFormat('pt-BR');
    new Runner('.interstitial-wrapper', undefined, {
        competitors,
        onElimination(id, score) {
            const result = entries.get(id);
            result.textContent = `Eliminado · ${formatScore.format(score)} pts`;
            result.parentElement.classList.add('eliminated');
            remaining--;
            showStatus();
            console.info(`Dino ${id} · Pontuação final:`, score);
        }
    });
})();
