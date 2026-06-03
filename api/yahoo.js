const ALLOWED_HOSTS = new Set([
  'query1.finance.yahoo.com',
  'query2.finance.yahoo.com',
]);

const ALLOWED_PATHS = [
  /^\/v8\/finance\/chart\/[A-Z0-9.\-]+$/i,
  /^\/v7\/finance\/options\/[A-Z0-9.\-]+$/i,
];

module.exports = async function handler(req, res) {
  if (req.method === 'OPTIONS') {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    return res.status(204).end();
  }

  if (req.method !== 'GET') {
    res.setHeader('Access-Control-Allow-Origin', '*');
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const fullUrl = new URL(req.url, 'http://localhost');
    const target = fullUrl.searchParams.get('url');
    if (!target) {
      res.setHeader('Access-Control-Allow-Origin', '*');
      return res.status(400).json({ error: 'Missing url parameter' });
    }

    const targetUrl = new URL(target);
    if (!ALLOWED_HOSTS.has(targetUrl.hostname) || !ALLOWED_PATHS.some(rx => rx.test(targetUrl.pathname))) {
      res.setHeader('Access-Control-Allow-Origin', '*');
      return res.status(400).json({ error: 'Target URL not allowed' });
    }

    const upstream = await fetch(targetUrl.toString(), {
      headers: {
        'Accept': 'application/json,text/plain,*/*',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
      },
    });

    const text = await upstream.text();
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate');
    res.setHeader('Content-Type', 'application/json; charset=utf-8');

    if (!upstream.ok) {
      return res.status(upstream.status).json({
        error: `Upstream request failed (${upstream.status})`,
        body: text.slice(0, 500),
      });
    }

    try {
      const data = JSON.parse(text);
      return res.status(200).json(data);
    } catch (parseErr) {
      return res.status(502).json({
        error: 'Upstream response was not valid JSON',
        body: text.slice(0, 500),
      });
    }
  } catch (err) {
    res.setHeader('Access-Control-Allow-Origin', '*');
    return res.status(500).json({
      error: err?.message || 'Unexpected proxy error',
    });
  }
};
