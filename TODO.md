# TODO do Dino Genetic

A primeira versão vai evoluir uma regra de pulo para desviar dos cactos. O jogo roda em JavaScript, e o algoritmo genético roda em Python.

**A disputa na tela é parte central do projeto.** Durante o treino, vários Dinos da mesma geração devem aparecer juntos no navegador, enfrentando os mesmos cactos ao mesmo tempo. Cada Dino usa seus próprios valores de `a` e `b` e tem sua própria pontuação.

- [x] **Fazer o Dino jogar uma partida sozinho.** No JavaScript, ler a distância até o próximo obstáculo, a velocidade e se o Dino está no chão. Usar um par fixo de valores `a` e `b` na regra `distância de pulo = a + b * velocidade` e registrar a pontuação ao fim da partida.
- [x] **Mostrar vários Dinos disputando a mesma pista.** Usar pares de valores diferentes e identificar os Dinos na tela. Confirmar que, quando um colide, sua pontuação é registrada e os outros continuam correndo.
- [x] **Conectar Python e JavaScript via HTTP com JSON.** Enviar a população do Python para o jogo e receber a pontuação de cada Dino ao fim de uma rodada automática.
- [x] **Preparar avaliações repetíveis.** Sortear uma semente nova nas corridas livres e usar um passo fixo na física para reproduzir uma pista a partir da semente. Em cada avaliação, usar as mesmas sementes para todos os Dinos e calcular a média das pontuações de cada um em várias pistas. Confirmar que repetir os mesmos valores de `a` e `b` na mesma pista produz a mesma pontuação.
- [x] **Calibrar a dificuldade da pista antes do treino.** Sortear trechos normais e desafiadores, variando tamanhos e espaçamentos dos grupos de cactos. Validar uma janela de três quadros para iniciar cada pulo com a física e as colisões do jogo. Comparar a dificuldade anterior com a calibrada usando o controlador fixo `a = 8`, `b = 8`.
- [ ] **Implementar o algoritmo genético clássico e acompanhar o treino.** Gerar uma população inicial aleatória em Python, avaliar em pistas variadas, selecionar os pais por roleta proporcional à pontuação média e gerar os filhos por cruzamento e mutação. Repetir até o critério de parada definido para o treino. Mostrar a geração atual e quantos Dinos ainda estão na pista. Registrar a melhor pontuação e a mediana de cada geração.
- [ ] **Validar o melhor Dino em pistas novas.** Sortear e registrar várias sementes que ficaram fora do treino. Comparar a pontuação média do Dino treinado com a do controlador fixo `a = 8`, `b = 8`, usando as mesmas pistas para os dois. Salvar o melhor par em JSON.
