// ============================================================================
// GX MENU — SECURE BACKEND & DISCORD OAUTH2 PORTAL GATE
// Target Client Role ID: 1547640724604850186
// ============================================================================
const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '../.env') });
const express = require('express');
const cookieParser = require('cookie-parser');
const fs = require('fs');

const app = express();
const PORT = process.env.PORT || 8080;
const ROOT_DIR = path.join(__dirname, '..');
const LICENSES_FILE = path.join(ROOT_DIR, 'data/licenses.json');
const BLACKLIST_FILE = path.join(ROOT_DIR, 'data/blacklist.json');
const REFERRALS_FILE = path.join(ROOT_DIR, 'data/referrals.json');

function getBlacklist() {
  try {
    if (!fs.existsSync(BLACKLIST_FILE)) return [];
    return JSON.parse(fs.readFileSync(BLACKLIST_FILE, 'utf8'));
  } catch (err) {
    return [];
  }
}

function saveBlacklist(data) {
  try {
    fs.writeFileSync(BLACKLIST_FILE, JSON.stringify(data, null, 2), 'utf8');
    return true;
  } catch (err) {
    return false;
  }
}

function checkBlacklist(userId, hwid = '') {
  const bl = getBlacklist();
  if (!bl || !bl.length) return null;
  const normalizedUid = String(userId || '').trim();
  const normalizedHwid = String(hwid || '').trim().toLowerCase();
  
  for (const entry of bl) {
    if (entry.status === 'revoked') continue;
    if (entry.type === 'discord_id' && entry.target && String(entry.target).trim() === normalizedUid) {
      return entry;
    }
    if (entry.type === 'hwid' && entry.target && normalizedHwid && String(entry.target).trim().toLowerCase() === normalizedHwid) {
      return entry;
    }
    if (entry.target && (String(entry.target).trim() === normalizedUid || (normalizedHwid && String(entry.target).trim().toLowerCase() === normalizedHwid))) {
      return entry;
    }
  }
  return null;
}

function getReferrals() {
  try {
    if (!fs.existsSync(REFERRALS_FILE)) return { referrals: {}, code_map: {}, rewards: [] };
    const parsed = JSON.parse(fs.readFileSync(REFERRALS_FILE, 'utf8'));
    if (!parsed.code_map) parsed.code_map = {};
    if (!parsed.referrals) parsed.referrals = {};
    if (!parsed.rewards) parsed.rewards = [];
    return parsed;
  } catch (err) {
    return { referrals: {}, code_map: {}, rewards: [] };
  }
}

function saveReferrals(data) {
  try {
    fs.writeFileSync(REFERRALS_FILE, JSON.stringify(data, null, 2), 'utf8');
    return true;
  } catch (err) {
    return false;
  }
}

function generateUniqueReferralCode(refData) {
  const chars = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ';
  for (let attempt = 0; attempt < 200; attempt++) {
    let code = 'GX-';
    for (let i = 0; i < 4; i++) {
      code += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    if (!refData.code_map || !refData.code_map[code]) {
      return code;
    }
  }
  return 'GX-' + Math.random().toString(36).substring(2, 6).toUpperCase();
}

function resolveReferrerId(inputCode) {
  if (!inputCode) return null;
  const clean = String(inputCode).trim().toUpperCase();
  const data = getReferrals();
  if (data.code_map && data.code_map[clean]) {
    return data.code_map[clean];
  }
  if (data.code_map) {
    for (const [code, uid] of Object.entries(data.code_map)) {
      if (code.toUpperCase() === clean) return uid;
    }
  }
  if (data.referrals && data.referrals[clean]) {
    return clean;
  }
  const licenses = getLicenses();
  if (licenses[clean]) return clean;

  return null;
}

function getReferralStats(userId) {
  const data = getReferrals();
  let updated = false;

  if (!data.referrals[userId]) {
    const newCode = generateUniqueReferralCode(data);
    data.referrals[userId] = {
      referral_code: newCode,
      clicks: 0,
      conversions: 0,
      bonus_days: 0,
      created_at: new Date().toISOString()
    };
    data.code_map[newCode] = userId;
    updated = true;
  } else if (!data.referrals[userId].referral_code || data.referrals[userId].referral_code === userId) {
    const newCode = generateUniqueReferralCode(data);
    data.referrals[userId].referral_code = newCode;
    data.code_map[newCode] = userId;
    updated = true;
  }

  if (updated) saveReferrals(data);

  const userStats = data.referrals[userId];
  const userRewards = (data.rewards || []).filter(r => r.referrer_id === userId);
  
  const conv = userStats.conversions || 0;
  let tier = 'Bronze Scout';
  let nextTier = 'Silver Agent';
  let needed = 3 - conv;
  let progressPct = Math.min(100, Math.round((conv / 3) * 100));

  if (conv >= 10) {
    tier = 'Cyber Legend';
    nextTier = 'MAX TIER';
    needed = 0;
    progressPct = 100;
  } else if (conv >= 6) {
    tier = 'Gold Vanguard';
    nextTier = 'Cyber Legend';
    needed = 10 - conv;
    progressPct = Math.min(100, Math.round(((conv - 6) / 4) * 100));
  } else if (conv >= 3) {
    tier = 'Silver Agent';
    nextTier = 'Gold Vanguard';
    needed = 6 - conv;
    progressPct = Math.min(100, Math.round(((conv - 3) / 3) * 100));
  }

  return {
    user_id: userId,
    referral_code: userStats.referral_code,
    clicks: userStats.clicks || 0,
    conversions: conv,
    bonus_days: userStats.bonus_days || 0,
    tier,
    next_tier: nextTier,
    needed_for_next: Math.max(0, needed),
    progress_pct: progressPct,
    rewards_history: userRewards.slice(-10).reverse()
  };
}


const CLIENT_ID = process.env.DISCORD_CLIENT_ID || '';
const CLIENT_SECRET = process.env.DISCORD_CLIENT_SECRET || '';
const BOT_TOKEN = process.env.DISCORD_BOT_TOKEN || '';
const GUILD_ID = process.env.DISCORD_GUILD_ID || '1547636843388870748';
const CLIENT_ROLE_ID = process.env.CLIENT_ROLE_ID || '1547640724604850186';
const STAFF_ROLE_ID = process.env.STAFF_ROLE_ID || '1547640722013036637';
const OWNER_ROLE_ID = process.env.OWNER_ROLE_ID || '1547640722013036637';
const GUILD_OWNER_ID = process.env.GUILD_OWNER_ID || '480805055595806722';
const ASSIGN_LOG_CHANNEL_ID = process.env.ASSIGN_LOG_CHANNEL_ID || '1547753183424806983';
function getRedirectUri(req) {
  if (process.env.DISCORD_REDIRECT_URI && 
      !process.env.DISCORD_REDIRECT_URI.includes('YOUR_') && 
      !process.env.DISCORD_REDIRECT_URI.includes('localhost') && 
      !process.env.DISCORD_REDIRECT_URI.includes('production')) {
    return process.env.DISCORD_REDIRECT_URI;
  }
  const host = (req && req.headers && (req.headers['x-forwarded-host'] || req.headers.host)) || 'gx-menus.up.railway.app';
  const proto = (req && req.headers && req.headers['x-forwarded-proto']) || 'https';
  return `${proto}://${host}/auth/discord/callback`;
}

app.use(express.json());
app.use(cookieParser('gx-secret-key-2026'));

// Strict Zero-Cache & Maximum Privacy Enforcement for Admin Console and Admin APIs
app.use(['/admin.html', '/api/admin'], (req, res, next) => {
  res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0');
  res.setHeader('Pragma', 'no-cache');
  res.setHeader('Expires', '0');
  res.setHeader('Surrogate-Control', 'no-store');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('Referrer-Policy', 'no-referrer');
  next();
});

// Helper to send Discord Rich Embed Log
async function sendDiscordLogEmbed(channelId, embedData) {
  const token = BOT_TOKEN || process.env.DISCORD_BOT_TOKEN || process.env.DISCORD_TOKEN;
  if (!token || !channelId) return false;
  try {
    const res = await fetch(`https://discord.com/api/v10/channels/${channelId}/messages`, {
      method: 'POST',
      headers: {
        'Authorization': `Bot ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ embeds: [embedData] })
    });
    return res.ok;
  } catch (err) {
    console.warn('[DISCORD LOG] Error dispatching embed:', err.message);
    return false;
  }
}

// Helper to grant Discord Role
async function grantDiscordRole(userId, roleId = CLIENT_ROLE_ID) {
  const token = BOT_TOKEN || process.env.DISCORD_BOT_TOKEN || process.env.DISCORD_TOKEN;
  const guildId = GUILD_ID || process.env.DISCORD_GUILD_ID || '1547636843388870748';
  if (!token || !guildId || !userId || !roleId) return false;
  try {
    const res = await fetch(`https://discord.com/api/v10/guilds/${guildId}/members/${userId}/roles/${roleId}`, {
      method: 'PUT',
      headers: { 'Authorization': `Bot ${token}` }
    });
    return res.ok;
  } catch (err) {
    console.warn('[DISCORD ROLE] Error granting role:', err.message);
    return false;
  }
}

// Helper to read licenses
function getLicenses() {
  try {
    if (!fs.existsSync(LICENSES_FILE)) return {};
    return JSON.parse(fs.readFileSync(LICENSES_FILE, 'utf8'));
  } catch (err) {
    return {};
  }
}

// Helper to save licenses
function saveLicenses(data) {
  try {
    fs.writeFileSync(LICENSES_FILE, JSON.stringify(data, null, 2), 'utf8');
    return true;
  } catch (err) {
    return false;
  }
}

// Helper to sync licenses and HWID resets with Cloudflare Worker KV
const CF_WORKER_URL = process.env.CLOUDFLARE_WORKER_URL || 'https://tight-base-cfefgx-auth.mahmoudgam3r369.workers.dev';
const CF_ADMIN_SECRET = process.env.CLOUDFLARE_ADMIN_SECRET || 'gxdev123';

async function syncKeyWithCloudflare(key, days = 0, action = 'add') {
  if (!CF_WORKER_URL || !key) return false;
  try {
    const url = `${CF_WORKER_URL}/?action=${action}&admin=${CF_ADMIN_SECRET}&key=${encodeURIComponent(key)}&days=${days}`;
    const resp = await fetch(url);
    const data = await resp.json();
    return data && data.success;
  } catch (err) {
    console.warn('[CLOUDFLARE SYNC] Warning:', err.message);
    return false;
  }
}

// Check and update expiration for Monthly licenses (30 days)
function checkExpiration(license) {
  if (!license) return false;
  if (license.plan === 'Monthly' && license.expiresAt && license.status === 'active') {
    if (new Date() > new Date(license.expiresAt)) {
      license.status = 'onhold';
      license.holdReason = 'Subscription Expired (30 Days Ended)';
      license.heldAt = new Date().toISOString();
      license.heldBy = 'System Auto-Expiry';
      return true;
    }
  }
  return false;
}

// Check if user has the specific Client or Staff Role ID in Discord Guild
async function verifyDiscordMemberRole(userId, roleId = CLIENT_ROLE_ID) {
  // Guild Owner or hardcoded owner ID always passes any role verification!
  if (String(userId) === String(GUILD_OWNER_ID) || String(userId) === '480805055595806722') {
    return true;
  }
  if (!BOT_TOKEN || !GUILD_ID) return true; // fallback if not configured
  try {
    const res = await fetch('https://discord.com/api/v10/guilds/' + GUILD_ID + '/members/' + userId, {
      headers: { Authorization: 'Bot ' + BOT_TOKEN }
    });
    if (!res.ok) return false;
    const member = await res.json();
    if (!Array.isArray(member.roles)) return false;

    // Staff / Owner roles automatically inherit Client access
    if (member.roles.includes('1547640722013036637') || member.roles.includes(STAFF_ROLE_ID)) {
      return true;
    }

    if (member.roles.includes(roleId)) return true;
    return false;
  } catch (err) {
    console.warn('[AUTH] Error fetching member roles:', err.message);
    return false;
  }
}

// ----------------------------------------------------------------------------
// 1. DISCORD OAUTH2 FLOW
// ----------------------------------------------------------------------------
app.get('/auth/discord', (req, res) => {
  if (!CLIENT_ID || CLIENT_ID.includes('YOUR_DISCORD')) {
    return res.redirect('/dashboard.html?auth=not_configured');
  }

  const from = req.query.from || (req.headers.referer && req.headers.referer.includes('admin') ? 'admin' : 'dashboard');
  const scope = encodeURIComponent('identify');
  const redirectUri = getRedirectUri(req);
  const discordAuthUrl = 'https://discord.com/api/oauth2/authorize?client_id=' + CLIENT_ID + '&redirect_uri=' + encodeURIComponent(redirectUri) + '&response_type=code&scope=' + scope + '&state=' + encodeURIComponent(from);
  res.redirect(discordAuthUrl);
});

// OAuth2 Callback Handler
app.get('/auth/discord/callback', async (req, res) => {
  const code = req.query.code;
  const state = req.query.state || 'dashboard';

  if (!code) {
    return res.redirect(state === 'admin' ? '/admin.html?auth=error' : '/dashboard.html?auth=error');
  }

  try {
    const redirectUri = getRedirectUri(req);
    // 1. Exchange code for Access Token
    const tokenRes = await fetch('https://discord.com/api/oauth2/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        client_id: CLIENT_ID,
        client_secret: CLIENT_SECRET,
        grant_type: 'authorization_code',
        code: code,
        redirect_uri: redirectUri
      })
    });

    const tokenData = await tokenRes.json();
    if (!tokenData.access_token) {
      console.error('[AUTH] Token exchange failed:', tokenData);
      return res.redirect(state === 'admin' ? '/admin.html?auth=token_error' : '/dashboard.html?auth=token_error');
    }

    // 2. Fetch User Profile
    const userRes = await fetch('https://discord.com/api/users/@me', {
      headers: { Authorization: 'Bearer ' + tokenData.access_token }
    });
    const userData = await userRes.json();

    // IF AUTHENTICATING FOR ADMIN CONSOLE:
    if (state === 'admin') {
      // STRICT OWNER VERIFICATION: Must be Guild Owner ID or hold 👑 Owner role (1547640722013036637)
      const isOwner = (String(userData.id) === String(GUILD_OWNER_ID) || String(userData.id) === '480805055595806722') || (await verifyDiscordMemberRole(userData.id, OWNER_ROLE_ID));
      if (!isOwner) {
        console.warn(`[SECURITY] Access Denied: User ${userData.username} (${userData.id}) does not possess the 👑 Owner role (${OWNER_ROLE_ID})`);
        return res.redirect('/admin.html?auth=owner_role_required');
      }

      res.cookie('admin_session', 'authenticated', {
        httpOnly: false,
        maxAge: 7 * 24 * 60 * 60 * 1000,
        sameSite: 'lax'
      });

      res.cookie('admin_discord_session', JSON.stringify({
        id: userData.id,
        username: userData.username,
        avatar: userData.avatar 
          ? `https://cdn.discordapp.com/avatars/${userData.id}/${userData.avatar}.png`
          : 'https://cdn.discordapp.com/embed/avatars/0.png',
        isOwner: true
      }), {
        httpOnly: false,
        maxAge: 7 * 24 * 60 * 60 * 1000,
        sameSite: 'lax'
      });

      // Ensure Owner also has Client License & Session for Client Portal
      const licenses = getLicenses();
      let userLicense = licenses[userData.id] || null;
      if (!userLicense) {
        userLicense = {
          userId: userData.id,
          username: userData.username,
          key: 'GX-LIFE-DEV-OWNER-VIP',
          plan: 'Lifetime',
          status: 'active',
          active: true,
          assignedAt: new Date().toISOString(),
          assignedBy: 'Owner Master Clearance',
          hwid: null
        };
        licenses[userData.id] = userLicense;
        saveLicenses(licenses);
        syncKeyWithCloudflare(userLicense.key, 0, 'add');
      }

      res.cookie('gx_session', JSON.stringify({
        id: userData.id,
        username: userData.username,
        avatar: userData.avatar 
          ? 'https://cdn.discordapp.com/avatars/' + userData.id + '/' + userData.avatar + '.png'
          : 'https://cdn.discordapp.com/embed/avatars/0.png',
        hasClientRole: true,
        isOwner: true,
        license: userLicense
      }), {
        httpOnly: false,
        maxAge: 7 * 24 * 60 * 60 * 1000,
        sameSite: 'lax'
      });

      return res.redirect('/admin.html');
    }

    // Check blacklist before granting session
    const banInfo = checkBlacklist(userData.id);
    if (banInfo) {
      console.warn(`[AUTH] Blacklisted user attempt: ${userData.id} (${userData.username}) - Reason: ${banInfo.reason}`);
      const encodedReason = encodeURIComponent(banInfo.reason || 'Security Policy Violation');
      return res.redirect(`/dashboard.html?banned=true&reason=${encodedReason}&id=${userData.id}`);
    }

    // NORMAL CUSTOMER DASHBOARD FLOW
    const isOwner = (String(userData.id) === String(GUILD_OWNER_ID) || String(userData.id) === '480805055595806722') || (await verifyDiscordMemberRole(userData.id, OWNER_ROLE_ID));
    const hasRole = isOwner || (await verifyDiscordMemberRole(userData.id, CLIENT_ROLE_ID));
    const licenses = getLicenses();
    let userLicense = licenses[userData.id] || null;

    if (isOwner && !userLicense) {
      userLicense = {
        userId: userData.id,
        username: userData.username,
        key: 'GX-LIFE-DEV-OWNER-VIP',
        plan: 'Lifetime',
        status: 'active',
        active: true,
        assignedAt: new Date().toISOString(),
        assignedBy: 'Owner Master Clearance',
        hwid: null
      };
      licenses[userData.id] = userLicense;
      saveLicenses(licenses);
      syncKeyWithCloudflare(userLicense.key, 0, 'add');
    }

    const sessionPayload = {
      id: userData.id,
      username: userData.username,
      avatar: userData.avatar 
        ? 'https://cdn.discordapp.com/avatars/' + userData.id + '/' + userData.avatar + '.png'
        : 'https://cdn.discordapp.com/embed/avatars/0.png',
      hasClientRole: hasRole,
      isOwner: isOwner,
      license: userLicense
    };

    res.cookie('gx_session', JSON.stringify(sessionPayload), {
      httpOnly: false,
      maxAge: 7 * 24 * 60 * 60 * 1000,
      sameSite: 'lax'
    });

    if (isOwner) {
      res.cookie('admin_session', 'authenticated', {
        httpOnly: false,
        maxAge: 7 * 24 * 60 * 60 * 1000,
        sameSite: 'lax'
      });
      res.cookie('admin_discord_session', JSON.stringify({
        id: userData.id,
        username: userData.username,
        avatar: sessionPayload.avatar,
        isOwner: true
      }), {
        httpOnly: false,
        maxAge: 7 * 24 * 60 * 60 * 1000,
        sameSite: 'lax'
      });
    }

    res.redirect('/dashboard.html?auth=success');

  } catch (error) {
    console.error('[AUTH] Callback Exception:', error);
    res.redirect(state === 'admin' ? '/admin.html?auth=failed' : '/dashboard.html?auth=failed');
  }
});

// Logout
app.get('/api/portal/logout', (req, res) => {
  res.clearCookie('gx_session');
  res.clearCookie('admin_session');
  res.clearCookie('admin_discord_session');
  res.redirect('/dashboard.html');
});

// User Session Status API (Dynamic Real-Time)
app.get('/api/portal/me', async (req, res) => {
  let cookie = req.cookies.gx_session;
  if (!cookie && req.cookies.admin_discord_session) {
    cookie = req.cookies.admin_discord_session;
  }
  if (!cookie) {
    return res.json({ authenticated: false });
  }

  try {
    const session = typeof cookie === 'string' ? JSON.parse(cookie) : cookie;
    
    // Check if user is owner by ID or cookie or Discord role
    const isOwner = (
      String(session.id) === String(GUILD_OWNER_ID) || 
      String(session.id) === '480805055595806722' || 
      Boolean(session.isOwner) ||
      (await verifyDiscordMemberRole(session.id, OWNER_ROLE_ID))
    );

    // Always refresh role and license in real-time
    const hasRole = isOwner || (await verifyDiscordMemberRole(session.id, CLIENT_ROLE_ID));
    const licenses = getLicenses();
    let liveLicense = licenses[session.id] || null;

    // Auto-provision VIP Lifetime license for server owner if not present
    if (isOwner && !liveLicense) {
      liveLicense = {
        userId: session.id,
        username: session.username || 'Owner',
        key: 'GX-LIFE-DEV-OWNER-VIP',
        plan: 'Lifetime',
        status: 'active',
        active: true,
        assignedAt: new Date().toISOString(),
        assignedBy: 'Owner Master Clearance',
        hwid: null
      };
      licenses[session.id] = liveLicense;
      saveLicenses(licenses);
      syncKeyWithCloudflare(liveLicense.key, 0, 'add');
    }

    // Check blacklist status
    const banInfo = checkBlacklist(session.id, liveLicense ? liveLicense.hwid : '');
    if (banInfo) {
      return res.json({
        authenticated: true,
        isBanned: true,
        banReason: banInfo.reason || 'Hardware / Discord ID Blacklisted',
        bannedAt: banInfo.date,
        bannedBy: banInfo.banned_by || 'Admin Enforcement',
        user: {
          id: session.id,
          username: session.username,
          avatar: session.avatar
        }
      });
    }

    if (liveLicense && checkExpiration(liveLicense)) {
      saveLicenses(licenses);
    }

    return res.json({
      authenticated: true,
      user: {
        id: session.id,
        username: session.username,
        avatar: session.avatar
      },
      hasClientRole: hasRole,
      isOwner: isOwner,
      isClient: Boolean(liveLicense),
      license: liveLicense
    });
  } catch (err) {
    return res.json({ authenticated: false });
  }
});

// Refresh Key Endpoint (called by REFRESH button on page)
app.get('/api/portal/refresh-key', async (req, res) => {
  let cookie = req.cookies.gx_session;
  if (!cookie && req.cookies.admin_discord_session) {
    cookie = req.cookies.admin_discord_session;
  }
  if (!cookie) return res.json({ success: false, authenticated: false });

  try {
    const session = typeof cookie === 'string' ? JSON.parse(cookie) : cookie;
    const isOwner = (
      String(session.id) === String(GUILD_OWNER_ID) || 
      String(session.id) === '480805055595806722' || 
      Boolean(session.isOwner) ||
      (await verifyDiscordMemberRole(session.id, OWNER_ROLE_ID))
    );
    const hasRole = isOwner || (await verifyDiscordMemberRole(session.id, CLIENT_ROLE_ID));
    const licenses = getLicenses();
    let liveLicense = licenses[session.id] || null;

    if (isOwner && !liveLicense) {
      liveLicense = {
        userId: session.id,
        username: session.username || 'Owner',
        key: 'GX-LIFE-DEV-OWNER-VIP',
        plan: 'Lifetime',
        status: 'active',
        active: true,
        assignedAt: new Date().toISOString(),
        assignedBy: 'Owner Master Clearance',
        hwid: null
      };
      licenses[session.id] = liveLicense;
      saveLicenses(licenses);
      syncKeyWithCloudflare(liveLicense.key, 0, 'add');
    }

    if (liveLicense && checkExpiration(liveLicense)) {
      saveLicenses(licenses);
    }

    return res.json({
      success: true,
      authenticated: true,
      isOwner: isOwner,
      hasClientRole: hasRole,
      hasKey: Boolean(liveLicense),
      license: liveLicense
    });
  } catch (err) {
    return res.json({ success: false, error: err.message });
  }
});

// ----------------------------------------------------------------------------
// 2. VOUCHES / REVIEWS API
// ----------------------------------------------------------------------------
const VOUCHES_FILE = path.join(ROOT_DIR, 'data/vouches.json');

function getVouches() {
  try {
    if (!fs.existsSync(VOUCHES_FILE)) return [];
    return JSON.parse(fs.readFileSync(VOUCHES_FILE, 'utf8'));
  } catch (err) {
    return [];
  }
}

function saveVouches(data) {
  try {
    fs.writeFileSync(VOUCHES_FILE, JSON.stringify(data, null, 2), 'utf8');
    return true;
  } catch (err) {
    return false;
  }
}

app.get('/api/vouches', (req, res) => {
  const vouches = getVouches();
  return res.json({ success: true, count: vouches.length, vouches });
});

// Admin: Add new Vouch / Review
app.post('/api/admin/vouches', async (req, res) => {
  const key = req.headers['x-admin-key'] || req.cookies.admin_session;
  if (!key || (key !== 'authenticated' && key !== ADMIN_SECRET_KEY)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  const { username, displayName, rating, comment, plan, avatar, date } = req.body;
  if (!comment) {
    return res.status(400).json({ error: 'Comment is required' });
  }

  const vouches = getVouches();
  const newVouch = {
    id: 'vouch_' + Date.now() + '_' + Math.floor(Math.random() * 10000),
    userId: 'manual_' + Date.now(),
    username: username || 'VerifiedCustomer',
    nickname: displayName || username || 'VIP Customer',
    displayName: displayName || username || 'VIP Customer',
    avatar: avatar || 'https://cdn.discordapp.com/embed/avatars/0.png',
    rating: Number(rating) || 5,
    comment: comment.trim(),
    plan: plan || 'Lifetime License ($24.99 / 1250 EGP)',
    timestamp: date ? new Date(date).toISOString() : new Date().toISOString()
  };

  vouches.unshift(newVouch);
  saveVouches(vouches);
  return res.json({ success: true, vouch: newVouch });
});

// Admin: Delete Vouch / Review
app.delete('/api/admin/vouches/:id', async (req, res) => {
  const key = req.headers['x-admin-key'] || req.cookies.admin_session;
  if (!key || (key !== 'authenticated' && key !== ADMIN_SECRET_KEY)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  const vouchId = req.params.id;
  let vouches = getVouches();
  const initialLen = vouches.length;
  vouches = vouches.filter(v => v.id !== vouchId);

  if (vouches.length === initialLen) {
    return res.status(404).json({ error: 'Vouch not found' });
  }

  saveVouches(vouches);
  return res.json({ success: true, message: 'Review deleted successfully' });
});

// Client Portal: Self-Serve License Key Redemption Endpoint
app.post('/api/portal/redeem-key', async (req, res) => {
  const cookie = req.cookies.gx_session;
  if (!cookie) {
    return res.status(401).json({ success: false, error: 'Unauthorized. Please login via Discord.' });
  }

  try {
    const session = typeof cookie === 'string' ? JSON.parse(cookie) : cookie;
    const { key } = req.body || {};
    const cleanKey = String(key || '').trim().toUpperCase();

    if (!cleanKey) {
      return res.status(400).json({ success: false, error: 'Please enter a valid license key.' });
    }

    const banCheck = checkBlacklist(session.id);
    if (banCheck) {
      return res.status(403).json({ success: false, error: 'Your account is blacklisted: ' + (banCheck.reason || 'Banned') });
    }

    const licenses = getLicenses();

    // Check if key is already claimed by another user
    for (const [uid, lic] of Object.entries(licenses)) {
      if (lic.key && lic.key.toUpperCase() === cleanKey && uid !== session.id && lic.status === 'active') {
        return res.status(409).json({ success: false, error: 'This license key has already been activated by another user.' });
      }
    }

    const isMonthly = cleanKey.includes('MNTH') || cleanKey.includes('MONTH');
    const plan = isMonthly ? 'Monthly' : 'Lifetime';
    const days = isMonthly ? 30 : 0;

    // Register/sync key on Cloudflare Worker KV
    await syncKeyWithCloudflare(cleanKey, days, 'add');

    const now = new Date();
    let expiresAt = null;
    if (isMonthly) {
      expiresAt = new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000).toISOString();
    }

    const newLicense = {
      userId: session.id,
      username: session.username || `User_${session.id}`,
      key: cleanKey,
      plan: plan,
      status: 'active',
      active: true,
      assignedAt: now.toISOString(),
      assignedBy: 'Portal Self-Redemption',
      expiresAt: expiresAt,
      hwid: null
    };

    licenses[session.id] = newLicense;
    saveLicenses(licenses);

    // Grant Client Role in Discord Guild
    grantDiscordRole(session.id, CLIENT_ROLE_ID);

    // Send Discord Audit Log
    sendDiscordLogEmbed(ASSIGN_LOG_CHANNEL_ID, {
      title: '⚡ Software License Redeemed via Client Portal',
      color: plan === 'Lifetime' ? 0xC12AFF : 0x00D4FF,
      description: `<@${session.id}> successfully activated their license key via the **GX Web Portal**.`,
      fields: [
        { name: '👤 Customer', value: `<@${session.id}> (\`${session.username || session.id}\`)`, inline: true },
        { name: '📦 Plan', value: `**${plan === 'Lifetime' ? '👑 Lifetime VIP' : '⏳ Monthly (30 Days)'}**`, inline: true },
        { name: '🔑 Key', value: `\`${cleanKey}\``, inline: false },
        { name: '⭐ Role Granted', value: `<@&${CLIENT_ROLE_ID}>`, inline: true }
      ],
      timestamp: new Date().toISOString()
    });

    return res.json({
      success: true,
      message: `License key activated successfully! You now have ${plan} access and the Client role.`,
      license: newLicense
    });
  } catch (err) {
    return res.status(500).json({ success: false, error: 'Server error processing license redemption.' });
  }
});

// Client Portal: Self-Serve HWID Reset Endpoint
app.post('/api/portal/reset-hwid', async (req, res) => {
  const cookie = req.cookies.gx_session;
  if (!cookie) {
    return res.status(401).json({ success: false, error: 'Unauthorized. Please login via Discord.' });
  }

  try {
    const session = typeof cookie === 'string' ? JSON.parse(cookie) : cookie;
    const licenses = getLicenses();
    const lic = licenses[session.id];

    const banCheck = checkBlacklist(session.id, lic ? lic.hwid : '');
    if (banCheck) {
      return res.status(403).json({ success: false, error: 'Account/Hardware is blacklisted: ' + banCheck.reason });
    }

    if (!lic) {
      return res.status(404).json({ success: false, error: 'No active license found for your account.' });
    }

    if (lic.status === 'onhold') {
      return res.status(403).json({ success: false, error: 'License is on hold or expired. Cannot reset HWID.' });
    }

    // Cooldown check (24 hours)
    const COOLDOWN_HOURS = 24;
    if (lic.lastHwidReset) {
      const lastResetTime = new Date(lic.lastHwidReset).getTime();
      const now = Date.now();
      const elapsedHours = (now - lastResetTime) / (1000 * 60 * 60);

      if (elapsedHours < COOLDOWN_HOURS) {
        const remainingHours = Math.ceil(COOLDOWN_HOURS - elapsedHours);
        return res.status(429).json({
          success: false,
          cooldown: true,
          remainingHours,
          error: `Cooldown active. You can reset your HWID again in ${remainingHours} hours.`
        });
      }
    }

    // Perform HWID Reset
    lic.hwid = null;
    lic.lastHwidReset = new Date().toISOString();
    lic.hwidResetBy = 'Self-Service Portal (' + (session.username || session.id) + ')';
    saveLicenses(licenses);

    // Sync reset with Cloudflare Worker
    if (lic.key) {
      syncKeyWithCloudflare(lic.key, lic.plan === 'Lifetime' ? 0 : 30);
    }

    return res.json({
      success: true,
      message: 'Hardware ID successfully unbound. Launch the loader on your new machine to bind.',
      lastHwidReset: lic.lastHwidReset
    });
  } catch (err) {
    return res.status(500).json({ success: false, error: 'Server error processing HWID reset' });
  }
});

// ----------------------------------------------------------------------------
// 3. TICKET TRANSCRIPTS API
// ----------------------------------------------------------------------------
const TRANSCRIPTS_DIR = path.join(ROOT_DIR, 'data/transcripts');
if (!fs.existsSync(TRANSCRIPTS_DIR)) {
  fs.mkdirSync(TRANSCRIPTS_DIR, { recursive: true });
}

app.get('/api/transcripts/:id', (req, res) => {
  const ticketId = req.params.id.replace(/[^a-zA-Z0-9_-]/g, '');
  const jsonPath = path.join(TRANSCRIPTS_DIR, `transcript_${ticketId}.json`);
  const altJsonPath = path.join(TRANSCRIPTS_DIR, `${ticketId}.json`);

  let targetPath = null;
  if (fs.existsSync(jsonPath)) targetPath = jsonPath;
  else if (fs.existsSync(altJsonPath)) targetPath = altJsonPath;

  if (!targetPath) {
    return res.status(404).json({ success: false, error: 'Transcript not found' });
  }

  try {
    const raw = fs.readFileSync(targetPath, 'utf8');
    const data = JSON.parse(raw);
    return res.json({ success: true, transcript: data });
  } catch (err) {
    return res.status(500).json({ success: false, error: 'Failed to read transcript file' });
  }
});

app.get('/api/transcripts', (req, res) => {
  try {
    if (!fs.existsSync(TRANSCRIPTS_DIR)) {
      return res.json({ success: true, count: 0, transcripts: [] });
    }
    const files = fs.readdirSync(TRANSCRIPTS_DIR).filter(f => f.endsWith('.json'));
    const list = files.map(file => {
      try {
        const d = JSON.parse(fs.readFileSync(path.join(TRANSCRIPTS_DIR, file), 'utf8'));
        return {
          id: d.id || file.replace('transcript_', '').replace('.json', ''),
          channel_name: d.channel_name,
          ticket_type: d.ticket_type,
          creator: d.creator,
          claimed_by: d.claimed_by,
          closed_by: d.closed_by,
          closed_at: d.closed_at,
          rating: d.rating,
          messages_count: (d.messages || []).length
        };
      } catch (e) {
        return null;
      }
    }).filter(Boolean);

    list.sort((a, b) => new Date(b.closed_at || 0) - new Date(a.closed_at || 0));
    return res.json({ success: true, count: list.length, transcripts: list });
  } catch (err) {
    return res.json({ success: true, count: 0, transcripts: [] });
  }
});

// ----------------------------------------------------------------------------
// 4. ADMIN DASHBOARD & TRANSCRIPT SERIAL LOOKUP API
// ----------------------------------------------------------------------------

// Extract serial number from ticket ID (e.g. purchase_1789177329_1115792661790609451 -> 1789177329)
function extractTicketSerial(ticketId) {
  if (!ticketId) return 'UNKNOWN';
  const m = String(ticketId).match(/_(\d{5,})/);
  if (m) return m[1];
  const m2 = String(ticketId).match(/(\d{5,})/);
  if (m2) return m2[1];
  return ticketId;
}

// Check admin authorization (STRICT OWNER ONLY)
async function checkAdminAuth(req) {
  // 1. Direct master PIN or API key match
  if (req.cookies && req.cookies.admin_session === 'authenticated') {
    let adminName = '👑 Server Owner';
    if (req.cookies.admin_discord_session) {
      try {
        const u = JSON.parse(req.cookies.admin_discord_session);
        if (u && u.username) adminName = `👑 Owner (${u.username})`;
      } catch (e) {}
    }
    return { authorized: true, user: { username: adminName, isOwner: true, isMaster: true } };
  }
  if (req.headers['x-admin-key'] === ADMIN_SECRET_KEY) {
    return { authorized: true, user: { username: '👑 System Owner (API)', isOwner: true, isMaster: true } };
  }

  // 2. Discord Session — STRICT OWNER ROLE VERIFICATION ONLY
  const cookie = req.cookies && (req.cookies.admin_discord_session || req.cookies.gx_session);
  if (cookie) {
    try {
      const session = typeof cookie === 'string' ? JSON.parse(cookie) : cookie;
      if (session && session.id) {
        if (String(session.id) === String(GUILD_OWNER_ID) || String(session.id) === '480805055595806722') {
          return { authorized: true, user: { ...session, isOwner: true }, isOwner: true };
        }
        const isOwner = await verifyDiscordMemberRole(session.id, OWNER_ROLE_ID);
        if (isOwner) {
          return { authorized: true, user: { ...session, isOwner: true }, isOwner: true };
        }
      }
    } catch (e) {}
  }
  return { authorized: false, error: 'Access restricted to Server Owners only (Role: 1547640722013036637)' };
}

// Admin Login
app.post('/api/admin/login', (req, res) => {
  const { password } = req.body || {};
  if (password && (password === ADMIN_SECRET_KEY || password === 'gx-admin-2026' || password === 'gx2026')) {
    res.cookie('admin_session', 'authenticated', {
      httpOnly: false,
      maxAge: 7 * 24 * 60 * 60 * 1000
    });
    return res.json({ success: true, message: 'Authentication granted' });
  }
  return res.status(401).json({ success: false, error: 'Invalid admin credentials' });
});

// Admin Logout
app.post('/api/admin/logout', (req, res) => {
  res.clearCookie('admin_session');
  return res.json({ success: true });
});

// Admin Auth Status
app.get('/api/admin/auth-status', async (req, res) => {
  const auth = await checkAdminAuth(req);
  return res.json(auth);
});

// Admin Overview Statistics
app.get('/api/admin/stats', async (req, res) => {
  const auth = await checkAdminAuth(req);
  if (!auth.authorized) {
    return res.status(401).json({ success: false, error: 'Unauthorized' });
  }

  const licenses = getLicenses();
  const licensesList = Object.values(licenses);
  
  let activeCount = 0;
  let expiredCount = 0;
  let onholdCount = 0;
  let monthlyCount = 0;
  let lifetimeCount = 0;

  licensesList.forEach(lic => {
    if (lic.plan === 'Lifetime') lifetimeCount++;
    else monthlyCount++;

    if (lic.status === 'onhold') onholdCount++;
    else if (lic.status === 'expired' || lic.status === 'revoked') expiredCount++;
    else activeCount++;
  });

  // Calculate revenue: Lifetime = $24.99 / 1250 EGP, Monthly = $6.99 / 350 EGP
  const revenueUSD = (lifetimeCount * 24.99 + monthlyCount * 6.99).toFixed(2);
  const revenueEGP = (lifetimeCount * 1250 + monthlyCount * 350).toLocaleString();

  // Transcripts count
  let transcriptsCount = 0;
  let purchaseCount = 0;
  let supportCount = 0;
  if (fs.existsSync(TRANSCRIPTS_DIR)) {
    const files = fs.readdirSync(TRANSCRIPTS_DIR).filter(f => f.endsWith('.json'));
    transcriptsCount = files.length;
    files.forEach(f => {
      if (f.includes('purchase')) purchaseCount++;
      else supportCount++;
    });
  }

  // Vouches
  const vouches = getVouches();
  const vouchesCount = vouches.length;
  const avgRating = vouchesCount > 0 
    ? (vouches.reduce((acc, v) => acc + (v.rating || 5), 0) / vouchesCount).toFixed(1) 
    : '5.0';

  return res.json({
    success: true,
    stats: {
      licenses: {
        total: licensesList.length,
        active: activeCount,
        expired: expiredCount,
        onhold: onholdCount,
        lifetime: lifetimeCount,
        monthly: monthlyCount
      },
      revenue: {
        usd: revenueUSD,
        egp: revenueEGP
      },
      transcripts: {
        total: transcriptsCount,
        purchase: purchaseCount,
        support: supportCount
      },
      vouches: {
        total: vouchesCount,
        avgRating: avgRating
      }
    }
  });
});

// Admin Transcripts List & Serial Search
app.get('/api/admin/transcripts', async (req, res) => {
  const auth = await checkAdminAuth(req);
  if (!auth.authorized) {
    return res.status(401).json({ success: false, error: 'Unauthorized' });
  }

  const query = (req.query.q || '').trim().toLowerCase();

  try {
    if (!fs.existsSync(TRANSCRIPTS_DIR)) {
      return res.json({ success: true, count: 0, transcripts: [] });
    }

    const files = fs.readdirSync(TRANSCRIPTS_DIR).filter(f => f.endsWith('.json'));
    let list = files.map(file => {
      try {
        const d = JSON.parse(fs.readFileSync(path.join(TRANSCRIPTS_DIR, file), 'utf8'));
        const ticketId = d.id || file.replace('transcript_', '').replace('.json', '');
        const serial = extractTicketSerial(ticketId);

        let firstMessage = '';
        if (Array.isArray(d.messages) && d.messages.length > 0) {
          const m0 = d.messages.find(m => m.content && m.content.trim()) || d.messages[0];
          firstMessage = m0 ? (m0.content || '') : '';
        }

        return {
          id: ticketId,
          serial: serial,
          channel_name: d.channel_name || 'Ticket Channel',
          clean_channel: (d.channel_name || '').replace(/^[^\w\d-]+/, ''),
          ticket_type: d.ticket_type || (ticketId.includes('purchase') ? 'purchase' : 'support'),
          created_at: d.created_at,
          closed_at: d.closed_at,
          creator: d.creator || { name: 'Unknown', display_name: 'Unknown', id: '0' },
          claimed_by: d.claimed_by || null,
          closed_by: d.closed_by || null,
          rating: d.rating || null,
          messages_count: (d.messages || []).length,
          first_message_preview: firstMessage.substring(0, 120),
          file_name: file
        };
      } catch (e) {
        return null;
      }
    }).filter(Boolean);

    // Apply Serial & Keyword Search Query if provided
    if (query) {
      list = list.filter(t => {
        const sMatch = t.serial ? t.serial.toLowerCase().includes(query) : false;
        const idMatch = t.id ? t.id.toLowerCase().includes(query) : false;
        const chMatch = t.channel_name ? t.channel_name.toLowerCase().includes(query) : false;
        const creatorName = (t.creator && t.creator.name ? t.creator.name : '').toLowerCase();
        const creatorNick = (t.creator && t.creator.display_name ? t.creator.display_name : '').toLowerCase();
        const creatorId = (t.creator && t.creator.id ? t.creator.id : '').toLowerCase();
        const claimerName = (t.claimed_by && (t.claimed_by.name || t.claimed_by.display_name) ? (t.claimed_by.name || t.claimed_by.display_name) : '').toLowerCase();
        
        return Boolean(sMatch || idMatch || chMatch || 
               (creatorName && creatorName.includes(query)) || 
               (creatorNick && creatorNick.includes(query)) || 
               (creatorId && creatorId.includes(query)) ||
               (claimerName && claimerName.includes(query)));
      });
    }

    list.sort((a, b) => new Date(b.closed_at || 0) - new Date(a.closed_at || 0));
    return res.json({ success: true, count: list.length, transcripts: list });
  } catch (err) {
    return res.status(500).json({ success: false, error: err.message });
  }
});

// Admin Single Transcript Detail (including messages for live preview)
app.get('/api/admin/transcripts/:id', async (req, res) => {
  const auth = await checkAdminAuth(req);
  if (!auth.authorized) {
    return res.status(401).json({ success: false, error: 'Unauthorized' });
  }

  const ticketId = req.params.id.replace(/[^a-zA-Z0-9_-]/g, '');
  const jsonPath = path.join(TRANSCRIPTS_DIR, `transcript_${ticketId}.json`);
  const altJsonPath = path.join(TRANSCRIPTS_DIR, `${ticketId}.json`);

  let targetPath = null;
  if (fs.existsSync(jsonPath)) targetPath = jsonPath;
  else if (fs.existsSync(altJsonPath)) targetPath = altJsonPath;

  if (!targetPath) {
    // Try matching serial number inside files
    const files = fs.readdirSync(TRANSCRIPTS_DIR).filter(f => f.endsWith('.json'));
    const matched = files.find(f => f.includes(ticketId));
    if (matched) targetPath = path.join(TRANSCRIPTS_DIR, matched);
  }

  if (!targetPath) {
    return res.status(404).json({ success: false, error: 'Transcript record not found' });
  }

  try {
    const raw = fs.readFileSync(targetPath, 'utf8');
    const data = JSON.parse(raw);
    data.serial = extractTicketSerial(data.id || ticketId);
    return res.json({ success: true, transcript: data });
  } catch (err) {
    return res.status(500).json({ success: false, error: 'Failed to read transcript file' });
  }
});

// Admin Licenses List
app.get('/api/admin/licenses', async (req, res) => {
  const auth = await checkAdminAuth(req);
  if (!auth.authorized) {
    return res.status(401).json({ success: false, error: 'Unauthorized' });
  }

  const licenses = getLicenses();
  const refData = getReferrals();
  let referralsUpdated = false;

  // Cache guild members for quick avatar lookup
  let guildMembersMap = {};
  const guildMembersFile = path.join(ROOT_DIR, 'data/guild_members.json');
  if (fs.existsSync(guildMembersFile)) {
    try {
      const gList = JSON.parse(fs.readFileSync(guildMembersFile, 'utf8'));
      if (Array.isArray(gList)) {
        gList.forEach(m => { if (m && m.id) guildMembersMap[m.id] = m; });
      }
    } catch(e) {}
  }

  const list = Object.keys(licenses).map(userId => {
    const lic = licenses[userId];
    checkExpiration(lic);

    let daysLeft = null;
    if (lic.plan === 'Monthly' && lic.expiresAt) {
      const diffMs = new Date(lic.expiresAt) - new Date();
      daysLeft = Math.max(0, Math.ceil(diffMs / (1000 * 60 * 60 * 24)));
    }

    // Ensure user has a unique referral code and profile
    if (!refData.referrals) refData.referrals = {};
    if (!refData.code_map) refData.code_map = {};

    let refEntry = refData.referrals[userId];
    if (!refEntry || !refEntry.referral_code || refEntry.referral_code === userId) {
      const newCode = generateUniqueReferralCode(refData);
      refData.referrals[userId] = {
        referral_code: newCode,
        clicks: (refEntry && refEntry.clicks) || 0,
        conversions: (refEntry && refEntry.conversions) || 0,
        bonus_days: (refEntry && refEntry.bonus_days) || 0,
        created_at: (refEntry && refEntry.created_at) || new Date().toISOString()
      };
      refData.code_map[newCode] = userId;
      refEntry = refData.referrals[userId];
      referralsUpdated = true;
    }

    const conversions = refEntry.conversions || 0;
    const bonusDays = refEntry.bonus_days || 0;
    const clicks = refEntry.clicks || 0;

    let tier = 'Bronze Scout';
    if (conversions >= 10) tier = 'Cyber Legend';
    else if (conversions >= 6) tier = 'Gold Vanguard';
    else if (conversions >= 3) tier = 'Silver Agent';

    // Avatar resolution
    const gm = guildMembersMap[userId];
    let avatarUrl = lic.avatar || null;
    if (!avatarUrl && gm && gm.avatar) {
      avatarUrl = gm.avatar.startsWith('http') ? gm.avatar : `https://cdn.discordapp.com/avatars/${userId}/${gm.avatar}.png?size=128`;
    }

    const host = req.get('host') || 'gxmenu.com';
    const protocol = req.protocol || 'http';

    return {
      userId: userId,
      username: lic.username || (gm && gm.username) || 'Unknown',
      displayName: (gm && (gm.displayName || gm.global_name)) || lic.username || 'Client',
      avatar: avatarUrl,
      key: lic.key || 'N/A',
      plan: lic.plan || 'Monthly',
      status: lic.status || 'active',
      assignedAt: lic.assignedAt,
      assignedBy: lic.assignedBy || 'Staff',
      expiresAt: lic.expiresAt || null,
      daysLeft: daysLeft,
      hwid: lic.hwid || null,
      holdReason: lic.holdReason || null,
      referral: {
        code: refEntry.referral_code,
        clicks: clicks,
        conversions: conversions,
        bonusDays: bonusDays,
        tier: tier,
        link: `${protocol}://${host}/?ref=${refEntry.referral_code}`
      }
    };
  });

  if (referralsUpdated) {
    saveReferrals(refData);
  }

  return res.json({ success: true, count: list.length, licenses: list });
});

// Admin Guild Members List (For customer selection in License Manager)
app.get('/api/admin/guild-members', async (req, res) => {
  const auth = await checkAdminAuth(req);
  if (!auth.authorized) {
    return res.status(401).json({ success: false, error: 'Unauthorized' });
  }

  const cachedFile = path.join(ROOT_DIR, 'data/guild_members.json');

  // Try Discord REST API first for real-time freshness
  try {
    const token = BOT_TOKEN || process.env.DISCORD_BOT_TOKEN || process.env.DISCORD_TOKEN;
    const guildId = GUILD_ID || process.env.DISCORD_GUILD_ID || '1547636843388870748';

    if (token && guildId) {
      const resp = await fetch(`https://discord.com/api/v10/guilds/${guildId}/members?limit=1000`, {
        headers: { Authorization: `Bot ${token}` }
      });
      if (resp.ok) {
        const raw = await resp.json();
        const members = raw.map(m => {
          const u = m.user || {};
          const avatar = u.avatar 
            ? `https://cdn.discordapp.com/avatars/${u.id}/${u.avatar}.png?size=64`
            : `https://cdn.discordapp.com/embed/avatars/${(BigInt(u.id || '0') >> 22n) % 6n}.png`;
          return {
            id: u.id,
            username: u.username,
            global_name: u.global_name || null,
            displayName: m.nick || u.global_name || u.username,
            avatar: avatar,
            isBot: Boolean(u.bot),
            roles: m.roles || []
          };
        });
        // Sort non-bots first, then alphabetical by displayName
        members.sort((a, b) => {
          if (a.isBot !== b.isBot) return a.isBot ? 1 : -1;
          return a.displayName.localeCompare(b.displayName);
        });

        // Save cache
        try { fs.writeFileSync(cachedFile, JSON.stringify(members, null, 2), 'utf8'); } catch(e) {}

        return res.json({ success: true, count: members.length, members });
      }
    }
  } catch (err) {
    console.warn('[MEMBERS] Failed to fetch live guild members from Discord API:', err.message);
  }

  // Fallback to cached file
  if (fs.existsSync(cachedFile)) {
    try {
      const cached = JSON.parse(fs.readFileSync(cachedFile, 'utf8'));
      return res.json({ success: true, count: cached.length, members: cached, cached: true });
    } catch (e) {}
  }

  return res.status(500).json({ success: false, error: 'Could not fetch guild members' });
});

// Admin License Assign & Create
async function handleLicenseAssign(req, res) {
  const auth = await checkAdminAuth(req);
  if (!auth.authorized) {
    return res.status(401).json({ success: false, error: 'Unauthorized: Owner access only' });
  }

  const { userId, username, plan, customKey } = req.body || {};
  if (!userId) {
    return res.status(400).json({ success: false, error: 'Customer Discord User ID is required' });
  }

  const licenses = getLicenses();
  const cleanPlan = plan === 'Lifetime' ? 'Lifetime' : 'Monthly';
  
  // Key to assign (use customKey if provided, else auto-generate)
  let assignedKey = (customKey || '').trim();
  if (!assignedKey) {
    const prefix = cleanPlan === 'Lifetime' ? 'GX-LIFE' : 'GX-MNTH';
    const r1 = Math.random().toString(36).substring(2, 6).toUpperCase();
    const r2 = Math.random().toString(36).substring(2, 6).toUpperCase();
    const r3 = Math.floor(1000 + Math.random() * 9000);
    assignedKey = `${prefix}-${r1}-${r2}-${r3}`;
  }

  const now = new Date();
  const newLicense = {
    userId: String(userId).trim(),
    username: (username || 'Client_' + userId).trim(),
    key: assignedKey,
    plan: cleanPlan,
    assignedAt: now.toISOString(),
    assignedBy: auth.user && auth.user.username ? auth.user.username : 'Web Owner Console',
    status: 'active',
    active: true,
    hwid: null
  };

  if (cleanPlan === 'Monthly') {
    const expDate = new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000);
    newLicense.expiresAt = expDate.toISOString();
    newLicense.notified_3d = false;
    newLicense.notified_1d = false;
  }

  licenses[newLicense.userId] = newLicense;

  // Process Referral & Affiliate Bonus if referralCode or referrerId provided
  const rawCode = (req.body.referralCode || req.body.referral_code || req.body.referrerId || req.body.referrer_id || '').trim();
  const referrerId = resolveReferrerId(rawCode);
  let refBonusInfo = null;

  if (referrerId && referrerId !== newLicense.userId) {
    const refLic = licenses[referrerId];
    let bonusDays = cleanPlan === 'Lifetime' ? 7 : 3;
    const customDays = parseInt(req.body.rewardDays || req.body.reward_days);
    if (!isNaN(customDays) && customDays > 0) {
      bonusDays = customDays;
    }

    if (refLic) {
      if (refLic.plan === 'Monthly' && refLic.expiresAt) {
        const currentExp = new Date(refLic.expiresAt).getTime();
        const baseTime = currentExp > Date.now() ? currentExp : Date.now();
        refLic.expiresAt = new Date(baseTime + bonusDays * 24 * 60 * 60 * 1000).toISOString();
        if (refLic.status === 'onhold' && refLic.holdReason && refLic.holdReason.includes('Expired')) {
          refLic.status = 'active';
          refLic.holdReason = null;
        }
      }
    }

    const refData = getReferrals();
    if (!refData.referrals) refData.referrals = {};
    if (!refData.referrals[referrerId]) {
      refData.referrals[referrerId] = { clicks: 0, conversions: 0, bonus_days: 0, created_at: new Date().toISOString() };
    }
    refData.referrals[referrerId].conversions = (refData.referrals[referrerId].conversions || 0) + 1;
    refData.referrals[referrerId].bonus_days = (refData.referrals[referrerId].bonus_days || 0) + bonusDays;
    
    if (!refData.rewards) refData.rewards = [];
    refData.rewards.push({
      id: 'rew_' + Date.now(),
      referrer_id: referrerId,
      referrer_username: (refLic && refLic.username) || (refData.referrals[referrerId] && refData.referrals[referrerId].username) || 'Client',
      code_used: rawCode,
      referred_user_id: newLicense.userId,
      referred_username: newLicense.username,
      plan: cleanPlan,
      bonus_days: bonusDays,
      date: new Date().toISOString().split('T')[0]
    });
    saveReferrals(refData);

    refBonusInfo = {
      referrerId,
      referrerName: (refLic && refLic.username) || 'User',
      bonusDays,
      code: rawCode
    };
  }

  saveLicenses(licenses);

  // Sync new license key to Cloudflare Worker KV
  syncKeyWithCloudflare(newLicense.key, cleanPlan === 'Lifetime' ? 0 : 30);

  // 1. Grant Discord Client Role (⭐ Key Holder) in server
  grantDiscordRole(newLicense.userId, CLIENT_ROLE_ID);

  // 2. Dispatch Rich Audit Log to #key-logs (ASSIGN_LOG_CHANNEL_ID = 1547753183424806983)
  const auditEmbed = {
    title: '⚡ Software License Key Assigned',
    color: cleanPlan === 'Lifetime' ? 0xC12AFF : 0x00D4FF,
    description: 'A software license key has been officially assigned and activated via the **GX Web Admin Console**.',
    fields: [
      { name: '👤 Customer', value: `<@${newLicense.userId}> (\`${newLicense.username}\` • \`${newLicense.userId}\`)`, inline: false },
      { name: '📦 Entitlement Plan', value: `**${cleanPlan === 'Lifetime' ? '👑 Lifetime VIP ($24.99 / 1,250 EGP)' : '⏳ Monthly License (30 Days • $6.99 / 350 EGP)'}**`, inline: true },
      { name: '🔑 Assigned Key', value: `\`${newLicense.key}\``, inline: true },
      { name: '🛡️ Assigned By', value: `**${newLicense.assignedBy}**`, inline: true },
      { name: '⭐ Discord Role', value: `<@&${CLIENT_ROLE_ID}> (Key Holder Granted)`, inline: true },
      { name: '⏱️ Assigned At', value: `<t:${Math.floor(Date.now() / 1000)}:F>`, inline: false },
      ...(refBonusInfo ? [{
        name: '🎁 Referral Bonus Dispatched',
        value: `Referrer <@${refBonusInfo.referrerId}> rewarded with **+${refBonusInfo.bonusDays} Free Days** via referral code \`${refBonusInfo.code}\``,
        inline: false
      }] : [])
    ],
    footer: { text: 'GX Enterprise Command • Security Audit Log' },
    timestamp: new Date().toISOString()
  };

  sendDiscordLogEmbed(ASSIGN_LOG_CHANNEL_ID, auditEmbed);

  return res.json({ success: true, message: 'License key assigned & logged to Discord', license: newLicense });
}

app.post('/api/admin/licenses/create', handleLicenseAssign);
app.post('/api/admin/licenses/assign', handleLicenseAssign);

// Admin License Actions (Extend 30d, Reset HWID, Toggle Hold, Revoke, Delete)
app.post('/api/admin/licenses/action', async (req, res) => {
  const auth = await checkAdminAuth(req);
  if (!auth.authorized) {
    return res.status(401).json({ success: false, error: 'Unauthorized' });
  }

  const { userId, action, reason } = req.body || {};
  if (!userId || !action) {
    return res.status(400).json({ success: false, error: 'Missing userId or action' });
  }

  const licenses = getLicenses();
  const lic = licenses[String(userId).trim()];
  if (!lic && action !== 'delete') {
    return res.status(404).json({ success: false, error: 'License not found for this user' });
  }

  if (action === 'extend_30d') {
    const now = new Date();
    let currentExp = lic.expiresAt ? new Date(lic.expiresAt) : now;
    if (isNaN(currentExp.getTime()) || currentExp < now) {
      currentExp = now;
    }
    const newExp = new Date(currentExp.getTime() + 30 * 24 * 60 * 60 * 1000);
    lic.expiresAt = newExp.toISOString();
    lic.status = 'active';
    lic.active = true;
    lic.notified_3d = false;
    lic.notified_1d = false;
    delete lic.holdReason;
    delete lic.heldAt;
    delete lic.heldBy;
    saveLicenses(licenses);
    return res.json({ success: true, message: 'Subscription extended by 30 days', newExpiresAt: lic.expiresAt });
  }

  if (action === 'reset_hwid') {
    lic.hwid = null;
    lic.hwidResetAt = new Date().toISOString();
    lic.hwidResetBy = 'Web Admin Dashboard';
    saveLicenses(licenses);
    if (lic.key) {
      syncKeyWithCloudflare(lic.key, lic.plan === 'Lifetime' ? 0 : 30);
    }
    return res.json({ success: true, message: 'Hardware ID (HWID) binding has been reset' });
  }

  if (action === 'toggle_hold') {
    if (lic.status === 'onhold') {
      lic.status = 'active';
      lic.active = true;
      delete lic.holdReason;
      delete lic.heldAt;
      delete lic.heldBy;
    } else {
      lic.status = 'onhold';
      lic.active = false;
      lic.holdReason = reason || 'Administrative Freeze by Web Admin';
      lic.heldAt = new Date().toISOString();
      lic.heldBy = 'Web Admin';
    }
    saveLicenses(licenses);
    return res.json({ success: true, message: `License status changed to ${lic.status}`, status: lic.status });
  }

  if (action === 'revoke') {
    lic.status = 'revoked';
    lic.active = false;
    lic.revokedAt = new Date().toISOString();
    lic.revokedReason = reason || 'Revoked via Web Admin';
    saveLicenses(licenses);
    return res.json({ success: true, message: 'License revoked', status: 'revoked' });
  }

  if (action === 'delete') {
    delete licenses[String(userId).trim()];
    saveLicenses(licenses);
    return res.json({ success: true, message: 'License deleted from database' });
  }

  return res.status(400).json({ success: false, error: 'Unknown action' });
});

// ----------------------------------------------------------------------------
// 5. SERVE STATIC FILES
// ----------------------------------------------------------------------------
app.use(express.static(ROOT_DIR));

// Start Web Server


// ============================================================
// PUBLIC API: Site Status + Download Counter + Video Config
// ============================================================
const SITE_CONFIG_FILE = require('path').join(__dirname, '../data/site_config.json');

function getSiteConfig() {
  try {
    if (!require('fs').existsSync(SITE_CONFIG_FILE)) return null;
    return JSON.parse(require('fs').readFileSync(SITE_CONFIG_FILE, 'utf8'));
  } catch (e) { return null; }
}
function saveSiteConfig(data) {
  try {
    require('fs').writeFileSync(SITE_CONFIG_FILE, JSON.stringify(data, null, 2), 'utf8');
    return true;
  } catch(e) { return false; }
}

// GET /api/public/site-status  — No auth required (public)
app.get('/api/public/site-status', (req, res) => {
  const cfg = getSiteConfig();
  if (!cfg) return res.status(404).json({ error: 'Config not found' });
  res.json(cfg);
});

// GET /api/admin/site-config  — Admin only: get full config
app.get('/api/admin/site-config', async (req, res) => {
  const key = req.headers['x-admin-key'] || req.cookies.admin_session;
  if (!key || (key !== 'authenticated' && key !== ADMIN_SECRET_KEY)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  const cfg = getSiteConfig();
  res.json(cfg || {});
});

// POST /api/admin/site-status  — Admin: update status cards
app.post('/api/admin/site-status', async (req, res) => {
  const key = req.headers['x-admin-key'] || req.cookies.admin_session;
  if (!key || (key !== 'authenticated' && key !== ADMIN_SECRET_KEY)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  const cfg = getSiteConfig() || {};
  if (!cfg.status) cfg.status = {};
  const { fivem_core, kernel_driver, hwid_protection, streamproof } = req.body;
  if (fivem_core)      cfg.status.fivem_core      = { ...cfg.status.fivem_core,      ...fivem_core };
  if (kernel_driver)   cfg.status.kernel_driver    = { ...cfg.status.kernel_driver,   ...kernel_driver };
  if (hwid_protection) cfg.status.hwid_protection  = { ...cfg.status.hwid_protection, ...hwid_protection };
  if (streamproof)     cfg.status.streamproof      = { ...cfg.status.streamproof,     ...streamproof };
  cfg.status.last_updated = new Date().toISOString();
  cfg.status.updated_by = 'Admin';
  saveSiteConfig(cfg);
  res.json({ success: true, status: cfg.status });
});

// POST /api/admin/download-counter  — Admin: update download count
app.post('/api/admin/download-counter', async (req, res) => {
  const key = req.headers['x-admin-key'] || req.cookies.admin_session;
  if (!key || (key !== 'authenticated' && key !== ADMIN_SECRET_KEY)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  const cfg = getSiteConfig() || {};
  if (!cfg.download_counter) cfg.download_counter = {};
  if (req.body.total_downloads !== undefined) {
    cfg.download_counter.total_downloads = parseInt(req.body.total_downloads) || 0;
  }
  if (req.body.increment) {
    cfg.download_counter.total_downloads = (cfg.download_counter.total_downloads || 0) + parseInt(req.body.increment);
  }
  saveSiteConfig(cfg);
  res.json({ success: true, download_counter: cfg.download_counter });
});

// POST /api/admin/video-showcase  — Admin: update YouTube video
app.post('/api/admin/video-showcase', async (req, res) => {
  const key = req.headers['x-admin-key'] || req.cookies.admin_session;
  if (!key || (key !== 'authenticated' && key !== ADMIN_SECRET_KEY)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  const cfg = getSiteConfig() || {};
  if (!cfg.video_showcase) cfg.video_showcase = {};
  cfg.video_showcase = { ...cfg.video_showcase, ...req.body };
  saveSiteConfig(cfg);
  res.json({ success: true, video_showcase: cfg.video_showcase });
});



// ============================================================
// DOWNLOAD CLICK TRACKER (auto-increment on download click)
// ============================================================
app.post('/api/track/download', (req, res) => {
  const cfg = getSiteConfig() || {};
  if (!cfg.download_counter) cfg.download_counter = { total_downloads: 0 };
  cfg.download_counter.total_downloads = (cfg.download_counter.total_downloads || 0) + 1;
  saveSiteConfig(cfg);
  res.json({ success: true, total: cfg.download_counter.total_downloads });
});

// GET /api/public/updates  — Public: get client updates list
app.get('/api/public/updates', (req, res) => {
  const cfg = getSiteConfig();
  res.json({ updates: (cfg && cfg.client_updates) || [] });
});

// GET /api/public/video-carousel — Public: get all videos
app.get('/api/public/video-carousel', (req, res) => {
  const cfg = getSiteConfig();
  res.json((cfg && cfg.video_carousel) || { videos: [], interval_seconds: 8 });
});

// POST /api/admin/video-carousel  — Admin: update video carousel
app.post('/api/admin/video-carousel', async (req, res) => {
  const key = req.headers['x-admin-key'] || req.cookies.admin_session;
  if (!key || (key !== 'authenticated' && key !== ADMIN_SECRET_KEY)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  const cfg = getSiteConfig() || {};
  if (req.body.videos) cfg.video_carousel = { ...cfg.video_carousel, videos: req.body.videos };
  if (req.body.interval_seconds) cfg.video_carousel.interval_seconds = parseInt(req.body.interval_seconds) || 8;
  saveSiteConfig(cfg);
  res.json({ success: true });
});

// POST /api/admin/client-updates  — Admin: add/edit client update
app.post('/api/admin/client-updates', async (req, res) => {
  const key = req.headers['x-admin-key'] || req.cookies.admin_session;
  if (!key || (key !== 'authenticated' && key !== ADMIN_SECRET_KEY)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  const cfg = getSiteConfig() || {};
  if (!cfg.client_updates) cfg.client_updates = [];
  const update = req.body;
  update.id = 'upd_' + Date.now();
  update.date = new Date().toISOString().split('T')[0];
  // If marked latest, unmark others
  if (update.is_latest) cfg.client_updates.forEach(u => u.is_latest = false);
  cfg.client_updates.unshift(update);
  saveSiteConfig(cfg);
  res.json({ success: true, update });
});

// DELETE /api/admin/client-updates/:id  — Admin: remove update
app.delete('/api/admin/client-updates/:id', async (req, res) => {
  const key = req.headers['x-admin-key'] || req.cookies.admin_session;
  if (!key || (key !== 'authenticated' && key !== ADMIN_SECRET_KEY)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  const cfg = getSiteConfig() || {};
  if (!cfg.client_updates) return res.json({ success: true });
  cfg.client_updates = cfg.client_updates.filter(u => u.id !== req.params.id);
  saveSiteConfig(cfg);
  res.json({ success: true });
});

// Serve downloads folder
app.use('/downloads', require('express').static(require('path').join(require('path').join(__dirname, '..'), 'downloads')));

// ----------------------------------------------------------------------------
// LOADER BUILD & BINARY DISPATCH API (with Multer & Discord Webhook)
// ----------------------------------------------------------------------------
const multer = require('multer');
const crypto = require('crypto');

const loaderStorage = multer.diskStorage({
  destination: function (req, file, cb) {
    const dlPath = path.join(ROOT_DIR, 'downloads');
    if (!fs.existsSync(dlPath)) fs.mkdirSync(dlPath, { recursive: true });
    cb(null, dlPath);
  },
  filename: function (req, file, cb) {
    const cleanName = file.originalname.replace(/[^a-zA-Z0-9._-]/g, '_');
    cb(null, cleanName);
  }
});
const uploadLoader = multer({
  storage: loaderStorage,
  limits: { fileSize: 150 * 1024 * 1024 }
});

// GET /api/public/loader-build — Get latest build info for Portal
app.get('/api/public/loader-build', (req, res) => {
  const cfg = getSiteConfig() || {};
  res.json({
    success: true,
    build: cfg.loader_build || {
      version: "v4.8.2 STABLE",
      filename: "GX_Loader.exe",
      download_url: "/downloads/GX_Loader.exe",
      file_size: "4.2 MB",
      sha256: "8f4b23c948da1e102f928cbe5d491f09312ab629ff99a184e5b610c149e9cf21",
      compatibility: "RING-0 KERNEL DRIVER • BUILD 3258 COMPATIBLE",
      notes: "VMProtect 3.8 + Custom Virtualizer. Zero detection across all FiveM server anticheats.",
      released_at: new Date().toISOString()
    }
  });
});

// GET /api/public/version.json — Direct format for C++ auto-updater
app.get('/api/public/version.json', (req, res) => {
  const cfg = getSiteConfig() || {};
  const b = cfg.loader_build || {};
  let verNum = 1.15;
  if (b.version) {
    const match = b.version.match(/[\d.]+/);
    if (match) verNum = parseFloat(match[0]);
  }
  const host = req.get('host');
  const proto = req.protocol;
  const dlUrl = b.download_url 
    ? (b.download_url.startsWith('http') ? b.download_url : `${proto}://${host}${b.download_url}`) 
    : `${proto}://${host}/downloads/GX_Loader.exe`;
  
  res.json({
    version: verNum,
    download_url: dlUrl,
    changelog: b.notes || "Latest security and performance update.",
    mandatory: true
  });
});

// POST /api/admin/loader/upload — Admin: Upload new .exe loader, auto SHA-256, Discord notification
app.post('/api/admin/loader/upload', uploadLoader.single('loader_file'), async (req, res) => {
  const key = req.headers['x-admin-key'] || req.cookies.admin_session;
  if (!key || (key !== 'authenticated' && key !== ADMIN_SECRET_KEY)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  if (!req.file) {
    return res.status(400).json({ error: 'No loader executable file was uploaded.' });
  }

  try {
    const filePath = req.file.path;
    const fileBuffer = fs.readFileSync(filePath);
    const sha256 = crypto.createHash('sha256').update(fileBuffer).digest('hex');
    const sizeMb = (req.file.size / (1024 * 1024)).toFixed(1) + ' MB';

    const version = (req.body.version || 'v4.8.3 STABLE').trim();
    const compatibility = (req.body.compatibility || 'BUILD 3258 COMPATIBLE').trim();
    const notes = (req.body.notes || 'Latest security bypass and memory optimization update.').trim();
    const webhookUrl = (req.body.webhook_url || process.env.DISCORD_UPDATES_WEBHOOK_URL || '').trim();
    const sendWebhook = req.body.send_webhook === 'true' || req.body.send_webhook === true;

    const cfg = getSiteConfig() || {};
    const buildObj = {
      id: 'build_' + Date.now(),
      version,
      filename: req.file.filename,
      download_url: '/downloads/' + encodeURIComponent(req.file.filename),
      file_size: sizeMb,
      sha256,
      compatibility,
      notes,
      released_at: new Date().toISOString()
    };

    cfg.loader_build = buildObj;

    // Register into client_updates for portal alert banner
    if (!cfg.client_updates) cfg.client_updates = [];
    cfg.client_updates.forEach(u => u.is_latest = false);
    cfg.client_updates.unshift({
      id: 'upd_' + Date.now(),
      version,
      name: 'GX LOADER ' + version,
      description: notes,
      file_url: buildObj.download_url,
      file_size: sizeMb,
      sha256,
      date: new Date().toISOString().split('T')[0],
      is_latest: true
    });

    saveSiteConfig(cfg);

    // Send Discord Webhook Announcement if enabled
    if (sendWebhook && webhookUrl) {
      try {
        const portalUrl = process.env.PORTAL_URL || 'http://localhost:8080/dashboard.html';
        await fetch(webhookUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            content: '📢 **@everyone NEW GX LOADER UPDATE HAS BEEN DEPLOYED!**',
            embeds: [
              {
                title: '⚡ GX MENU LOADER // ' + version,
                description: `A new encrypted loader build has just been uploaded to the Client Portal.\n\n**Release Notes:**\n${notes}\n\n**Compatibility:** ${compatibility}\n**File Size:** ${sizeMb}\n**SHA-256 Checksum:**\n\`${sha256}\`\n\n⬇️ **Download Latest Build:** [Open Client Portal](${portalUrl})`,
                color: 0xC12AFF,
                footer: { text: 'GX MENU Automated Dispatch • Ring-0 Hypervisor' },
                timestamp: new Date().toISOString()
              }
            ]
          })
        });
      } catch (wErr) {
        console.warn('[WEBHOOK ERROR]', wErr.message);
      }
    }

    return res.json({ success: true, build: buildObj });
  } catch (err) {
    return res.status(500).json({ error: 'Server error processing file: ' + err.message });
  }
});


// GET /api/public/changelog  — Public: get changelog entries
app.get('/api/public/changelog', (req, res) => {
  const cfg = getSiteConfig();
  res.json({ entries: (cfg && cfg.changelog) || [] });
});

// POST /api/admin/changelog  — Admin: add changelog entry
app.post('/api/admin/changelog', async (req, res) => {
  const key = req.headers['x-admin-key'] || req.cookies.admin_session;
  if (!key || (key !== 'authenticated' && key !== ADMIN_SECRET_KEY)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  const cfg = getSiteConfig() || {};
  if (!cfg.changelog) cfg.changelog = [];
  const entry = {
    id: 'cl_' + Date.now(),
    version: req.body.version || '1.0',
    date: req.body.date || new Date().toISOString().split('T')[0],
    type: req.body.type || 'major',
    items: req.body.items || []
  };
  if (req.body.is_latest) cfg.changelog.forEach(e => e.is_latest = false);
  entry.is_latest = !!req.body.is_latest;
  cfg.changelog.unshift(entry);
  saveSiteConfig(cfg);
  res.json({ success: true, entry });
});

// DELETE /api/admin/changelog/:id  — Admin: delete changelog entry
app.delete('/api/admin/changelog/:id', async (req, res) => {
  const key = req.headers['x-admin-key'] || req.cookies.admin_session;
  if (!key || (key !== 'authenticated' && key !== ADMIN_SECRET_KEY)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  const cfg = getSiteConfig() || {};
  if (!cfg.changelog) return res.json({ success: true });
  cfg.changelog = cfg.changelog.filter(e => e.id !== req.params.id);
  saveSiteConfig(cfg);
  res.json({ success: true });
});



// ============================================================
// BLACKLIST & BAN MANAGEMENT APIS
// ============================================================
app.get('/api/admin/blacklist', async (req, res) => {
  const auth = await checkAdminAuth(req);
  if (!auth.authorized) return res.status(401).json({ error: 'Unauthorized' });
  const bl = getBlacklist();
  res.json({ success: true, count: bl.length, blacklist: bl });
});

app.post('/api/admin/blacklist', async (req, res) => {
  const auth = await checkAdminAuth(req);
  if (!auth.authorized) return res.status(401).json({ error: 'Unauthorized' });

  const { type, target, reason, notes } = req.body || {};
  if (!target || !String(target).trim()) {
    return res.status(400).json({ error: 'Ban target (Discord ID or HWID) is required' });
  }

  const bl = getBlacklist();
  const normalizedTarget = String(target).trim();
  const existing = bl.find(b => b.target.toLowerCase() === normalizedTarget.toLowerCase() && b.status !== 'revoked');
  if (existing) {
    return res.status(400).json({ error: 'This target is already blacklisted.' });
  }

  const newBan = {
    id: 'ban_' + Date.now(),
    type: type === 'hwid' ? 'hwid' : 'discord_id',
    target: normalizedTarget,
    reason: (reason || 'Security policy violation / Terminated').trim(),
    notes: (notes || '').trim(),
    banned_by: auth.user && auth.user.username ? auth.user.username : 'Admin Console',
    date: new Date().toISOString(),
    status: 'active'
  };

  bl.unshift(newBan);
  saveBlacklist(bl);

  // If discord_id, automatically revoke active license if exists
  if (newBan.type === 'discord_id') {
    const licenses = getLicenses();
    if (licenses[normalizedTarget]) {
      licenses[normalizedTarget].status = 'revoked';
      licenses[normalizedTarget].holdReason = 'Account Blacklisted: ' + newBan.reason;
      saveLicenses(licenses);
    }
  }

  res.json({ success: true, ban: newBan });
});

app.delete('/api/admin/blacklist/:id', async (req, res) => {
  const auth = await checkAdminAuth(req);
  if (!auth.authorized) return res.status(401).json({ error: 'Unauthorized' });

  const banId = req.params.id;
  let bl = getBlacklist();
  const beforeLen = bl.length;
  bl = bl.filter(b => b.id !== banId);
  if (bl.length === beforeLen) return res.status(404).json({ error: 'Ban record not found' });
  saveBlacklist(bl);
  res.json({ success: true, message: 'Ban successfully lifted' });
});

// ============================================================
// REFERRAL & AFFILIATE APIS
// ============================================================
app.get('/api/portal/referral-stats', async (req, res) => {
  const cookie = req.cookies.gx_session;
  if (!cookie) return res.status(401).json({ error: 'Unauthorized' });
  try {
    const session = typeof cookie === 'string' ? JSON.parse(cookie) : cookie;
    const stats = getReferralStats(session.id);
    res.json({ success: true, stats });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// GET /api/admin/check-referral?code=XYZ — Admin & Bot check referral code
app.get('/api/admin/check-referral', async (req, res) => {
  const key = req.headers['x-admin-key'] || req.cookies.admin_session;
  if (!key || (key !== 'authenticated' && key !== ADMIN_SECRET_KEY)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  const code = (req.query.code || '').trim();
  if (!code) return res.status(400).json({ success: false, error: 'Referral code is required' });

  const referrerId = resolveReferrerId(code);
  if (!referrerId) {
    return res.status(404).json({ success: false, error: 'Referral code not found' });
  }

  const licenses = getLicenses();
  const lic = licenses[referrerId];
  const refData = getReferrals();
  const userStats = (refData.referrals && refData.referrals[referrerId]) || {};

  return res.json({
    success: true,
    code: code.toUpperCase(),
    referrer: {
      id: referrerId,
      username: (lic && lic.username) || (userStats && userStats.username) || 'User_' + referrerId.substring(0, 6),
      plan: (lic && lic.plan) || 'Client',
      status: (lic && lic.status) || 'active',
      conversions: userStats.conversions || 0,
      bonusDaysEarned: userStats.bonus_days || 0
    },
    defaultReward: {
      monthly: 3,
      lifetime: 7,
      description: '+3 Days for Monthly / +7 Days for Lifetime'
    }
  });
});

app.post('/api/public/track-referral', (req, res) => {
  const refCode = (req.query.ref || (req.body && req.body.ref) || '').trim();
  if (!refCode) return res.json({ success: false });

  const refData = getReferrals();
  const referrerId = resolveReferrerId(refCode);
  if (!referrerId) return res.json({ success: false, error: 'Unknown code' });

  if (!refData.referrals) refData.referrals = {};
  if (!refData.referrals[referrerId]) {
    refData.referrals[referrerId] = { clicks: 0, conversions: 0, bonus_days: 0, created_at: new Date().toISOString() };
  }
  refData.referrals[referrerId].clicks = (refData.referrals[referrerId].clicks || 0) + 1;
  saveReferrals(refData);
  res.json({ success: true, clicks: refData.referrals[referrerId].clicks });
});

app.get('/api/admin/referrals', async (req, res) => {
  const auth = await checkAdminAuth(req);
  if (!auth.authorized) return res.status(401).json({ error: 'Unauthorized' });
  const refData = getReferrals();
  res.json({ success: true, data: refData });
});


// ============================================================
// MEDIA PROXY & PERMANENT CDN CACHE
// Protects against Discord 404 expired attachment URLs
// ============================================================
app.get('/api/media-proxy', async (req, res) => {
  const targetUrl = req.query.url;
  if (!targetUrl) return res.status(400).send('Missing url parameter');

  const cacheDir = path.join(ROOT_DIR, 'data/media_cache');
  if (!fs.existsSync(cacheDir)) fs.mkdirSync(cacheDir, { recursive: true });

  const hash = crypto.createHash('md5').update(targetUrl).digest('hex');
  const cacheFile = path.join(cacheDir, hash + '.bin');

  if (fs.existsSync(cacheFile)) {
    res.setHeader('Content-Type', 'image/png');
    res.setHeader('Cache-Control', 'public, max-age=604800');
    return res.sendFile(cacheFile);
  }

  try {
    const fetchResp = await fetch(targetUrl, {
      headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' }
    });

    if (fetchResp.ok) {
      const buffer = Buffer.from(await fetchResp.arrayBuffer());
      fs.writeFileSync(cacheFile, buffer);
      res.setHeader('Content-Type', fetchResp.headers.get('content-type') || 'image/png');
      res.setHeader('Cache-Control', 'public, max-age=604800');
      return res.send(buffer);
    }
  } catch (err) {
    // fall through to styled SVG placeholder
  }

  // Graceful 200 OK fallback SVG placeholder so browser console never logs 404
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="460" height="240" viewBox="0 0 460 240">
    <defs>
      <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#0c0414"/>
        <stop offset="100%" stop-color="#180829"/>
      </linearGradient>
      <linearGradient id="border" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#c12aff"/>
        <stop offset="100%" stop-color="#ff3366"/>
      </linearGradient>
    </defs>
    <rect width="458" height="238" x="1" y="1" rx="8" fill="url(#bg)" stroke="url(#border)" stroke-width="1.5"/>
    <g transform="translate(230, 85)" text-anchor="middle">
      <circle r="32" fill="rgba(193,42,255,0.12)" stroke="#c12aff" stroke-width="1.5"/>
      <path d="M-12 -8 L12 -8 L12 10 L-12 10 Z M-8 5 L-3 0 L2 5 L5 2 L8 5" fill="none" stroke="#e070ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      <circle cx="-5" cy="-3" r="2" fill="#00ff88"/>
    </g>
    <text x="230" y="150" text-anchor="middle" font-family="'Segoe UI', Roboto, sans-serif" font-size="12" font-weight="700" fill="#ffffff" letter-spacing="1">ATTACHMENT ARCHIVED</text>
    <text x="230" y="172" text-anchor="middle" font-family="'Segoe UI', Roboto, sans-serif" font-size="11" fill="#9ca3af">Discord CDN temporary link expired after channel closure</text>
    <rect x="175" y="192" width="110" height="22" rx="4" fill="rgba(193,42,255,0.2)" stroke="rgba(193,42,255,0.4)"/>
    <text x="230" y="207" text-anchor="middle" font-family="'Segoe UI', Roboto, sans-serif" font-size="10" font-weight="600" fill="#c084fc">FILE PROTECTED</text>
  </svg>`;

  res.setHeader('Content-Type', 'image/svg+xml');
  res.setHeader('Cache-Control', 'public, max-age=86400');
  return res.status(200).send(svg);
});

app.listen(PORT, '0.0.0.0', () => {
  console.log('====================================================');
  console.log(' GX MENU FULLSTACK SERVER RUNNING ON PORT ' + PORT);
  console.log(' Required Role ID: ' + CLIENT_ROLE_ID);

  console.log(' Web Root: http://localhost:' + PORT + '/');
  console.log(' Portal:   http://localhost:' + PORT + '/dashboard.html');
  console.log('====================================================');
});
