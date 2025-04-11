// Minimal fireworks effect

document.addEventListener('DOMContentLoaded', function() {
  const canvas = document.getElementById('fireworks-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  canvas.style.position = 'fixed';
  canvas.style.top = '0';
  canvas.style.left = '0';
  canvas.style.width = '100%';
  canvas.style.height = '100%';
  canvas.style.pointerEvents = 'none';
  canvas.style.zIndex = '9999';

  function resizeCanvas() {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
  }
  window.addEventListener('resize', resizeCanvas);
  resizeCanvas();

  let particles = [];

  function launchFireworks() {
      for(let i=0; i<30; i++) {
          particles.push({
              x: canvas.width/2,
              y: canvas.height/2,
              angle: Math.random() * 2 * Math.PI,
              speed: Math.random() * 5 + 2,
              radius: 2 + Math.random() * 2,
              alpha: 1,
              decay: 0.02 + Math.random() * 0.02,
              color: `hsl(${Math.random()*360},100%,70%)`
          });
      }
  }

  function animate() {
      ctx.clearRect(0,0,canvas.width,canvas.height);
      ctx.fillRect(0,0,canvas.width,canvas.height);

      particles.forEach((p, index) => {
          p.x += Math.cos(p.angle) * p.speed;
          p.y += Math.sin(p.angle) * p.speed;
          p.alpha -= p.decay;
          if(p.alpha <= 0) {
              particles.splice(index,1);
          } else {
              ctx.beginPath();
              ctx.arc(p.x, p.y, p.radius, 0, 2*Math.PI);
              ctx.fillStyle = `rgba(${hexToRgb(p.color)},${p.alpha})`;
              ctx.fill();
          }
      });

      requestAnimationFrame(animate);
  }

  function hexToRgb(h) {
      // convert hsl to rgb string
      const tmp = document.createElement('div');
      tmp.style.color = h;
      document.body.appendChild(tmp);
      const cs = getComputedStyle(tmp).color;
      document.body.removeChild(tmp);
      return cs.match(/\d+, \d+, \d+/)[0];
  }

  animate();

  window.launchFireworks = launchFireworks;
});
