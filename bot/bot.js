// ============================================================================
// GX MENU — ROBUST DISCORD BOT ENGINE (COMPONENTS V2 — 100% ENGLISH)
// Staff Role ID:  1547640722013036637 (Allowed to execute commands & click buttons)
// Client Role ID: 1547640724604850186 (Given to buyers)
// Log Channel ID: 1547753183424806983 (License management panel & logs)
// ============================================================================
const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '../.env') });
const { 
  Client, 
  GatewayIntentBits, 
  SlashCommandBuilder, 
  REST, 
  Routes, 
  EmbedBuilder,
  ActionRowBuilder,
  ButtonBuilder,
  ButtonStyle,
  ModalBuilder,
  TextInputBuilder,
  TextInputStyle,
  MessageFlags 
} = require('discord.js');
const fs = require('fs');

// Global safety error handlers
process.on('unhandledRejection', error => {
  console.error('[GX BOT] Unhandled rejection:', (error && error.message) || error);
});
process.on('uncaughtException', error => {
  console.error('[GX BOT] Uncaught exception:', (error && error.message) || error);
});

const LICENSES_FILE = path.join(__dirname, '../data/licenses.json');
const REFERRALS_FILE = path.join(__dirname, '../data/referrals.json');
const CLIENT_ROLE_ID = process.env.CLIENT_ROLE_ID || '1547640724604850186';
const STAFF_ROLE_ID = process.env.STAFF_ROLE_ID || '1547640722013036637';
const LOG_CHANNEL_ID = process.env.ASSIGN_LOG_CHANNEL_ID || '1547753183424806983';
const PORTAL_URL = process.env.PORTAL_URL || 'http://localhost:8080/dashboard.html';
const IS_COMPONENTS_V2 = 32768; // (1 << 15) Discord Components V2 Flag

// Cloudflare Worker KV Unlimited Key Authentication
const CF_WORKER_URL = process.env.CLOUDFLARE_WORKER_URL || 'https://tight-base-cfefgx-auth.mahmoudgam3r369.workers.dev';
const CF_ADMIN_SECRET = process.env.CLOUDFLARE_ADMIN_SECRET || 'gxdev123';

function generateRandomKey(plan = 'Lifetime') {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  const prefix = plan === 'Monthly' ? 'GX-MNTH' : 'GX-LIFE';
  const part = () => Array.from({ length: 4 }, () => chars[Math.floor(Math.random() * chars.length)]).join('');
  return `${prefix}-${part()}-${part()}-${part()}`;
}

async function syncKeyWithCloudflare(key, days = 0, action = 'add') {
  if (!CF_WORKER_URL || !key) return { success: false, message: 'Missing worker URL or key' };
  try {
    const url = `${CF_WORKER_URL}/?action=${action}&admin=${CF_ADMIN_SECRET}&key=${encodeURIComponent(key)}&days=${days}`;
    const resp = await fetch(url);
    const data = await resp.json();
    return data || { success: false };
  } catch (err) {
    console.warn('[CLOUDFLARE SYNC] Warning:', err.message);
    return { success: false, message: err.message };
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

// Helper to read referrals
function getReferrals() {
  try {
    if (!fs.existsSync(REFERRALS_FILE)) return { referrals: {}, code_map: {}, rewards: [] };
    const d = JSON.parse(fs.readFileSync(REFERRALS_FILE, 'utf8'));
    if (!d.referrals) d.referrals = {};
    if (!d.code_map) d.code_map = {};
    if (!d.rewards) d.rewards = [];
    return d;
  } catch (err) {
    return { referrals: {}, code_map: {}, rewards: [] };
  }
}

// Helper to save referrals
function saveReferrals(data) {
  try {
    fs.writeFileSync(REFERRALS_FILE, JSON.stringify(data, null, 2), 'utf8');
    return true;
  } catch (err) {
    return false;
  }
}

// Helper to resolve referral code (random GX-XXXX or Discord ID)
function resolveReferrerId(input) {
  if (!input) return null;
  const clean = String(input).trim().toUpperCase();
  const data = getReferrals();
  if (data.code_map) {
    for (const [code, uid] of Object.entries(data.code_map)) {
      if (code.toUpperCase() === clean) return uid;
    }
  }
  if (data.referrals) {
    for (const [uid, r] of Object.entries(data.referrals)) {
      if (r && r.referral_code && r.referral_code.toUpperCase() === clean) return uid;
      if (uid.toUpperCase() === clean) return uid;
    }
  }
  const cleanOriginal = String(input).trim();
  if (data.referrals && data.referrals[cleanOriginal]) return cleanOriginal;
  const licenses = getLicenses();
  if (licenses[cleanOriginal]) return cleanOriginal;
  return null;
}

// Check if member is authorized staff
function isAuthorizedStaff(member, guild, userId) {
  if (guild && guild.ownerId === userId) return true;
  if (!member || !member.roles) return false;
  if (member.roles.cache && member.roles.cache.has(STAFF_ROLE_ID)) return true;
  if (Array.isArray(member.roles) && member.roles.includes(STAFF_ROLE_ID)) return true;
  return false;
}

// ============================================================================
// COMPONENTS V2 BUILDER: BUTTONS EMBEDDED DIRECTLY INSIDE THE CONTAINER
// ============================================================================
function buildV2LicenseContainer(targetUserId, licenseData) {
  const isHeld = licenseData.status === 'onhold';
  const isRevoked = licenseData.status === 'revoked';
  const isMonthly = licenseData.plan === 'Monthly';

  let accentColor = 0xC12AFF; // GX Neon Purple
  if (isHeld) accentColor = 0xFFB800; // Warning Orange
  if (isRevoked) accentColor = 0xFF2A55; // Danger Red

  const assignedUnix = Math.floor(new Date(licenseData.assignedAt || Date.now()).getTime() / 1000);
  const expiresUnix = licenseData.expiresAt ? Math.floor(new Date(licenseData.expiresAt).getTime() / 1000) : null;

  const planTitle = isMonthly 
    ? 'Monthly License (30 Days) — $6.99 / 350 EGP' 
    : 'Lifetime License (VIP) — $14.99 / 750 EGP';

  const textLines = [
    '### ⚡ GX MENU — LICENSE MANAGEMENT CARD\n',
    '> **DISCORD USER MENTION :** <@' + targetUserId + '>',
    '> **PLAN :** `' + planTitle + '`',
    '> **STATUS :** ' + (isHeld ? '⏸️ ON-HOLD / FROZEN' : isRevoked ? '🔴 DELETED / REVOKED' : '🟢 ACTIVE'),
    '> **KEY :** ||' + (licenseData.key || 'N/A') + '||',
    '> **ACTIVATION TIME :** <t:' + assignedUnix + ':f> (<t:' + assignedUnix + ':R>)',
    '> **EXPIRATION :** ' + (expiresUnix ? '<t:' + expiresUnix + ':f> (<t:' + expiresUnix + ':R>)' : '♾️ NEVER (UNLIMITED LIFETIME VIP)')
  ];

  if (isHeld && licenseData.holdReason) {
    textLines.push('> **HOLD REASON :** `' + licenseData.holdReason + '`');
  }

  const assignedByText = licenseData.assignedById ? '<@' + licenseData.assignedById + '>' : (licenseData.assignedBy || 'Staff');
  textLines.push('> **ASSIGNED BY :** ' + assignedByText);

  if (licenseData.referralReward) {
    textLines.push('> **REFERRAL BONUS :** <@' + licenseData.referralReward.referrerId + '> earned +' + licenseData.referralReward.bonusDays + ' Days (Code: `' + licenseData.referralReward.code + '`)');
  }

  const componentsInside = [
    {
      type: 10, // TextDisplay
      content: textLines.join('\n')
    },
    {
      type: 14, // Separator
      divider: true,
      spacing: 1
    }
  ];

  if (isRevoked) {
    componentsInside.push({
      type: 1, // ActionRow INSIDE the Container
      components: [
        {
          type: 2, // Button
          style: 2, // Secondary (Gray)
          label: 'HOLD / FREEZE KEY',
          custom_id: 'dis_hold',
          disabled: true,
          emoji: { name: '⏸️' }
        },
        {
          type: 2, // Button
          style: 4, // Danger (Red)
          label: 'DELETED',
          custom_id: 'dis_del',
          disabled: true,
          emoji: { name: '🗑️' }
        }
      ]
    });
  } else {
    componentsInside.push({
      type: 1, // ActionRow INSIDE the Container
      components: [
        {
          type: 2, // Button
          style: isHeld ? 3 : 2, // Gray (2) when active, Green (3) when held
          label: isHeld ? 'UNFREEZE / REACTIVATE' : 'HOLD / FREEZE KEY',
          custom_id: 'license_hold_' + targetUserId,
          emoji: { name: isHeld ? '▶️' : '⏸️' }
        },
        {
          type: 2, // Button
          style: 4, // Danger (Red)
          label: 'DELETE KEY',
          custom_id: 'license_delete_' + targetUserId,
          emoji: { name: '🗑️' }
        }
      ]
    });
  }

  return {
    type: 17, // Container component
    accent_color: accentColor,
    components: componentsInside
  };
}

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMembers
  ]
});

client.on('error', error => {
  console.error('[GX BOT] Discord Client Error:', error.message);
});

// Build Slash Commands (Matching Website Plans & Cloudflare Worker Auth)
const commands = [
  new SlashCommandBuilder()
    .setName('assign')
    .setDescription('GX MENU Client & License Manager')
    .addSubcommand(sub =>
      sub
        .setName('key')
        .setDescription('Assign a license key to a customer (auto-generates if empty), grant Client role, and post V2 card')
        .addUserOption(opt =>
          opt
            .setName('user')
            .setDescription('Target customer')
            .setRequired(true)
        )
        .addStringOption(opt =>
          opt
            .setName('key')
            .setDescription('License key (Leave empty to auto-generate a fresh Cloudflare key)')
            .setRequired(false)
        )
        .addStringOption(opt =>
          opt
            .setName('plan')
            .setDescription('Subscription plan matching website pricing')
            .setRequired(false)
            .addChoices(
              { name: 'Monthly License (30 Days) — $6.99 / 350 EGP', value: 'Monthly' },
              { name: 'Lifetime License (VIP) — $14.99 / 750 EGP', value: 'Lifetime' }
            )
        )
        .addStringOption(opt =>
          opt
            .setName('referral_code')
            .setDescription('Referral or promo code (e.g. GX-8K2P or Referrer Discord ID)')
            .setRequired(false)
        )
        .addIntegerOption(opt =>
          opt
            .setName('reward_days')
            .setDescription('Custom bonus reward days for referrer (Leave empty for default +3/+7 days)')
            .setRequired(false)
        )
    )
    .addSubcommand(sub =>
      sub
        .setName('check_referral')
        .setDescription('Check who owns a referral code and their reward details')
        .addStringOption(opt =>
          opt
            .setName('code')
            .setDescription('Referral code to verify (e.g. GX-8K2P or Discord ID)')
            .setRequired(true)
        )
    )
    .addSubcommand(sub =>
      sub
        .setName('hold')
        .setDescription('Place a license ON-HOLD / Suspended with reason')
        .addUserOption(opt =>
          opt
            .setName('user')
            .setDescription('Target customer')
            .setRequired(true)
        )
        .addStringOption(opt =>
          opt
            .setName('reason')
            .setDescription('Reason for hold (e.g. Subscription Expired)')
            .setRequired(true)
        )
    )
    .addSubcommand(sub =>
      sub
        .setName('unhold')
        .setDescription('Reactivate an on-hold license to Active')
        .addUserOption(opt =>
          opt
            .setName('user')
            .setDescription('Target customer')
            .setRequired(true)
        )
    )
    .addSubcommand(sub =>
      sub
        .setName('revoke')
        .setDescription('Revoke key and remove client role')
        .addUserOption(opt =>
          opt
            .setName('user')
            .setDescription('Target customer')
            .setRequired(true)
        )
    )
    .addSubcommand(sub =>
      sub
        .setName('check')
        .setDescription('Inspect assigned license record & expiration')
        .addUserOption(opt =>
          opt
            .setName('user')
            .setDescription('Target customer')
            .setRequired(true)
        )
    ),

  // Dedicated Quick Key Generator
  new SlashCommandBuilder()
    .setName('genkey')
    .setDescription('Generate an unlimited Cloudflare & Portal license key')
    .addStringOption(opt =>
      opt
        .setName('plan')
        .setDescription('License duration tier')
        .setRequired(true)
        .addChoices(
          { name: 'Monthly License (30 Days) — $6.99 / 350 EGP', value: 'Monthly' },
          { name: 'Lifetime License (VIP) — $14.99 / 750 EGP', value: 'Lifetime' }
        )
    )
    .addIntegerOption(opt =>
      opt
        .setName('days')
        .setDescription('Custom days override (0 for lifetime, or specify e.g. 30, 60)')
        .setRequired(false)
    )
    .addUserOption(opt =>
      opt
        .setName('customer')
        .setDescription('Optionally assign key directly to a customer')
        .setRequired(false)
    ),

  // HWID Unbind / Reset
  new SlashCommandBuilder()
    .setName('resethwid')
    .setDescription('Reset hardware ID (HWID) lock in Cloudflare Worker and Portal')
    .addUserOption(opt =>
      opt
        .setName('user')
        .setDescription('Customer Discord user to reset HWID for')
        .setRequired(false)
    )
    .addStringOption(opt =>
      opt
        .setName('key')
        .setDescription('License key string to reset HWID for')
        .setRequired(false)
    ),

  // Delete / Revoke Key
  new SlashCommandBuilder()
    .setName('deletekey')
    .setDescription('Permanently delete/revoke a license key from Cloudflare and Portal')
    .addUserOption(opt =>
      opt
        .setName('user')
        .setDescription('Customer Discord user')
        .setRequired(false)
    )
    .addStringOption(opt =>
      opt
        .setName('key')
        .setDescription('License key string')
        .setRequired(false)
    ),

  // Full Database Sync to Cloudflare
  new SlashCommandBuilder()
    .setName('sync')
    .setDescription('Synchronize all active portal licenses to Cloudflare Worker KV'),

  // Public Self-Redeem Command
  new SlashCommandBuilder()
    .setName('redeem')
    .setDescription('Redeem and activate a GX MENU license key to get Client role')
    .addStringOption(opt =>
      opt
        .setName('key')
        .setDescription('Your license key (e.g. GX-LIFE-XXXX-XXXX)')
        .setRequired(true)
    )
].map(c => c.toJSON());

// Ready event
client.once('ready', async () => {
  console.log('[GX BOT] Logged in as ' + client.user.tag);

  if (!process.env.DISCORD_BOT_TOKEN || process.env.DISCORD_BOT_TOKEN.includes('YOUR_DISCORD')) {
    return;
  }

  const rest = new REST({ version: '10' }).setToken(process.env.DISCORD_BOT_TOKEN);
  try {
    console.log('[GX BOT] Cleaning old global commands and registering guild slash commands...');
    // Ensure no stale global commands exist that cause duplication
    await rest.put(Routes.applicationCommands(process.env.DISCORD_CLIENT_ID), { body: [] });

    if (process.env.DISCORD_GUILD_ID) {
      await rest.put(
        Routes.applicationGuildCommands(process.env.DISCORD_CLIENT_ID, process.env.DISCORD_GUILD_ID),
        { body: commands }
      );
      console.log('[GX BOT] Commands registered for Guild: ' + process.env.DISCORD_GUILD_ID);
    }
  } catch (error) {
    console.error('[GX BOT] Error registering commands:', error.message);
  }
});

// ============================================================================
// INTERACTION HANDLING (Slash Commands, Buttons, Modals)
// ============================================================================
client.on('interactionCreate', async interaction => {
  // --------------------------------------------------------------------------
  // A. CHAT INPUT COMMANDS (/assign)
  // --------------------------------------------------------------------------
  if (interaction.isChatInputCommand()) {
    if (interaction.commandName === 'assign') {
      try {
        await interaction.deferReply({ flags: MessageFlags.Ephemeral });
      } catch (e) {
        return;
      }

      // Check Staff Role
      if (!isAuthorizedStaff(interaction.member, interaction.guild, interaction.user.id)) {
        return interaction.editReply({
          content: '⛔ **Access Denied! You are not authorized to use this command.**\nThis command is strictly reserved for Staff Members with role: <@&' + STAFF_ROLE_ID + '>'
        });
      }

      const subcommand = interaction.options.getSubcommand();

      // 0. CHECK REFERRAL CODE
      if (subcommand === 'check_referral') {
        const code = (interaction.options.getString('code') || '').trim();
        if (!code) {
          return interaction.editReply({ content: '⚠️ Please specify a referral code to verify.' });
        }
        const referrerId = resolveReferrerId(code);
        if (!referrerId) {
          const notFoundEmbed = new EmbedBuilder()
            .setColor(0xFF3366)
            .setTitle('❌ Invalid Referral Code')
            .setDescription(`No customer or active referral record was found for: \`${code}\`.`)
            .setFooter({ text: 'Ensure the code was entered accurately (e.g. GX-XXXX or Discord User ID).' })
            .setTimestamp();
          return interaction.editReply({ embeds: [notFoundEmbed] });
        }

        const licenses = getLicenses();
        const lic = licenses[referrerId];
        const refData = getReferrals();
        const userStats = (refData.referrals && refData.referrals[referrerId]) || {};
        const bonusDays = userStats.bonus_days || 0;
        const conversions = userStats.conversions || 0;

        const checkEmbed = new EmbedBuilder()
          .setColor(0x00FF88)
          .setTitle('✅ Verified Referral Code')
          .setDescription(`Code **\`${code.toUpperCase()}\`** is verified and belongs to **<@${referrerId}>**.`)
          .addFields(
            { name: 'Referrer Member', value: `<@${referrerId}> (${(lic && lic.username) || (userStats && userStats.username) || 'User_' + referrerId.substring(0, 6)})`, inline: true },
            { name: 'Current Plan', value: (lic && lic.plan) || 'Client', inline: true },
            { name: 'Subscription Status', value: (lic && lic.status) === 'active' ? '🟢 ACTIVE' : ((lic && lic.status) || 'N/A'), inline: true },
            { name: 'Total Referrals', value: `${conversions} customers`, inline: true },
            { name: 'Bonus Days Earned', value: `+${bonusDays} Days`, inline: true },
            { name: 'Default Reward', value: '📅 Monthly: **+3 Days** | 👑 Lifetime: **+7 Days**', inline: false },
            { name: 'Custom Reward', value: 'You can customize gift days using the `reward_days` option in `/assign key`', inline: false }
          )
          .setFooter({ text: 'GX MENU Affiliate & Referral Engine' })
          .setTimestamp();

        return interaction.editReply({ embeds: [checkEmbed] });
      }

      const targetUser = interaction.options.getUser('user');
      if (!targetUser) {
        return interaction.editReply({ content: '⚠️ Customer user option is required.' });
      }

      // 1. ASSIGN KEY
      if (subcommand === 'key') {
        const rawKey = (interaction.options.getString('key') || '').trim();
        const plan = interaction.options.getString('plan') || 'Monthly';
        const rawReferralCode = (interaction.options.getString('referral_code') || '').trim();
        const customReward = interaction.options.getInteger('reward_days');

        const finalKey = rawKey || generateRandomKey(plan);
        const isMonthly = plan === 'Monthly';
        const cfDays = isMonthly ? 30 : 0;

        // Sync with Cloudflare Worker KV for unlimited auth
        const cfSyncRes = await syncKeyWithCloudflare(finalKey, cfDays, 'add');

        // Precise time calculations matching website
        const now = new Date();
        const assignedAt = now.toISOString();
        let expiresAt = null;

        if (isMonthly) {
          // Exactly 30 days duration
          const expDate = new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000);
          expiresAt = expDate.toISOString();
        }

        const licenses = getLicenses();
        const newLicense = {
          userId: targetUser.id,
          username: targetUser.tag,
          key: finalKey,
          plan: plan, // 'Monthly' or 'Lifetime'
          status: 'active',
          holdReason: null,
          assignedAt: assignedAt,
          expiresAt: expiresAt,
          assignedBy: interaction.user.tag,
          assignedById: interaction.user.id
        };

        // Process Referral Code & Reward if provided
        let referralRewardInfo = null;
        if (rawReferralCode) {
          const referrerId = resolveReferrerId(rawReferralCode);
          if (referrerId && referrerId !== targetUser.id) {
            let bonusDays = plan === 'Monthly' ? 3 : 7;
            if (customReward !== null && customReward !== undefined && customReward >= 0) {
              bonusDays = parseInt(customReward);
            }

            const refLic = licenses[referrerId];
            if (refLic) {
              if (refLic.plan === 'Monthly' && refLic.expiresAt) {
                const curExp = new Date(refLic.expiresAt).getTime();
                const baseTime = curExp > Date.now() ? curExp : Date.now();
                refLic.expiresAt = new Date(baseTime + bonusDays * 24 * 60 * 60 * 1000).toISOString();
                if (refLic.status === 'onhold' && refLic.holdReason && refLic.holdReason.includes('Expired')) {
                  refLic.status = 'active';
                  refLic.holdReason = null;
                }
              }
            }

            const refData = getReferrals();
            if (!refData.referrals[referrerId]) {
              refData.referrals[referrerId] = { clicks: 0, conversions: 0, bonus_days: 0, created_at: new Date().toISOString() };
            }
            refData.referrals[referrerId].conversions = (refData.referrals[referrerId].conversions || 0) + 1;
            refData.referrals[referrerId].bonus_days = (refData.referrals[referrerId].bonus_days || 0) + bonusDays;

            if (!refData.rewards) refData.rewards = [];
            refData.rewards.push({
              id: 'rew_' + Date.now(),
              referrer_id: referrerId,
              referrer_username: (refLic && refLic.username) || 'Client',
              code_used: rawReferralCode.toUpperCase(),
              referred_user_id: targetUser.id,
              referred_username: targetUser.tag,
              plan: plan,
              bonus_days: bonusDays,
              date: new Date().toISOString().split('T')[0]
            });
            saveReferrals(refData);

            referralRewardInfo = {
              referrerId,
              referrerName: (refLic && refLic.username) || 'User_' + referrerId.substring(0, 6),
              code: rawReferralCode.toUpperCase(),
              bonusDays
            };
            newLicense.referralReward = referralRewardInfo;
          }
        }

        // Assign Client Role
        let roleGranted = false;
        try {
          if (interaction.guild) {
            const member = await interaction.guild.members.fetch(targetUser.id);
            if (member && CLIENT_ROLE_ID) {
              await member.roles.add(CLIENT_ROLE_ID);
              roleGranted = true;
            }
          }
        } catch (err) {
          console.warn('[GX BOT] Client role grant warning:', err.message);
        }

        // Send Direct Message to Customer in clean professional English
        let dmSent = false;
        const assignedUnix = Math.floor(now.getTime() / 1000);
        const expiresUnix = expiresAt ? Math.floor(new Date(expiresAt).getTime() / 1000) : null;

        try {
          const dmEmbed = new EmbedBuilder()
            .setColor(isMonthly ? 0x6C5CE7 : 0xC12AFF)
            .setTitle('⚡ GX MENU — Your License Key Has Been Assigned!')
            .setDescription('Welcome **' + targetUser.username + '**! Your subscription has been activated in the system. You now have immediate access to the Client Portal.')
            .addFields(
              { name: 'Your License Key', value: '```' + finalKey + '```', inline: false },
              { name: 'Subscription Plan', value: isMonthly ? '📅 Monthly License (30 Days) — $6.99 / 350 EGP' : '👑 Lifetime License (VIP) — $14.99 / 750 EGP', inline: false },
              { name: 'Status', value: '🟢 ACTIVE', inline: true },
              { name: 'Activated At', value: `<t:${assignedUnix}:f>`, inline: true },
              { name: 'Expires At', value: expiresUnix ? `<t:${expiresUnix}:f> (<t:${expiresUnix}:R>)` : '♾️ NEVER (LIFETIME ACCESS)', inline: false },
              { name: 'Client Portal Link', value: '[Click Here to Open Client Portal](' + PORTAL_URL + ')', inline: false }
            );

          if (referralRewardInfo) {
            dmEmbed.addFields({
              name: '🎁 Referral Applied',
              value: `Invited via **${referralRewardInfo.code}**! Referrer <@${referralRewardInfo.referrerId}> received +${referralRewardInfo.bonusDays} bonus days.`,
              inline: false
            });
          }

          dmEmbed.setFooter({ text: 'Key is encrypted and automatically HWID-locked upon first loader injection.' }).setTimestamp();

          await targetUser.send({ embeds: [dmEmbed] });
          dmSent = true;
        } catch (err) {
          console.warn('[GX BOT] DM delivery warning:', err.message);
        }

        // Send Components V2 (Container with Buttons INSIDE) to Channel 1547753183424806983
        let channelSent = false;
        try {
          const logChannel = await client.channels.fetch(LOG_CHANNEL_ID);
          if (logChannel && logChannel.isTextBased()) {
            const v2Container = buildV2LicenseContainer(targetUser.id, newLicense);
            const sentMsg = await logChannel.send({
              flags: IS_COMPONENTS_V2,
              components: [v2Container]
            });
            channelSent = true;
            newLicense.logMessageId = sentMsg.id;
            newLicense.logChannelId = logChannel.id;
          }
        } catch (logErr) {
          console.warn('[GX BOT] Log channel dispatch warning:', logErr.message);
        }

        licenses[targetUser.id] = newLicense;
        saveLicenses(licenses);

        // Ephemeral Reply to Staff in English
        const replyEmbed = new EmbedBuilder()
          .setColor(0x00FF88)
          .setTitle('✅ License Assigned & Components V2 Card Dispatched')
          .addFields(
            { name: 'Customer', value: '<@' + targetUser.id + '> (' + targetUser.tag + ')', inline: true },
            { name: 'Plan', value: isMonthly ? 'Monthly (30 Days)' : 'Lifetime (VIP)', inline: true },
            { name: 'Key', value: '||' + finalKey + '||', inline: false },
            { name: 'Expires', value: expiresUnix ? `<t:${expiresUnix}:f> (<t:${expiresUnix}:R>)` : '♾️ Lifetime (Never)', inline: true },
            { name: 'Client Role', value: roleGranted ? '✅ GRANTED' : '⚠️ FAILED', inline: true },
            { name: 'Discord DM', value: dmSent ? '✅ DELIVERED' : '⚠️ CLOSED DMs', inline: true },
            { name: 'Components V2 Card', value: channelSent ? '✅ Sent to <#' + LOG_CHANNEL_ID + '>' : '⚠️ Check Permissions', inline: true },
            { name: 'Cloudflare Worker', value: cfSyncRes.success ? '🟢 Registered in KV' : '⚠️ Offline/Sync Error', inline: true }
          );

        if (referralRewardInfo) {
          replyEmbed.addFields({
            name: '🎁 Referral Bonus Dispatched',
            value: `Referrer <@${referralRewardInfo.referrerId}> earned **+${referralRewardInfo.bonusDays} Free Days** (Code: \`${referralRewardInfo.code}\`)`,
            inline: false
          });
        }

        replyEmbed.setTimestamp();

        return interaction.editReply({ embeds: [replyEmbed] });
      }

      // 2. PLACE ON-HOLD
      if (subcommand === 'hold') {
        const reason = interaction.options.getString('reason');
        const licenses = getLicenses();

        if (!licenses[targetUser.id]) {
          return interaction.editReply({ content: '⚠️ No license record found for <@' + targetUser.id + '>.' });
        }

        licenses[targetUser.id].status = 'onhold';
        licenses[targetUser.id].holdReason = reason;
        licenses[targetUser.id].heldAt = new Date().toISOString();
        licenses[targetUser.id].heldBy = interaction.user.tag;
        saveLicenses(licenses);

        // Notify user via DM in English
        try {
          const holdEmbed = new EmbedBuilder()
            .setColor(0xFFB800)
            .setTitle('GX MENU — License Status Notice (ON-HOLD)')
            .setDescription('Dear **' + targetUser.username + '**, your license has been temporarily suspended in the Client Portal.')
            .addFields(
              { name: 'Hold Reason', value: '```' + reason + '```', inline: false },
              { name: 'Renewal & Inquiries', value: 'Please open a support ticket in our official Discord server.', inline: false }
            )
            .setTimestamp();
          await targetUser.send({ embeds: [holdEmbed] });
        } catch (err) {}

        // Sync channel Components V2 message
        try {
          if (licenses[targetUser.id].logMessageId && licenses[targetUser.id].logChannelId) {
            const ch = await client.channels.fetch(licenses[targetUser.id].logChannelId);
            if (ch && ch.isTextBased()) {
              const msg = await ch.messages.fetch(licenses[targetUser.id].logMessageId).catch(() => null);
              if (msg) {
                const updatedContainer = buildV2LicenseContainer(targetUser.id, licenses[targetUser.id]);
                await msg.edit({ flags: IS_COMPONENTS_V2, components: [updatedContainer] });
              }
            }
          }
        } catch (syncErr) {}

        return interaction.editReply({ 
          content: '⏸️ Subscription for <@' + targetUser.id + '> is now **ON-HOLD**.\nReason: `' + reason + '`'
        });
      }

      // 3. UNHOLD (REACTIVATE)
      if (subcommand === 'unhold') {
        const licenses = getLicenses();

        if (!licenses[targetUser.id]) {
          return interaction.editReply({ content: '⚠️ No license record found for <@' + targetUser.id + '>.' });
        }

        licenses[targetUser.id].status = 'active';
        licenses[targetUser.id].holdReason = null;
        delete licenses[targetUser.id].heldAt;
        delete licenses[targetUser.id].heldBy;
        saveLicenses(licenses);

        // Notify user via DM in English
        try {
          const unholdEmbed = new EmbedBuilder()
            .setColor(0x00FF88)
            .setTitle('GX MENU — Your Subscription Has Been Reactivated!')
            .setDescription('The hold status has been lifted from your account. You can now access the Client Portal, view your key, and download the loader.')
            .addFields({ name: 'Client Portal', value: '[Click Here to Access](' + PORTAL_URL + ')', inline: false })
            .setTimestamp();
          await targetUser.send({ embeds: [unholdEmbed] });
        } catch (err) {}

        // Sync channel Components V2 message
        try {
          if (licenses[targetUser.id].logMessageId && licenses[targetUser.id].logChannelId) {
            const ch = await client.channels.fetch(licenses[targetUser.id].logChannelId);
            if (ch && ch.isTextBased()) {
              const msg = await ch.messages.fetch(licenses[targetUser.id].logMessageId).catch(() => null);
              if (msg) {
                const updatedContainer = buildV2LicenseContainer(targetUser.id, licenses[targetUser.id]);
                await msg.edit({ flags: IS_COMPONENTS_V2, components: [updatedContainer] });
              }
            }
          }
        } catch (syncErr) {}

        return interaction.editReply({ 
          content: '✅ Subscription for <@' + targetUser.id + '> has been reactivated to **ACTIVE**.'
        });
      }

      // 4. REVOKE
      if (subcommand === 'revoke') {
        const licenses = getLicenses();
        const userRec = licenses[targetUser.id];
        if (!userRec) {
          return interaction.editReply({ content: '⚠️ No license record found for <@' + targetUser.id + '>.' });
        }

        const logMsgId = userRec.logMessageId;
        const logChId = userRec.logChannelId;

        licenses[targetUser.id].status = 'revoked';
        const revokedRec = { ...licenses[targetUser.id] };
        delete licenses[targetUser.id];
        saveLicenses(licenses);

        try {
          if (interaction.guild) {
            const member = await interaction.guild.members.fetch(targetUser.id);
            if (member && CLIENT_ROLE_ID) {
              await member.roles.remove(CLIENT_ROLE_ID);
            }
          }
        } catch (err) {}

        // Update Components V2 card to Revoked with disabled buttons
        try {
          if (logMsgId && logChId) {
            const ch = await client.channels.fetch(logChId);
            if (ch && ch.isTextBased()) {
              const msg = await ch.messages.fetch(logMsgId).catch(() => null);
              if (msg) {
                const disabledContainer = buildV2LicenseContainer(targetUser.id, revokedRec);
                await msg.edit({ flags: IS_COMPONENTS_V2, components: [disabledContainer] });
              }
            }
          }
        } catch (err) {}

        return interaction.editReply({ 
          content: '🚫 License for <@' + targetUser.id + '> has been completely revoked and client role removed.' 
        });
      }

      // 5. CHECK
      if (subcommand === 'check') {
        const licenses = getLicenses();
        const userLicense = licenses[targetUser.id];

        if (!userLicense) {
          return interaction.editReply({ content: 'ℹ️ No license found for <@' + targetUser.id + '> in the system.' });
        }

        const checkAssignedUnix = Math.floor(new Date(userLicense.assignedAt || Date.now()).getTime() / 1000);
        const checkExpiresUnix = userLicense.expiresAt ? Math.floor(new Date(userLicense.expiresAt).getTime() / 1000) : null;
        const isMonthly = userLicense.plan === 'Monthly';

        const checkEmbed = new EmbedBuilder()
          .setColor(userLicense.status === 'onhold' ? 0xFFB800 : 0x00FF88)
          .setTitle('License Record for ' + (userLicense.username || targetUser.tag))
          .addFields(
            { name: 'Assigned Key', value: '||' + userLicense.key + '||', inline: false },
            { name: 'Plan', value: isMonthly ? 'Monthly License (30 Days) — $6.99 / 350 EGP' : 'Lifetime License (VIP) — $14.99 / 750 EGP', inline: true },
            { name: 'Status', value: userLicense.status === 'onhold' ? '⏸️ ON-HOLD' : '🟢 ACTIVE', inline: true },
            { name: 'Activation Time', value: `<t:${checkAssignedUnix}:f> (<t:${checkAssignedUnix}:R>)`, inline: false },
            { name: 'Expiration Time', value: checkExpiresUnix ? `<t:${checkExpiresUnix}:f> (<t:${checkExpiresUnix}:R>)` : '♾️ NEVER (UNLIMITED LIFETIME ACCESS)', inline: false },
            { name: 'Hold Reason', value: userLicense.holdReason || 'None', inline: false }
          );

        return interaction.editReply({ embeds: [checkEmbed] });
      }
    }

    // ------------------------------------------------------------------------
    // /genkey: Generate Unlimited Key via Cloudflare Worker & Portal
    // ------------------------------------------------------------------------
    if (interaction.commandName === 'genkey') {
      try {
        await interaction.deferReply({ flags: MessageFlags.Ephemeral });
      } catch (e) {
        return;
      }

      if (!isAuthorizedStaff(interaction.member, interaction.guild, interaction.user.id)) {
        return interaction.editReply({
          content: '⛔ **Access Denied!** This command is strictly reserved for Staff Members with role: <@&' + STAFF_ROLE_ID + '>'
        });
      }

      const plan = interaction.options.getString('plan') || 'Monthly';
      const customDays = interaction.options.getInteger('days');
      const targetCustomer = interaction.options.getUser('customer');
      const isMonthly = plan === 'Monthly';
      const days = customDays !== null && customDays !== undefined ? customDays : (isMonthly ? 30 : 0);
      const generatedKey = generateRandomKey(plan);

      // Register key on Cloudflare Worker KV
      const cfRes = await syncKeyWithCloudflare(generatedKey, days, 'add');

      const now = new Date();
      let expiresAt = null;
      if (days > 0) {
        expiresAt = new Date(now.getTime() + days * 24 * 60 * 60 * 1000).toISOString();
      }

      if (targetCustomer) {
        const licenses = getLicenses();
        const newLicense = {
          userId: targetCustomer.id,
          username: targetCustomer.tag,
          key: generatedKey,
          plan: plan,
          status: 'active',
          holdReason: null,
          assignedAt: now.toISOString(),
          expiresAt: expiresAt,
          assignedBy: interaction.user.tag,
          assignedById: interaction.user.id
        };

        licenses[targetCustomer.id] = newLicense;
        saveLicenses(licenses);

        // Grant role
        try {
          if (interaction.guild) {
            const member = await interaction.guild.members.fetch(targetCustomer.id);
            if (member && CLIENT_ROLE_ID) await member.roles.add(CLIENT_ROLE_ID);
          }
        } catch (e) {}

        // Send DM
        try {
          const dmEmbed = new EmbedBuilder()
            .setColor(isMonthly ? 0x6C5CE7 : 0xC12AFF)
            .setTitle('⚡ GX MENU — Your License Key Has Been Generated!')
            .setDescription(`Welcome **${targetCustomer.username}**! Your subscription has been created and bound to your account.`)
            .addFields(
              { name: 'Your License Key', value: '```' + generatedKey + '```', inline: false },
              { name: 'Plan', value: plan === 'Monthly' ? `Monthly (${days} Days)` : 'Lifetime VIP', inline: true },
              { name: 'Portal', value: `[Access Portal](${PORTAL_URL})`, inline: true }
            )
            .setFooter({ text: 'Cloudflare Worker & Portal Verified' });
          await targetCustomer.send({ embeds: [dmEmbed] });
        } catch (e) {}

        // Send Components V2 Card to log channel
        try {
          const logChannel = await client.channels.fetch(LOG_CHANNEL_ID);
          if (logChannel && logChannel.isTextBased()) {
            const v2Container = buildV2LicenseContainer(targetCustomer.id, newLicense);
            const sentMsg = await logChannel.send({ flags: IS_COMPONENTS_V2, components: [v2Container] });
            newLicense.logMessageId = sentMsg.id;
            newLicense.logChannelId = logChannel.id;
            saveLicenses(licenses);
          }
        } catch (e) {}

        return interaction.editReply({
          embeds: [
            new EmbedBuilder()
              .setColor(0x00FF88)
              .setTitle('✅ Key Generated & Assigned to Customer')
              .addFields(
                { name: 'Customer', value: `<@${targetCustomer.id}>`, inline: true },
                { name: 'License Key', value: '`' + generatedKey + '`', inline: true },
                { name: 'Duration', value: days === 0 ? '👑 Lifetime' : `⏳ ${days} Days`, inline: true },
                { name: 'Cloudflare Worker', value: cfRes.success ? '🟢 Registered in KV' : '⚠️ Offline/Sync Warning', inline: true }
              )
              .setTimestamp()
          ]
        });
      }

      // Standalone generated key (for manual delivery / sale)
      return interaction.editReply({
        embeds: [
          new EmbedBuilder()
            .setColor(0x00FF88)
            .setTitle('🔑 New License Key Generated')
            .setDescription('Key has been registered on the Cloudflare KV database and is ready for use in the loader.')
            .addFields(
              { name: 'License Key (Click to Copy)', value: '```' + generatedKey + '```', inline: false },
              { name: 'Plan Tier', value: plan === 'Monthly' ? `Monthly (${days} Days)` : '👑 Lifetime VIP', inline: true },
              { name: 'Cloudflare Status', value: cfRes.success ? '🟢 Active & Ready in KV' : '⚠️ Cloudflare Sync Warning', inline: true }
            )
            .setFooter({ text: 'Deliver this key to customer or use /assign key to bind to customer account.' })
            .setTimestamp()
        ]
      });
    }

    // ------------------------------------------------------------------------
    // /resethwid: Reset HWID in Cloudflare Worker & Portal
    // ------------------------------------------------------------------------
    if (interaction.commandName === 'resethwid') {
      try {
        await interaction.deferReply({ flags: MessageFlags.Ephemeral });
      } catch (e) {
        return;
      }

      if (!isAuthorizedStaff(interaction.member, interaction.guild, interaction.user.id)) {
        return interaction.editReply({
          content: '⛔ **Access Denied!** Strictly reserved for Staff Members with role: <@&' + STAFF_ROLE_ID + '>'
        });
      }

      const targetUser = interaction.options.getUser('user');
      const targetKey = (interaction.options.getString('key') || '').trim();

      if (!targetUser && !targetKey) {
        return interaction.editReply({ content: '⚠️ Please provide either a customer `@user` or a `key`.' });
      }

      const licenses = getLicenses();
      let foundUserId = null;
      let targetLic = null;

      if (targetUser && licenses[targetUser.id]) {
        foundUserId = targetUser.id;
        targetLic = licenses[targetUser.id];
      } else if (targetKey) {
        for (const [uid, lic] of Object.entries(licenses)) {
          if (lic.key && lic.key.toUpperCase() === targetKey.toUpperCase()) {
            foundUserId = uid;
            targetLic = lic;
            break;
          }
        }
      }

      const keyToReset = (targetLic && targetLic.key) || targetKey;
      if (!keyToReset) {
        return interaction.editReply({ content: '❌ No matching license found.' });
      }

      if (targetLic) {
        targetLic.hwid = null;
        targetLic.hwidResetAt = new Date().toISOString();
        targetLic.hwidResetBy = interaction.user.tag;
        saveLicenses(licenses);
      }

      // Reset on Cloudflare Worker
      const cfRes = await syncKeyWithCloudflare(keyToReset, (targetLic && targetLic.plan === 'Monthly') ? 30 : 0, 'add');

      return interaction.editReply({
        embeds: [
          new EmbedBuilder()
            .setColor(0x00D4FF)
            .setTitle('🔄 Hardware ID (HWID) Reset Successful')
            .setDescription(`HWID unbind complete for key: \`${keyToReset}\`. The user can now launch the loader on their new machine.`)
            .addFields(
              { name: 'Customer', value: foundUserId ? `<@${foundUserId}>` : 'Unassigned Key', inline: true },
              { name: 'Cloudflare Worker Sync', value: cfRes.success ? '🟢 HWID Cleared in KV' : '⚠️ Cloudflare API Warning', inline: true }
            )
            .setTimestamp()
        ]
      });
    }

    // ------------------------------------------------------------------------
    // /deletekey: Permanently Delete / Revoke License
    // ------------------------------------------------------------------------
    if (interaction.commandName === 'deletekey') {
      try {
        await interaction.deferReply({ flags: MessageFlags.Ephemeral });
      } catch (e) {
        return;
      }

      if (!isAuthorizedStaff(interaction.member, interaction.guild, interaction.user.id)) {
        return interaction.editReply({
          content: '⛔ **Access Denied!** Strictly reserved for Staff Members with role: <@&' + STAFF_ROLE_ID + '>'
        });
      }

      const targetUser = interaction.options.getUser('user');
      const targetKey = (interaction.options.getString('key') || '').trim();

      if (!targetUser && !targetKey) {
        return interaction.editReply({ content: '⚠️ Please provide either a customer `@user` or a `key`.' });
      }

      const licenses = getLicenses();
      let foundUserId = null;
      let targetLic = null;

      if (targetUser && licenses[targetUser.id]) {
        foundUserId = targetUser.id;
        targetLic = licenses[targetUser.id];
      } else if (targetKey) {
        for (const [uid, lic] of Object.entries(licenses)) {
          if (lic.key && lic.key.toUpperCase() === targetKey.toUpperCase()) {
            foundUserId = uid;
            targetLic = lic;
            break;
          }
        }
      }

      const keyToDelete = (targetLic && targetLic.key) || targetKey;
      if (foundUserId) {
        delete licenses[foundUserId];
        saveLicenses(licenses);

        try {
          if (interaction.guild) {
            const member = await interaction.guild.members.fetch(foundUserId);
            if (member && CLIENT_ROLE_ID) await member.roles.remove(CLIENT_ROLE_ID);
          }
        } catch (e) {}
      }

      return interaction.editReply({
        embeds: [
          new EmbedBuilder()
            .setColor(0xFF2A55)
            .setTitle('🗑️ License Key Deleted')
            .setDescription(`Key \`${keyToDelete}\` has been revoked and deleted from the portal system.`)
            .setTimestamp()
        ]
      });
    }

    // ------------------------------------------------------------------------
    // /sync: Synchronize All Portal Licenses to Cloudflare Worker
    // ------------------------------------------------------------------------
    if (interaction.commandName === 'sync') {
      try {
        await interaction.deferReply({ flags: MessageFlags.Ephemeral });
      } catch (e) {
        return;
      }

      if (!isAuthorizedStaff(interaction.member, interaction.guild, interaction.user.id)) {
        return interaction.editReply({ content: '⛔ **Access Denied!**' });
      }

      const licenses = getLicenses();
      let syncedCount = 0;
      let failCount = 0;

      for (const [uid, lic] of Object.entries(licenses)) {
        if (lic.key && lic.status === 'active') {
          const days = lic.plan === 'Monthly' ? 30 : 0;
          const res = await syncKeyWithCloudflare(lic.key, days, 'add');
          if (res.success) syncedCount++;
          else failCount++;
        }
      }

      return interaction.editReply({
        embeds: [
          new EmbedBuilder()
            .setColor(0x00FF88)
            .setTitle('⚡ Cloudflare Worker Sync Completed')
            .setDescription(`Successfully synchronized **${syncedCount}** active licenses to Cloudflare Worker KV.`)
            .addFields(
              { name: 'Synced Successfully', value: `${syncedCount}`, inline: true },
              { name: 'Failed / Skipped', value: `${failCount}`, inline: true }
            )
            .setTimestamp()
        ]
      });
    }

    // ------------------------------------------------------------------------
    // /redeem: User self-redemption command
    // ------------------------------------------------------------------------
    if (interaction.commandName === 'redeem') {
      try {
        await interaction.deferReply({ flags: MessageFlags.Ephemeral });
      } catch (e) {
        return;
      }

      const rawKey = (interaction.options.getString('key') || '').trim().toUpperCase();
      const licenses = getLicenses();

      // Check if user already has an active license
      if (licenses[interaction.user.id] && licenses[interaction.user.id].status === 'active') {
        return interaction.editReply({
          content: `ℹ️ You already have an active **${licenses[interaction.user.id].plan}** license key: \`${licenses[interaction.user.id].key}\`.\nAccess your portal here: ${PORTAL_URL}`
        });
      }

      // Check if key is claimed by someone else
      for (const [uid, lic] of Object.entries(licenses)) {
        if (lic.key && lic.key.toUpperCase() === rawKey && uid !== interaction.user.id && lic.status === 'active') {
          return interaction.editReply({
            content: '❌ This license key has already been activated by another user.'
          });
        }
      }

      const isMonthly = rawKey.includes('MNTH') || rawKey.includes('MONTH');
      const plan = isMonthly ? 'Monthly' : 'Lifetime';
      const days = isMonthly ? 30 : 0;

      // Sync with Cloudflare Worker KV
      const cfRes = await syncKeyWithCloudflare(rawKey, days, 'add');

      const now = new Date();
      let expiresAt = null;
      if (isMonthly) {
        expiresAt = new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000).toISOString();
      }

      const newLicense = {
        userId: interaction.user.id,
        username: interaction.user.tag,
        key: rawKey,
        plan: plan,
        status: 'active',
        holdReason: null,
        assignedAt: now.toISOString(),
        expiresAt: expiresAt,
        assignedBy: 'Self-Redeemed in Discord',
        assignedById: interaction.user.id
      };

      licenses[interaction.user.id] = newLicense;
      saveLicenses(licenses);

      // Grant Client role
      let roleGranted = false;
      try {
        if (interaction.guild) {
          const member = await interaction.guild.members.fetch(interaction.user.id);
          if (member && CLIENT_ROLE_ID) {
            await member.roles.add(CLIENT_ROLE_ID);
            roleGranted = true;
          }
        }
      } catch (e) {}

      // Dispatch Components V2 Card to Log Channel
      try {
        const logChannel = await client.channels.fetch(LOG_CHANNEL_ID);
        if (logChannel && logChannel.isTextBased()) {
          const v2Container = buildV2LicenseContainer(interaction.user.id, newLicense);
          const sentMsg = await logChannel.send({ flags: IS_COMPONENTS_V2, components: [v2Container] });
          newLicense.logMessageId = sentMsg.id;
          newLicense.logChannelId = logChannel.id;
          saveLicenses(licenses);
        }
      } catch (e) {}

      return interaction.editReply({
        embeds: [
          new EmbedBuilder()
            .setColor(0x00FF88)
            .setTitle('🎉 License Key Redeemed Successfully!')
            .setDescription(`Welcome to **GX MENU**! Your **${plan}** subscription is now active.`)
            .addFields(
              { name: 'License Key', value: `\`${rawKey}\``, inline: false },
              { name: 'Subscription Plan', value: plan === 'Monthly' ? '📅 Monthly (30 Days)' : '👑 Lifetime VIP', inline: true },
              { name: 'Client Role', value: roleGranted ? '✅ Granted' : '⚠️ Pending Role Sync', inline: true },
              { name: 'Web Portal', value: `[Click Here to Open Client Portal](${PORTAL_URL})`, inline: false }
            )
            .setFooter({ text: 'Cloudflare Worker & Portal Verified' })
            .setTimestamp()
        ]
      });
    }
  }

  // --------------------------------------------------------------------------
  // B. BUTTON INTERACTIONS (Components V2 Controls)
  // --------------------------------------------------------------------------
  if (interaction.isButton()) {
    // 1. Strict Staff Permission Check
    if (!isAuthorizedStaff(interaction.member, interaction.guild, interaction.user.id)) {
      return interaction.reply({
        content: '⛔ **Access Denied! You are not authorized to perform this action.**\nThis action is strictly restricted to Staff Members with role: <@&' + STAFF_ROLE_ID + '>',
        flags: MessageFlags.Ephemeral
      });
    }

    // 2. HOLD / FREEZE BUTTON (Toggle or Modal)
    if (interaction.customId.startsWith('license_hold_')) {
      const targetUserId = interaction.customId.replace('license_hold_', '');
      const licenses = getLicenses();
      const record = licenses[targetUserId];

      if (!record) {
        return interaction.reply({
          content: '⚠️ No license record found for this user in the database.',
          flags: MessageFlags.Ephemeral
        });
      }

      // If already on hold -> Clicking will Unfreeze / Reactivate directly
      if (record.status === 'onhold') {
        record.status = 'active';
        record.holdReason = null;
        delete record.heldAt;
        delete record.heldBy;
        saveLicenses(licenses);

        // Notify customer in DM
        try {
          const targetUser = await client.users.fetch(targetUserId);
          if (targetUser) {
            const unholdEmbed = new EmbedBuilder()
              .setColor(0x00FF88)
              .setTitle('GX MENU — License Reactivated!')
              .setDescription('Your subscription has been successfully reactivated. You may now access the Client Portal and use your license key.')
              .addFields({ name: 'Client Portal', value: '[Click Here to Access](' + PORTAL_URL + ')', inline: false })
              .setTimestamp();
            await targetUser.send({ embeds: [unholdEmbed] });
          }
        } catch (err) {}

        const updatedContainer = buildV2LicenseContainer(targetUserId, record);
        await interaction.update({ flags: IS_COMPONENTS_V2, components: [updatedContainer] });
        return;
      }

      // If active -> Open Modal to ask for Hold Reason
      const modal = new ModalBuilder()
        .setCustomId('modal_hold_' + targetUserId)
        .setTitle('HOLD / FREEZE LICENSE KEY');

      const reasonInput = new TextInputBuilder()
        .setCustomId('hold_reason_input')
        .setLabel('Reason for Hold / Freeze')
        .setStyle(TextInputStyle.Paragraph)
        .setPlaceholder('e.g. Subscription Expired / Policy Violation')
        .setValue('Subscription Expired')
        .setRequired(true);

      const firstActionRow = new ActionRowBuilder().addComponents(reasonInput);
      modal.addComponents(firstActionRow);

      return interaction.showModal(modal);
    }

    // 3. DELETE KEY BUTTON (Ask for Confirmation)
    if (interaction.customId.startsWith('license_delete_')) {
      const targetUserId = interaction.customId.replace('license_delete_', '');
      const messageId = interaction.message ? interaction.message.id : '';

      const confirmRow = new ActionRowBuilder().addComponents(
        new ButtonBuilder()
          .setCustomId('confirm_del_' + targetUserId + '_' + messageId)
          .setLabel('Confirm Delete')
          .setStyle(ButtonStyle.Danger)
          .setEmoji('⚠️'),
        new ButtonBuilder()
          .setCustomId('cancel_del_' + targetUserId)
          .setLabel('Cancel')
          .setStyle(ButtonStyle.Secondary)
          .setEmoji('✖️')
      );

      return interaction.reply({
        content: '⚠️ **Permanent License Deletion Confirmation:**\nAre you sure you want to permanently delete the license key for <@' + targetUserId + '>?\nThis will immediately revoke portal access and remove the Client role <@&' + CLIENT_ROLE_ID + '>.',
        components: [confirmRow],
        flags: MessageFlags.Ephemeral
      });
    }

    // 4. CONFIRMED DELETE
    if (interaction.customId.startsWith('confirm_del_')) {
      const parts = interaction.customId.replace('confirm_del_', '').split('_');
      const targetUserId = parts[0];
      const messageId = parts[1];

      const licenses = getLicenses();
      const userRecord = licenses[targetUserId] || { status: 'revoked' };
      userRecord.status = 'revoked';

      delete licenses[targetUserId];
      saveLicenses(licenses);

      // Remove Client Role
      try {
        if (interaction.guild) {
          const member = await interaction.guild.members.fetch(targetUserId);
          if (member && CLIENT_ROLE_ID) {
            await member.roles.remove(CLIENT_ROLE_ID);
          }
        }
      } catch (err) {}

      // Notify customer via DM in English
      try {
        const targetUser = await client.users.fetch(targetUserId);
        if (targetUser) {
          await targetUser.send({
            embeds: [
              new EmbedBuilder()
                .setColor(0xFF2A55)
                .setTitle('GX MENU — License Key Revoked')
                .setDescription('Your license key and Client role have been revoked by administration.')
                .setTimestamp()
            ]
          });
        }
      } catch (err) {}

      // Update the channel Components V2 message: mark deleted & disable buttons
      try {
        if (messageId && interaction.channel) {
          const targetMsg = await interaction.channel.messages.fetch(messageId).catch(() => null);
          if (targetMsg) {
            const disabledContainer = buildV2LicenseContainer(targetUserId, userRecord);
            await targetMsg.edit({ flags: IS_COMPONENTS_V2, components: [disabledContainer] });
          }
        }
      } catch (err) {}

      return interaction.update({
        content: '✅ **License successfully deleted.**\nKey removed and Client role stripped from <@' + targetUserId + '>.',
        components: []
      });
    }

    // 5. CANCELLED DELETE
    if (interaction.customId.startsWith('cancel_del_')) {
      return interaction.update({
        content: '✖️ **Deletion cancelled.** The license remains active and untouched.',
        components: []
      });
    }
  }

  // --------------------------------------------------------------------------
  // C. MODAL SUBMISSIONS (Hold Reason)
  // --------------------------------------------------------------------------
  if (interaction.isModalSubmit()) {
    if (interaction.customId.startsWith('modal_hold_')) {
      const targetUserId = interaction.customId.replace('modal_hold_', '');
      const reason = interaction.fields.getTextInputValue('hold_reason_input') || 'Subscription Expired';

      const licenses = getLicenses();
      if (!licenses[targetUserId]) {
        return interaction.reply({
          content: '⚠️ No license record found for this user in the database.',
          flags: MessageFlags.Ephemeral
        });
      }

      licenses[targetUserId].status = 'onhold';
      licenses[targetUserId].holdReason = reason;
      licenses[targetUserId].heldAt = new Date().toISOString();
      licenses[targetUserId].heldBy = interaction.user.tag;
      saveLicenses(licenses);

      // Notify customer via DM in English
      try {
        const targetUser = await client.users.fetch(targetUserId);
        if (targetUser) {
          const holdEmbed = new EmbedBuilder()
            .setColor(0xFFB800)
            .setTitle('GX MENU — License Placed ON-HOLD')
            .setDescription('Dear **' + targetUser.username + '**, your license has been placed on hold (Frozen).')
            .addFields(
              { name: 'Hold Reason', value: '```' + reason + '```', inline: false },
              { name: 'Renewal & Inquiries', value: 'Please open a support ticket in our official Discord server.', inline: false }
            )
            .setTimestamp();
          await targetUser.send({ embeds: [holdEmbed] });
        }
      } catch (err) {}

      // Update the channel Components V2 message
      const updatedContainer = buildV2LicenseContainer(targetUserId, licenses[targetUserId]);

      if (interaction.message) {
        await interaction.update({ flags: IS_COMPONENTS_V2, components: [updatedContainer] });
      } else {
        await interaction.reply({
          content: '⏸️ Subscription for <@' + targetUserId + '> is now **ON-HOLD** with reason: `' + reason + '`',
          flags: MessageFlags.Ephemeral
        });
      }
    }
  }
});

// Start bot
if (process.env.DISCORD_BOT_TOKEN && !process.env.DISCORD_BOT_TOKEN.includes('YOUR_DISCORD')) {
  client.login(process.env.DISCORD_BOT_TOKEN);
}
