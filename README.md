# Dino Genetic

O objetivo do projeto é treinar uma IA para jogar o Dino do Chrome usando um algoritmo genético. A cada geração, as estratégias com melhor pontuação servem de base para a próxima.

## Rodar a disputa

Na pasta do projeto, execute `python server.py` e abra [a corrida no navegador](http://127.0.0.1:8000). Cada pista dura até 30 segundos de simulação. O Python registra no terminal a semente e a pontuação de cada Dino.

A pista sorteia trechos mais espaçados e trechos com grupos de cactos maiores e mais próximos. Cada grupo tem uma janela de pelo menos três quadros para iniciar um pulo que o ultrapasse.

- **Sortear nova pista** inicia uma corrida com outra semente.
- **Repetir** carrega a mesma semente ou repete a lista de sementes da avaliação.
- **Avaliar em 3 pistas** roda três pistas em sequência com os mesmos Dinos e mostra a média de cada um no navegador e no terminal. Para escolher as sementes, abra [uma avaliação com sementes fixas](http://127.0.0.1:8000/?sementes=101,202,303).

## Créditos e licença

O jogo é baseado no [t-rex-runner de wayou](https://github.com/wayou/t-rex-runner), extraído do Chromium. [Licença deste repositório](LICENSE) · [Licença do Chromium](https://raw.githubusercontent.com/chromium/chromium/55.0.2883.87/LICENSE)
