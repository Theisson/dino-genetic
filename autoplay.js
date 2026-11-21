(function () {
    'use strict';

    const a = 8;
    const b = 8;
    const status = document.getElementById('autoplay-status');

    new Runner('.interstitial-wrapper', undefined, {
        shouldJump(distance, speed, onGround) {
            return onGround && distance <= a + b * speed;
        },

        onFinish(score) {
            status.textContent = `Pontuação final: ${score}`;
            console.info('Pontuação final:', score);
        }
    });
})();
