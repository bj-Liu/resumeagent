'use strict';
// Progressive enhancement only: every image, video and link works without JS.
document.documentElement.classList.add('js');
const menu = document.querySelector('.menu-toggle');
const navigation = document.getElementById('navigation');
menu.addEventListener('click', () => {
  const open = menu.getAttribute('aria-expanded') !== 'true';
  menu.setAttribute('aria-expanded', String(open));
  navigation.classList.toggle('is-open', open);
});
navigation.addEventListener('click', (event) => {
  if (event.target.closest('a')) {
    menu.setAttribute('aria-expanded', 'false');
    navigation.classList.remove('is-open');
  }
});
const viewer = document.getElementById('image-viewer');
const expanded = document.getElementById('expanded-image');
document.querySelectorAll('[data-zoom]').forEach((link) => {
  link.addEventListener('click', (event) => {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || typeof viewer.showModal !== 'function') return;
    event.preventDefault();
    const image = link.querySelector('img');
    expanded.src = link.href;
    expanded.alt = image ? image.alt : link.textContent.trim();
    document.getElementById('image-caption').textContent = expanded.alt;
    viewer.showModal();
  });
});
document.getElementById('close-image').addEventListener('click', () => viewer.close());
viewer.addEventListener('click', (event) => { if (event.target === viewer) viewer.close(); });