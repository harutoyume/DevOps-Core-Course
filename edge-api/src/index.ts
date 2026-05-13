export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    console.log("request", {
      path: url.pathname,
      colo: request.cf?.colo,
      method: request.method,
    });

    if (url.pathname === "/health") {
      return Response.json({ status: "ok" });
    }

    if (url.pathname === "/edge") {
      const cf = request.cf;
      return Response.json({
        colo: cf?.colo,
        country: cf?.country,
        city: cf?.city,
        asn: cf?.asn,
        httpProtocol: cf?.httpProtocol,
        tlsVersion: cf?.tlsVersion,
      });
    }

    if (url.pathname === "/deploy") {
      return Response.json({
        app: env.APP_NAME,
        course: env.COURSE_NAME,
        message: "Deployment metadata for this Worker (v2)",
        timestamp: new Date().toISOString(),
        hasApiToken: Boolean(env.API_TOKEN),
        adminConfigured: Boolean(env.ADMIN_EMAIL),
      });
    }

    if (url.pathname === "/counter") {
      const raw = await env.SETTINGS.get("visits");
      const visits = Number(raw ?? "0") + 1;
      await env.SETTINGS.put("visits", String(visits));
      return Response.json({ visits });
    }

    if (url.pathname === "/" || url.pathname === "") {
      return Response.json({
        app: env.APP_NAME,
        course: env.COURSE_NAME,
        message: "Hello from Cloudflare Workers",
        routes: ["/", "/health", "/edge", "/deploy", "/counter"],
        timestamp: new Date().toISOString(),
      });
    }

    return new Response("Not Found", { status: 404 });
  },
};
