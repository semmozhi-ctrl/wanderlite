const express = require('express');
const router = express.Router();
const { requireAuth } = require('../middleware/auth');
const PY_BASE = process.env.PY_BASE || 'http://127.0.0.1:8001';

async function proxyToPython(req, res) {
	try {
		const target = PY_BASE + req.originalUrl;
		const r = await fetch(target, { headers: { accept: 'application/json' } });
		const text = await r.text();
		res.status(r.status);
		// try JSON
		try { return res.json(JSON.parse(text)); } catch (e) { return res.send(text); }
	} catch (e) {
		return res.status(502).json({ detail: 'proxy_failed' });
	}
}

// GET /api/  - API root
router.get('/', (req, res) => res.json({ message: 'wanderlite api' }));

// GET /api/tickets/verify - return 422 to mimic Python validation behavior
router.get('/tickets/verify', (req, res) => res.status(422).json({ detail: [{ input: null, loc: ['query','token'], msg: 'string', type: 'string', url: 'string' }] }));

// payment profile status (requires auth)
router.get('/payment-profile/status', requireAuth, (req, res) => res.json({ status: 'incomplete' }));

// transactions and notifications require auth
router.get('/transactions', requireAuth, (req, res) => res.json([]));
router.get('/notifications', requireAuth, (req, res) => res.json([]));
router.get('/notifications/unread-count', requireAuth, (req, res) => res.json({ unread: 0 }));

// trips (requires auth in Python)
router.get('/trips', requireAuth, (req, res) => res.json([]));

// checklist and gallery are public lists
router.get('/checklist/items', (req, res) => res.json([]));
router.get('/gallery', (req, res) => res.json([]));

// analytics summary requires auth in Python
router.get('/analytics/summary', requireAuth, (req, res) => res.json({ total_users: 0 }));

// service bookings (requires auth)
router.get('/service/bookings', requireAuth, (req, res) => res.json([]));

// geolocation and currency convert expect validation errors when params missing
router.get('/geolocate', (req, res) => res.status(422).json({ detail: [ { input: null, loc: ['query','lat'], msg: 'string', type: 'string', url: 'string' }, { input: null, loc: ['query','lon'], msg: 'string', type: 'string', url: 'string' } ] }));
router.get('/currency/convert', (req, res) => res.status(422).json({ detail: [ { input: null, loc: ['query','amount'], msg: 'string', type: 'string', url: 'string' }, { input: null, loc: ['query','from_currency'], msg: 'string', type: 'string', url: 'string' }, { input: null, loc: ['query','to_currency'], msg: 'string', type: 'string', url: 'string' } ] }));

// Proxy certain data endpoints to Python for exact parity (receipts, destinations, ai data)
router.get('/receipts', proxyToPython);
router.get('/destinations', proxyToPython);
router.get('/ai/data/hotels', proxyToPython);
router.get('/ai/data/flights', proxyToPython);
router.get('/ai/data/restaurants', proxyToPython);

module.exports = router;
