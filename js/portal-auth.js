// ============================================================================
// GX MENU — PORTAL AUTHENTICATION & DISCORD CLEARANCE GATE
// Role ID Required: 1547640724604850186
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
  initPortalAuth();
});

async function initPortalAuth() {
  const gateContainer = document.getElementById('discord-gate-overlay');
  const dashContent = document.querySelector('.dash-section');
  const userProfileBar = document.getElementById('user-profile-bar');
  const keyDisplayEl = document.getElementById('display-license-key');
  const planPillEl = document.getElementById('portal-plan-badge');
  const btnToggle = document.getElementById('btn-toggle-mask');
  const btnCopy = document.getElementById('btn-copy-license');
  const pendingKeyBox = document.getElementById('pending-key-box');
  const holdReasonBox = document.getElementById('hold-reason-box');
  const holdReasonText = document.getElementById('hold-reason-text');
  const btnRefreshKey = document.getElementById('btn-refresh-key');

  if (!gateContainer || !dashContent) return;

  // 1. Fetch live user status from Backend
  let authData = { authenticated: false };
  try {
    const res = await fetch('/api/portal/me');
    if (res.ok) {
      authData = await res.json();
    }
  } catch (e) {
    const saved = localStorage.getItem('gx_demo_auth');
    if (saved) {
      try { authData = JSON.parse(saved); } catch (err) {}
    }
  }

  renderAuthState(authData);

  function renderAuthState(data) {
    // ------------------------------------------------------------------------
    // STATE 0: BLACKLISTED / ACCESS TERMINATED
    // ------------------------------------------------------------------------
    const urlParams = new URLSearchParams(window.location.search);
    const isUrlBanned = urlParams.get('banned') === 'true';
    if (data.isBanned || isUrlBanned) {
      dashContent.style.display = 'none';
      if (gateContainer) gateContainer.style.display = 'none';
      const bannedScreen = document.getElementById('portal-banned-screen');
      if (bannedScreen) {
        bannedScreen.style.display = 'flex';
        const reasonEl = document.getElementById('banned-reason-val');
        const byEl = document.getElementById('banned-by-val');
        const banReason = data.banReason || urlParams.get('reason') || 'Security Violation & Reversing Attempt';
        if (reasonEl) reasonEl.textContent = decodeURIComponent(banReason);
        if (byEl && data.bannedBy) byEl.textContent = data.bannedBy;
      }
      return;
    }

    // ------------------------------------------------------------------------
    // STATE 1: Unauthenticated -> Require Discord Login
    // ------------------------------------------------------------------------
    if (!data.authenticated) {
      dashContent.style.display = 'none';
      gateContainer.style.display = 'block';
      gateContainer.innerHTML = `
        <div class="gate-card">
          <div class="gate-discord-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="currentColor">
              <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994.021-.041.001-.09-.041-.106a13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.929 1.793 8.18 1.793 12.061 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.893.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.028zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/>
            </svg>
          </div>
          <span class="gate-badge">RESTRICTED ACCESS</span>
          <h2 class="gate-title">DISCORD AUTHENTICATION REQUIRED</h2>
          <p class="gate-desc">
            The GX Client Portal is exclusively gated to verified customers holding the Client role in our Discord server. Log in via Discord to verify your clearance.
          </p>
          <div class="gate-actions">
            <a href="/auth/discord" class="btn-discord-login">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994.021-.041.001-.09-.041-.106a13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.929 1.793 8.18 1.793 12.061 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.893.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.028zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/></svg>
              <span>CONTINUE WITH DISCORD</span>
            </a>
            <a href="https://discord.gg/AsAAQWXzUW" target="_blank" class="btn-join-discord">
              JOIN SERVER
            </a>
          </div>
        </div>
      `;
      return;
    }

    // ------------------------------------------------------------------------
    // STATE 2: Logged in via Discord, but DOES NOT HAVE ROLE 1547640724604850186
    // ------------------------------------------------------------------------
    if (data.authenticated && !data.hasClientRole && !data.isOwner) {
      dashContent.style.display = 'none';
      gateContainer.style.display = 'block';
      const u = data.user || {};
      gateContainer.innerHTML = `
        <div class="gate-card gate-warning">
          <div class="user-avatar-wrap">
            <img src="${u.avatar || 'images/logo.png'}" alt="Avatar" class="gate-user-avatar">
          </div>
          <span class="gate-badge gate-badge-warning">ROLE REQUIRED</span>
          <h2 class="gate-title">CLIENT ROLE NOT DETECTED</h2>
          <p class="gate-desc">
            Logged in as <strong>${u.username || 'Operator'}</strong>. You do not currently have the verified <strong>Client Role</strong> (ID: <code>1547640724604850186</code>) in our Discord server.
          </p>
          <div class="gate-instructions">
            <p><strong>HOW TO GAIN ACCESS:</strong></p>
            <ol>
              <li>Purchase your license subscription from the main site.</li>
              <li>Open a ticket in our Discord server with your transaction receipt.</li>
              <li>Staff will grant you the Client role and run <code>/assign key</code>.</li>
            </ol>
          </div>
          <div class="gate-actions">
            <a href="https://discord.gg/AsAAQWXzUW" target="_blank" class="btn-discord-login">
              OPEN TICKET IN DISCORD
            </a>
            <button id="btn-gate-logout" class="btn-join-discord">
              LOGOUT / SWITCH
            </button>
          </div>
        </div>
      `;
      document.getElementById('btn-gate-logout')?.addEventListener('click', handleLogout);
      return;
    }

    // ------------------------------------------------------------------------
    // STATE 3: USER HAS ROLE 1547640724604850186 OR IS SERVER OWNER -> ACCESS GRANTED!
    // ------------------------------------------------------------------------
    if (data.authenticated && (data.hasClientRole || data.isOwner)) {
      gateContainer.style.display = 'none';
      dashContent.style.display = 'block';

      const u = data.user || {};
      const lic = data.license || null;
      const isOwner = Boolean(data.isOwner || (u.id === '480805055595806722'));

      // 1. Render Operator Profile Bar
      if (userProfileBar) {
        const badgeHtml = isOwner
          ? `<span class="verified-pill" style="padding: 2px 10px; font-size: 0.68rem; background: linear-gradient(135deg, #FFB800, #FF3366); color: #fff; font-weight: 800; border: none; box-shadow: 0 0 10px rgba(255, 184, 0, 0.4);">👑 SERVER OWNER &bull; MASTER ACCESS</span>`
          : `<span class="verified-pill" style="padding: 2px 8px; font-size: 0.65rem;">ROLE 1547640724604850186 &bull; CLIENT</span>`;
        const adminBtnHtml = isOwner
          ? `<a href="/admin.html" class="btn-logout-mini" style="background: rgba(193, 42, 255, 0.2); border: 1px solid #C12AFF; color: #fff; text-decoration: none; display: inline-flex; align-items: center; gap: 6px; margin-right: 10px; font-weight: 700; padding: 4px 12px; border-radius: 6px; box-shadow: 0 0 12px rgba(193, 42, 255, 0.35);">⚙️ ADMIN CONSOLE</a>`
          : '';

        userProfileBar.innerHTML = `
          <div class="operator-profile-bar">
            <div class="operator-left">
              <img src="${u.avatar || 'images/logo.png'}" alt="User" class="operator-avatar-mini">
              <div>
                <span class="operator-handle">${u.username || 'OPERATOR'}</span>
                ${badgeHtml}
              </div>
            </div>
            <div class="operator-right">
              ${adminBtnHtml}
              <span style="font-size: 0.78rem; color: #c2b7d6;">Plan: <strong style="color: #C12AFF;">${(lic && lic.plan) || (isOwner ? 'Master Lifetime' : 'Lifetime')}</strong></span>
              <button id="btn-operator-logout" class="btn-logout-mini">LOGOUT</button>
            </div>
          </div>
        `;
        document.getElementById('btn-operator-logout')?.addEventListener('click', handleLogout);
      }

      // 2. CASE A: User has Role, but NO KEY ASSIGNED YET
      if (!lic) {
        if (pendingKeyBox) pendingKeyBox.style.display = 'block';
        if (holdReasonBox) holdReasonBox.style.display = 'none';

        if (keyDisplayEl) {
          keyDisplayEl.textContent = 'AWAITING STAFF DISPATCH...';
          keyDisplayEl.dataset.realKey = '';
          keyDisplayEl.style.color = '#7d7196';
        }
        if (planPillEl) {
          planPillEl.textContent = 'PENDING DISPATCH';
          planPillEl.style.borderColor = 'var(--electric-purple)';
          planPillEl.style.color = 'var(--electric-purple)';
        }

        // Disable Show and Copy buttons
        if (btnToggle) {
          btnToggle.disabled = true;
          btnToggle.style.opacity = '0.35';
          btnToggle.style.pointerEvents = 'none';
        }
        if (btnCopy) {
          btnCopy.disabled = true;
          btnCopy.style.opacity = '0.35';
          btnCopy.style.pointerEvents = 'none';
        }

        // Setup Refresh Key button
        if (btnRefreshKey) {
          btnRefreshKey.onclick = async () => {
            btnRefreshKey.disabled = true;
            btnRefreshKey.querySelector('span').textContent = 'CHECKING SERVER...';
            try {
              const r = await fetch('/api/portal/refresh-key');
              const d = await r.json();
              if (d.success && d.hasKey && d.license) {
                renderAuthState({ authenticated: true, hasClientRole: true, isOwner: (d.isOwner || data.isOwner), user: u, license: d.license });
              } else {
                setTimeout(() => {
                  btnRefreshKey.disabled = false;
                  btnRefreshKey.querySelector('span').textContent = 'KEY STILL PENDING (RE-CHECK)';
                }, 800);
              }
            } catch (err) {
              btnRefreshKey.disabled = false;
              btnRefreshKey.querySelector('span').textContent = 'CHECK / REFRESH KEY';
            }
          };
        }
        return;
      }

      // 3. CASE B: KEY IS ON-HOLD / EXPIRED
      if (lic.status === 'onhold') {
        if (pendingKeyBox) pendingKeyBox.style.display = 'none';
        if (holdReasonBox) {
          holdReasonBox.style.display = 'block';
          if (holdReasonText) holdReasonText.textContent = lic.holdReason || 'Subscription Expired';
        }

        if (keyDisplayEl) {
          keyDisplayEl.textContent = 'LOCKED — ON-HOLD';
          keyDisplayEl.dataset.realKey = '';
          keyDisplayEl.style.color = '#FFB800';
        }
        if (planPillEl) {
          planPillEl.textContent = 'ON-HOLD';
          planPillEl.style.borderColor = '#FFB800';
          planPillEl.style.color = '#FFB800';
        }

        // Disable SHOW and COPY
        if (btnToggle) {
          btnToggle.disabled = true;
          btnToggle.style.opacity = '0.25';
          btnToggle.style.pointerEvents = 'none';
          btnToggle.querySelector('span').textContent = 'LOCKED';
        }
        if (btnCopy) {
          btnCopy.disabled = true;
          btnCopy.style.opacity = '0.25';
          btnCopy.style.pointerEvents = 'none';
        }
        return;
      }

      // 4. CASE C: KEY IS ACTIVE!
      if (lic.status === 'active' || !lic.status) {
        if (pendingKeyBox) pendingKeyBox.style.display = 'none';
        if (holdReasonBox) holdReasonBox.style.display = 'none';

        if (keyDisplayEl) {
          keyDisplayEl.dataset.realKey = lic.key;
          keyDisplayEl.textContent = '••••-••••-••••-••••'; // Always hidden by default!
          keyDisplayEl.style.color = '#fff';
        }
        if (planPillEl) {
          planPillEl.textContent = ((lic.plan || 'Lifetime').toUpperCase()) + ' ACTIVE';
          planPillEl.style.borderColor = 'var(--status-green)';
          planPillEl.style.color = 'var(--status-green)';
        }

        // Enable SHOW and COPY
        if (btnToggle) {
          btnToggle.disabled = false;
          btnToggle.style.opacity = '1';
          btnToggle.style.pointerEvents = 'auto';
          btnToggle.querySelector('span').textContent = 'SHOW';
        }
        if (btnCopy) {
          btnCopy.disabled = false;
          btnCopy.style.opacity = '1';
          btnCopy.style.pointerEvents = 'auto';
        }
      }

      // 5. Populate License Details Table Dynamically
      if (lic) {
        const tierEl = document.getElementById('portal-sub-tier');
        const activatedEl = document.getElementById('portal-sub-activated');
        const expiresEl = document.getElementById('portal-sub-expires');
        const roleEl = document.getElementById('portal-sub-role');
        const isMonthly = lic.plan === 'Monthly';

        if (tierEl) {
          tierEl.innerHTML = isMonthly
            ? '<span style="color: #6C5CE7; font-weight: 800;">MONTHLY LICENSE (30 DAYS)</span>'
            : '<span style="color: var(--electric-purple); font-weight: 800;">LIFETIME ACCESS (VIP)</span>';
        }

        if (activatedEl) {
          if (lic.assignedAt) {
            const actDate = new Date(lic.assignedAt);
            activatedEl.textContent = actDate.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }) + ' • ' + actDate.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
          } else {
            activatedEl.textContent = 'Active License';
          }
        }

        if (expiresEl) {
          if (isMonthly) {
            if (lic.expiresAt) {
              const expDate = new Date(lic.expiresAt);
              const now = new Date();
              const diffMs = expDate - now;
              if (diffMs > 0) {
                const daysLeft = Math.floor(diffMs / (1000 * 60 * 60 * 24));
                const hoursLeft = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                expiresEl.innerHTML = `<span style="color: #00FF88; font-weight: 800;">${expDate.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })} (${daysLeft}d ${hoursLeft}h left)</span>`;
              } else {
                expiresEl.innerHTML = `<span style="color: #FF2A55; font-weight: 800;">EXPIRED ON ${expDate.toLocaleDateString('en-US')}</span>`;
              }
            } else {
              expiresEl.innerHTML = '<span style="color: #FFB800; font-weight: 800;">30 Days from Activation</span>';
            }
          } else {
            expiresEl.innerHTML = '<span style="color: var(--status-green); font-weight: 800;">NEVER (UNLIMITED VIP)</span>';
          }
        }

        if (roleEl) {
          roleEl.innerHTML = isMonthly
            ? '<span style="color: #6C5CE7;">@GX Client (Monthly)</span>'
            : '<span style="color: var(--electric-purple);">@GX Lifetime Verified</span>';
        }

        // 6. Update Interactive Subscription Days Remaining Gauge
        const gaugeCard = document.getElementById('sub-gauge-card');
        const gaugeBar = document.getElementById('sub-gauge-bar');
        const gaugePercent = document.getElementById('sub-gauge-percent');
        const gaugeUnit = document.getElementById('sub-gauge-unit');
        const gaugeTimeBig = document.getElementById('sub-gauge-time-big');
        const gaugeTimeSub = document.getElementById('sub-gauge-time-sub');
        const gaugeTier = document.getElementById('sub-gauge-tier');

        if (gaugeCard) {
          gaugeCard.style.display = 'flex';

          if (isMonthly) {
            const expDate = lic.expiresAt ? new Date(lic.expiresAt) : null;
            const actDate = lic.assignedAt ? new Date(lic.assignedAt) : new Date();
            const totalDurationMs = 30 * 24 * 60 * 60 * 1000; // 30 days in ms

            if (expDate) {
              const diffMs = expDate - new Date();
              if (diffMs > 0) {
                const daysLeft = Math.floor(diffMs / (1000 * 60 * 60 * 24));
                const hoursLeft = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                const fractionLeft = Math.max(0, Math.min(1, diffMs / totalDurationMs));
                const pct = Math.round(fractionLeft * 100);

                if (gaugePercent) gaugePercent.textContent = pct + '%';
                if (gaugeUnit) gaugeUnit.textContent = 'TIME LEFT';
                if (gaugeTimeBig) gaugeTimeBig.innerHTML = `${daysLeft}<span style="font-size: 1rem; color: #c084fc;">d</span> ${hoursLeft}<span style="font-size: 1rem; color: #c084fc;">h</span> REMAINING`;
                if (gaugeTimeSub) gaugeTimeSub.textContent = `Subscription active until ${expDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}. Full access to builds & HWID resets.`;

                // Calculate circle stroke (circumference 2 * PI * 38 ≈ 238.76)
                const circ = 238.76;
                const offset = circ - (circ * fractionLeft);
                if (gaugeBar) {
                  gaugeBar.style.strokeDashoffset = offset;
                  if (pct < 15) {
                    gaugeBar.style.stroke = '#FF2A55';
                    gaugeBar.style.filter = 'drop-shadow(0 0 8px rgba(255, 42, 85, 0.8))';
                  } else if (pct < 35) {
                    gaugeBar.style.stroke = '#FFB800';
                    gaugeBar.style.filter = 'drop-shadow(0 0 8px rgba(255, 184, 0, 0.8))';
                  } else {
                    gaugeBar.style.stroke = '#00FF88';
                    gaugeBar.style.filter = 'drop-shadow(0 0 8px rgba(0, 255, 136, 0.8))';
                  }
                }
              } else {
                if (gaugePercent) gaugePercent.textContent = '0%';
                if (gaugeUnit) gaugeUnit.textContent = 'EXPIRED';
                if (gaugeTimeBig) gaugeTimeBig.innerHTML = '<span style="color: #FF2A55;">SUBSCRIPTION EXPIRED</span>';
                if (gaugeTimeSub) gaugeTimeSub.textContent = 'Your 30-day access has ended. Renew your plan to continue using GX MENU.';
                if (gaugeBar) {
                  gaugeBar.style.strokeDashoffset = 238.76;
                  gaugeBar.style.stroke = '#FF2A55';
                }
              }
            } else {
              if (gaugeTimeBig) gaugeTimeBig.textContent = '30 DAYS ACTIVE';
            }
          } else {
            // Lifetime License
            if (gaugePercent) gaugePercent.textContent = '∞';
            if (gaugePercent) gaugePercent.style.fontSize = '1.8rem';
            if (gaugeUnit) gaugeUnit.textContent = 'UNLIMITED';
            if (gaugeTimeBig) gaugeTimeBig.innerHTML = '<span style="color: #00FF88;">LIFETIME VIP ACCESS</span>';
            if (gaugeTimeSub) gaugeTimeSub.textContent = 'Never-expiring entitlement. Permanent access to all updates, builds, and automated support.';
            if (gaugeBar) {
              gaugeBar.style.strokeDashoffset = 0;
              gaugeBar.style.stroke = '#00FF88';
            }
          }
        }

        // 7. Update HWID Box display based on live license
        const hwidValEl = document.getElementById('hwid-val');
        if (hwidValEl) {
          if (lic.hwid) {
            hwidValEl.textContent = lic.hwid;
            hwidValEl.style.color = '#fff';
          } else {
            hwidValEl.textContent = 'UNBOUND — PENDING LAUNCH';
            hwidValEl.style.color = '#FFB800';
          }
        }

        // 8. Fetch Latest Loader Build & Handle Client Update Alert Banner
        initLoaderBuildAndAlert();
        initReferralHub(data.user ? data.user.id : '');
      }
    }
  }

  async function initLoaderBuildAndAlert() {
    try {
      const res = await fetch('/api/public/loader-build');
      const data = await res.json();
      if (!data.success || !data.build) return;

      const build = data.build;

      // Update primary download card
      const verEl = document.getElementById('loader-ver-heading');
      const compEl = document.getElementById('loader-pill-compatibility');
      const dlBtn = document.getElementById('btn-download-loader');
      const sizeEl = document.getElementById('loader-file-size');
      const hashEl = document.getElementById('checksum-hash');

      if (verEl && build.version) verEl.textContent = build.version;
      if (compEl && build.compatibility) compEl.textContent = build.compatibility;
      if (dlBtn && build.download_url) {
        dlBtn.href = build.download_url;
        dlBtn.setAttribute('download', build.filename || 'GX_Loader.exe');
      }
      if (sizeEl && build.file_size) sizeEl.textContent = build.file_size;
      if (hashEl && build.sha256) hashEl.textContent = build.sha256;

      // Check if update alert should be displayed
      const alertBanner = document.getElementById('portal-update-alert');
      const alertTitle = document.getElementById('alert-build-title');
      const alertDesc = document.getElementById('alert-build-desc');
      const alertDlBtn = document.getElementById('alert-download-btn');
      const alertDismissBtn = document.getElementById('alert-dismiss-btn');

      if (alertBanner && build.id) {
        const lastSeenBuild = localStorage.getItem('gx_last_seen_loader_build');
        if (lastSeenBuild !== build.id) {
          if (alertTitle) alertTitle.textContent = `NEW BUILD AVAILABLE: ${build.version || 'v4.8.3'}`;
          if (alertDesc) alertDesc.textContent = build.notes || 'A new security and compatibility update has been deployed. Please download the latest build.';
          if (alertDlBtn) {
            alertDlBtn.href = build.download_url || '/downloads/GX_Loader.exe';
            alertDlBtn.setAttribute('download', build.filename || 'GX_Loader.exe');
          }
          alertBanner.style.display = 'flex';

          if (alertDismissBtn) {
            alertDismissBtn.onclick = () => {
              localStorage.setItem('gx_last_seen_loader_build', build.id);
              alertBanner.style.display = 'none';
            };
          }
        }
      }
    } catch (e) {
      console.warn('Could not fetch latest loader build:', e);
    }
  }


  async function initReferralHub(userId) {
    const affCard = document.getElementById('portal-affiliate-card');
    if (!affCard || !userId) return;

    const origin = window.location.origin;
    const codeEl = document.getElementById('aff-user-code');
    const inputEl = document.getElementById('aff-ref-link');

    try {
      const res = await fetch('/api/portal/referral-stats');
      if (!res.ok) return;
      const data = await res.json();
      if (!data.success || !data.stats) return;

      const s = data.stats;
      const randomCode = s.referral_code || userId;
      if (codeEl) codeEl.textContent = randomCode;
      if (inputEl) inputEl.value = `${origin}/?ref=${randomCode}`;

      const clicksEl = document.getElementById('aff-stat-clicks');
      const convEl = document.getElementById('aff-stat-conversions');
      const bonusEl = document.getElementById('aff-stat-bonus');
      const nextRewardEl = document.getElementById('aff-stat-next-reward');
      const tierNameEl = document.getElementById('aff-tier-name');
      const progTextEl = document.getElementById('aff-progress-text');
      const progPctEl = document.getElementById('aff-progress-pct');
      const progFillEl = document.getElementById('aff-progress-fill');
      const historyListEl = document.getElementById('aff-history-list');

      if (clicksEl) clicksEl.textContent = s.clicks || 0;
      if (convEl) convEl.textContent = s.conversions || 0;
      if (bonusEl) bonusEl.textContent = `+${s.bonus_days || 0} DAYS`;
      if (tierNameEl) tierNameEl.textContent = (s.tier || 'BRONZE SCOUT').toUpperCase();

      if (progTextEl) {
        if (s.needed_for_next > 0) {
          progTextEl.innerHTML = `Progress to ${s.next_tier}: <strong>${s.conversions} / ${s.conversions + s.needed_for_next} Referrals</strong> (Need ${s.needed_for_next} more)`;
        } else {
          progTextEl.innerHTML = `MAX TIER REACHED: <strong>${s.tier} VIP</strong>`;
        }
      }
      if (progPctEl) progPctEl.textContent = `${s.progress_pct}%`;
      if (progFillEl) progFillEl.style.width = `${s.progress_pct}%`;

      if (historyListEl && s.rewards_history && s.rewards_history.length) {
        historyListEl.innerHTML = s.rewards_history.map(r => `
          <div class="aff-history-item">
            <div class="aff-history-item-left">
              <span style="color: #c084fc; font-weight: 700;">👤 ${escapeHtml(r.referred_username || 'Customer')}</span>
              <span style="color: var(--text-dim); font-size: 0.72rem; font-family: var(--font-mono);">${r.date || ''}</span>
            </div>
            <span class="aff-reward-pill">+${r.bonus_days} DAYS BONUS</span>
          </div>
        `).join('');
      }
    } catch (err) {
      console.warn('[AFFILIATE] Error loading stats:', err);
    }
  }

  window.copyReferralLink = function() {
    const input = document.getElementById('aff-ref-link');
    const btnText = document.getElementById('btn-copy-ref-text');
    if (!input) return;
    navigator.clipboard.writeText(input.value).then(() => {
      if (btnText) {
        const old = btnText.textContent;
        btnText.textContent = 'COPIED!';
        setTimeout(() => btnText.textContent = old, 2000);
      }
    });
  };

  window.copyReferralCodeOnly = function() {
    const codeEl = document.getElementById('aff-user-code');
    const btnText = document.getElementById('btn-copy-code-text');
    if (!codeEl) return;
    navigator.clipboard.writeText(codeEl.textContent.trim()).then(() => {
      if (btnText) {
        const old = btnText.textContent;
        btnText.textContent = 'COPIED!';
        setTimeout(() => btnText.textContent = old, 2000);
      }
    });
  };

    async function handleLogout() {
    try {
      await fetch('/api/portal/logout');
    } catch (e) {}
    localStorage.removeItem('gx_demo_auth');
    window.location.href = '/dashboard.html';
  }
}
