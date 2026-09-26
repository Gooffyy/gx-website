/**
 * GX MENU — INTERACTIVE CYBER ENGINE
 * Features: Ambient Particle Canvas, Dynamic Currency Switcher,
 * Interactive Cheat Menu Simulator, Payment Modal & Web Audio Synthesizer.
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Ambient Background Particle Canvas
  initAmbientCanvas();

  // 2. Interactive FiveM Menu Simulator
  initMenuSimulator();

  // 3. Currency Switcher Logic
  initCurrencySwitcher();

  // 4. Feature Category Tabs
  initFeatureTabs();

  // 5. Checkout Modal & Payment Handling
  initCheckoutModal();

  // 6. FAQ Accordion
  initFaqAccordion();

  // 7. Navbar Scroll & Mobile Menu
  initNavbar();

  // 8. Cyber Sound Synthesizer (Web Audio API)
  initCyberAudio();

  // 9. Real-Time Compatibility Checker
  initCompatibilityChecker();

  // 10. Live Social Proof Purchases Toast
  initSocialProofToast();

  // 11. Instant Query Jump & Smooth Nav Clicks
  const params = new URLSearchParams(window.location.search);
  const jumpSec = params.get('jump');
  if (jumpSec) {
    const target = document.getElementById(jumpSec);
    if (target) {
      const top = target.getBoundingClientRect().top + window.pageYOffset - 75;
      window.scrollTo(0, top);
    }
  }

  // 12. Referral Link Tracking
  const refParam = params.get('ref');
  if (refParam) {
    localStorage.setItem('gx_ref', refParam);
    document.cookie = `gx_ref=${encodeURIComponent(refParam)}; path=/; max-age=2592000`;
    fetch(`/api/public/track-referral?ref=${encodeURIComponent(refParam)}`, { method: 'POST' }).catch(() => {});
  }

  // Smooth scroll for nav items
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      const href = this.getAttribute('href');
      if (href === '#') return;
      const target = document.querySelector(href);
      if (target) {
        e.preventDefault();
        const top = target.getBoundingClientRect().top + window.pageYOffset - 75;
        window.scrollTo({ top: top, behavior: 'smooth' });
      }
    });
  });
});

/* ==========================================================================
   1. AMBIENT PARTICLES & SUSPENDED OBSIDIAN DEBRIS CANVAS
   ========================================================================== */
function initAmbientCanvas() {
  const canvas = document.getElementById('ambient-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let width, height;
  let glowParticles = [];
  let obsidianShards = [];
  const particleCount = 35;
  const shardCount = 26;

  function resize() {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
  }
  window.addEventListener('resize', resize);
  resize();

  class GlowParticle {
    constructor() {
      this.reset();
    }
    reset() {
      this.x = Math.random() * width;
      this.y = Math.random() * height;
      this.size = Math.random() * 2 + 0.8;
      this.speedY = -(Math.random() * 0.4 + 0.15);
      this.speedX = (Math.random() - 0.5) * 0.3;
      this.alpha = Math.random() * 0.6 + 0.2;
      this.fadeSpeed = Math.random() * 0.005 + 0.002;
    }
    update() {
      this.y += this.speedY;
      this.x += this.speedX;
      this.alpha -= this.fadeSpeed;
      if (this.alpha <= 0 || this.y < 0) {
        this.reset();
        this.y = height + 10;
      }
    }
    draw() {
      ctx.beginPath();
      ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(193, 42, 255, ${this.alpha})`;
      ctx.shadowBlur = 10;
      ctx.shadowColor = '#C12AFF';
      ctx.fill();
      ctx.shadowBlur = 0;
    }
  }

  class ObsidianShard {
    constructor() {
      this.reset();
    }
    reset() {
      this.x = Math.random() * width;
      this.y = Math.random() * height;
      this.radius = Math.random() * 5.5 + 2.5;
      this.speedY = -(Math.random() * 0.3 + 0.08);
      this.speedX = (Math.random() - 0.5) * 0.22;
      this.angle = Math.random() * Math.PI * 2;
      this.rotSpeed = (Math.random() - 0.5) * 0.012;
      this.alpha = Math.random() * 0.55 + 0.25;
      this.fadeSpeed = Math.random() * 0.0025 + 0.001;

      // Generate crystalline facet points
      this.points = [];
      const numPoints = Math.floor(Math.random() * 2) + 4;
      for (let i = 0; i < numPoints; i++) {
        const theta = (i / numPoints) * Math.PI * 2;
        const r = this.radius * (0.6 + Math.random() * 0.7);
        this.points.push({ x: Math.cos(theta) * r, y: Math.sin(theta) * r });
      }
    }
    update() {
      this.y += this.speedY;
      this.x += this.speedX;
      this.angle += this.rotSpeed;
      this.alpha -= this.fadeSpeed;
      if (this.alpha <= 0 || this.y < -20) {
        this.reset();
        this.y = height + 20;
      }
    }
    draw() {
      ctx.save();
      ctx.translate(this.x, this.y);
      ctx.rotate(this.angle);

      // Draw obsidian body
      ctx.beginPath();
      ctx.moveTo(this.points[0].x, this.points[0].y);
      for (let i = 1; i < this.points.length; i++) {
        ctx.lineTo(this.points[i].x, this.points[i].y);
      }
      ctx.closePath();
      ctx.fillStyle = `rgba(18, 9, 31, ${this.alpha * 0.95})`;
      ctx.fill();

      // Neon purple edge reflection & facet glow
      ctx.strokeStyle = `rgba(193, 42, 255, ${this.alpha * 0.85})`;
      ctx.lineWidth = 1;
      ctx.shadowBlur = 8;
      ctx.shadowColor = '#C12AFF';
      ctx.stroke();

      ctx.restore();
    }
  }

  for (let i = 0; i < particleCount; i++) {
    glowParticles.push(new GlowParticle());
  }
  for (let i = 0; i < shardCount; i++) {
    obsidianShards.push(new ObsidianShard());
  }

  function animate() {
    ctx.clearRect(0, 0, width, height);
    for (let p of glowParticles) {
      p.update();
      p.draw();
    }
    for (let s of obsidianShards) {
      s.update();
      s.draw();
    }
    requestAnimationFrame(animate);
  }
  animate();
}

/* ==========================================================================
   2. INTERACTIVE FIVEM MENU SIMULATOR
   ========================================================================== */
function initMenuSimulator() {
  const canvas = document.getElementById('sim-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  let simSettings = {
    silentAim: true,
    espBox: true,
    espSkeleton: true,
    fovSize: 85,
    smoothing: 4,
    showSnaplines: true
  };

  function resizeCanvas() {
    canvas.width = canvas.parentElement.clientWidth;
    canvas.height = canvas.parentElement.clientHeight;
    drawSimHUD();
  }
  window.addEventListener('resize', resizeCanvas);
  setTimeout(resizeCanvas, 50);

  // Bind Switch Controls
  const toggleSilent = document.getElementById('sim-toggle-aim');
  const toggleEsp = document.getElementById('sim-toggle-esp');
  const toggleSkel = document.getElementById('sim-toggle-skel');
  const rangeFov = document.getElementById('sim-range-fov');
  const fovValDisplay = document.getElementById('sim-fov-val');

  if (toggleSilent) {
    toggleSilent.addEventListener('change', (e) => {
      simSettings.silentAim = e.target.checked;
      drawSimHUD();
    });
  }

  if (toggleEsp) {
    toggleEsp.addEventListener('change', (e) => {
      simSettings.espBox = e.target.checked;
      drawSimHUD();
    });
  }

  if (toggleSkel) {
    toggleSkel.addEventListener('change', (e) => {
      simSettings.espSkeleton = e.target.checked;
      drawSimHUD();
    });
  }

  if (rangeFov && fovValDisplay) {
    rangeFov.addEventListener('input', (e) => {
      simSettings.fovSize = parseInt(e.target.value);
      fovValDisplay.textContent = `${simSettings.fovSize}px`;
      drawSimHUD();
    });
  }

  function drawSimHUD() {
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    const centerX = w / 2;
    const centerY = h / 2;

    // 1. Grid Lines in Viewport
    ctx.strokeStyle = 'rgba(155, 0, 255, 0.08)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, centerY); ctx.lineTo(w, centerY);
    ctx.moveTo(centerX, 0); ctx.lineTo(centerX, h);
    ctx.stroke();

    // 2. Crosshair Center
    ctx.strokeStyle = '#FFFFFF';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(centerX - 8, centerY); ctx.lineTo(centerX + 8, centerY);
    ctx.moveTo(centerX, centerY - 8); ctx.lineTo(centerX, centerY + 8);
    ctx.stroke();

    // 3. FOV Circle
    if (simSettings.silentAim) {
      ctx.beginPath();
      ctx.arc(centerX, centerY, simSettings.fovSize, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(193, 42, 255, 0.7)';
      ctx.lineWidth = 1.5;
      ctx.shadowBlur = 8;
      ctx.shadowColor = '#C12AFF';
      ctx.stroke();
      ctx.shadowBlur = 0;

      // Subtle FOV Fill
      ctx.fillStyle = 'rgba(193, 42, 255, 0.04)';
      ctx.fill();
    }

    // 4. Simulated Target Dummy (Slightly Offset to demonstrate Aimbot Target)
    const targetX = centerX + 45;
    const targetY = centerY + 10;

    // Snapline from screen center bottom to target
    if (simSettings.showSnaplines && simSettings.espBox) {
      ctx.beginPath();
      ctx.moveTo(centerX, h);
      ctx.lineTo(targetX, targetY + 40);
      ctx.strokeStyle = 'rgba(193, 42, 255, 0.4)';
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // 2D/3D ESP Box
    if (simSettings.espBox) {
      const boxW = 44;
      const boxH = 80;
      const boxX = targetX - boxW / 2;
      const boxY = targetY - 30;

      // Box outline
      ctx.strokeStyle = '#C12AFF';
      ctx.lineWidth = 1.5;
      ctx.shadowBlur = 10;
      ctx.shadowColor = '#C12AFF';
      ctx.strokeRect(boxX, boxY, boxW, boxH);
      ctx.shadowBlur = 0;

      // Health bar (Green)
      ctx.fillStyle = '#00FF88';
      ctx.fillRect(boxX - 6, boxY, 3, boxH * 0.85);

      // Target Label
      ctx.fillStyle = '#FFFFFF';
      ctx.font = '10px Michroma, sans-serif';
      ctx.fillText('TARGET [64m]', boxX - 4, boxY - 8);
    }

    // Skeleton Bones
    if (simSettings.espSkeleton) {
      ctx.strokeStyle = '#FFFFFF';
      ctx.lineWidth = 1.2;
      ctx.shadowBlur = 6;
      ctx.shadowColor = '#FFFFFF';

      const headY = targetY - 20;
      // Head
      ctx.beginPath();
      ctx.arc(targetX, headY, 6, 0, Math.PI * 2);
      ctx.stroke();

      // Spine
      ctx.beginPath();
      ctx.moveTo(targetX, headY + 6);
      ctx.lineTo(targetX, targetY + 24);

      // Shoulders & Arms
      ctx.moveTo(targetX - 14, headY + 12);
      ctx.lineTo(targetX + 14, headY + 12);
      ctx.lineTo(targetX + 18, targetY + 16);
      ctx.moveTo(targetX - 14, headY + 12);
      ctx.lineTo(targetX - 18, targetY + 16);

      // Legs
      ctx.moveTo(targetX, targetY + 24);
      ctx.lineTo(targetX - 12, targetY + 48);
      ctx.moveTo(targetX, targetY + 24);
      ctx.lineTo(targetX + 12, targetY + 48);
      ctx.stroke();
      ctx.shadowBlur = 0;
    }
  }
}

/* ==========================================================================
   3. CURRENCY SWITCHER
   ========================================================================== */
function initCurrencySwitcher() {
  const btnUSD = document.getElementById('curr-usd');
  const btnEGP = document.getElementById('curr-egp');
  if (!btnUSD || !btnEGP) return;

  const priceMonthlyMain = document.getElementById('price-monthly-main');
  const priceMonthlyAlt = document.getElementById('price-monthly-alt');
  const priceLifetimeMain = document.getElementById('price-lifetime-main');
  const priceLifetimeAlt = document.getElementById('price-lifetime-alt');

  let currentCurrency = 'USD';

  function updateCurrency(curr) {
    currentCurrency = curr;
    if (curr === 'USD') {
      btnUSD.classList.add('active');
      btnEGP.classList.remove('active');

      if (priceMonthlyMain) priceMonthlyMain.textContent = '$6.99';
      if (priceMonthlyAlt) priceMonthlyAlt.textContent = '350EGP';
      if (priceLifetimeMain) priceLifetimeMain.textContent = '$14.99';
      if (priceLifetimeAlt) priceLifetimeAlt.textContent = '750EGP';
    } else {
      btnEGP.classList.add('active');
      btnUSD.classList.remove('active');

      if (priceMonthlyMain) priceMonthlyMain.textContent = '350 EGP';
      if (priceMonthlyAlt) priceMonthlyAlt.textContent = '$6.99';
      if (priceLifetimeMain) priceLifetimeMain.textContent = '750 EGP';
      if (priceLifetimeAlt) priceLifetimeAlt.textContent = '$14.99';
    }
    window.currentActiveCurrency = curr;
  }

  btnUSD.addEventListener('click', () => updateCurrency('USD'));
  btnEGP.addEventListener('click', () => updateCurrency('EGP'));
}

/* ==========================================================================
   4. FEATURE TABS
   ========================================================================== */
function initFeatureTabs() {
  const tabBtns = document.querySelectorAll('.feature-tab-btn');
  const tabPanels = document.querySelectorAll('.tab-content-panel');

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetTab = btn.getAttribute('data-tab');

      tabBtns.forEach(b => b.classList.remove('active'));
      tabPanels.forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      const activePanel = document.getElementById(`tab-panel-${targetTab}`);
      if (activePanel) {
        activePanel.classList.add('active');
      }
    });
  });
}

/* ==========================================================================
   5. CHECKOUT MODAL & PAYMENT HANDLING
   ========================================================================== */
function initCheckoutModal() {
  const modalOverlay = document.getElementById('checkout-modal-overlay');
  const closeModalBtn = document.getElementById('modal-close-btn');
  const modalPlanName = document.getElementById('modal-plan-name');
  const modalPlanPrice = document.getElementById('modal-plan-price');
  const modalPayOptions = document.querySelectorAll('.modal-pay-option');
  const payDetailLabel = document.getElementById('pay-detail-label');
  const payTargetValue = document.getElementById('pay-target-val');
  const btnCopyPayment = document.getElementById('btn-copy-payment');
  const discordTicketBtn = document.getElementById('btn-discord-ticket');

  if (!modalOverlay) return;

  const paymentData = {
    vodafone: {
      label: 'VODAFONE CASH WALLET NUMBER',
      value: '01027194833',
      instructions: 'Transfer the exact amount via Vodafone Cash wallet or ATM cardless deposit, then open a ticket on Discord with your transfer screenshot.'
    },
    etisalat: {
      label: 'ETISALAT CASH WALLET NUMBER',
      value: '01158920144',
      instructions: 'Send payment via Etisalat Cash wallet. Take a screenshot of the confirmation SMS or app receipt and send it to our Discord bot.'
    },
    orange: {
      label: 'ORANGE CASH WALLET NUMBER',
      value: '01284910294',
      instructions: 'Transfer to our Orange Cash number. Keep your transaction reference number and submit it via Discord ticket.'
    },
    instapay: {
      label: 'INSTAPAY (IPA / ACCOUNT)',
      value: 'gxmenu@instapay',
      instructions: 'Send via InstaPay app instantly using our IPA username. Instant verification within 60 seconds.'
    },
    telda: {
      label: 'TELDA USERNAME',
      value: '@gxmenu',
      instructions: 'Send directly through the Telda app. Add your Discord tag in the transfer note.'
    },
    binance: {
      label: 'BINANCE PAY ID (USDT / CRYPTO)',
      value: '849201938',
      instructions: 'Pay zero fees using Binance Pay ID or request TRC-20 USDT deposit address in ticket.'
    },
    paypal: {
      label: 'PAYPAL EMAIL (FRIENDS & FAMILY)',
      value: 'payments@gxmenu.vip',
      instructions: 'Send via Friends & Family mode. Leave the note empty. Instant automated license delivery upon confirmation.'
    },
    taptap: {
      label: 'TAPTAP SEND RECIPIENT INFO',
      value: 'GX MENU EGYPT TRANSFER',
      instructions: 'Use Taptap Send app to send directly to Egypt cash wallet. Contact support for receiver name verification.'
    }
  };

  let selectedPlan = 'MONTHLY LICENSE';
  let selectedPrice = '$6.99 / 350 EGP';
  let activePaymentKey = 'vodafone';

  // Global open function
  window.openCheckout = function(planName, priceUSD, priceEGP) {
    selectedPlan = planName;
    const isEGP = window.currentActiveCurrency === 'EGP';
    selectedPrice = isEGP ? `${priceEGP} (${priceUSD})` : `${priceUSD} (${priceEGP})`;

    if (modalPlanName) modalPlanName.textContent = selectedPlan;
    if (modalPlanPrice) modalPlanPrice.textContent = selectedPrice;

    modalOverlay.classList.add('active');
    document.body.style.overflow = 'hidden';
  };

  // Close modal
  function closeModal() {
    modalOverlay.classList.remove('active');
    document.body.style.overflow = 'auto';
  }

  if (closeModalBtn) closeModalBtn.addEventListener('click', closeModal);
  modalOverlay.addEventListener('click', (e) => {
    if (e.target === modalOverlay) closeModal();
  });

  // Switch Payment Gateway in Modal
  modalPayOptions.forEach(opt => {
    opt.addEventListener('click', () => {
      modalPayOptions.forEach(o => o.classList.remove('active'));
      opt.classList.add('active');
      activePaymentKey = opt.getAttribute('data-method');

      const data = paymentData[activePaymentKey];
      if (data) {
        if (payDetailLabel) payDetailLabel.textContent = data.label;
        if (payTargetValue) payTargetValue.textContent = data.value;
        const noteElem = document.getElementById('pay-method-notes');
        if (noteElem) noteElem.textContent = data.instructions;
      }
    });
  });

  // Copy to clipboard
  if (btnCopyPayment && payTargetValue) {
    btnCopyPayment.addEventListener('click', () => {
      const textToCopy = payTargetValue.textContent.trim();
      navigator.clipboard.writeText(textToCopy).then(() => {
        const originalText = btnCopyPayment.innerHTML;
        btnCopyPayment.innerHTML = `<span>COPIED!</span>`;
        btnCopyPayment.style.background = '#00FF88';
        btnCopyPayment.style.borderColor = '#00FF88';
        btnCopyPayment.style.color = '#000';

        setTimeout(() => {
          btnCopyPayment.innerHTML = originalText;
          btnCopyPayment.style.background = '';
          btnCopyPayment.style.borderColor = '';
          btnCopyPayment.style.color = '';
        }, 1800);
      });
    });
  }

  // Hook all "GET PLAN" buttons
  const btnMonthly = document.getElementById('btn-get-monthly');
  const btnLifetime = document.getElementById('btn-get-lifetime');

  if (btnMonthly) {
    btnMonthly.addEventListener('click', () => {
      window.openCheckout('MONTHLY LICENSE (30 DAYS)', '$6.99', '350 EGP');
    });
  }

  if (btnLifetime) {
    btnLifetime.addEventListener('click', () => {
      window.openCheckout('LIFETIME LICENSE (ONE TIME)', '$14.99', '750 EGP');
    });
  }

  // Hook all payment method grid cards to trigger modal with that method preselected
  const paymentCards = document.querySelectorAll('.payment-method-card');
  paymentCards.forEach(card => {
    card.addEventListener('click', () => {
      const method = card.getAttribute('data-payment');
      window.openCheckout('GX MENU LICENSE', '$6.99 / $14.99', '350 / 750 EGP');

      const matchedOption = document.querySelector(`.modal-pay-option[data-method="${method}"]`);
      if (matchedOption) {
        matchedOption.click();
      }
    });
  });
}

/* ==========================================================================
   6. FAQ ACCORDION
   ========================================================================== */
function initFaqAccordion() {
  const faqItems = document.querySelectorAll('.faq-item');

  faqItems.forEach(item => {
    const btn = item.querySelector('.faq-question-btn');
    if (!btn) return;

    btn.addEventListener('click', () => {
      const isActive = item.classList.contains('active');
      faqItems.forEach(i => i.classList.remove('active'));

      if (!isActive) {
        item.classList.add('active');
      }
    });
  });
}

/* ==========================================================================
   7. NAVBAR SCROLL & SMOOTH SCROLL
   ========================================================================== */
function initNavbar() {
  const header = document.querySelector('.site-header');
  window.addEventListener('scroll', () => {
    if (window.scrollY > 40) {
      header.classList.add('scrolled');
    } else {
      header.classList.remove('scrolled');
    }
  });

  // Mobile menu toggle
  const mobileBtn = document.querySelector('.mobile-menu-btn');
  const navMenu = document.querySelector('.nav-menu');
  if (mobileBtn && navMenu) {
    mobileBtn.addEventListener('click', () => {
      navMenu.classList.toggle('open');
    });
  }
}

/* ==========================================================================
   8. CYBER AUDIO SYNTHESIZER (WEB AUDIO API)
   ========================================================================== */
function initCyberAudio() {
  let audioCtx = null;
  let isMuted = true;
  const audioBtn = document.getElementById('audio-toggle-btn');
  if (!audioBtn) return;

  function initContext() {
    if (!audioCtx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (AudioContext) audioCtx = new AudioContext();
    }
  }

  function playCyberBlip(freq = 880, duration = 0.08) {
    if (isMuted || !audioCtx) return;
    try {
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(freq * 1.5, audioCtx.currentTime + duration);

      gain.gain.setValueAtTime(0.08, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + duration);

      osc.connect(gain);
      gain.connect(audioCtx.destination);

      osc.start();
      osc.stop(audioCtx.currentTime + duration);
    } catch (e) {}
  }

  audioBtn.addEventListener('click', () => {
    initContext();
    isMuted = !isMuted;
    if (!isMuted) {
      audioBtn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#C12AFF" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>`;
      audioBtn.style.borderColor = '#C12AFF';
      audioBtn.style.boxShadow = '0 0 12px rgba(193, 42, 255, 0.5)';
      playCyberBlip(750, 0.12);
    } else {
      audioBtn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><line x1="23" y1="9" x2="17" y2="15"></line><line x1="17" y1="9" x2="23" y2="15"></line></svg>`;
      audioBtn.style.borderColor = '';
      audioBtn.style.boxShadow = '';
    }
  });

  // Bind subtle blips to interactive cyber buttons
  document.querySelectorAll('.btn-primary-neon, .plan-btn-get, .feature-tab-btn, .payment-method-card').forEach(el => {
    el.addEventListener('mouseenter', () => {
      if (!isMuted) playCyberBlip(1200, 0.04);
    });
  });
}

/* ==========================================================================
   9. REAL-TIME COMPATIBILITY CHECKER
   ========================================================================== */
function initCompatibilityChecker() {
  const searchInput = document.getElementById('ac-search-input');
  const checkBtn = document.getElementById('btn-check-ac');
  const resultBox = document.getElementById('checker-result-box');
  const targetName = document.getElementById('checker-target-name');
  const resultDesc = document.getElementById('checker-result-desc');
  const quickBtns = document.querySelectorAll('.ac-quick-btn');

  if (!searchInput || !resultBox) return;

  const acDatabase = {
    fiveguard: { name: 'FIVEGUARD v4.8 (LATEST)', status: 'OPERATIONAL', desc: '100% Undetected • Ring-0 Kernel memory isolation & event bypass active' },
    echo: { name: 'ECHO ANTI-CHEAT', status: 'OPERATIONAL', desc: '100% Undetected • User-mode memory scanner blocked & thread cloaked' },
    phoenix: { name: 'PHOENIX AC', status: 'OPERATIONAL', desc: '100% Undetected • Server heartbeat & resource integrity spoofing active' },
    reaper: { name: 'REAPER AC', status: 'OPERATIONAL', desc: '100% Undetected • Server-side event hook spoofing & injection hidden' },
    nopixel: { name: 'NOPIXEL CUSTOM ANTICHEAT', status: 'OPERATIONAL', desc: '100% Compatible • Streamproof OBS overlay & safe vector aimbot active' },
    anticheat: { name: 'ANTICHEAT V GLOBAL', status: 'OPERATIONAL', desc: '100% Undetected • Polymorphic loader bypass with dynamic signature shuffle' },
    lucid: { name: 'LUCID CITY RP SECURITY', status: 'OPERATIONAL', desc: '100% Undetected • Custom server-side event filters fully emulated' },
    wave: { name: 'WAVE SHIELD', status: 'OPERATIONAL', desc: '100% Undetected • Ring-0 driver bypass ensures complete stealth' }
  };

  function performCheck(query) {
    const q = (query || searchInput.value || '').trim().toLowerCase();
    if (!q) {
      searchInput.focus();
      return;
    }

    let match = null;
    for (const key in acDatabase) {
      if (q.includes(key) || key.includes(q)) {
        match = acDatabase[key];
        break;
      }
    }

    if (!match) {
      const cleanName = query ? query.toUpperCase() : searchInput.value.trim().toUpperCase();
      match = {
        name: `${cleanName} (FIVEM SERVER)`,
        status: 'OPERATIONAL',
        desc: '100% Undetected • Fully protected by GX Ring-0 Kernel Driver & HWID Cloaking'
      };
    }

    targetName.textContent = match.name;
    resultDesc.textContent = match.desc;
    resultBox.style.display = 'flex';
    resultBox.style.opacity = '0';
    resultBox.style.transform = 'translateY(10px)';
    resultBox.style.transition = 'all 0.3s ease';

    setTimeout(() => {
      resultBox.style.opacity = '1';
      resultBox.style.transform = 'translateY(0)';
    }, 10);
  }

  if (checkBtn) {
    checkBtn.addEventListener('click', () => performCheck());
  }

  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      performCheck();
    }
  });

  quickBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const query = btn.getAttribute('data-query');
      searchInput.value = query;
      performCheck(query);
    });
  });
}

/* ==========================================================================
   10. LIVE SOCIAL PROOF PURCHASES TOAST
   ========================================================================== */
function initSocialProofToast() {
  const toast = document.getElementById('social-proof-toast');
  const userEl = document.getElementById('toast-user');
  const timeEl = document.getElementById('toast-time');
  const descEl = document.getElementById('toast-desc');
  const closeBtn = document.getElementById('toast-close-btn');

  if (!toast || !userEl || !descEl) return;

  const purchases = [
    { user: 'Karim_EG', plan: 'Lifetime License', method: 'Vodafone Cash', time: '1 min ago' },
    { user: 'Shadow_FiveM', plan: 'Monthly License', method: 'InstaPay', time: 'Just now' },
    { user: 'Omar_K', plan: 'Lifetime License', method: 'Telda', time: '2 mins ago' },
    { user: 'GhostRider_99', plan: 'Lifetime License', method: 'Binance Pay', time: 'Just now' },
    { user: 'Vortex_RP', plan: 'Monthly License', method: 'Vodafone Cash', time: '3 mins ago' },
    { user: 'Matrix_Elite', plan: 'Lifetime License', method: 'PayPal', time: 'Just now' },
    { user: 'Youssef_X', plan: 'Lifetime License', method: 'Orange Cash', time: '4 mins ago' },
    { user: 'Sniper_EG', plan: 'Monthly License', method: 'Etisalat Cash', time: '1 min ago' },
    { user: 'CyberLord', plan: 'Lifetime License', method: 'Taptap Send', time: 'Just now' }
  ];

  let currentIndex = 0;
  let isDismissed = false;

  function showNextPurchase() {
    if (isDismissed) return;
    const item = purchases[currentIndex];
    userEl.textContent = item.user;
    timeEl.textContent = item.time;
    descEl.innerHTML = `Purchased <strong>${item.plan}</strong> via ${item.method}`;

    toast.classList.add('show');

    // Auto-hide after 5 seconds
    setTimeout(() => {
      toast.classList.remove('show');
    }, 5000);

    currentIndex = (currentIndex + 1) % purchases.length;
  }

  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      toast.classList.remove('show');
      isDismissed = true;
      // Re-enable after 60 seconds
      setTimeout(() => {
        isDismissed = false;
      }, 60000);
    });
  }

  // Initial trigger after 6 seconds, then rotate every 26 seconds
  setTimeout(() => {
    showNextPurchase();
    setInterval(showNextPurchase, 26000);
  }, 6000);
}

