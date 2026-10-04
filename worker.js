let deviceState = {
  temp: 0,
  hum: 0,
  soil: 0,
  valve1: false,
  valve2: false,
  lastSeen: 0
};

let pendingCommands = [];

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    const headers = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, X-API-KEY",
      "Content-Type": "application/json"
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { headers });
    }

    const apiKey = request.headers.get("X-API-KEY");
    const VALID_KEY = "138712"; // کلید مستر دستگاه شما

    if (apiKey !== VALID_KEY) {
      return new Response(JSON.stringify({ ok: false, error: "Unauthorized" }), { status: 401, headers });
    }

    // سینک شدن ESP32 با سرور
    if (path === "/api/device/sync" && request.method === "POST") {
      const data = await request.json();
      deviceState = { ...data, lastSeen: Date.now() };

      const cmdsToSend = [...pendingCommands];
      pendingCommands = [];

      return new Response(JSON.stringify({ ok: true, commands: cmdsToSend }), { headers });
    }

    // دریافت وضعیت توسط وب‌سایت کنترل از راه دور
    if (path === "/api/remote/status" && request.method === "GET") {
      return new Response(JSON.stringify({ ok: true, state: deviceState }), { headers });
    }

    // ارسال دستور از وب‌سایت به ESP32
    if (path === "/api/remote/command" && request.method === "POST") {
      const body = await request.json();
      if (body.command) {
        pendingCommands.push(body.command);
        return new Response(JSON.stringify({ ok: true, message: "Command queued" }), { headers });
      }
      return new Response(JSON.stringify({ ok: false, error: "Invalid command" }), { status: 400, headers });
    }

    return new Response(JSON.stringify({ ok: false, error: "Not found" }), { status: 404, headers });
  }
};
