const express = require('express');
const router = express.Router();
const { requireAuth, optionalAuth } = require('../middleware/auth');

// POST /api/search/flights
router.post('/search/flights', async (req, res) => {
  const body = req.body || {};
  const { origin, destination, journey_date, page = 1, limit = 20 } = body;
  const pool = require('../db').getPool();
  try {
    const params = [];
    let where = '1=1';
    if (origin) {
      where += ' AND origin_code = ?';
      params.push(origin.toUpperCase());
    }
    if (destination) {
      where += ' AND dest_code = ?';
      params.push(destination.toUpperCase());
    }
    if (journey_date) {
      where += ' AND DATE(departure_datetime) = ?';
      params.push(journey_date);
    }

    const offset = (Number(page) - 1) * Number(limit);
    const sql = `SELECT id, flight_number, airline_code, airline_name, origin_code, origin_city, dest_code, dest_city, DATE_FORMAT(departure_datetime, '%Y-%m-%dT%TZ') as departure_datetime, DATE_FORMAT(arrival_datetime, '%Y-%m-%dT%TZ') as arrival_datetime, duration_mins, base_price_economy, base_price_business, available_economy, available_business FROM flights WHERE ${where} ORDER BY departure_datetime ASC LIMIT ? OFFSET ?`;
    params.push(Number(limit));
    params.push(Number(offset));

    const conn = await pool.getConnection();
    const [rows] = await conn.query(sql, params);
    const [countRows] = await conn.query(`SELECT COUNT(*) as c FROM flights WHERE ${where}`, params.slice(0, params.length-2));
    conn.release();

    const flights = rows.map(r => ({
      flight_id: r.id,
      flight_number: r.flight_number,
      airline: { code: r.airline_code, name: r.airline_name },
      departure_datetime: r.departure_datetime,
      arrival_datetime: r.arrival_datetime,
      duration_mins: r.duration_mins,
      base_price_economy: r.base_price_economy,
      base_price_business: r.base_price_business,
      available_seats: { economy: r.available_economy, business: r.available_business },
      origin: { code: r.origin_code, city: r.origin_city },
      destination: { code: r.dest_code, city: r.dest_city }
    }));

    res.json({ flights, total: countRows[0].c, page: Number(page), limit: Number(limit) });
  } catch (e) {
    console.error('flight search error', e && e.message);
    res.status(500).json({ error: 'flight search failed' });
  }
});

// POST /api/flight/lock
router.post('/flight/lock', (req, res) => {
  const { schedule_id, seats } = req.body || {};
  if (!schedule_id || !seats) return res.status(400).json({ error: 'schedule_id and seats required' });
  // Return a mock lock token
  res.json({ lock_token: `lock_${Date.now()}`, expires_at: new Date(Date.now() + 5*60*1000).toISOString() });
});

// POST /api/flight/book
router.post('/flight/book', requireAuth, (req, res) => {
  // Accept booking payload; respond with booking summary
  const booking = {
    booking_id: 1001,
    booking_reference: `PNR${Math.floor(Math.random()*900000)+100000}`,
    pnr: `PNR${Math.floor(Math.random()*9000)+1000}`,
    final_amount: 4500,
    payment_status: 'pending',
    segments: [],
    created_at: new Date().toISOString()
  };
  res.status(201).json(booking);
});

// GET /api/flight/booking/:booking_ref
router.get('/flight/booking/:booking_ref', requireAuth, (req, res) => {
  const { booking_ref } = req.params;
  // Placeholder: return not found for unknown
  if (booking_ref === 'demo') {
    return res.json({ id: 1, booking_reference: 'demo', pnr: 'PNRDEMO', segments: [], passengers: [], total_amount: 1000, booking_status: 'confirmed' });
  }
  return res.status(404).json({ detail: 'Booking not found' });
});

// GET /api/flight/my-bookings
router.get('/flight/my-bookings', requireAuth, (req, res) => {
  res.json([]);
});

// POST /api/flight/cancel
router.post('/flight/cancel', requireAuth, (req, res) => {
  const { booking_id } = req.body || {};
  if (!booking_id) return res.status(400).json({ error: 'booking_id required' });
  res.json({ booking_id, status: 'cancelled', refund_percentage: 50, refund_amount: 1000, message: 'Booking cancelled' });
});

// GET /api/flight/tracking/:schedule_id
router.get('/flight/tracking/:schedule_id', (req, res) => {
  const schedule_id = Number(req.params.schedule_id);
  if (!schedule_id) return res.status(404).json({ detail: 'Schedule not found' });
  res.json({ schedule_id, flight_number: '6E123', status: 'in_air', progress_percentage: 45.0, current_latitude: 19.1, current_longitude: 72.9, altitude_ft: 35000, speed_kmph: 850, origin: { code: 'DEL', city: 'Delhi' }, destination: { code: 'BOM', city: 'Mumbai' }, departure_time: new Date().toISOString(), arrival_time: new Date(Date.now()+3600000).toISOString(), eta_mins: 60 });
});

module.exports = router;
