# TODO do Dino Genetic

A primeira versão vai evoluir uma regra de pulo para desviar dos cactos. O jogo roda em JavaScript, e o algoritmo genético roda em Python.

**A disputa na tela é parte central do projeto.** Durante o treino, vários Dinos da mesma geração devem aparecer juntos no navegador, enfrentando os mesmos cactos ao mesmo tempo. Cada Dino usa seus próprios valores de `a` e `b` e tem sua própria pontuação.

- [x] **Fazer o Dino jogar uma partida sozinho.** No JavaScript, ler a distância até o próximo obstáculo, a velocidade e se o Dino está no chão. Usar um par fixo de valores `a` e `b` na regra `distância de pulo = a + b * velocidade` e registrar a pontuação ao fim da partida.
- [ ] **Mostrar vários Dinos disputando a mesma pista.** Usar pares de valores diferentes e identificar os Dinos na tela. Confirmar que, quando um colide, sua pontuação é registrada e os outros continuam correndo.
- [ ] **Conectar Python e JavaScript.** Enviar a população do Python para o jogo e receber em JSON a pontuação de cada Dino. Confirmar que uma rodada inteira roda automaticamente.
- [ ] **Preparar avaliações repetíveis.** Fazer cada candidato jogar com as mesmas sequências de cactos e calcular a média das pontuações. Confirmar que repetir um par de valores e uma sequência produz a mesma pontuação.
- [ ] **Calibrar a dificuldade da pista antes do treino.** Variar os tamanhos e os espaçamentos dos grupos de cactos. Usar a física e as colisões do jogo para validar que cada trecho admite uma sequência de pulos com alguma margem no tempo de reação. Medir a dificuldade com o controlador fixo `a = 8`, `b = 8`.
- [ ] **Evoluir a população e acompanhar o treino.** Gerar uma população inicial em Python, selecionar os melhores e criar novas gerações com cruzamento e mutação. Mostrar a geração atual e quantos Dinos ainda estão na pista. Registrar a melhor pontuação e a mediana de cada geração.
- [ ] **Testar o melhor candidato.** Comparar sua pontuação com a de uma regra que sempre pula à mesma distância, usando sequências que ficaram fora do treino. Salvar o melhor par em JSON.
