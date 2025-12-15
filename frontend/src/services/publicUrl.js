// Utility to get the public base URL for QR codes and sharing
export const getPublicBaseUrl = () => {
  // Check if there's a stored IP from receipt page
  const storedIp = localStorage.getItem('wanderlite_ip');
  if (storedIp) {
    return `http://${storedIp}:3001`;
  }

  // Check environment variable
  if (process.env.REACT_APP_PUBLIC_BASE_URL) {
    return process.env.REACT_APP_PUBLIC_BASE_URL;
  }

  // Default to current origin
  return window.location.origin;
};

// Get IP from local storage or ipify
export const detectAndStoreIP = async () => {
  try {
    const response = await fetch('https://api.ipify.org?format=json');
    const data = await response.json();
    localStorage.setItem('wanderlite_ip', data.ip);
    return data.ip;
  } catch (err) {
    console.log('Could not detect IP');
    return null;
  }
};
