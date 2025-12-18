const express = require('express');
const jwt = require('jsonwebtoken');
const router = express.Router();
const secret = process.env.JWT_SECRET || 'change_this_secret';
const { getPool } = require('../db');
const bcrypt = require('bcryptjs');

// POST /api/auth/login
router.post('/login', async (req, res) => {
  const { email, password } = req.body || {};
  if (!email || !password) return res.status(400).json({ error: 'email and password required' });

  try {
    const pool = getPool();
    // detect available columns on users table to be resilient to different schemas
    const [colsRows] = await pool.query("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='users'");
    const cols = (colsRows || []).map(r => r.COLUMN_NAME);
    const selectCols = ['id','email'];
    const passwordCol = cols.includes('password_hash') ? 'password_hash' : (cols.includes('password') ? 'password' : null);
    const nameCol = cols.includes('name') ? 'name' : (cols.includes('username') ? 'username' : null);
    if (passwordCol) selectCols.push(passwordCol);
    if (cols.includes('phone')) selectCols.push('phone');

    const q = `SELECT ${selectCols.join(', ')} FROM users WHERE email = ? LIMIT 1`;
    const [rows] = await pool.query(q, [email]);
    const user = rows && rows[0];
    if (!user) return res.status(401).json({ error: 'Invalid credentials' });

    const hashValue = passwordCol ? user[passwordCol] : null;
    const ok = await bcrypt.compare(password, hashValue || '');
    if (!ok) return res.status(401).json({ error: 'Invalid credentials' });

    const tokenPayload = { sub: user.id, email: user.email };
    if (nameCol && user[nameCol]) tokenPayload.name = user[nameCol];
    const token = jwt.sign(tokenPayload, secret, { expiresIn: '7d' });
    if (passwordCol) delete user[passwordCol];
    res.json({ access_token: token, token_type: 'bearer', user });
  } catch (e) {
    console.error('Login error', e);
    res.status(500).json({ error: 'internal_error' });
  }
});

// POST /api/auth/signup
router.post('/signup', async (req, res) => {
  const { name, email, password, phone } = req.body || {};
  if (!email || !password) return res.status(400).json({ error: 'email and password required' });

  try {
    const hash = await bcrypt.hash(password, 10);
    const pool = getPool();
    // determine password column to write to
    const [colsRows] = await pool.query("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='users'");
    const cols = (colsRows || []).map(r => r.COLUMN_NAME);
    const passwordCol = cols.includes('password_hash') ? 'password_hash' : (cols.includes('password') ? 'password' : null);
    const nameCol = cols.includes('name') ? 'name' : (cols.includes('username') ? 'username' : null);

    let insertQ, insertParams;
    const havePhone = cols.includes('phone');
    if (passwordCol) {
      const extraCols = [];
      const extraPlaceholders = [];
      if (havePhone) { extraCols.push('phone'); extraPlaceholders.push('?'); }
      if (nameCol) { extraCols.push(nameCol); extraPlaceholders.push('?'); }
      insertQ = `INSERT INTO users (email, ${passwordCol}${extraCols.length ? ', ' + extraCols.join(', ') : ''}) VALUES (?, ?${extraPlaceholders.length ? ', ' + extraPlaceholders.join(', ') : ''})`;
      insertParams = [email, hash];
      if (havePhone) insertParams.push(phone || null);
      if (nameCol) insertParams.push(name || null);
    } else {
      // fallback: insert only email (and phone if available)
      if (havePhone) {
        insertQ = 'INSERT INTO users (email, phone) VALUES (?, ?)';
        insertParams = [email, phone || null];
      } else {
        insertQ = 'INSERT INTO users (email) VALUES (?)';
        insertParams = [email];
      }
    }

    const [result] = await pool.query(insertQ, insertParams);
    return res.status(201).json({ message: 'user created', user_id: result.insertId });
  } catch (e) {
    if (e && e.code === 'ER_DUP_ENTRY') return res.status(400).json({ error: 'email_exists' });
    console.error('Signup error', e);
    res.status(500).json({ error: 'internal_error' });
  }
});

// GET /api/auth/me
const { requireAuth } = require('../middleware/auth');
router.get('/me', requireAuth, async (req, res) => {
  try {
    const pool = getPool();
    const userId = req.user && req.user.sub;
    const [rows] = await pool.query('SELECT id, name as full_name, email, phone, created_at FROM users WHERE id = ? LIMIT 1', [userId]);
    const user = rows && rows[0];
    if (!user) return res.status(404).json({ error: 'user_not_found' });
    user.kyc_status = 'not_submitted';
    res.json(user);
  } catch (e) {
    console.error('Me error', e);
    res.status(500).json({ error: 'internal_error' });
  }
});

module.exports = router;
