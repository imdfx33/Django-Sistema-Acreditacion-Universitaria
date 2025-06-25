// auth-extra.js
// ==========================================
// Efectos e interactividad para el login
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
  // 1) Toggle mostrar/ocultar contraseña
  const toggles = document.querySelectorAll('.toggle-password');
  toggles.forEach(btn => {
    btn.addEventListener('click', () => {
      const input = document.querySelector(btn.dataset.target);
      if (!input) return;
      if (input.type === 'password') {
        input.type = 'text';
        btn.classList.add('visible');
      } else {
        input.type = 'password';
        btn.classList.remove('visible');
      }
    });
  });

  // 2) Animación de fondo al mover el ratón
  const body = document.querySelector('.login-body');
  body.addEventListener('mousemove', e => {
    const x = (e.clientX / window.innerWidth  - 0.5) * 20;
    const y = (e.clientY / window.innerHeight - 0.5) * 20;
    body.style.transform = `rotateX(${y}deg) rotateY(${x}deg)`;
  });
  body.addEventListener('mouseleave', () => {
    body.style.transform = '';
  });

  // 3) Transición suave al enviar formularios
  const forms = document.querySelectorAll('.login-container form');
  forms.forEach(f => {
    f.addEventListener('submit', () => {
      document.querySelector('.login-container').style.opacity = '0.6';
    });
  });
});
