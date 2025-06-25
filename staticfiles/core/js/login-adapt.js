(function(){
  function adaptForm() {
    const container = document.querySelector('.login-container');
    const form      = document.querySelector('.login-form');
    if (!container || !form) return;

    const style = window.getComputedStyle(container);
    const padTop    = parseFloat(style.paddingTop);
    const padBottom = parseFloat(style.paddingBottom);
    const availH = container.clientHeight - padTop - padBottom;
    
    const formH = form.scrollHeight;
    if (formH > availH) {
      const scale = availH / formH;
      form.style.transform = `scale(${scale})`;
    } else {
      form.style.transform = '';
    }
  }

  window.addEventListener('load', adaptForm);
  window.addEventListener('resize', adaptForm);
  document.addEventListener('DOMContentLoaded', function(){
    setTimeout(adaptForm, 100);
  });
})();
