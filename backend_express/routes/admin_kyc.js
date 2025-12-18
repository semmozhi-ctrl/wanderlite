const express = require('express');
const router = express.Router();
const { requireAuth } = require('../middleware/auth');
const { getPool } = require('../db');
const os = require('os');

function now() { return new Date().toISOString(); }

function makeLog(meta) {
  return Object.assign({ ts: now(), host: os.hostname() }, meta);
}

function requireAdmin(req, res, next) {
  // Configurable admin guard: check claim specified by ADMIN_CLAIM (default 'is_admin').
  const claim = process.env.ADMIN_CLAIM || 'is_admin';
  const claimValue = process.env.ADMIN_CLAIM_VALUE; // optional
  if (!req.user) return res.status(403).json({ error: 'admin_required' });
  const val = req.user[claim];
  if (typeof claimValue !== 'undefined') {
    // compare stringified values for flexibility
    if (String(val) === String(claimValue)) return next();
  } else {
    if (val) return next();
  }
  return res.status(403).json({ error: 'admin_required' });
}

async function recordAdminAudit(conn, { adminId, action, target, targetId, note, ip }){
  try {
    // insert into audit table if available
    await conn.query('INSERT INTO kyc_audit_logs (kyc_id, admin_id, action, note, ip) VALUES (?, ?, ?, ?, ?)', [targetId || null, adminId || null, action, note || null, ip || null]);
  } catch (e) {
    // fallback to generic admin_actions table
    try {
      await conn.query('INSERT INTO admin_actions (admin_id, action, target, target_id, note, ip) VALUES (?, ?, ?, ?, ?, ?)', [adminId || null, action, target || null, targetId || null, note || null, ip || null]);
    } catch (err) {
      console.warn('recordAdminAudit failed:', err && err.message);
    }
  }
}

// GET /api/admin/kyc/counts
router.get('/kyc/counts', requireAuth, requireAdmin, async (req, res) => {
  try {
    const pool = getPool();
    const [pendingRows] = await pool.query("SELECT COUNT(*) as c FROM kyc_details WHERE verification_status = 'pending'");
    const [verifiedRows] = await pool.query("SELECT COUNT(*) as c FROM kyc_details WHERE verification_status = 'verified'");
    const [rejectedRows] = await pool.query("SELECT COUNT(*) as c FROM kyc_details WHERE verification_status = 'rejected'");
    const out = { pending: pendingRows[0].c || 0, verified: verifiedRows[0].c || 0, rejected: rejectedRows[0].c || 0 };
    console.log('ADMIN_KYC_COUNTS', JSON.stringify(makeLog({ adminId: req.user && req.user.sub, result: out }))); 
    return res.json(out);
  } catch (e) {
    console.error('admin kyc counts error', e && (e.stack || e.message));
    res.status(500).json({ error: 'kyc_counts_failed', message: e && e.message });
  }
});

// GET /api/admin/kyc - list KYC requests (query: status, page, limit)
router.get('/kyc', requireAuth, requireAdmin, async (req, res) => {
  const status = req.query.status;
  const page = Math.max(1, parseInt(req.query.page || '1'));
  const limit = Math.min(100, parseInt(req.query.limit || '20'));
  const offset = (page - 1) * limit;
  try {
    const pool = getPool();
    let q = 'SELECT * FROM kyc_details';
    const params = [];
    if (status) {
      q += ' WHERE verification_status = ?';
      params.push(status);
    }
    q += ' ORDER BY submitted_at DESC LIMIT ? OFFSET ?';
    params.push(limit, offset);
    const [rows] = await pool.query(q, params);
    console.log('ADMIN_KYC_LIST', JSON.stringify(makeLog({ adminId: req.user && req.user.sub, status: status || 'all', count: rows.length })));
    return res.json(rows);
  } catch (e) {
    console.error('admin kyc list error', e && (e.stack || e.message));
    res.status(500).json({ error: 'kyc_list_failed', message: e && e.message });
  }
});

// GET /api/admin/kyc/:id - get detail
router.get('/kyc/:id', requireAuth, requireAdmin, async (req, res) => {
  const id = parseInt(req.params.id);
  try {
    const pool = getPool();
    const [rows] = await pool.query('SELECT * FROM kyc_details WHERE id = ? LIMIT 1', [id]);
    if (!rows || rows.length === 0) return res.status(404).json({ error: 'kyc_not_found' });
    const kyc = rows[0];
    console.log('ADMIN_KYC_DETAIL', JSON.stringify(makeLog({ adminId: req.user && req.user.sub, kycId: id })));
    return res.json(kyc);
  } catch (e) {
    console.error('admin kyc detail error', e && (e.stack || e.message));
    res.status(500).json({ error: 'kyc_detail_failed', message: e && e.message });
  }
});

// POST /api/admin/kyc/:id/review { action: 'approve'|'reject', reason?: string }
router.post('/kyc/:id/review', requireAuth, requireAdmin, async (req, res) => {
  const id = parseInt(req.params.id);
  const action = req.body && req.body.action;
  const reason = req.body && req.body.reason;
  if (!action || !['approve', 'reject'].includes(action)) return res.status(400).json({ error: 'invalid_action' });
  const pool = getPool();
  let conn;
  let kycUpdated = false;
  try {
    conn = await pool.getConnection();
    const [rows] = await conn.query('SELECT * FROM kyc_details WHERE id = ? LIMIT 1', [id]);
    if (!rows || rows.length === 0) return res.status(404).json({ error: 'kyc_not_found' });
    const kyc = rows[0];
    if (action === 'approve') {
      // mark KYC record verified (do not require altering users table here)
      await conn.query("UPDATE kyc_details SET verification_status = 'verified', verified_at = NOW() WHERE id = ?", [id]);
      kycUpdated = true;
    } else {
      await conn.query("UPDATE kyc_details SET verification_status = 'rejected', verified_at = NOW() WHERE id = ?", [id]);
      kycUpdated = true;
    }
    // record audit / action with IP and admin id
    const adminId = (req.user && (req.user.sub || req.user.id || req.user.email)) || null;
    const ip = req.ip || (req.headers && (req.headers['x-forwarded-for'] || req.connection && req.connection.remoteAddress)) || null;
    try {
      await recordAdminAudit(conn, { adminId, action, target: 'kyc', targetId: id, note: reason || null, ip });
    } catch (auditErr) {
      console.warn('audit insert failed', auditErr && auditErr.message);
    }
    console.log('ADMIN_KYC_REVIEW', JSON.stringify(makeLog({ adminId, action, kycId: id, ip })));
    return res.json({ message: `KYC ${action}d successfully` });
  } catch (e) {
    console.error('admin kyc review error', e && (e.stack || e.message));
    if (kycUpdated) {
      // record failure to audit as a warning
      try {
        if (conn) await conn.query('INSERT INTO admin_actions (admin_id, action, target, target_id, note, ip) VALUES (?, ?, ?, ?, ?, ?)', [(req.user && req.user.sub) || null, action, 'kyc', id, 'partial_failure: ' + (e && e.message), req.ip || null]);
      } catch (err2) {
        console.warn('failed to write fallback admin_actions after partial update', err2 && err2.message);
      }
      return res.json({ message: `KYC ${action}d (partial)`, warning: e && e.message });
    }
    res.status(500).json({ error: 'kyc_review_failed', message: e && e.message });
  } finally {
    if (conn && conn.release) conn.release();
  }
});

module.exports = router;
