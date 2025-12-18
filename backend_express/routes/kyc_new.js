const express = require('express');
const router = express.Router();
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const { requireAuth } = require('../middleware/auth');
const { getPool } = require('../db');

// store KYC uploads under uploads/kyc/<userId>/
const baseKycDir = path.join(__dirname, '..', '..', 'uploads', 'kyc');
fs.mkdirSync(baseKycDir, { recursive: true });

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const userId = req.user && req.user.sub;
    const userDir = path.join(baseKycDir, String(userId || 'anonymous'));
    fs.mkdirSync(userDir, { recursive: true });
    cb(null, userDir);
  },
  filename: (req, file, cb) => {
    const ext = path.extname(file.originalname) || '';
    const name = Date.now() + '-' + Math.random().toString(36).slice(2,8) + ext;
    cb(null, name);
  }
});

const upload = multer({ storage });

// POST /api/kyc  - submit KYC form (fields + optional files id_front, id_back, selfie)
router.post('/', requireAuth, upload.fields([
  { name: 'id_front', maxCount: 1 },
  { name: 'id_back', maxCount: 1 },
  { name: 'selfie', maxCount: 1 }
]), async (req, res) => {
  const userId = req.user && req.user.sub;
  const body = req.body || {};
  try {
    const pool = getPool();
    const conn = await pool.getConnection();
    try {
      const idFront = req.files && req.files.id_front && req.files.id_front[0] ? path.relative(path.join(__dirname, '..', '..'), req.files.id_front[0].path).replace(/\\/g, '/') : null;
      const idBack = req.files && req.files.id_back && req.files.id_back[0] ? path.relative(path.join(__dirname, '..', '..'), req.files.id_back[0].path).replace(/\\/g, '/') : null;
      const selfie = req.files && req.files.selfie && req.files.selfie[0] ? path.relative(path.join(__dirname, '..', '..'), req.files.selfie[0].path).replace(/\\/g, '/') : null;

      const q = `INSERT INTO kyc_details (user_id, full_name, dob, gender, nationality, id_type, address_line, city, state, country, pincode, id_proof_front_path, id_proof_back_path, selfie_path, verification_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`;
      const params = [
        userId,
        body.full_name || null,
        body.dob || null,
        body.gender || null,
        body.nationality || null,
        body.id_type || null,
        body.address_line || null,
        body.city || null,
        body.state || null,
        body.country || null,
        body.pincode || null,
        idFront,
        idBack,
        selfie,
        'pending'
      ];
      const [r] = await conn.query(q, params);

      // Also insert into kyc_uploads for file tracking (if any files)
      if (idFront) await conn.query('INSERT INTO kyc_uploads (user_id, file_path, status) VALUES (?, ?, ?)', [userId, idFront, 'uploaded']);
      if (idBack) await conn.query('INSERT INTO kyc_uploads (user_id, file_path, status) VALUES (?, ?, ?)', [userId, idBack, 'uploaded']);
      if (selfie) await conn.query('INSERT INTO kyc_uploads (user_id, file_path, status) VALUES (?, ?, ?)', [userId, selfie, 'uploaded']);

      // return response similar to Python: message + is_kyc_completed false
      return res.status(201).json({ message: 'KYC submitted successfully. Pending admin verification.', is_kyc_completed: false, kyc_id: r.insertId });
    } finally {
      if (conn && conn.release) conn.release();
    }
  } catch (e) {
    console.error('kyc submit error', e && e.stack);
    return res.status(500).json({ error: 'kyc_submit_failed' });
  }
});

// POST /api/kyc/upload  (multipart: file) - single file upload tracking
router.post('/upload', requireAuth, upload.single('file'), async (req, res) => {
  const userId = req.user && req.user.sub;
  if (!req.file) return res.status(400).json({ error: 'file required' });
  try {
    const pool = getPool();
    const filePath = path.relative(path.join(__dirname, '..', '..'), req.file.path).replace(/\\/g, '/');
    const conn = await pool.getConnection();
    try {
      const [r] = await conn.query('INSERT INTO kyc_uploads (user_id, file_path, status) VALUES (?, ?, ?)', [userId, filePath, 'uploaded']);
      return res.status(201).json({ id: r.insertId, user_id: userId, file_path: filePath, status: 'uploaded' });
    } finally {
      if (conn && conn.release) conn.release();
    }
  } catch (e) {
    console.error('kyc upload error', e && e.message);
    res.status(500).json({ error: 'kyc_upload_failed' });
  }
});

// GET /api/kyc/status -- return latest KYC status and details for current user
router.get('/status', requireAuth, async (req, res) => {
  const userId = req.user && req.user.sub;
  try {
    const pool = getPool();
    const conn = await pool.getConnection();
    try {
      const [rows] = await conn.query('SELECT id, full_name, verification_status, submitted_at, id_proof_front_path, id_proof_back_path, selfie_path FROM kyc_details WHERE user_id = ? ORDER BY submitted_at DESC LIMIT 1', [userId]);
      if (!rows || rows.length === 0) return res.json({ is_completed: false, status: 'not_submitted' });
      const last = rows[0];
      return res.json({ id: last.id, full_name: last.full_name, verification_status: last.verification_status, submitted_at: last.submitted_at, id_proof_front: last.id_proof_front_path, id_proof_back: last.id_proof_back_path, selfie: last.selfie_path, is_completed: last.verification_status === 'verified' });
    } finally {
      if (conn && conn.release) conn.release();
    }
  } catch (e) {
    console.error('kyc status error', e && e.message);
    res.status(500).json({ error: 'kyc_status_failed' });
  }
});

module.exports = router;
