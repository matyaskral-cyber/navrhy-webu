/**
 * MARBOTIM s.r.o. — Main JavaScript
 * Pure vanilla JS, no dependencies, no inline handlers, no eval()
 */

'use strict';

/* ============================================================
   UTILITY HELPERS
   ============================================================ */

/**
 * Query selector shorthand
 * @param {string} selector
 * @param {Element} [ctx=document]
 * @returns {Element|null}
 */
const $ = (selector, ctx = document) => ctx.querySelector(selector);

/**
 * Query selector all shorthand
 * @param {string} selector
 * @param {Element} [ctx=document]
 * @returns {NodeList}
 */
const $$ = (selector, ctx = document) => ctx.querySelectorAll(selector);

/**
 * Throttle a function call
 * @param {Function} fn
 * @param {number} limit ms
 * @returns {Function}
 */
function throttle(fn, limit) {
  let inThrottle = false;
  return function (...args) {
    if (!inThrottle) {
      fn.apply(this, args);
      inThrottle = true;
      setTimeout(() => { inThrottle = false; }, limit);
    }
  };
}

/**
 * Clamp a number between min and max
 */
const clamp = (val, min, max) => Math.min(Math.max(val, min), max);

/* ============================================================
   MODULE: HEADER — scroll behaviour & sticky
   ============================================================ */
function initHeader() {
  const header = $('#header');
  if (!header) return;

  const SCROLL_THRESHOLD = 60;

  function updateHeader() {
    if (window.scrollY > SCROLL_THRESHOLD) {
      header.classList.add('header--scrolled');
    } else {
      header.classList.remove('header--scrolled');
    }
  }

  window.addEventListener('scroll', throttle(updateHeader, 100), { passive: true });
  updateHeader(); // run once on load
}

/* ============================================================
   MODULE: MOBILE NAVIGATION
   ============================================================ */
function initMobileNav() {
  const hamburger = $('#hamburger');
  const navMenu   = $('#nav-menu');
  if (!hamburger || !navMenu) return;

  let isOpen = false;
  let overlay = null;

  function openMenu() {
    isOpen = true;
    navMenu.classList.add('is-open');
    hamburger.setAttribute('aria-expanded', 'true');
    document.body.style.overflow = 'hidden';

    // Create overlay
    overlay = document.createElement('div');
    overlay.style.cssText = `
      position: fixed; inset: 0;
      background: rgba(0,0,0,0.5);
      z-index: 98;
      backdrop-filter: blur(2px);
    `;
    overlay.setAttribute('aria-hidden', 'true');
    document.body.appendChild(overlay);
    overlay.addEventListener('click', closeMenu);
  }

  function closeMenu() {
    isOpen = false;
    navMenu.classList.remove('is-open');
    hamburger.setAttribute('aria-expanded', 'false');
    document.body.style.overflow = '';

    if (overlay) {
      overlay.remove();
      overlay = null;
    }
  }

  hamburger.addEventListener('click', () => {
    if (isOpen) { closeMenu(); } else { openMenu(); }
  });

  // Close on nav link click
  $$('.nav__link', navMenu).forEach(link => {
    link.addEventListener('click', closeMenu);
  });

  // Close on Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && isOpen) {
      closeMenu();
      hamburger.focus();
    }
  });

  // Close on resize to desktop
  window.addEventListener('resize', throttle(() => {
    if (window.innerWidth > 768 && isOpen) {
      closeMenu();
    }
  }, 200));
}

/* ============================================================
   MODULE: SCROLL ANIMATIONS (IntersectionObserver)
   ============================================================ */
function initScrollAnimations() {
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (prefersReducedMotion) {
    // Make all animated elements visible immediately
    $$('[data-animate]').forEach(el => el.classList.add('is-visible'));
    return;
  }

  const options = {
    root: null,
    rootMargin: '0px 0px -80px 0px',
    threshold: 0.08,
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;

      const el = entry.target;
      const delay = parseInt(el.dataset.delay || '0', 10);

      setTimeout(() => {
        el.classList.add('is-visible');
      }, delay);

      observer.unobserve(el);
    });
  }, options);

  $$('[data-animate]').forEach(el => observer.observe(el));
}

/* ============================================================
   MODULE: COUNTER ANIMATION (hero stats)
   ============================================================ */
function initCounters() {
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const counters = $$('[data-count]');
  if (!counters.length) return;

  const DURATION = 2000; // ms
  const easeOut = (t) => 1 - Math.pow(1 - t, 3); // cubic ease-out

  function animateCounter(el) {
    const target = parseInt(el.dataset.count, 10);
    if (isNaN(target)) return;

    if (prefersReducedMotion) {
      el.textContent = target;
      return;
    }

    const startTime = performance.now();

    function tick(currentTime) {
      const elapsed = currentTime - startTime;
      const progress = clamp(elapsed / DURATION, 0, 1);
      const easedProgress = easeOut(progress);
      const current = Math.round(easedProgress * target);

      el.textContent = current;

      if (progress < 1) {
        requestAnimationFrame(tick);
      } else {
        el.textContent = target;
      }
    }

    requestAnimationFrame(tick);
  }

  const statsSection = $('.hero__stats');
  if (!statsSection) return;

  let hasRun = false;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting && !hasRun) {
        hasRun = true;
        counters.forEach(counter => animateCounter(counter));
        observer.disconnect();
      }
    });
  }, { threshold: 0.5 });

  observer.observe(statsSection);
}

/* ============================================================
   MODULE: SMOOTH ACTIVE NAV LINK (highlight on scroll)
   ============================================================ */
function initActiveNavLink() {
  const sections = $$('section[id]');
  const navLinks = $$('.nav__link:not(.nav__link--cta)');
  if (!sections.length || !navLinks.length) return;

  const HEADER_OFFSET = 90;

  function updateActiveLink() {
    let currentId = '';
    const scrollY = window.scrollY + HEADER_OFFSET;

    sections.forEach(section => {
      const sectionTop = section.offsetTop;
      const sectionHeight = section.offsetHeight;
      if (scrollY >= sectionTop && scrollY < sectionTop + sectionHeight) {
        currentId = section.id;
      }
    });

    navLinks.forEach(link => {
      const href = link.getAttribute('href');
      if (href === `#${currentId}`) {
        link.style.color = 'rgba(255,255,255,1)';
        link.style.background = 'rgba(255,255,255,0.1)';
      } else {
        link.style.color = '';
        link.style.background = '';
      }
    });
  }

  window.addEventListener('scroll', throttle(updateActiveLink, 150), { passive: true });
  updateActiveLink();
}

/* ============================================================
   MODULE: SMOOTH SCROLL (for anchor links)
   ============================================================ */
function initSmoothScroll() {
  const HEADER_OFFSET = 70;

  document.addEventListener('click', (e) => {
    const link = e.target.closest('a[href^="#"]');
    if (!link) return;

    const targetId = link.getAttribute('href').slice(1);
    if (!targetId) return;

    const targetEl = document.getElementById(targetId);
    if (!targetEl) return;

    e.preventDefault();

    const top = targetEl.getBoundingClientRect().top + window.scrollY - HEADER_OFFSET;

    window.scrollTo({ top, behavior: 'smooth' });

    // Update URL without reload
    history.pushState(null, '', `#${targetId}`);
  });
}

/* ============================================================
   MODULE: CONTACT FORM VALIDATION & SUBMIT
   ============================================================ */
function initContactForm() {
  const form = $('#contact-form');
  if (!form) return;

  const successPanel = $('#form-success');

  // Validation rules
  const validators = {
    name: {
      required: true,
      minLength: 2,
      errorId: 'name-error',
      messages: {
        required: 'Vyplňte prosím své jméno.',
        minLength: 'Jméno musí mít alespoň 2 znaky.',
      },
    },
    phone: {
      required: true,
      pattern: /^[+\d\s\-()]{7,20}$/,
      errorId: 'phone-error',
      messages: {
        required: 'Vyplňte prosím telefonní číslo.',
        pattern: 'Zadejte platné telefonní číslo.',
      },
    },
    email: {
      required: true,
      pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
      errorId: 'email-error',
      messages: {
        required: 'Vyplňte prosím e-mailovou adresu.',
        pattern: 'Zadejte platnou e-mailovou adresu.',
      },
    },
    gdpr: {
      required: true,
      errorId: 'gdpr-error',
      messages: {
        required: 'Pro odeslání poptávky je nutný váš souhlas.',
      },
    },
  };

  /**
   * Validate a single field
   * @param {HTMLElement} field
   * @param {Object} rules
   * @returns {string} error message or empty string
   */
  function validateField(field, rules) {
    const value = field.type === 'checkbox' ? field.checked : field.value.trim();

    if (rules.required && !value) {
      return rules.messages.required;
    }

    if (rules.minLength && typeof value === 'string' && value.length < rules.minLength) {
      return rules.messages.minLength;
    }

    if (rules.pattern && typeof value === 'string' && value && !rules.pattern.test(value)) {
      return rules.messages.pattern;
    }

    return '';
  }

  /**
   * Show or clear field error
   * @param {HTMLElement} field
   * @param {string} errorId
   * @param {string} message
   */
  function setFieldError(field, errorId, message) {
    const errorEl = document.getElementById(errorId);
    if (!errorEl) return;

    if (message) {
      errorEl.textContent = message;
      field.classList.add('is-invalid');
      field.setAttribute('aria-describedby', errorId);
      field.setAttribute('aria-invalid', 'true');
    } else {
      errorEl.textContent = '';
      field.classList.remove('is-invalid');
      field.removeAttribute('aria-describedby');
      field.removeAttribute('aria-invalid');
    }
  }

  // Live validation on blur
  Object.entries(validators).forEach(([fieldName, rules]) => {
    const field = form.elements[fieldName];
    if (!field) return;

    field.addEventListener('blur', () => {
      const error = validateField(field, rules);
      setFieldError(field, rules.errorId, error);
    });

    // Clear error on input/change
    const eventType = field.type === 'checkbox' ? 'change' : 'input';
    field.addEventListener(eventType, () => {
      if (field.classList.contains('is-invalid')) {
        const error = validateField(field, rules);
        setFieldError(field, rules.errorId, error);
      }
    });
  });

  // Form submit
  form.addEventListener('submit', (e) => {
    e.preventDefault();

    let isValid = true;
    const firstErrorField = null;

    // Validate all fields
    Object.entries(validators).forEach(([fieldName, rules]) => {
      const field = form.elements[fieldName];
      if (!field) return;

      const error = validateField(field, rules);
      setFieldError(field, rules.errorId, error);

      if (error) {
        isValid = false;
        if (!firstErrorField) {
          // Focus first invalid field for accessibility
          field.focus();
        }
      }
    });

    if (!isValid) return;

    // Build mailto URL
    const name    = form.elements['name'].value.trim();
    const phone   = form.elements['phone'].value.trim();
    const email   = form.elements['email'].value.trim();
    const service = form.elements['service'].value;
    const message = form.elements['message'].value.trim();

    const serviceLabels = {
      podlahove: 'Podlahové vytápění',
      ustredni:  'Ústřední topení',
      plyn:      'Plynový kotel',
      tc:        'Tepelné čerpadlo',
      kotelna:   'Rekonstrukce kotelny',
      biomasa:   'Biomasa / pelety',
      servis:    'Servis / oprava',
      jine:      'Jiné',
    };

    const serviceLabel = serviceLabels[service] || 'Neuvedeno';

    const subject = encodeURIComponent(`Poptávka: ${name} — ${serviceLabel}`);
    const body = encodeURIComponent(
      `Jméno: ${name}\nTelefon: ${phone}\nE-mail: ${email}\nSlužba: ${serviceLabel}\n\nZpráva:\n${message || '(nevyplněno)'}`
    );

    const mailtoLink = `mailto:info@marbotim.cz?subject=${subject}&body=${body}`;

    // Open mail client
    window.location.href = mailtoLink;

    // Show success state after brief delay
    setTimeout(() => {
      showSuccess();
    }, 400);
  });

  function showSuccess() {
    // Hide form fields, show success
    const formElements = form.querySelectorAll(
      '.form__row--two, .form__group, .form__note, button[type="submit"]'
    );

    formElements.forEach(el => {
      el.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
      el.style.opacity = '0';
      el.style.transform = 'translateY(-10px)';
      el.style.pointerEvents = 'none';
    });

    setTimeout(() => {
      formElements.forEach(el => { el.hidden = true; });
      if (successPanel) {
        successPanel.hidden = false;
        successPanel.focus();
      }
    }, 350);
  }
}

/* ============================================================
   MODULE: BACK TO TOP BUTTON
   ============================================================ */
function initBackToTop() {
  const btn = $('#back-to-top');
  if (!btn) return;

  const SHOW_THRESHOLD = 500;

  function updateVisibility() {
    if (window.scrollY > SHOW_THRESHOLD) {
      btn.hidden = false;
    } else {
      btn.hidden = true;
    }
  }

  btn.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  window.addEventListener('scroll', throttle(updateVisibility, 200), { passive: true });
  updateVisibility();
}

/* ============================================================
   MODULE: SET CURRENT YEAR IN FOOTER
   ============================================================ */
function initFooterYear() {
  const yearEl = $('#year');
  if (yearEl) {
    yearEl.textContent = new Date().getFullYear();
  }
}

/* ============================================================
   MODULE: CARD TILT EFFECT (subtle, desktop only)
   ============================================================ */
function initCardTilt() {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  if (window.matchMedia('(pointer: coarse)').matches) return; // skip touch devices

  const cards = $$('.service-card');

  cards.forEach(card => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const cx = rect.width / 2;
      const cy = rect.height / 2;

      const tiltX = clamp(((y - cy) / cy) * -5, -5, 5);
      const tiltY = clamp(((x - cx) / cx) * 5, -5, 5);

      card.style.transform = `translateY(-6px) perspective(600px) rotateX(${tiltX}deg) rotateY(${tiltY}deg)`;
    });

    card.addEventListener('mouseleave', () => {
      card.style.transform = '';
    });
  });
}

/* ============================================================
   MODULE: HERO PARALLAX (subtle)
   ============================================================ */
function initHeroParallax() {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  if (window.matchMedia('(pointer: coarse)').matches) return;

  const heroContent = $('.hero__content');
  const heroFlames  = $$('.hero__flame');
  if (!heroContent) return;

  window.addEventListener('scroll', throttle(() => {
    const scrollY = window.scrollY;
    if (scrollY > window.innerHeight) return; // only in hero

    const factor = scrollY * 0.25;
    heroContent.style.transform = `translateY(${factor}px)`;
    heroContent.style.opacity = `${1 - (scrollY / window.innerHeight) * 1.5}`;

    heroFlames.forEach((flame, i) => {
      const speed = 0.1 + i * 0.05;
      flame.style.transform = `translateY(${scrollY * speed}px)`;
    });
  }, 16), { passive: true });
}

/* ============================================================
   MODULE: SERVICE CARDS — staggered reveal
   ============================================================ */
function initServiceCardReveal() {
  // Additional micro interaction: highlight card number on hover
  const cards = $$('.service-card');

  cards.forEach((card, index) => {
    // Add subtle index indicator
    const num = document.createElement('span');
    num.textContent = String(index + 1).padStart(2, '0');
    num.style.cssText = `
      position: absolute;
      top: 1.5rem;
      right: 1.75rem;
      font-size: 0.65rem;
      font-weight: 800;
      letter-spacing: 0.1em;
      color: rgba(230,126,34,0.18);
      font-variant-numeric: tabular-nums;
      transition: color 0.25s ease;
      pointer-events: none;
      user-select: none;
    `;
    card.style.position = 'relative'; // ensure relative positioning
    card.appendChild(num);

    card.addEventListener('mouseenter', () => {
      num.style.color = 'rgba(230,126,34,0.45)';
    });

    card.addEventListener('mouseleave', () => {
      num.style.color = 'rgba(230,126,34,0.18)';
    });
  });
}

/* ============================================================
   MODULE: FOCUS VISIBLE (keyboard navigation enhancement)
   ============================================================ */
function initFocusVisible() {
  // Add focus-visible styles dynamically to supplement CSS
  const style = document.createElement('style');
  style.textContent = `
    :focus-visible {
      outline: 2px solid #c0392b !important;
      outline-offset: 3px !important;
    }
    :focus:not(:focus-visible) {
      outline: none;
    }
  `;
  document.head.appendChild(style);
}

/* ============================================================
   MODULE: INTERSECTION OBSERVER — nav mobile overlay z-fix
   ============================================================ */
function initNavOverlap() {
  // Ensure the overlay is removed if scrolled after menu is closed
  // This is a safety net for edge cases
  window.addEventListener('scroll', throttle(() => {
    const menu = $('#nav-menu');
    const hamburger = $('#hamburger');
    if (!menu || !hamburger) return;
    if (menu.classList.contains('is-open')) {
      // Don't auto-close on scroll — user might be scrolling within menu
    }
  }, 300), { passive: true });
}

/* ============================================================
   INIT — Run all modules on DOMContentLoaded
   ============================================================ */
function init() {
  initHeader();
  initMobileNav();
  initScrollAnimations();
  initCounters();
  initActiveNavLink();
  initSmoothScroll();
  initContactForm();
  initBackToTop();
  initFooterYear();
  initCardTilt();
  initHeroParallax();
  initServiceCardReveal();
  initFocusVisible();
  initNavOverlap();
}

// Run when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  // DOM already parsed (script deferred or at end of body)
  init();
}
