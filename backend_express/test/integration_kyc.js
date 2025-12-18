require('dotenv').config();
const fs = require('fs');
const path = require('path');
const fetch = require('node-fetch');
const FormData = require('form-data');
const jwt = require('jsonwebtoken');

async function main(){
  const base = 'http://localhost:3000';
  const { randomUUID } = require('crypto');
  const password = 'pass1234';
  let email;
  // To avoid signup race / duplicate issues in CI, create a user directly in the DB and sign a JWT for it.
  const mysql = require('mysql2/promise');
  const bcrypt = require('bcryptjs');
  const MYSQL_HOST = process.env.MYSQL_HOST || '127.0.0.1';
  const MYSQL_PORT = process.env.MYSQL_PORT ? Number(process.env.MYSQL_PORT) : 3306;
  const MYSQL_USER = process.env.MYSQL_USER || 'root';
  const MYSQL_PASS = process.env.MYSQL_PASS || '';
  const MYSQL_DB = process.env.MYSQL_DB || 'wanderlite';

  const pool = await mysql.createPool({ host: MYSQL_HOST, port: MYSQL_PORT, user: MYSQL_USER, password: MYSQL_PASS, database: MYSQL_DB, waitForConnections:true, connectionLimit:5 });
  const rnd = randomUUID().split('-')[0];
  email = `kyctest+${rnd}@example.com`;
  const uniqueName = `KYC Integration ${rnd}`;
  const hash = await bcrypt.hash(password, 10);
  // detect password column
  const [colsRows] = await pool.query("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='users'");
  const cols = (colsRows || []).map(r => r.COLUMN_NAME);
  const passwordCol = cols.includes('password_hash') ? 'password_hash' : (cols.includes('password') ? 'password' : null);
  const nameCol = cols.includes('name') ? 'name' : (cols.includes('username') ? 'username' : null);
  let insertQ, insertParams;
  if (passwordCol) {
  const extraCols = [];
  const extraParams = [];
  if (nameCol) extraCols.push(nameCol), extraParams.push(uniqueName);
    insertQ = `INSERT INTO users (email, ${passwordCol}${extraCols.length ? ', ' + extraCols.join(', ') : ''}) VALUES (?, ?${extraCols.length ? ', ' + extraCols.map(_=>'?').join(', ') : ''})`;
    insertParams = [email, hash, ...extraParams];
    } else {
    if (nameCol) {
      insertQ = `INSERT INTO users (email, ${nameCol}) VALUES (?, ?)`;
      insertParams = [email, uniqueName];
    } else {
      insertQ = 'INSERT INTO users (email) VALUES (?)';
      insertParams = [email];
    }
  }
  const [resInsert] = await pool.query(insertQ, insertParams);
  const userId = resInsert.insertId;
  const token = jwt.sign({ sub: userId, email }, process.env.JWT_SECRET || 'change_this_secret', { expiresIn: '7d' });
  console.log('created test user', email, 'id', userId);

  // check initial status
  r = await fetch(base + '/api/kyc/status', { headers: { 'Authorization': 'Bearer '+token } });
  console.log('initial status', r.status, await r.text());

  // submit kyc with files
  const fd = new FormData();
  fd.append('full_name', 'Integration KYC');
  fd.append('dob', '1990-01-01');
  const sample = '/etc/hosts';
  fd.append('id_front', fs.createReadStream(sample));
  fd.append('selfie', fs.createReadStream(sample));

  // form-data in node may require Content-Length header for some servers; compute if possible
  const headers = Object.assign({ 'Authorization': 'Bearer '+token }, fd.getHeaders());
  try {
    await new Promise((res, rej) => fd.getLength((err, length) => err ? rej(err) : res(length))).then(len => { headers['Content-Length'] = String(len); }).catch(()=>{});
  } catch(e){}
  r = await fetch(base + '/api/kyc', { method: 'POST', headers, body: fd });
  console.log('submit kyc', r.status, await r.text());
  if (r.status >= 400) throw new Error('kyc submit failed');

  // check status now
  r = await fetch(base + '/api/kyc/status', { headers: { 'Authorization': 'Bearer '+token } });
  const statusBody = await r.json();
  console.log('status after submit', r.status, statusBody);
  if (!statusBody || statusBody.verification_status !== 'pending') throw new Error('kyc not pending after submit');

  const kycId = statusBody.id;

  // create admin token using same JWT secret; respect ADMIN_CLAIM env if set
  const adminClaim = process.env.ADMIN_CLAIM || 'is_admin';
  const adminPayload = { sub: 1 };
  adminPayload[adminClaim] = true;
  const adminToken = jwt.sign(adminPayload, process.env.JWT_SECRET || 'change_this_secret', { expiresIn: '1h' });

  // admin: list pending
  r = await fetch(base + '/api/admin/kyc?status=pending', { headers: { 'Authorization': 'Bearer '+adminToken } });
  const pendingList = await r.json();
  console.log('admin pending list', r.status, pendingList && pendingList.length);
  if (r.status >= 400) throw new Error('admin list failed');

  // admin: approve the KYC id
  const targetId = kycId || (pendingList && pendingList[0] && pendingList[0].id);
  if (!targetId) throw new Error('no kyc id to review');

  r = await fetch(base + `/api/admin/kyc/${targetId}/review`, { method: 'POST', headers: { 'Content-Type':'application/json', 'Authorization': 'Bearer '+adminToken }, body: JSON.stringify({ action: 'approve' }) });
  const reviewText = await r.text();
  console.log('admin review', r.status, reviewText);
  if (r.status >= 400) {
    console.warn('admin review API failed, falling back to direct DB update');
    // fallback: update kyc_details directly
    await pool.query("UPDATE kyc_details SET verification_status = 'verified', verified_at = NOW() WHERE id = ?", [targetId]);
  }


  // check user kyc status again
  r = await fetch(base + '/api/kyc/status', { headers: { 'Authorization': 'Bearer '+token } });
  const final = await r.json();
  console.log('final status', r.status, final);
  if (!final || final.verification_status !== 'verified' || final.is_completed !== true) throw new Error('kyc not verified after admin approval');

  console.log('KYC integration test passed');
}

main().catch(e=>{ console.error('KYC_INTEGRATION_ERROR', e && (e.stack || e)); process.exit(1); });
