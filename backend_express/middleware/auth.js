const jwt = require('jsonwebtoken');
const secret = process.env.JWT_SECRET || 'change_this_secret';

function requireAuth(req, res, next) {
  const auth = req.headers['authorization'];
  if (!auth) return res.status(403).json({ detail: 'Missing Authorization header' });
  const parts = auth.split(' ');
  const token = parts.length === 2 ? parts[1] : parts[0];
  try {
    const payload = jwt.verify(token, secret);
    req.user = payload;
    next();
  } catch (err) {
    // If an Authorization header was present but token verification failed,
    // return 403 to match the Python service behavior (forbidden vs unauthenticated).
    return res.status(403).json({ detail: 'Could not validate credentials' });
  }
}

function optionalAuth(req, res, next) {
  const auth = req.headers['authorization'];
  if (!auth) return next();
  try {
    const token = auth.split(' ')[1] || auth;
    req.user = jwt.verify(token, secret);
  } catch (e) {
    // ignore
  }
  return next();
}

module.exports = { requireAuth, optionalAuth };
