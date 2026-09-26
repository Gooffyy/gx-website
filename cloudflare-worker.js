// ==============================================================================
// GX MENU — CLOUDFLARE WORKER: AUTHENTICATION & AUTO-UPDATER ENGINE
// Deployed to: https://tight-base-cfefgx-auth.mahmoudgam3r369.workers.dev
// Bound KV: AUTH_KV
// ==============================================================================

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const key = url.searchParams.get("key");
    const hwid = url.searchParams.get("hwid");
    const action = url.searchParams.get("action");

    // --------------------------------------------------------------------------
    // 0. AUTO-UPDATER MANIFEST (Never expires, replaces dead Pastebin!)
    // URL: /?action=version or /version.json
    // --------------------------------------------------------------------------
    if (action === "version" || url.pathname === "/version.json") {
      const manifestStr = await env.AUTH_KV.get("VERSION_MANIFEST");
      if (manifestStr) {
        return new Response(manifestStr, {
          headers: { 
            "Content-Type": "application/json", 
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-cache"
          }
        });
      }
      // Default fallback manifest
      return new Response(JSON.stringify({
        version: 1.15,
        download_url: "http://localhost:8080/downloads/GX_Loader.exe",
        changelog: "GX Menu v1.15 - Cloudflare Workers KV Authentication & Performance",
        mandatory: true
      }), {
        headers: { 
          "Content-Type": "application/json", 
          "Access-Control-Allow-Origin": "*",
          "Cache-Control": "no-cache"
        }
      });
    }

    // --------------------------------------------------------------------------
    // 1. ADMIN: SET NEW VERSION MANIFEST
    // Example: /?action=set_version&admin=gxdev123&ver=1.16&url=https://...&notes=NewBuild
    // --------------------------------------------------------------------------
    if (action === "set_version") {
      const adminSecret = url.searchParams.get("admin");
      if (adminSecret !== "gxdev123") {
        return new Response(JSON.stringify({ success: false, message: "Unauthorized" }), { status: 403 });
      }
      const ver = parseFloat(url.searchParams.get("ver") || "1.15");
      const dlUrl = url.searchParams.get("url") || "http://localhost:8080/downloads/GX_Loader.exe";
      const notes = url.searchParams.get("notes") || "Latest build release.";
      const manifest = {
        version: ver,
        download_url: dlUrl,
        changelog: notes,
        mandatory: true
      };
      await env.AUTH_KV.put("VERSION_MANIFEST", JSON.stringify(manifest));
      return new Response(JSON.stringify({ 
        success: true, 
        message: "Version manifest updated successfully!", 
        manifest 
      }), {
        headers: { "Content-Type": "application/json" }
      });
    }

    // --------------------------------------------------------------------------
    // 2. ADMIN: GENERATE / ADD KEYS
    // --------------------------------------------------------------------------
    if (action === "add") {
      const adminSecret = url.searchParams.get("admin");
      if (adminSecret !== "gxdev123") {
        return new Response(JSON.stringify({ success: false, message: "Unauthorized" }), { status: 403 });
      }
      if (!key) return new Response(JSON.stringify({ success: false, message: "Missing key parameter" }));

      const days = parseInt(url.searchParams.get("days") || "0"); // 0 = lifetime
      let expiry = "lifetime";
      if (days > 0) {
        const expDate = new Date();
        expDate.setDate(expDate.getDate() + days);
        expiry = expDate.toISOString();
      }

      await env.AUTH_KV.put(key, JSON.stringify({ hwid: "", expiry: expiry, banned: false }));
      return new Response(JSON.stringify({ success: true, message: `Key ${key} created successfully!` }));
    }

    // --------------------------------------------------------------------------
    // 3. ADMIN: RESET HWID
    // --------------------------------------------------------------------------
    if (action === "reset_hwid") {
      const adminSecret = url.searchParams.get("admin");
      if (adminSecret !== "gxdev123") {
        return new Response(JSON.stringify({ success: false, message: "Unauthorized" }), { status: 403 });
      }
      if (!key) return new Response(JSON.stringify({ success: false, message: "Missing key parameter" }));
      const recordStr = await env.AUTH_KV.get(key);
      if (!recordStr) return new Response(JSON.stringify({ success: false, message: "Key not found" }), { status: 404 });
      const data = JSON.parse(recordStr);
      data.hwid = "";
      await env.AUTH_KV.put(key, JSON.stringify(data));
      return new Response(JSON.stringify({ success: true, message: `HWID reset for ${key}` }));
    }

    // --------------------------------------------------------------------------
    // 4. ADMIN: DELETE KEY
    // --------------------------------------------------------------------------
    if (action === "delete") {
      const adminSecret = url.searchParams.get("admin");
      if (adminSecret !== "gxdev123") {
        return new Response(JSON.stringify({ success: false, message: "Unauthorized" }), { status: 403 });
      }
      if (!key) return new Response(JSON.stringify({ success: false, message: "Missing key parameter" }));
      await env.AUTH_KV.delete(key);
      return new Response(JSON.stringify({ success: true, message: `Key ${key} deleted` }));
    }

    // --------------------------------------------------------------------------
    // 5. CLIENT: LICENSE CHECK & HWID LOCK
    // --------------------------------------------------------------------------
    if (!key || !hwid) {
      return new Response(JSON.stringify({ success: false, message: "Missing key or HWID" }), { status: 400 });
    }

    const recordStr = await env.AUTH_KV.get(key);
    if (!recordStr) {
      return new Response(JSON.stringify({ success: false, message: "Invalid license key." }));
    }

    const data = JSON.parse(recordStr);

    if (data.banned) {
      return new Response(JSON.stringify({ success: false, message: "This key has been banned." }));
    }

    // Expiry check
    if (data.expiry !== "lifetime" && new Date(data.expiry) < new Date()) {
      return new Response(JSON.stringify({ success: false, message: "License key has expired." }));
    }

    // First login locks the HWID
    if (!data.hwid || data.hwid === "") {
      data.hwid = hwid;
      await env.AUTH_KV.put(key, JSON.stringify(data));
      return new Response(JSON.stringify({ success: true, message: "Key activated! Bound to your PC." }));
    }

    // If already locked, verify HWID
    if (data.hwid !== hwid) {
      return new Response(JSON.stringify({ success: false, message: "HWID mismatch! Key is locked to another PC." }));
    }

    return new Response(JSON.stringify({ success: true, message: "Access granted!" }));
  }
};
