import React, { useState, useEffect } from 'react';
import './CookieBanner.css';

const CookieBanner = () => {
  const [showBanner, setShowBanner] = useState(false);

  useEffect(() => {
    const accepted = localStorage.getItem('cookiesAccepted');
    if (!accepted) {
      setShowBanner(true);
    }
  }, []);

  const handleAcceptCookies = () => {
    localStorage.setItem('cookiesAccepted', 'true');
    setShowBanner(false);
  };

  const handleDeclineCookies = () => {
    localStorage.setItem('cookiesAccepted', 'false');
    setShowBanner(false);
  };

  if (!showBanner) return null;

  return (
    <div className="cookie-banner">
      <div className="cookie-content">
        <div className="cookie-text">
          <h3>Cookie Consent</h3>
          <p>
            We use cookies to enhance your browsing experience, serve personalized content,
            and analyze our traffic. By clicking "Accept All Cookies", you consent to our use
            of cookies. You can manage your cookie preferences in your browser settings.
          </p>
        </div>
        <div className="cookie-buttons">
          <button onClick={handleDeclineCookies} className="decline-btn">
            Decline
          </button>
          <button onClick={handleAcceptCookies} className="accept-btn">
            Accept All Cookies
          </button>
        </div>
      </div>
    </div>
  );
};

export default CookieBanner;
