const express = require('express');
const router = express.Router();
const { requireAuth } = require('../middleware/auth');

// POST /api/ai/proxy  -- forwards request body to external AI API configured with env vars
router.post('/proxy', requireAuth, async (req, res) => {
  const AI_URL = process.env.AI_API_URL;
  const AI_KEY = process.env.AI_API_KEY;
  if (!AI_URL || !AI_KEY) return res.status(500).json({ error: 'ai_not_configured' });
  try {
    const body = req.body || {};
    const fetchImpl = global.fetch || require('node-fetch');
    const r = await fetchImpl(AI_URL, {
      method: 'POST',
      headers: Object.assign({ 'Content-Type': 'application/json', 'Authorization': `Bearer ${AI_KEY}` }, req.headers || {}),
      body: JSON.stringify(body)
    });
    const text = await r.text();
    // try to parse JSON, otherwise return raw
    try { return res.status(r.status).json(JSON.parse(text)); } catch (e) { return res.status(r.status).send(text); }
  } catch (e) {
    console.error('ai proxy error', e && e.message);
    res.status(500).json({ error: 'ai_proxy_failed' });
  }
});

module.exports = router;

// Lightweight data endpoints used by AI features (read-only stubs to preserve API parity)
router.get('/data/hotels', (req, res) => {
  return res.json({ count: 2, hotels: [
    { amenities: ['Pool','WiFi'], best_for: 'family', location: 'City A', name: 'Sample Hotel A', price_per_night: 100, rating: 4.2, type: 'hotel' },
    { amenities: ['WiFi','Breakfast'], best_for: 'budget', location: 'City B', name: 'Sample Hotel B', price_per_night: 50, rating: 3.9, type: 'hostel' }
  ] });
});

router.get('/data/flights', (req, res) => {
  return res.json({ count: 2, flights: [
    { airline: 'SampleAir', class: 'economy', destination: 'City B', duration: '1h', flight_number: 'SA100', origin: 'City A', price: 50, stops: 0 },
    { airline: 'FlyNow', class: 'business', destination: 'City C', duration: '2h', flight_number: 'FN200', origin: 'City A', price: 150, stops: 1 }
  ] });
});

router.get('/data/restaurants', (req, res) => {
  return res.json({ count: 2, restaurants: [
    { best_for: 'dinner', cuisine: 'Indian', location: 'City A', name: 'Resto A', price_range: '$$', rating: 4.5, specialties: ['Dish1'] },
    { best_for: 'lunch', cuisine: 'Italian', location: 'City B', name: 'Resto B', price_range: '$', rating: 4.0, specialties: ['Pasta'] }
  ] });
});

router.get('/policies', (req, res) => {
  return res.json({ booking: { flights: 'string', hotels: 'string', restaurants: 'string' }, cancellation: { flights: 'string', hotels: 'string', restaurants: 'string' }, refund: { general: 'string' } });
});
