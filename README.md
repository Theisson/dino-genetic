# Dino Genetic

O objetivo do projeto é treinar uma IA para jogar o Dino do Chrome usando um algoritmo genético. A cada geração, as estratégias com melhor pontuação servem de base para a próxima.

## Rodar a disputa

Na pasta do projeto, execute `python server.py` e abra [a corrida no navegador](http://127.0.0.1:8000). O Python registra no terminal a semente e a pontuação de cada Dino.

Corridas, treinos e validações continuam em segundo plano enquanto o navegador mantém a aba em execução.

A pista sorteia trechos mais espaçados e trechos com grupos de cactos maiores e mais próximos. Cada grupo tem uma janela de pelo menos três quadros para iniciar um pulo que o ultrapasse.

- **Sortear nova pista** inicia uma corrida com outra semente.
- **Repetir** carrega a mesma semente ou repete a lista de sementes da avaliação.
- **Avaliar em 3 pistas** roda três pistas em sequência com os mesmos Dinos e mostra a média de cada um no navegador e no terminal. Para escolher as sementes, abra [uma avaliação com sementes fixas](http://127.0.0.1:8000/?sementes=101,202,303).

## Treinar a população

Abra **Treino** e clique em **Começar treino** uma vez. As gerações avançam automaticamente. Cada execução sorteia três parâmetros para os 12 Dinos. A regra de pulo usa a distância `a + b × velocidade + c × (largura − 25)`. O gene `c` ajusta o momento do pulo ao tamanho do grupo de cactos. O treino padrão tem dez gerações, com duas pistas de referência e uma pista nova por geração. A pontuação média é usada na roleta, e o melhor Dino de cada geração é preservado por elitismo.

Marque **Treino rápido** antes ou durante a corrida para simular em lotes e atualizar a tela com menos quadros. Desmarque para voltar a assistir em velocidade normal.

Cada pista de treino termina quando sobra um Dino ou quando a corrida chega a **5.000 pontos**. Na meta, todos os sobreviventes recebem 5.000 pontos. **Registrar empate e avançar** encerra a pista na pontuação atual.

A semente do treino aparece na página e no terminal. Para repetir o sorteio inicial, use um endereço como [treino com semente 42](http://127.0.0.1:8000/?treino=1&sementetreino=42). Para alterar o tamanho da população e o número de gerações, use `python server.py --populacao 12 --geracoes 10`.

## Validar o campeão

Ao concluir o treino, o Python salva os parâmetros do melhor Dino e as sementes usadas em `best.json`. O resultado fica na tela com o botão **Começar validação**. Você também pode abrir **Validação** mais tarde.

O Dino salvo e as regras fixas `8, 8` e `14, 9` correm nas mesmas cinco pistas sorteadas fora do treino. Cada um pode correr até colidir ou atingir 5.000 pontos, inclusive quando fica sozinho. A média, a pior pontuação e o número de pistas em que cada um chegou à meta aparecem no navegador e no terminal. **Resultados por semente** mostra os placares individuais na validação e guarda, na página do treino, os resultados de cada geração.

## Créditos e licença

O jogo é baseado no [t-rex-runner de wayou](https://github.com/wayou/t-rex-runner), extraído do Chromium. [Licença deste repositório](LICENSE) · [Licença do Chromium](https://raw.githubusercontent.com/chromium/chromium/55.0.2883.87/LICENSE)
