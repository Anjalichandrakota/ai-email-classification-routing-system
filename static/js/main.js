// main.js — AI Email Classification & Routing System

(function () {
  'use strict';

  /* ── Sidebar Toggle ────────────────────────────────────────────── */
  const sidebar = document.getElementById('appSidebar');
  const overlay = document.getElementById('sidebarOverlay');
  const hamburger = document.getElementById('hamburgerBtn');

  function openSidebar() {
    if (sidebar) sidebar.classList.add('sidebar-open');
    if (overlay) overlay.classList.add('overlay-visible');
    if (hamburger) hamburger.setAttribute('aria-expanded', 'true');
  }

  function closeSidebar() {
    if (sidebar) sidebar.classList.remove('sidebar-open');
    if (overlay) overlay.classList.remove('overlay-visible');
    if (hamburger) hamburger.setAttribute('aria-expanded', 'false');
  }

  if (hamburger) hamburger.addEventListener('click', openSidebar);
  if (overlay)   overlay.addEventListener('click', closeSidebar);

  const analyticsLink = document.getElementById('sidebarAnalytics');
  if (analyticsLink && window.location.hash === '#charts') {
    document.querySelectorAll('.sidebar-nav-link.active').forEach(function (link) {
      link.classList.remove('active');
    });
    analyticsLink.classList.add('active');
  }

  if (sidebar) {
    sidebar.querySelectorAll('.sidebar-nav-link').forEach(function (link) {
      link.addEventListener('click', closeSidebar);
    });
  }

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeSidebar();
  });

  /* ── Auto-dismiss flash messages ──────────────────────────────── */
  setTimeout(function () {
    const flashMsgs = document.querySelectorAll('.flash-msg');
    flashMsgs.forEach(function (el) {
      el.style.transition = 'opacity 0.4s ease';
      el.style.opacity = '0';
      setTimeout(function () { el.remove(); }, 450);
    });
  }, 5500);

  /* ── Analyze Form: loading state ──────────────────────────────── */
  const analyzeForm = document.getElementById('analyzeForm');
  const analyzeBtn  = document.getElementById('analyzeBtnSubmit');
  if (analyzeForm && analyzeBtn) {
    analyzeForm.addEventListener('submit', function () {
      analyzeBtn.disabled = true;
      analyzeBtn.innerHTML = '<span class="btn-spinner"></span> Analyzing…';
      analyzeBtn.style.opacity = '0.75';
    });
  }

  /* ── Sample Email Loader ───────────────────────────────────────── */
  const sampleBtn = document.getElementById('loadSampleBtn');
  if (sampleBtn) {
    const samples = [
      {
        sender: 'alice.johnson@techcorp.com',
        subject: 'My account login is completely broken',
        body: "Hi Support,\n\nI've been trying to log into my account since yesterday but keep getting an error message saying 'Invalid credentials' even though I'm sure my password is correct.\n\nI tried resetting the password twice but still cannot access my dashboard. This is affecting my work urgently.\n\nPlease help as soon as possible.\n\nBest regards,\nAlice Johnson"
      },
      {
        sender: 'bob.smith@enterprise.net',
        subject: 'Invoice overcharge for October subscription',
        body: "Hello Billing Team,\n\nI noticed my October invoice shows $299 but I should be on the $199 Professional plan. I downgraded my subscription in September, yet the billing still reflects the old Enterprise rate.\n\nCould you please review and issue a corrected invoice with a refund for the difference?\n\nThank you,\nBob Smith"
      },
      {
        sender: 'carol.white@gmail.com',
        subject: 'Completely unacceptable service experience',
        body: "I am extremely disappointed with the level of service I received this week. Your agent kept me on hold for 45 minutes, transferred me three times, and my issue was never resolved.\n\nThis is absolutely unacceptable for a paying customer. I demand a formal apology and compensation.\n\nCarol White"
      },
      {
        sender: 'david.lee@startup.io',
        subject: 'Interested in upgrading to Enterprise plan',
        body: "Hi there,\n\nWe're a growing startup currently on the Business plan and we're very interested in upgrading to Enterprise. Could you send me information about the Enterprise tier features, pricing, and whether there are discounts for annual billing?\n\nLooking forward to hearing from you.\n\nDavid Lee\nCTO, StartupIO"
      },
      {
        sender: 'emma.davis@company.com',
        subject: 'Need help setting up two-factor authentication',
        body: "Hello,\n\nI'm trying to enable two-factor authentication on my account but the setup wizard keeps failing at the verification step. I've tried three different authenticator apps (Google Authenticator, Authy, Microsoft Authenticator) and none work.\n\nCould you provide step-by-step guidance or troubleshoot this for me?\n\nThank you,\nEmma Davis"
      }
    ];

    let sampleIndex = 0;

    sampleBtn.addEventListener('click', function () {
      const s = samples[sampleIndex % samples.length];
      const senderEl  = document.getElementById('id_sender_email');
      const subjectEl = document.getElementById('id_subject');
      const bodyEl    = document.getElementById('id_body');

      if (senderEl)  { senderEl.value  = s.sender;  animateField(senderEl);  }
      if (subjectEl) { subjectEl.value = s.subject; animateField(subjectEl); }
      if (bodyEl)    { bodyEl.value    = s.body;    animateField(bodyEl);    }

      sampleIndex++;

      sampleBtn.textContent = 'Next Sample →';
      sampleBtn.style.borderColor = 'rgba(99,102,241,0.5)';
      setTimeout(function () {
        sampleBtn.style.borderColor = '';
      }, 800);
    });
  }

  function animateField(el) {
    el.style.borderColor = 'rgba(99,102,241,0.7)';
    el.style.boxShadow   = '0 0 0 3px rgba(99,102,241,0.18)';
    setTimeout(function () {
      el.style.borderColor = '';
      el.style.boxShadow   = '';
    }, 800);
  }

  /* ── History: Filter submit on select change ───────────────────── */
  const filterSelects = document.querySelectorAll('.auto-submit-select');
  filterSelects.forEach(function (sel) {
    sel.addEventListener('change', function () {
      this.closest('form').submit();
    });
  });

})();
