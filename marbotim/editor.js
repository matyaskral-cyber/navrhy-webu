/**
 * MARBOTIM — Jednoduchý editor webu
 * Otevři/zavři:  Ctrl + E  (nebo přidej ?edit do URL)
 * Jak použít:   nastav hodnoty, klikni "Stáhnout CSS" a nahraď style.css na serveru
 */

(function () {
  'use strict';

  const STORAGE_KEY = 'marbotim_editor_vals';

  // ── Nastavení, která lze měnit ──────────────────────────────────────────────
  const controls = [
    {
      group: 'Písmo',
      items: [
        { label: 'Základní velikost textu', prop: '--editor-fs-base',   unit: 'px', min: 13,  max: 22,  step: 0.5, default: 16 },
        { label: 'Nadpis H1 (hero)',        prop: '--editor-fs-h1',     unit: 'rem', min: 2,  max: 6,   step: 0.1, default: 3.25 },
        { label: 'Nadpis H2 (sekce)',       prop: '--editor-fs-h2',     unit: 'rem', min: 1.5,max: 4,   step: 0.1, default: 2.5 },
        { label: 'Nadpis H3 (karty)',       prop: '--editor-fs-h3',     unit: 'rem', min: 1,  max: 2.5, step: 0.1, default: 1.25 },
        { label: 'Běžný text odstavce',     prop: '--editor-fs-body',   unit: 'rem', min: 0.8,max: 1.4, step: 0.05,default: 1 },
      ]
    },
    {
      group: 'Logo & navigace',
      items: [
        { label: 'Velikost loga',           prop: '--editor-logo-h',    unit: 'px',  min: 30, max: 200, step: 2,   default: 112 },
        { label: 'Výška navigace',          prop: '--editor-header-h',  unit: 'px',  min: 50, max: 160, step: 2,   default: 120 },
      ]
    },
    {
      group: 'Mezery',
      items: [
        { label: 'Odsazení sekcí',          prop: '--editor-section-py',unit: 'rem', min: 3,  max: 12,  step: 0.5, default: 6 },
      ]
    },
    {
      group: 'Barvy',
      items: [
        { label: 'Červená (vytápění)',  prop: '--editor-clr-accent', type: 'color', default: '#c0392b' },
        { label: 'Modrá (voda)',        prop: '--editor-clr-water',  type: 'color', default: '#1565c0' },
        { label: 'Tmavé pozadí',        prop: '--editor-clr-dark',   type: 'color', default: '#1a1a2e' },
      ]
    }
  ];

  // ── CSS přemostění (propojí editor proměnné na skutečné CSS vars) ───────────
  const BRIDGE_CSS = `
    :root {
      font-size: var(--editor-fs-base, 16px);
      --clr-accent:        var(--editor-clr-accent, #c0392b);
      --clr-water:         var(--editor-clr-water,  #1565c0);
      --clr-dark:          var(--editor-clr-dark,   #1a1a2e);
      --header-h:          var(--editor-header-h,   70px);
      --section-py:        var(--editor-section-py, 6rem);
    }
    .nav__logo-img { height: var(--editor-logo-h, 112px) !important; }
    h1, .hero__title { font-size: var(--editor-fs-h1, 3.25rem) !important; }
    h2, .section__title { font-size: var(--editor-fs-h2, 2.5rem) !important; }
    h3, .service-card__title, .why-card__title { font-size: var(--editor-fs-h3, 1.25rem) !important; }
    p, li, .about__desc, .service-card__desc, .why-card__desc { font-size: var(--editor-fs-body, 1rem) !important; }
  `;

  // ── Načtení uložených hodnot ────────────────────────────────────────────────
  function loadValues() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}; } catch { return {}; }
  }
  function saveValues(vals) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(vals));
  }

  // ── Aplikace hodnot na :root ────────────────────────────────────────────────
  let bridgeEl = null;
  function applyValues(vals) {
    const root = document.documentElement;
    controls.forEach(g => g.items.forEach(c => {
      const val = vals[c.prop] !== undefined ? vals[c.prop] : c.default;
      if (c.type === 'color') {
        root.style.setProperty(c.prop, val);
      } else {
        root.style.setProperty(c.prop, val + c.unit);
      }
    }));
  }

  // ── Panel HTML ──────────────────────────────────────────────────────────────
  function buildPanel() {
    const vals = loadValues();

    const overlay = document.createElement('div');
    overlay.id = 'siteEditor';
    overlay.style.cssText = `
      position:fixed; top:0; right:0; width:340px; height:100vh;
      background:#1a1a2e; color:#fff; z-index:99999;
      font-family:system-ui,sans-serif; font-size:13px;
      display:flex; flex-direction:column;
      box-shadow:-6px 0 32px rgba(0,0,0,0.5);
      transform:translateX(100%); transition:transform .3s ease;
    `;

    let html = `
      <div style="padding:16px 20px; background:#c0392b; display:flex; align-items:center; justify-content:space-between; flex-shrink:0">
        <span style="font-weight:700; font-size:15px; letter-spacing:.04em">✏️ Editor webu</span>
        <button id="editorClose" style="background:none;border:none;color:#fff;font-size:22px;cursor:pointer;line-height:1">×</button>
      </div>
      <div style="overflow-y:auto; flex:1; padding:16px 20px">
    `;

    controls.forEach(group => {
      html += `<div style="margin-bottom:20px">
        <div style="font-size:11px; font-weight:700; letter-spacing:.1em; color:#999; text-transform:uppercase; margin-bottom:10px">${group.group}</div>`;

      group.items.forEach(c => {
        const val = vals[c.prop] !== undefined ? vals[c.prop] : c.default;
        if (c.type === 'color') {
          html += `
            <div style="margin-bottom:12px">
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px">
                <label style="color:#ccc">${c.label}</label>
                <input type="color" data-prop="${c.prop}" value="${val}"
                  style="width:36px;height:24px;border:none;padding:0;cursor:pointer;background:none">
              </div>
            </div>`;
        } else {
          html += `
            <div style="margin-bottom:14px">
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px">
                <label style="color:#ccc">${c.label}</label>
                <span id="val-${c.prop.replace('--','')}${c.unit}" style="color:#fff;font-weight:600;min-width:55px;text-align:right">${val}${c.unit}</span>
              </div>
              <input type="range" data-prop="${c.prop}" data-unit="${c.unit}"
                min="${c.min}" max="${c.max}" step="${c.step}" value="${val}"
                style="width:100%;accent-color:#c0392b;cursor:pointer">
            </div>`;
        }
      });

      html += `</div>`;
    });

    html += `</div>
      <div style="padding:16px 20px; border-top:1px solid rgba(255,255,255,.1); display:flex;gap:8px;flex-shrink:0">
        <button id="editorReset" style="flex:1;padding:9px;background:rgba(255,255,255,.1);color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px">
          Resetovat
        </button>
        <button id="editorExport" style="flex:2;padding:9px;background:#c0392b;color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:700;font-size:13px">
          ⬇ Stáhnout CSS
        </button>
      </div>
    `;

    overlay.innerHTML = html;
    document.body.appendChild(overlay);

    // ── event listeners ───────────────────────────────────────────────────────
    overlay.querySelectorAll('input[data-prop]').forEach(input => {
      input.addEventListener('input', () => {
        const prop = input.dataset.prop;
        const unit = input.dataset.unit || '';
        const val = input.value;
        const vals = loadValues();
        vals[prop] = parseFloat(val) || val;
        saveValues(vals);
        applyValues(vals);
        const label = document.getElementById(`val-${prop.replace('--','')}${unit}`);
        if (label) label.textContent = val + unit;
      });
    });

    document.getElementById('editorClose').addEventListener('click', closePanel);

    document.getElementById('editorReset').addEventListener('click', () => {
      localStorage.removeItem(STORAGE_KEY);
      applyValues({});
      document.querySelectorAll('#siteEditor input[data-prop]').forEach(input => {
        const ctrl = controls.flatMap(g => g.items).find(c => c.prop === input.dataset.prop);
        if (ctrl) {
          input.value = ctrl.default;
          const unit = input.dataset.unit || '';
          const label = document.getElementById(`val-${ctrl.prop.replace('--','')}${unit}`);
          if (label) label.textContent = ctrl.default + unit;
        }
      });
    });

    document.getElementById('editorExport').addEventListener('click', exportCSS);

    return overlay;
  }

  // ── Export jako CSS soubor ──────────────────────────────────────────────────
  function exportCSS() {
    const vals = loadValues();
    const lines = [
      '/* ============================================================',
      '   MARBOTIM — Vlastní nastavení webu',
      '   Tento soubor je automaticky generovaný editorem.',
      '   Přidej ho do index.html PŘED style.css:',
      '   <link rel="stylesheet" href="theme-custom.css" />',
      '   ============================================================ */',
      '',
      ':root {'
    ];

    controls.forEach(g => g.items.forEach(c => {
      const val = vals[c.prop] !== undefined ? vals[c.prop] : c.default;
      const unit = c.unit || '';
      lines.push(`  ${c.prop}: ${val}${unit};  /* ${c.label} */`);
    }));

    lines.push('}', '', BRIDGE_CSS.trim());

    const blob = new Blob([lines.join('\n')], { type: 'text/css' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'theme-custom.css';
    a.click();
    URL.revokeObjectURL(a.href);
  }

  // ── Otevřít / Zavřít ────────────────────────────────────────────────────────
  let panel = null;
  let isOpen = false;

  function openPanel() {
    if (!panel) panel = buildPanel();
    isOpen = true;
    panel.style.transform = 'translateX(0)';
  }

  function closePanel() {
    if (panel) panel.style.transform = 'translateX(100%)';
    isOpen = false;
  }

  // ── Klávesová zkratka Ctrl+E ────────────────────────────────────────────────
  document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'e') {
      e.preventDefault();
      isOpen ? closePanel() : openPanel();
    }
  });

  // ── Otevřít automaticky pokud je ?edit v URL ────────────────────────────────
  if (new URLSearchParams(location.search).has('edit')) {
    document.addEventListener('DOMContentLoaded', openPanel);
  }

  // ── Aplikovat bridge CSS vždy (propojí proměnné na vlastnosti) ────────────
  const bridgeStyle = document.createElement('style');
  bridgeStyle.textContent = BRIDGE_CSS;
  document.head.appendChild(bridgeStyle);

  // ── Uložené hodnoty aplikovat POUZE v edit módu (?edit v URL) ─────────────
  // Normální návštěvníci vždy vidí CSS výchozí hodnoty — žádný flash
  if (new URLSearchParams(location.search).has('edit')) {
    const saved = loadValues();
    if (Object.keys(saved).length > 0) {
      applyValues(saved);
    }
  }

})();
