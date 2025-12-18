const express = require('express');
const router = express.Router();
const { requireAuth } = require('../middleware/auth');

router.post('/restaurant/search', async (req, res) => {
  const body = req.body || {};
  const { city, cuisine, page = 1, limit = 20 } = body;
  const pool = require('../db').getPool();
  try {
    let where = '1=1';
    const params = [];
    if (city) { where += ' AND city = ?'; params.push(city); }
    if (cuisine) { where += ' AND cuisine = ?'; params.push(cuisine); }
    const offset = (Number(page)-1)*Number(limit);
    const conn = await pool.getConnection();
    const [rows] = await conn.query(`SELECT id, name, city, cuisine, rating, average_cost, available_slots FROM restaurants WHERE ${where} ORDER BY rating DESC LIMIT ? OFFSET ?`, [...params, Number(limit), Number(offset)]);
    const [countRows] = await conn.query(`SELECT COUNT(*) as c FROM restaurants WHERE ${where}`, params);
    conn.release();
    res.json({ restaurants: rows, total: countRows[0].c, page: Number(page), limit: Number(limit), pages: Math.ceil(countRows[0].c/limit) });
  } catch (e) {
    console.error('restaurant search error', e && e.message);
    res.status(500).json({ error: 'restaurant search failed' });
  }
});

router.post('/restaurant/book', requireAuth, async (req, res) => {
  const userId = req.user && req.user.sub;
  const { restaurant_id, booking_date, time_slot, guests = 1, total_amount } = req.body || {};
  if (!booking_date || !time_slot) return res.status(400).json({ error: 'booking_date and time_slot required' });
  try {
    const pool = require('../db').getPool();
    const conn = await pool.getConnection();
    try {
      // Lookup restaurant basic info if id given
      let restaurantName = 'Unknown Restaurant';
      if (restaurant_id) {
        const [rrows] = await conn.query('SELECT id, name, average_cost FROM restaurants WHERE id = ? LIMIT 1', [restaurant_id]);
        if (rrows && rrows[0]) {
          restaurantName = rrows[0].name;
        }
      }

      const bookingRef = `RB${Date.now()}`;
      const bookingData = { restaurant_id: restaurant_id || null, restaurant_name: restaurantName, booking_date, time_slot, guests };
      // insert booking into available bookings schema
      const [colsRows] = await conn.query("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='bookings'");
      const bcols = (colsRows || []).map(r => r.COLUMN_NAME);
      let bookingId;
      if (bcols.includes('type') && bcols.includes('reference')) {
        const [bres] = await conn.query('INSERT INTO bookings (user_id, type, reference, data) VALUES (?, ?, ?, ?)', [userId, 'restaurant', bookingRef, JSON.stringify(bookingData)]);
        bookingId = bres.insertId;
      } else if (bcols.includes('service_type') && bcols.includes('booking_ref')) {
        const [bres] = await conn.query('INSERT INTO bookings (user_id, service_type, booking_ref, service_details) VALUES (?, ?, ?, ?)', [userId, 'restaurant', bookingRef, JSON.stringify(bookingData)]);
        bookingId = bres.insertId;
      } else {
        const [bres] = await conn.query('INSERT INTO bookings (user_id, service_details) VALUES (?, ?)', [userId, JSON.stringify(bookingData)]);
        bookingId = bres.insertId;
      }

      // Create a payment record (pending) for this booking - be resilient to existing payments schema
      const amount = typeof total_amount !== 'undefined' ? Number(total_amount) : null;
      const [payColsRows] = await conn.query("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='payments'");
      const payCols = (payColsRows || []).map(r => r.COLUMN_NAME);
      let paymentId = null;
      if (payCols.includes('booking_id')) {
        const [pres] = await conn.query('INSERT INTO payments (booking_id, user_id, amount, currency, status) VALUES (?, ?, ?, ?, ?)', [bookingId, userId, amount, 'INR', 'pending']);
        paymentId = pres.insertId;
      } else if (payCols.includes('booking_ref')) {
        // insert into legacy payments table: choose only columns that exist
        const insertCols = [];
        const insertVals = [];
        insertCols.push('booking_ref'); insertVals.push(bookingRef);
        if (payCols.includes('amount')) { insertCols.push('amount'); insertVals.push(amount); }
        if (payCols.includes('method')) { insertCols.push('method'); insertVals.push(null); }
        if (payCols.includes('receipt_url')) { insertCols.push('receipt_url'); insertVals.push(null); }
        if (payCols.includes('ticket_url')) { insertCols.push('ticket_url'); insertVals.push(null); }
        const q = `INSERT INTO payments (${insertCols.join(',')}) VALUES (${insertCols.map(()=>'?').join(',')})`;
        const [pres] = await conn.query(q, insertVals);
        paymentId = pres.insertId;
      } else {
        // best-effort fallback: insert into payments only if minimal columns exist
        try {
          const [pres] = await conn.query('INSERT INTO payments (user_id, amount, status) VALUES (?, ?, ?)', [userId, amount, 'pending']);
          paymentId = pres.insertId;
        } catch (e) {
          console.warn('Unable to create payment record for booking:', e && e.message);
          paymentId = null;
        }
      }

      conn.release();

      return res.status(201).json({ booking: { id: bookingId, booking_reference: bookingRef, restaurant_name: restaurantName, booking_date, time_slot, guests, total_amount: amount, payment: { id: paymentId, status: 'pending' }, created_at: new Date().toISOString() } });
    } catch (e) {
      conn.release();
      throw e;
    }
  } catch (e) {
    console.error('restaurant booking error', e && e.message);
    res.status(500).json({ error: 'restaurant booking failed' });
  }
});

module.exports = router;
