/* Coyhaique River Lodge — comportamiento compartido (ES / EN / FR) */
(function () {
  'use strict';

  var CFG = {};
  try { CFG = JSON.parse(document.getElementById('crl-config').textContent); } catch (e) {}
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  };

  /* ---------- Idioma elegido a mano: se recuerda (localStorage + cookie leída por vercel.json) ---------- */
  function rememberLang(l) {
    store.set('crl_lang', l);
    try { document.cookie = 'crl_lang=' + l + '; path=/; max-age=31536000; SameSite=Lax'; } catch (e) {}
  }
  $$('.lang-switch a').forEach(function (a) {
    a.addEventListener('click', function () { rememberLang(a.getAttribute('data-lang')); });
  });

  /* ---------- Header sólido al hacer scroll ---------- */
  var header = $('#siteHeader');
  function onScroll() { header.classList.toggle('solid', window.scrollY > 60); }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* ---------- Menú móvil ---------- */
  var toggle = $('#menuToggle');
  function setMenu(open) {
    document.body.classList.toggle('menu-open', open);
    if (toggle) toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  if (toggle) toggle.addEventListener('click', function () { setMenu(!document.body.classList.contains('menu-open')); });
  $$('#mainNav a').forEach(function (a) { a.addEventListener('click', function () { setMenu(false); }); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') setMenu(false); });

  /* ---------- Hero minimalista ----------
     El texto y el menú aparecen al FINAL del video (config: hero.reveal_on_video_end).
     También se pueden saltar con clic, scroll, Tab o Enter. Si el video no puede reproducirse
     (sin conexión, autoplay bloqueado, ahorro de datos, movimiento reducido) se revelan solos. */
  var hero = $('.hero');
  var video = $('#heroVideo');
  var cueLogo = $('#heroCueLogo');
  var navLogoImg = $('.nav-logo img');
  var revealed = false;
  var startGuard = null;

  function reducedMotion() {
    return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }
  function revealSite() {
    if (revealed) return;
    revealed = true;
    if (startGuard) clearTimeout(startGuard);
    try {
      if (cueLogo && navLogoImg && window.scrollY < 4 && !reducedMotion()) {
        cueLogo.style.animation = 'none';
        var from = cueLogo.getBoundingClientRect();
        var to = navLogoImg.getBoundingClientRect();
        var scale = to.height / from.height;
        var dx = (to.left + to.width / 2) - (from.left + from.width / 2);
        var dy = (to.top + to.height / 2) - (from.top + from.height / 2);
        cueLogo.style.transition = 'transform .9s cubic-bezier(.2,.7,.2,1), opacity .5s ease .55s';
        cueLogo.style.transform = 'translate(' + dx + 'px,' + dy + 'px) scale(' + scale + ')';
        setTimeout(function () { cueLogo.style.opacity = '0'; }, 550);
      } else if (cueLogo) {
        cueLogo.style.opacity = '0';
      }
    } catch (e) {}
    document.body.classList.add('revealed');
    // Una vez revelado el sitio, el video sigue en bucle de fondo
    if (video) {
      video.loop = true;
      if (video.ended) { try { video.currentTime = 0; var p = video.play(); if (p && p.catch) p.catch(function () {}); } catch (e) {} }
    }
  }
  function revealLater(ms) { setTimeout(revealSite, ms); }

  if (hero) hero.addEventListener('click', revealSite);
  window.addEventListener('scroll', function () { if (window.scrollY > 4) revealSite(); }, { once: true, passive: true });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Tab' || e.key === 'Enter' || e.key === ' ') revealSite();
  });
  if (window.location.hash && window.location.hash !== '#top') revealSite();
  if (CFG.autoRevealMs > 0) revealLater(CFG.autoRevealMs);      // tope opcional (0 = sin tope)

  /* ---------- Video del hero: mp4/webm > HLS > imagen fija ---------- */
  function loadScript(src, ok, fail) {
    var s = document.createElement('script');
    s.src = src; s.async = true; s.onload = ok; s.onerror = fail;
    document.head.appendChild(s);
  }
  function startVideo() {
    if (!video) { revealLater(CFG.noVideoRevealMs); return; }
    var saveData = navigator.connection && navigator.connection.saveData;
    if (saveData || reducedMotion()) { revealLater(CFG.noVideoRevealMs); return; }   // solo imagen fija
    var mp4 = video.getAttribute('data-mp4');
    var webm = video.getAttribute('data-webm');
    var hls = video.getAttribute('data-hls');
    var giveUp = function () { revealLater(CFG.noVideoRevealMs); };
    video.loop = !CFG.revealOnVideoEnd;                    // si se espera el final, no hay bucle hasta revelar
    video.addEventListener('playing', function () { video.classList.add('playing'); });
    video.addEventListener('ended', function () { if (CFG.revealOnVideoEnd) revealSite(); });
    video.addEventListener('error', giveUp);
    // Si el video no arranca a tiempo (red lenta, flujo caído), no se deja al visitante esperando
    startGuard = setTimeout(function () { if (!video.classList.contains('playing')) revealSite(); },
                            CFG.videoStartTimeoutMs || 8000);
    var play = function () { var p = video.play(); if (p && p.catch) p.catch(giveUp); };
    if (mp4 || webm) {
      if (webm) { var s1 = document.createElement('source'); s1.src = webm; s1.type = 'video/webm'; video.appendChild(s1); }
      if (mp4) { var s2 = document.createElement('source'); s2.src = mp4; s2.type = 'video/mp4'; video.appendChild(s2); }
      video.load(); play();
    } else if (hls) {
      if (video.canPlayType('application/vnd.apple.mpegurl')) {
        video.src = hls; play();                            // Safari / iOS / Chrome reciente: HLS nativo
      } else {
        loadScript('https://cdnjs.cloudflare.com/ajax/libs/hls.js/1.5.15/hls.min.js', function () {
          if (!window.Hls || !window.Hls.isSupported()) { giveUp(); return; }
          var h = new window.Hls();
          h.on(window.Hls.Events.ERROR, function (ev, data) { if (data && data.fatal) { h.destroy(); giveUp(); } });
          h.loadSource(hls); h.attachMedia(video); play();
        }, giveUp);
      }
    } else {
      giveUp();
    }
  }
  if ('requestIdleCallback' in window) requestIdleCallback(startVideo, { timeout: 1500 });
  else setTimeout(startVideo, 200);

  /* ---------- Disponibilidad: filtro por programa ---------- */
  var filters = $$('.filter-btn');
  filters.forEach(function (btn) {
    btn.addEventListener('click', function () {
      var f = btn.getAttribute('data-filter');
      filters.forEach(function (b) { b.setAttribute('aria-pressed', b === btn ? 'true' : 'false'); });
      $$('#availBody tr').forEach(function (tr) {
        tr.hidden = !(f === 'all' || tr.getAttribute('data-program') === f);
      });
    });
  });

  /* ---------- Formulario: pre-llenado desde programas / salidas ---------- */
  var form = $('#inquiryForm');
  var chip = $('#slotChip');
  var slotInput = $('#f_slot');
  function setSlot(prog, start, end, label) {
    if (!form) return;
    if (prog) $('#f_program').value = prog;
    if (start) $('#f_arrival').value = start;
    if (end) $('#f_departure').value = end;
    slotInput.value = label || '';
    if (label) {
      chip.textContent = (CFG.labels ? CFG.labels.slot_selected : '') + ': ' + label;
      chip.classList.add('on');
    } else {
      chip.classList.remove('on');
      chip.textContent = '';
    }
  }
  $$('[data-slot-program]').forEach(function (a) {
    a.addEventListener('click', function () {
      setSlot(a.getAttribute('data-slot-program'), a.getAttribute('data-slot-start'),
              a.getAttribute('data-slot-end'), a.getAttribute('data-slot-label'));
      setTimeout(function () { var n = $('#f_name'); if (n) n.focus({ preventScroll: true }); }, 500);
    });
  });
  // También acepta ?program=pesca&start=2026-11-08&end=2026-11-15 en la URL
  try {
    var q = new URLSearchParams(window.location.search);
    if (q.get('program')) setSlot(q.get('program'), q.get('start'), q.get('end'), q.get('label') || '');
  } catch (e) {}
  var arrival = $('#f_arrival'), departure = $('#f_departure');
  if (arrival && departure) {
    arrival.addEventListener('change', function () {
      departure.min = arrival.value;
      slotInput.value = ''; if (chip) chip.classList.remove('on');
    });
  }

  /* ---------- Formulario: envío ---------- */
  var statusEl = $('#formStatus');
  var submitBtn = $('#submitBtn');
  function setStatus(msg, kind) {
    statusEl.textContent = msg || '';
    statusEl.className = 'form-status' + (kind ? ' ' + kind : '');
  }
  function selectedText(sel) { return sel.options[sel.selectedIndex] ? sel.options[sel.selectedIndex].text : ''; }
  function buildBody(data) {
    var L = CFG.labels || {};
    var lines = [
      L.name + ': ' + data.name,
      L.email + ': ' + data.email,
      data.phone ? L.phone + ': ' + data.phone : '',
      L.reply_lang + ': ' + selectedText($('#f_lang')),
      data.program ? L.program + ': ' + selectedText($('#f_program')) : '',
      data.slot ? L.slot_selected + ': ' + data.slot : '',
      data.arrival ? L.arrival + ': ' + data.arrival : '',
      data.departure ? L.departure + ': ' + data.departure : '',
      data.guests ? L.guests + ': ' + data.guests : '',
      '',
      data.message
    ];
    return lines.filter(function (l, i) { return l !== '' || i === 9; }).join('\n');
  }
  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (!form.checkValidity()) { form.reportValidity(); return; }
      var fd = new FormData(form);
      if (fd.get('website')) { setStatus(CFG.msg.success, 'ok'); form.reset(); return; }   // trampa anti-spam
      var data = {
        name: fd.get('name'), email: fd.get('email'), phone: fd.get('phone') || '',
        reply_lang: fd.get('reply_lang'), program: fd.get('program') || '',
        slot: fd.get('slot') || '', arrival: fd.get('arrival') || '', departure: fd.get('departure') || '',
        guests: fd.get('guests') || '', message: fd.get('message') || '',
        page_lang: CFG.lang, page: window.location.href
      };
      if (CFG.formEndpoint) {
        submitBtn.disabled = true; submitBtn.textContent = CFG.msg.sending; setStatus('');
        fetch(CFG.formEndpoint, {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data)
        }).then(function (r) {
          if (!r.ok) throw new Error('http ' + r.status);
          setStatus(CFG.msg.success, 'ok'); form.reset(); setSlot();
        }).catch(function () {
          setStatus(CFG.msg.error, 'err');
        }).then(function () {
          submitBtn.disabled = false; submitBtn.textContent = CFG.msg.submit;
        });
      } else {
        // Sin endpoint configurado: se abre el correo del visitante con la consulta lista
        var subject = 'CRL — ' + data.name + (data.slot ? ' — ' + data.slot : '');
        setStatus(CFG.msg.mailto, 'ok');
        window.location.href = 'mailto:' + CFG.email + '?subject=' + encodeURIComponent(subject) +
          '&body=' + encodeURIComponent(buildBody(data));
      }
    });
  }

  /* ---------- Cookies ---------- */
  var banner = $('#cookieBanner');
  if (banner) {
    if (!store.get('crl_consent')) banner.hidden = false;
    $$('[data-consent]', banner).forEach(function (btn) {
      btn.addEventListener('click', function () {
        store.set('crl_consent', btn.getAttribute('data-consent'));
        banner.hidden = true;
        // Aquí se activaría la medición (p. ej. Google Analytics) solo si consent === 'accept'
      });
    });
  }
})();
