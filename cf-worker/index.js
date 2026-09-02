import puppeteer from "@cloudflare/puppeteer";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Xac thuc bang secret token - chap nhan ca qua header (dung cho production/GitHub Actions)
    // va qua query param ?token=... (de test nhanh bang trinh duyet)
    const authHeader = request.headers.get("Authorization");
    const queryToken = url.searchParams.get("token");
    const validAuth =
      authHeader === `Bearer ${env.AUTH_TOKEN}` || queryToken === env.AUTH_TOKEN;

    if (!validAuth) {
      return new Response("Unauthorized", { status: 401 });
    }

    const targetUrl = url.searchParams.get("target") || "https://www.vietlott.vn";

    let browser;
    try {
      browser = await puppeteer.launch(env.MYBROWSER);
      const page = await browser.newPage();

      await page.setUserAgent(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
      );

      const response = await page.goto(targetUrl, {
        waitUntil: "networkidle0",
        timeout: 45000,
      });

      const initialStatus = response.status();

      // Doi them cho Cloudflare Managed Challenge tu giai (neu co)
      await new Promise((resolve) => setTimeout(resolve, 8000));

      const title = await page.title();
      const content = await page.content();

      await browser.close();

      const stillChallenged =
        title.toLowerCase().includes("just a moment") ||
        content.toLowerCase().includes("checking your browser");

      return new Response(
        JSON.stringify({
          initial_status: initialStatus,
          title: title,
          still_challenged: stillChallenged,
          html_length: content.length,
          html: content,
        }, null, 2),
        {
          headers: { "Content-Type": "application/json" },
        }
      );
    } catch (err) {
      if (browser) await browser.close();
      return new Response(
        JSON.stringify({ error: err.message }),
        { status: 500, headers: { "Content-Type": "application/json" } }
      );
    }
  },
};
