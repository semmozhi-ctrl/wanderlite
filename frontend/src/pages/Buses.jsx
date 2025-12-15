import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Bus, 
  MapPin, 
  Calendar, 
  Search, 
  ArrowRight, 
  RefreshCw,
  ChevronDown,
  X,
  ArrowLeftRight,
  Info
} from 'lucide-react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const Buses = () => {
  const navigate = useNavigate();
  const [cities, setCities] = useState([]);
  const [fromCity, setFromCity] = useState(null);
  const [toCity, setToCity] = useState(null);
  const [journeyDate, setJourneyDate] = useState('');
  const [fromSearch, setFromSearch] = useState('');
  const [toSearch, setToSearch] = useState('');
  const [showFromDropdown, setShowFromDropdown] = useState(false);
  const [showToDropdown, setShowToDropdown] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const fromRef = useRef(null);
  const toRef = useRef(null);

  // Set minimum date to today
  const today = new Date().toISOString().split('T')[0];

  // Fetch cities on mount
  useEffect(() => {
    const fetchCities = async () => {
      try {
        const response = await axios.get(`${API_URL}/api/bus/cities`);
        setCities(response.data);
      } catch (err) {
        console.error('Error fetching cities:', err);
        setError('Failed to load cities. Please try again.');
      }
    };
    fetchCities();
  }, []);

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (fromRef.current && !fromRef.current.contains(event.target)) {
        setShowFromDropdown(false);
      }
      if (toRef.current && !toRef.current.contains(event.target)) {
        setShowToDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Filter cities based on search
  const filteredFromCities = cities.filter(city => 
    city.name.toLowerCase().includes(fromSearch.toLowerCase()) ||
    city.state.toLowerCase().includes(fromSearch.toLowerCase())
  );

  const filteredToCities = cities.filter(city => 
    city.name.toLowerCase().includes(toSearch.toLowerCase()) ||
    city.state.toLowerCase().includes(toSearch.toLowerCase())
  );

  // Swap cities
  const swapCities = () => {
    const temp = fromCity;
    const tempSearch = fromSearch;
    setFromCity(toCity);
    setToCity(temp);
    setFromSearch(toSearch);
    setToSearch(tempSearch);
  };

  // Handle search
  const handleSearch = async () => {
    if (!fromCity || !toCity) {
      setError('Please select both source and destination cities');
      return;
    }
    if (!journeyDate) {
      setError('Please select a journey date');
      return;
    }
    if (fromCity.id === toCity.id) {
      setError('Source and destination cannot be the same');
      return;
    }

    setError('');
    setLoading(true);

    try {
      const response = await axios.post(`${API_URL}/api/bus/search`, {
        from_city_id: fromCity.id,
        to_city_id: toCity.id,
        journey_date: journeyDate
      });

      navigate('/bus-results', {
        state: {
          results: response.data,
          fromCity,
          toCity,
          journeyDate
        }
      });
    } catch (err) {
      console.error('Search error:', err);
      setError('Failed to search buses. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Popular routes for quick selection
  const popularRoutes = [
    { from: 'Chennai', to: 'Bangalore' },
    { from: 'Bangalore', to: 'Hyderabad' },
    { from: 'Mumbai', to: 'Pune' },
    { from: 'Chennai', to: 'Coimbatore' },
    { from: 'Bangalore', to: 'Mysore' },
    { from: 'Chennai', to: 'Hyderabad' },
  ];

  const handlePopularRoute = (route) => {
    const from = cities.find(c => c.name === route.from);
    const to = cities.find(c => c.name === route.to);
    if (from && to) {
      setFromCity(from);
      setToCity(to);
      setFromSearch(from.name);
      setToSearch(to.name);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-orange-50 to-white">
      {/* Hero Section */}
      <div className="relative bg-gradient-to-r from-orange-600 to-red-600 text-white py-20">
        <div className="absolute inset-0 bg-black/20"></div>
        <div className="container mx-auto px-4 relative z-10">
          <div className="text-center mb-10">
            <h1 className="text-4xl md:text-5xl font-bold mb-4">
              Book Bus Tickets Online
            </h1>
            <p className="text-lg text-orange-100">
              Safe, Comfortable & Affordable Travel Across India
            </p>
          </div>

          {/* Search Card */}
          <div className="max-w-5xl mx-auto bg-white rounded-2xl shadow-2xl p-6 md:p-8">
            <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-end">
              
              {/* From City */}
              <div className="md:col-span-4 relative" ref={fromRef}>
                <label className="block text-gray-700 font-medium mb-2">
                  <MapPin className="inline w-4 h-4 mr-1 text-orange-500" />
                  From
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={fromSearch}
                    onChange={(e) => {
                      setFromSearch(e.target.value);
                      setFromCity(null);
                      setShowFromDropdown(true);
                    }}
                    onFocus={() => setShowFromDropdown(true)}
                    placeholder="Enter city name"
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-orange-500 focus:ring-0 outline-none text-gray-800 transition"
                  />
                  {fromCity && (
                    <button
                      onClick={() => {
                        setFromCity(null);
                        setFromSearch('');
                      }}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
                
                {/* From Dropdown */}
                {showFromDropdown && filteredFromCities.length > 0 && (
                  <div className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-xl shadow-lg max-h-60 overflow-y-auto">
                    {filteredFromCities.map(city => (
                      <button
                        key={city.id}
                        onClick={() => {
                          setFromCity(city);
                          setFromSearch(city.name);
                          setShowFromDropdown(false);
                        }}
                        className="w-full px-4 py-3 text-left hover:bg-orange-50 flex items-center gap-2 border-b border-gray-100 last:border-0"
                      >
                        <MapPin className="w-4 h-4 text-orange-500" />
                        <div>
                          <p className="font-medium text-gray-800">{city.name}</p>
                          <p className="text-sm text-gray-500">{city.state}</p>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Swap Button */}
              <div className="hidden md:flex md:col-span-1 justify-center items-center">
                <button
                  onClick={swapCities}
                  className="p-3 rounded-full bg-orange-100 hover:bg-orange-200 text-orange-600 transition transform hover:rotate-180 duration-300"
                >
                  <ArrowLeftRight className="w-5 h-5" />
                </button>
              </div>

              {/* To City */}
              <div className="md:col-span-4 relative" ref={toRef}>
                <label className="block text-gray-700 font-medium mb-2">
                  <MapPin className="inline w-4 h-4 mr-1 text-red-500" />
                  To
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={toSearch}
                    onChange={(e) => {
                      setToSearch(e.target.value);
                      setToCity(null);
                      setShowToDropdown(true);
                    }}
                    onFocus={() => setShowToDropdown(true)}
                    placeholder="Enter city name"
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-red-500 focus:ring-0 outline-none text-gray-800 transition"
                  />
                  {toCity && (
                    <button
                      onClick={() => {
                        setToCity(null);
                        setToSearch('');
                      }}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
                
                {/* To Dropdown */}
                {showToDropdown && filteredToCities.length > 0 && (
                  <div className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-xl shadow-lg max-h-60 overflow-y-auto">
                    {filteredToCities.map(city => (
                      <button
                        key={city.id}
                        onClick={() => {
                          setToCity(city);
                          setToSearch(city.name);
                          setShowToDropdown(false);
                        }}
                        className="w-full px-4 py-3 text-left hover:bg-red-50 flex items-center gap-2 border-b border-gray-100 last:border-0"
                      >
                        <MapPin className="w-4 h-4 text-red-500" />
                        <div>
                          <p className="font-medium text-gray-800">{city.name}</p>
                          <p className="text-sm text-gray-500">{city.state}</p>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Mobile Swap Button */}
              <div className="md:hidden flex justify-center -my-2">
                <button
                  onClick={swapCities}
                  className="p-2 rounded-full bg-orange-100 hover:bg-orange-200 text-orange-600 transition"
                >
                  <ArrowLeftRight className="w-4 h-4" />
                </button>
              </div>

              {/* Journey Date */}
              <div className="md:col-span-3">
                <label className="block text-gray-700 font-medium mb-2">
                  <Calendar className="inline w-4 h-4 mr-1 text-purple-500" />
                  Journey Date
                </label>
                <input
                  type="date"
                  value={journeyDate}
                  min={today}
                  onChange={(e) => setJourneyDate(e.target.value)}
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-purple-500 focus:ring-0 outline-none text-gray-800 transition"
                />
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm flex items-center gap-2">
                <Info className="w-4 h-4" />
                {error}
              </div>
            )}

            {/* Search Button */}
            <button
              onClick={handleSearch}
              disabled={loading}
              className="w-full mt-6 bg-gradient-to-r from-orange-500 to-red-500 text-white py-4 rounded-xl font-semibold text-lg hover:from-orange-600 hover:to-red-600 transition flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-5 h-5 animate-spin" />
                  Searching...
                </>
              ) : (
                <>
                  <Search className="w-5 h-5" />
                  Search Buses
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Popular Routes */}
      <div className="container mx-auto px-4 py-12">
        <h2 className="text-2xl font-bold text-gray-800 mb-6 text-center">
          Popular Routes
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {popularRoutes.map((route, index) => (
            <button
              key={index}
              onClick={() => handlePopularRoute(route)}
              className="bg-white p-4 rounded-xl shadow hover:shadow-lg transition border border-gray-100 hover:border-orange-200 group"
            >
              <div className="flex items-center justify-center gap-2 text-gray-700 group-hover:text-orange-600">
                <span className="font-medium">{route.from}</span>
                <ArrowRight className="w-4 h-4" />
                <span className="font-medium">{route.to}</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Features Section */}
      <div className="bg-gray-50 py-16">
        <div className="container mx-auto px-4">
          <h2 className="text-2xl font-bold text-gray-800 mb-10 text-center">
            Why Book With Us?
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div className="text-center">
              <div className="w-16 h-16 bg-orange-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Bus className="w-8 h-8 text-orange-600" />
              </div>
              <h3 className="font-semibold text-gray-800 mb-2">2000+ Bus Partners</h3>
              <p className="text-gray-600 text-sm">Wide selection of operators</p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="font-semibold text-gray-800 mb-2">Safe & Secure</h3>
              <p className="text-gray-600 text-sm">Verified operators only</p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="font-semibold text-gray-800 mb-2">Best Prices</h3>
              <p className="text-gray-600 text-sm">Lowest fares guaranteed</p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192l-3.536 3.536M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-5 0a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
              </div>
              <h3 className="font-semibold text-gray-800 mb-2">24/7 Support</h3>
              <p className="text-gray-600 text-sm">Round the clock assistance</p>
            </div>
          </div>
        </div>
      </div>

      {/* Bus Types Info */}
      <div className="container mx-auto px-4 py-16">
        <h2 className="text-2xl font-bold text-gray-800 mb-10 text-center">
          Bus Types Available
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white rounded-xl shadow-md overflow-hidden hover:shadow-lg transition">
            <div className="h-3 bg-gradient-to-r from-blue-500 to-blue-600"></div>
            <div className="p-6">
              <h3 className="font-bold text-lg text-gray-800 mb-2">AC Seater</h3>
              <p className="text-gray-600 text-sm mb-4">
                Comfortable push-back seats with air conditioning. Perfect for day journeys.
              </p>
              <div className="flex flex-wrap gap-2">
                <span className="px-2 py-1 bg-blue-50 text-blue-600 text-xs rounded">AC</span>
                <span className="px-2 py-1 bg-blue-50 text-blue-600 text-xs rounded">2+2 Layout</span>
                <span className="px-2 py-1 bg-blue-50 text-blue-600 text-xs rounded">Charging Point</span>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-xl shadow-md overflow-hidden hover:shadow-lg transition">
            <div className="h-3 bg-gradient-to-r from-purple-500 to-purple-600"></div>
            <div className="p-6">
              <h3 className="font-bold text-lg text-gray-800 mb-2">AC Sleeper</h3>
              <p className="text-gray-600 text-sm mb-4">
                Full-length sleeper berths with blankets. Ideal for overnight travel.
              </p>
              <div className="flex flex-wrap gap-2">
                <span className="px-2 py-1 bg-purple-50 text-purple-600 text-xs rounded">AC</span>
                <span className="px-2 py-1 bg-purple-50 text-purple-600 text-xs rounded">2+1 Layout</span>
                <span className="px-2 py-1 bg-purple-50 text-purple-600 text-xs rounded">Blanket</span>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-xl shadow-md overflow-hidden hover:shadow-lg transition">
            <div className="h-3 bg-gradient-to-r from-orange-500 to-orange-600"></div>
            <div className="p-6">
              <h3 className="font-bold text-lg text-gray-800 mb-2">Volvo Multi-Axle</h3>
              <p className="text-gray-600 text-sm mb-4">
                Premium luxury buses with extra legroom and smooth ride quality.
              </p>
              <div className="flex flex-wrap gap-2">
                <span className="px-2 py-1 bg-orange-50 text-orange-600 text-xs rounded">AC</span>
                <span className="px-2 py-1 bg-orange-50 text-orange-600 text-xs rounded">Premium</span>
                <span className="px-2 py-1 bg-orange-50 text-orange-600 text-xs rounded">WiFi</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Buses;
