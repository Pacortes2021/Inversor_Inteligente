/**
 * Mobile Navigation — Hamburger Menu
 * Archivo: frontend/js/mobile-nav.js
 * Agregar en index.html DESPUÉS de app.js:
 *   <script src="js/mobile-nav.js"></script>
 */

(function () {
  'use strict';

  const hamburger = document.getElementById('hamburger-btn');
  const mobileNav = document.getElementById('mobile-nav');
  const closeBtn = document.getElementById('mobile-nav-close');
  const mobileSearch = document.getElementById('mobile-search-input');
  const navLinks = mobileNav ? mobileNav.querySelectorAll('.mobile-nav-link') : [];

  if (!hamburger || !mobileNav) return;

  function openMenu() {
    mobileNav.classList.add('open');
    hamburger.classList.add('open');
    hamburger.setAttribute('aria-expanded', 'true');
    document.body.style.overflow = 'hidden';
    // Focus trap: enfocar el primer elemento
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
    if (mobileNav.classList.contains('open')) {
      closeMenu();
    } else {
      openMenu();
    }
  }

  // Toggle hamburger
  hamburger.addEventListener('click', toggleMenu);

  // Close button
  if (closeBtn) closeBtn.addEventListener('click', closeMenu);

  // Close on nav link click
  navLinks.forEach(function (link) {
    link.addEventListener('click', function () {
      closeMenu();
    });
  });

  // Close on Escape
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && mobileNav.classList.contains('open')) {
      closeMenu();
    }
  });

  // Close on overlay click (outside links)
  mobileNav.addEventListener('click', function (e) {
    if (e.target === mobileNav) {
      closeMenu();
    }
  });

  // Mobile search: sync with main search
  if (mobileSearch) {
    mobileSearch.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        var val = mobileSearch.value.trim();
        if (val) {
          // Navigate to analysis with this symbol
          closeMenu();
          if (typeof window.loadStock === 'function') {
            window.loadStock(val);
          } else {
            window.location.hash = '#/analisis';
            // Fallback: set hash and let app.js handle it
            setTimeout(function () {
              var searchInput = document.getElementById('search-input');
              if (searchInput) {
                searchInput.value = val;
                searchInput.dispatchEvent(new Event('input'));
              }
            }, 100);
          }
        }
      }
    });
  }

  // Sync active state: update mobile nav links based on current hash
  function syncActiveLink() {
    var hash = window.location.hash || '#/analisis';
    navLinks.forEach(function (link) {
      var href = link.getAttribute('href');
      if (href === hash) {
        link.classList.add('active');
      } else {
        link.classList.remove('active');
      }
    });
  }

  window.addEventListener('hashchange', syncActiveLink);
  syncActiveLink();

  // Responsive: close menu if window resizes above mobile breakpoint
  window.addEventListener('resize', function () {
    if (window.innerWidth > 768 && mobileNav.classList.contains('open')) {
      closeMenu();
    }
  });
})();
