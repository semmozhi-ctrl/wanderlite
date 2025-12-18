const express = require('express');
const router = express.Router();
const { requireAuth, optionalAuth } = require('../middleware/auth');
const { getPool } = require('../db');

// POST /api/bookings  -- create a generic booking record
router.post('/', requireAuth, async (req, res) => {
  const userId = req.user && req.user.sub;
  const { type, reference, data } = req.body || {};
  if (!type) return res.status(400).json({ error: 'type required' });
  try {
    const pool = getPool();
    // detect bookings table columns and insert accordingly
    const [colsRows] = await pool.query("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='bookings'");
    const cols = (colsRows || []).map(r => r.COLUMN_NAME);
    if (cols.includes('type') && cols.includes('reference')) {
      const [result] = await pool.query('INSERT INTO bookings (user_id, type, reference, data) VALUES (?, ?, ?, ?)', [userId, type, reference || null, JSON.stringify(data || {})]);
      return res.status(201).json({ id: result.insertId, user_id: userId, type, reference, data });
    } else if (cols.includes('service_type') && cols.includes('booking_ref')) {
      const [result] = await pool.query('INSERT INTO bookings (user_id, service_type, booking_ref, service_details) VALUES (?, ?, ?, ?)', [userId, type, reference || null, JSON.stringify(data || {})]);
      return res.status(201).json({ id: result.insertId, user_id: userId, type, reference, data });
    } else {
      // fallback generic insert where possible
      const [result] = await pool.query('INSERT INTO bookings (user_id, data) VALUES (?, ?)', [userId, JSON.stringify({ type, reference, data })]);
      return res.status(201).json({ id: result.insertId, user_id: userId, type, reference, data });
    }
  } catch (e) {
    console.error('Create booking error', e);
    res.status(500).json({ error: 'internal_error' });
  }
});

// GET /api/bookings  -- list bookings for current user (optional for public)
router.get('/', optionalAuth, async (req, res) => {
  const userId = req.user && req.user.sub;
  if (!userId) return res.json([]);
  try {
    const pool = getPool();
    const [colsRows] = await pool.query("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='bookings'");
    const cols = (colsRows || []).map(r => r.COLUMN_NAME);
    let rows;
    if (cols.includes('type') && cols.includes('reference')) {
      const [r] = await pool.query('SELECT id, type, reference, data, created_at FROM bookings WHERE user_id = ? ORDER BY created_at DESC LIMIT 100', [userId]);
      rows = r;
    } else if (cols.includes('service_type') && cols.includes('booking_ref')) {
      const [r] = await pool.query('SELECT id, service_type, booking_ref, service_details as data, created_at FROM bookings WHERE user_id = ? ORDER BY created_at DESC LIMIT 100', [userId]);
      // normalize to expected keys
      rows = r.map(x => ({ id: x.id, type: x.service_type, reference: x.booking_ref, data: x.data, created_at: x.created_at }));
    } else {
      const [r] = await pool.query('SELECT id, NULL as type, NULL as reference, service_details as data, created_at FROM bookings WHERE user_id = ? ORDER BY created_at DESC LIMIT 100', [userId]);
      rows = r;
    }
    // return as an array to match Python's `/api/bookings` which returns a list
    return res.json(rows || []);
  } catch (e) {
    console.error('List bookings error', e);
    res.status(500).json({ error: 'internal_error' });
  }
});

module.exports = router;
