(function () {
    'use strict';

    const previewCompetitors = [
        { id: 1, a: 8, b: 8 }, { id: 2, a: 16, b: 4 },
        { id: 3, a: 14, b: 9 }, { id: 4, a: 3, b: 4 }
    ];
    const colors = [
        '#1d4ed8', '#b91c1c', '#047857', '#7e22ce', '#a16207', '#0e7490',
        '#c2410c', '#4d7c0f', '#be185d', '#4338ca', '#0f766e', '#7e5b3a'
    ];
    const resultLabels = {
        collision: 'Eliminado', winner: 'Venceu', tie: 'Empate',
        time_limit: 'Tempo limite', score_limit: 'Meta atingida'
    };
    const status = document.getElementById('autoplay-status');
    const standings = document.getElementById('race-standings');
    const seedLink = document.getElementById('race-seed');
    const evaluateLink = document.getElementById('race-evaluate');
    const trainLink = document.getElementById('race-train');
    const validateLink = document.getElementById('race-validate');
    const startButton = document.getElementById('race-start');
    const tieButton = document.getElementById('race-tie');
    const fastControl = document.getElementById('race-fast');
    const fastToggle = document.getElementById('fast-training');
    const progress = document.getElementById('training-progress');
    const trackResults = document.getElementById('track-results');
    const trackScoreTable = document.getElementById('track-score-table');
    const formatScore = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 });
    const params = new URLSearchParams(location.search);
    const trainingMode = params.get('treino') === '1';
    const validationMode = params.get('validacao') === '1';
    let startMode = trainingMode ? 'treino' : validationMode ? 'validacao' : 'rodada';
    let runner;

    tieButton.addEventListener('click', () => runner?.endTiedRace());
    fastToggle.addEventListener('change', () => runner?.setFastMode(fastToggle.checked));

    function getPreviewRound() {
        const requested = params.get('sementes');
        const seed = requested === null ? Math.floor(Math.random() * 2 ** 32) : Number(requested);
        if (!Number.isInteger(seed) || seed < 0 || seed >= 2 ** 32 || requested?.trim() === '') {
            throw new Error('Informe uma semente inteira entre 0 e 4294967295.');
        }
        return { id: null, competitors: previewCompetitors, seeds: [seed] };
    }

    async function getRound(mode) {
        if (location.protocol === 'file:') {
            if (mode !== 'rodada') throw new Error('Abra a página pelo servidor Python.');
            return getPreviewRound();
        }

        const query = mode === 'validacao' ? '' : location.search;
        const response = await fetch('./' + mode + query, { cache: 'no-store' });
        if (response.status === 404) {
            if (mode !== 'rodada') throw new Error('Abra a página pelo servidor Python.');
            return getPreviewRound();
        }
        if (!response.ok) {
            const { error } = await response.json().catch(() => ({}));
            throw new Error(error || ('HTTP ' + response.status));
        }
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

    function formatGenes({ a, b, c = 0 }) {
        return `a = ${formatScore.format(a)} · b = ${formatScore.format(b)} · c = ${formatScore.format(c)}`;
    }

    function recordTrack({ training, competitors, index, seed, results }) {
        if (trackResults.hidden) {
            const headers = [
                ...(training ? ['Geração'] : []), 'Pista', 'Semente',
                ...competitors.map(({ id, label }) => label || `Dino ${id}`)
            ];
            const header = trackScoreTable.createTHead().insertRow();
            for (const label of headers) {
                const cell = document.createElement('th');
                cell.scope = 'col';
                cell.textContent = label;
                header.append(cell);
            }
            trackScoreTable.createTBody();
            trackResults.hidden = false;
        }

        const row = trackScoreTable.tBodies[0].insertRow();
        const columns = [
            ...(training ? [training.generation] : []), index + 1, seed,
            ...results.map(({ score }) => formatScore.format(score))
        ];
        for (const value of columns) row.insertCell().textContent = value;
    }

    function createStandings(competitors) {
        const entries = new Map();
        standings.replaceChildren();
        for (const competitor of competitors) {
            const { id, color, label } = competitor;
            const entry = document.createElement('li');
            const badge = document.createElement('span');
            badge.className = 'race-badge';
            badge.style.backgroundColor = color;
            badge.textContent = id;
            badge.setAttribute('aria-label', `Dino ${id}`);
            entry.title = formatGenes(competitor);

            const content = document.createElement('div');
            if (label) {
                const name = document.createElement('strong');
                name.className = 'race-entry-name';
                name.textContent = label;
                content.append(name);
            }
            const result = document.createElement('span');
            result.className = 'race-result';
            content.append(result);
            entry.append(badge, content);
            standings.append(entry);
            entries.set(id, { entry, result });
        }
        return entries;
    }

    async function runTracks(evaluation) {
        const competitors = evaluation.competitors.map(({ id, a, b, c = 0, label }, index) => ({
            id, a, b, c, label,
            color: colors[index] ?? `hsl(${index * 137.5 % 360} 68% 36%)`,
            shouldJump(distance, speed, onGround, obstacleWidth = 25) {
                return onGround && distance <= a + b * speed + c * (obstacleWidth - 25);
            }
        }));
        const entries = createStandings(competitors);
        const { training, validation, seeds } = evaluation;
        const generationLabel = training ? `Geração ${training.generation}/${training.generations} · ` :
            validation ? 'Validação · ' : '';
        const replay = training || validation ? '' : ' · Repetir';
        if (training || validation) {
            seedLink.removeAttribute('href');
        } else {
            seedLink.href = '?sementes=' + seeds.join(',');
            seedLink.title = seeds.length === 1 ? 'Repetir esta pista' : 'Repetir esta avaliação';
        }
        seedLink.hidden = false;

        let response = null;
        for (const [index, seed] of seeds.entries()) {
            seedLink.textContent = seeds.length === 1 ? `Semente ${seed}${replay}` :
                `Pista ${index + 1}/${seeds.length} · semente ${seed}${replay}`;
            for (const { entry, result } of entries.values()) {
                result.textContent = 'Na pista';
                entry.classList.remove('eliminated');
            }

            let remaining = competitors.length;
            function showRaceStatus() {
                tieButton.hidden = !training || remaining < 2;
                const raceStatus = remaining === 0 ? 'Disputa encerrada' :
                    remaining === 1 ? '1 Dino na pista' : `${remaining} Dinos na pista`;
                status.textContent = generationLabel + raceStatus;
            }
            showRaceStatus();

            const results = await new Promise(resolve => {
                const race = {
                    competitors, seed,
                    timeLimitMs: evaluation.timeLimitMs ?? Infinity,
                    scoreLimit: training?.scoreLimit ?? validation?.scoreLimit,
                    stopAtLast: Boolean(training),
                    continueInBackground: true,
                    fastMode: Boolean(training && fastToggle.checked),
                    onResult({ id, score, outcome }) {
                        const { entry, result } = entries.get(id);
                        result.textContent = `${resultLabels[outcome]} · ${formatScore.format(score)} pts`;
                        if (outcome === 'collision') entry.classList.add('eliminated');
                        remaining--;
                        showRaceStatus();
                        console.info(`Dino ${id} · Pontuação final:`, score);
                    },
                    onFinish: resolve
                };
                if (runner) runner.startRace(race);
                else runner = new Runner('.interstitial-wrapper', undefined, race);
            });

            if (evaluation.id === null) return null;
            response = await sendResults(evaluation.id, seed, results);
            if (!response) return null;
            if (training || validation) recordTrack({ training, competitors, index, seed, results });
        }

        if (seeds.length > 1) {
            for (const { id, average, worst, reachedGoal } of response.averages) {
                const { entry, result } = entries.get(id);
                const mean = `Média · ${formatScore.format(average)} pts`;
                result.textContent = validation ?
                    `${mean} · Pior: ${formatScore.format(worst)} pts · Meta em ${reachedGoal}/${seeds.length} pistas` : mean;
                entry.classList.remove('eliminated');
            }
            const label = validation ? 'Validação' : 'Avaliação';
            status.textContent = `${label} concluída · ${seeds.length} pistas`;
        } else {
            status.textContent = 'Disputa encerrada. O Python recebeu os resultados.';
        }
        return response;
    }

    async function runEvaluation(evaluation) {
        trackResults.hidden = true;
        trackResults.open = false;
        trackScoreTable.replaceChildren();
        evaluateLink.hidden = trainLink.hidden = evaluation.id === null;
        validateLink.hidden = evaluation.id === null || Boolean(evaluation.training);
        progress.hidden = !evaluation.training;
        fastControl.hidden = !evaluation.training;
        if (evaluation.training) {
            progress.textContent = `Semente do treino ${evaluation.training.seed} · meta por pista ${formatScore.format(evaluation.training.scoreLimit)} pts`;
        }

        while (evaluation) {
            const response = await runTracks(evaluation);
            const report = response?.training;
            if (report) {
                progress.textContent = `Geração ${report.generation} · melhor ${formatScore.format(report.best)} pts` +
                    ` · mediana ${formatScore.format(report.median)} pts · semente do treino ${report.seed}`;
                if (report.complete) {
                    fastControl.hidden = true;
                    const genes = formatGenes(report.champion);
                    const saved = report.saved ? 'Campeão salvo para validação.' : 'Falha ao salvar best.json.';
                    status.textContent = `Treino concluído · ${genes}. ${saved}`;
                    if (report.saved) {
                        startMode = 'validacao';
                        startButton.textContent = 'Começar validação';
                        startButton.hidden = false;
                    }
                }
            }
            evaluation = response?.nextRound;
        }
    }

    evaluateLink.hidden = trainLink.hidden = location.protocol === 'file:';
    validateLink.hidden = location.protocol === 'file:' || trainingMode;
    fastControl.hidden = location.protocol === 'file:' || !trainingMode;

    async function startRun() {
        startButton.disabled = true;
        status.textContent = 'Preparando a disputa…';
        try {
            const evaluation = await getRound(startMode);
            startButton.hidden = true;
            await runEvaluation(evaluation);
        } catch (error) {
            status.textContent = error.message || 'Falha ao carregar ou executar a rodada.';
            console.error(error);
        } finally {
            startButton.disabled = false;
        }
    }

    startButton.addEventListener('click', startRun);
    if (startMode === 'rodada') {
        void startRun();
    } else {
        status.textContent = trainingMode ? 'Treino pronto para começar' : 'Validação pronta para começar';
        startButton.textContent = trainingMode ? 'Começar treino' : 'Começar validação';
        startButton.hidden = false;
    }
})();
