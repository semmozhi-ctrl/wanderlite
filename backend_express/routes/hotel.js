const express = require('express');
const router = express.Router();
const { requireAuth } = require('../middleware/auth');

router.get('/hotel/cities', (req, res) => {
  const search = req.query.search || null;
  res.json([{ city: 'Mumbai', state: 'Maharashtra', country: 'India', hotel_count: 120 }]);
});

router.post('/hotel/search', async (req, res) => {
  const body = req.body || {};
  const { city, page = 1, limit = 20 } = body;
  const pool = require('../db').getPool();
  try {
    const params = [];
    let where = '1=1';
    if (city) { where += ' AND city = ?'; params.push(city); }
    const offset = (Number(page)-1)*Number(limit);
    const conn = await pool.getConnection();
    const [rows] = await conn.query(`SELECT id, name, city, state, country, rating, price_per_night, rooms_available FROM hotels WHERE ${where} ORDER BY rating DESC LIMIT ? OFFSET ?`, [...params, Number(limit), Number(offset)]);
    const [countRows] = await conn.query(`SELECT COUNT(*) as c FROM hotels WHERE ${where}`, params);
    conn.release();
    res.json({ hotels: rows, total: countRows[0].c, page: Number(page), limit: Number(limit), pages: Math.ceil(countRows[0].c/limit), search_params: { city } });
  } catch (e) {
    console.error('hotel search error', e && e.message);
    res.status(500).json({ error: 'hotel search failed' });
  }
});

router.get('/hotel/:hotel_id/rooms', (req, res) => {
  const hotel_id = Number(req.params.hotel_id);
  res.json({ rooms: [{ id: 1, hotel_id, room_name: 'Standard', price_per_night: 3500, available_rooms: 5 }], count: 1 });
});

router.post('/hotel/book', requireAuth, (req, res) => {
  // Minimal create booking response
  res.status(201).json({ booking_id: `hb-${Date.now()}`, booking_reference: `HTL${Math.floor(Math.random()*900000)+100000}`, hotel_name: 'Demo Hotel', room_name: 'Standard', nights: 2, total_amount: 7000, payment_status: 'pending', qr_code: 'base64...', created_at: new Date().toISOString() });
});

module.exports = router;
