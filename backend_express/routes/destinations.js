const express = require('express');
const router = express.Router();

// GET /api/destinations - proxy to Python for exact parity
const PY_BASE = process.env.PY_BASE || 'http://127.0.0.1:8001';
router.get('/', async (req, res) => {
  try {
    const target = PY_BASE + req.originalUrl;
    const r = await fetch(target, { headers: { accept: 'application/json' } });
    const text = await r.text();
    res.status(r.status);
    try { return res.json(JSON.parse(text)); } catch (e) { return res.send(text); }
  } catch (e) {
    return res.status(502).json({ detail: 'proxy_failed' });
  }
});

module.exports = router;
