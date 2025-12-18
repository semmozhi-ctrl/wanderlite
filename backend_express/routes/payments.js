const express = require('express');
const router = express.Router();
const { requireAuth } = require('../middleware/auth');
const { getPool } = require('../db');

// POST /api/payments/create  -- create a payment for an existing booking
router.post('/create', requireAuth, async (req, res) => {
  const userId = req.user && req.user.sub;
  const { booking_id, amount, method } = req.body || {};
  if (!booking_id || !amount) return res.status(400).json({ error: 'booking_id and amount required' });
  try {
    const pool = getPool();
    const conn = await pool.getConnection();
    try {
      const [colsRows] = await conn.query("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='payments'");
      const cols = (colsRows || []).map(r => r.COLUMN_NAME);
      let r;
      if (cols.includes('booking_id')) {
        [r] = await conn.query('INSERT INTO payments (booking_id, user_id, amount, currency, method, status) VALUES (?, ?, ?, ?, ?, ?)', [booking_id, userId, amount, 'INR', method || null, 'pending']);
      } else if (cols.includes('booking_ref')) {
        [r] = await conn.query('INSERT INTO payments (booking_ref, amount, method, status) VALUES (?, ?, ?, ?)', [booking_id, amount, method || null, 'pending']);
      } else {
        [r] = await conn.query('INSERT INTO payments (user_id, amount, status) VALUES (?, ?, ?)', [userId, amount, 'pending']);
      }
      const paymentId = r.insertId;
      conn.release();
      return res.status(201).json({ id: paymentId, booking_id, amount, currency: 'INR', method: method || null, status: 'pending' });
    } finally {
      if (conn && conn.release) conn.release();
    }
  } catch (e) {
    console.error('create payment error', e && e.message);
    res.status(500).json({ error: 'payment_create_failed' });
  }
});

// POST /api/payments/:id/complete  -- mark payment complete (simulate gateway callback)
router.post('/:id/complete', requireAuth, async (req, res) => {
  const paymentId = req.params.id;
  try {
    const pool = getPool();
    const conn = await pool.getConnection();
    try {
      const [colsRows] = await conn.query("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='payments'");
      const cols = (colsRows || []).map(r => r.COLUMN_NAME);
      if (cols.includes('status')) {
        await conn.query('UPDATE payments SET status = ?, external_ref = ? WHERE id = ?', ['completed', req.body.external_ref || null, paymentId]);
      } else if (cols.includes('ticket_url')) {
        await conn.query('UPDATE payments SET ticket_url = ? WHERE id = ?', [req.body.external_ref || null, paymentId]);
      } else {
        // fallback: try to set receipt_url or do nothing
        if (cols.includes('receipt_url')) await conn.query('UPDATE payments SET receipt_url = ? WHERE id = ?', [req.body.external_ref || null, paymentId]);
      }
      const [rows] = await conn.query('SELECT * FROM payments WHERE id = ?', [paymentId]);
      conn.release();
      return res.json(rows && rows[0] ? rows[0] : {});
    } finally {
      if (conn && conn.release) conn.release();
    }
  } catch (e) {
    console.error('complete payment error', e && e.message);
    res.status(500).json({ error: 'payment_complete_failed' });
  }
});

// GET /api/payments/:id
router.get('/:id', requireAuth, async (req, res) => {
  const paymentId = req.params.id;
  try {
    const pool = getPool();
    const [rows] = await pool.query('SELECT * FROM payments WHERE id = ?', [paymentId]);
    return res.json(rows && rows[0] ? rows[0] : {});
  } catch (e) {
    console.error('get payment error', e && e.message);
    res.status(500).json({ error: 'payment_lookup_failed' });
  }
});

module.exports = router;

// GET /api/payments  -- list payments for current user (schema-aware)
router.get('/', requireAuth, async (req, res) => {
  const userId = req.user && req.user.sub;
  try {
    const pool = getPool();
    const [colsRows] = await pool.query("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='payments'");
    const cols = (colsRows || []).map(r => r.COLUMN_NAME);

    if (cols.includes('user_id')) {
      const [rows] = await pool.query('SELECT * FROM payments WHERE user_id = ? ORDER BY created_at DESC LIMIT 200', [userId]);
      return res.json({ payments: rows });
    }

    if (cols.includes('booking_ref')) {
      // find booking_refs for this user
      const [brows] = await pool.query('SELECT booking_ref FROM bookings WHERE user_id = ?', [userId]);
      const refs = (brows || []).map(r => r.booking_ref).filter(Boolean);
      if (refs.length === 0) return res.json({ payments: [] });
      // build placeholders
      const placeholders = refs.map(()=>'?').join(',');
      const [rows] = await pool.query(`SELECT * FROM payments WHERE booking_ref IN (${placeholders}) ORDER BY created_at DESC LIMIT 200`, refs);
      return res.json({ payments: rows });
    }

    // fallback: try to select payments and return those that match a booking via join if possible
    try {
      const [rows] = await pool.query('SELECT p.* FROM payments p JOIN bookings b ON (p.booking_ref = b.booking_ref) WHERE b.user_id = ? ORDER BY p.created_at DESC LIMIT 200', [userId]);
      return res.json({ payments: rows });
    } catch (e) {
      return res.json({ payments: [] });
    }
  } catch (e) {
    console.error('payments list error', e && e.message);
    res.status(500).json({ error: 'payments_list_failed' });
  }
});

