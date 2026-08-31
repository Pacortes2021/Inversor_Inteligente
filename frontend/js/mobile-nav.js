/**
 * Mobile Navigation — Hamburger Menu
 * Módulo ES6: los handlers se registran al importarse (desde init.js).
 */

import { go } from "./router.js?v=80";

const hamburger = document.getElementById('hamburger-btn');
const mobileNav = document.getElementById('mobile-nav');
const closeBtn = document.getElementById('mobile-nav-close');
const mobileSearch = document.getElementById('mobile-search-input');
const navLinks = mobileNav ? mobileNav.querySelectorAll('.mobile-nav-link') : [];

if (hamburger && mobileNav) {
  function openMenu() {
    mobileNav.classList.add('open');
    hamburger.classList.add('open');
    hamburger.setAttribute('aria-expanded', 'true');
    document.body.style.overflow = 'hidden';
    if (mobileSearch) mobileSearch.focus();
  }

  function closeMenu() {
    mobileNav.classList.remove('open');
    hamburger.classList.remove('open');
    hamburger.setAttribute('aria-expanded', 'false');
    document.body.style.overflow = '';
    hamburger.focus();
  }

  function toggleMenu() {
    if (mobileNav.classList.contains('open')) closeMenu();
    else openMenu();
  }

  hamburger.addEventListener('click', toggleMenu);
  if (closeBtn) closeBtn.addEventListener('click', closeMenu);
  navLinks.forEach(link => link.addEventListener('click', closeMenu));

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && mobileNav.classList.contains('open')) closeMenu();
  });

  mobileNav.addEventListener('click', e => {
    if (e.target === mobileNav) closeMenu();
  });

  if (mobileSearch) {
    mobileSearch.addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        const val = mobileSearch.value.trim();
        if (val) {
          closeMenu();
          go(val);
        }
      }
    });
  }

  function syncActiveLink() {
    const hash = window.location.hash || '#/analisis';
    navLinks.forEach(link => {
      link.classList.toggle('active', link.getAttribute('href') === hash);
    });
  }

  window.addEventListener('hashchange', syncActiveLink);
  syncActiveLink();

  window.addEventListener('resize', () => {
    if (window.innerWidth > 768 && mobileNav.classList.contains('open')) closeMenu();
  });
}
