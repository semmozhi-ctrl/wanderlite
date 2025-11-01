import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import axios from 'axios';
import { 
  MapPin, Calendar, Plus, Trash2,
  Plane, Wallet, Navigation, ListChecks, User,
  Cloud, Droplets, Wind, TrendingUp
} from 'lucide-react';
import { Link } from 'react-router-dom';

const Dashboard = () => {
  const { user } = useAuth();
  const [trips, setTrips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [weather, setWeather] = useState(null);
  const [weatherLoading, setWeatherLoading] = useState(false);
  const [stats, setStats] = useState({
    totalTrips: 0,
    upcomingTrips: 0,
    totalBudget: 0,
    savedDestinations: 0
  });
  const [analytics, setAnalytics] = useState(null);

  useEffect(() => {
    fetchTrips();
    fetchWeather();
    fetchAnalytics();
  }, []);

  const fetchTrips = async () => {
    try {
      const response = await axios.get('/api/trips');
      const userTrips = response.data || [];
      setTrips(userTrips);
      
      const now = new Date();
      const upcoming = userTrips.filter(trip => {
        return new Date(trip.created_at) > new Date(now.setDate(now.getDate() - 7));
      });

      const totalBudget = userTrips.reduce((sum, trip) => {
        const budget = parseFloat(trip.total_cost) || 0;
        return sum + budget;
      }, 0);

      setStats({
        totalTrips: userTrips.length,
        upcomingTrips: upcoming.length,
        totalBudget: totalBudget,
        savedDestinations: userTrips.length
      });
    } catch (error) {
      console.error('Error fetching trips:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchWeather = async (city = 'Mumbai') => {
    setWeatherLoading(true);
    try {
      const apiKey = process.env.REACT_APP_OPENWEATHER_API_KEY || 'demo';
      const response = await axios.get(
        `https://api.openweathermap.org/data/2.5/weather?q=${city}&units=metric&appid=${apiKey}`
      );
      setWeather(response.data);
    } catch (error) {
      console.error('Failed to fetch weather', error);
      setWeather({
        name: city,
        main: { temp: 28, humidity: 65, pressure: 1013 },
        weather: [{ main: 'Clear', description: 'clear sky', icon: '01d' }],
        wind: { speed: 5.2 }
      });
    } finally {
      setWeatherLoading(false);
    }
  };

  const useMyLocation = () => {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(async (pos) => {
      try {
        const { latitude, longitude } = pos.coords;
        const base = process.env.REACT_APP_BACKEND_URL || '';
        const { data } = await axios.get(`${base}/api/geolocate`, { params: { lat: latitude, lon: longitude } });
        const city = data.city || 'Mumbai';
        fetchWeather(city);
      } catch (e) {
        fetchWeather('Mumbai');
      }
    }, () => fetchWeather('Mumbai'));
  };

  const fetchAnalytics = async () => {
    try {
      const { data } = await axios.get('/api/analytics/summary');
      setAnalytics(data);
    } catch (e) {
      // ignore
    }
  };

  const deleteTrip = async (tripId) => {
    if (window.confirm('Are you sure you want to delete this trip?')) {
      try {
        await axios.delete(`/api/trips/${tripId}`);
        setTrips(trips.filter(trip => trip.id !== tripId));
        fetchTrips();
      } catch (error) {
        console.error('Error deleting trip:', error);
      }
    }
  };

  const quickActions = [
    { icon: Navigation, label: 'Explore', path: '/explore', color: 'from-blue-500 to-cyan-500' },
    { icon: Plane, label: 'Planner', path: '/planner', color: 'from-purple-500 to-pink-500' },
    { icon: ListChecks, label: 'Checklist', path: '/checklist', color: 'from-orange-500 to-red-500' },
    { icon: User, label: 'Profile', path: '/profile', color: 'from-green-500 to-teal-500' }
  ];

  if (loading) {
    return (
      <div className="min-h-screen pt-24 pb-16 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#31A8E0] mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading your dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen pt-24 pb-16 bg-gradient-to-b from-[#E1F0FD] to-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Welcome back, {user?.username || user?.name || 'Traveler'} 👋
          </h1>
          <p className="text-gray-600">Ready for your next adventure?</p>
        </div>

  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card className="border-0 shadow-lg bg-gradient-to-br from-blue-50 to-white">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 mb-1">Total Trips</p>
                  <p className="text-3xl font-bold text-[#31A8E0]">{stats.totalTrips}</p>
                </div>
                <div className="p-3 bg-blue-100 rounded-full">
                  <Plane className="w-6 h-6 text-[#31A8E0]" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-0 shadow-lg bg-gradient-to-br from-purple-50 to-white">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 mb-1">Recent Trips</p>
                  <p className="text-3xl font-bold text-purple-600">{stats.upcomingTrips}</p>
                </div>
                <div className="p-3 bg-purple-100 rounded-full">
                  <Calendar className="w-6 h-6 text-purple-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-0 shadow-lg bg-gradient-to-br from-green-50 to-white">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 mb-1">Total Budget</p>
                  <p className="text-3xl font-bold text-green-600">₹{stats.totalBudget.toLocaleString()}</p>
                </div>
                <div className="p-3 bg-green-100 rounded-full">
                  <Wallet className="w-6 h-6 text-green-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-0 shadow-lg bg-gradient-to-br from-orange-50 to-white">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 mb-1">Destinations</p>
                  <p className="text-3xl font-bold text-orange-600">{stats.savedDestinations}</p>
                </div>
                <div className="p-3 bg-orange-100 rounded-full">
                  <MapPin className="w-6 h-6 text-orange-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-0 shadow-lg bg-gradient-to-br from-cyan-50 to-white">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 mb-1">Avg. Days</p>
                  <p className="text-3xl font-bold text-cyan-600">{analytics?.avg_days ? analytics.avg_days.toFixed(1) : 0}</p>
                </div>
                <div className="p-3 bg-cyan-100 rounded-full">
                  <Calendar className="w-6 h-6 text-cyan-600" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
          <Card className="lg:col-span-2 border-0 shadow-xl">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-[#31A8E0]">
                  <TrendingUp className="w-5 h-5" />
                  Your Trips
                </div>
                <Link to="/planner">
                  <Button size="sm" className="bg-[#31A8E0] text-white">
                    <Plus className="w-4 h-4 mr-2" />
                    New Trip
                  </Button>
                </Link>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {trips.length === 0 ? (
                <div className="text-center py-12">
                  <Plane className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                  <p className="text-gray-500 mb-4">No trips yet. Start planning your first adventure!</p>
                  <Link to="/planner">
                    <Button className="bg-[#31A8E0] text-white">
                      Plan a Trip
                    </Button>
                  </Link>
                </div>
              ) : (
                <div className="space-y-4">
                  {trips.slice(0, 3).map((trip) => (
                    <div 
                      key={trip.id} 
                      className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition"
                    >
                      <div className="flex items-center gap-4">
                        <div className="p-3 bg-[#31A8E0]/10 rounded-full">
                          <MapPin className="w-5 h-5 text-[#31A8E0]" />
                        </div>
                        <div>
                          <h3 className="font-semibold text-gray-900">{trip.destination}</h3>
                          <p className="text-sm text-gray-600">{trip.days} days • ₹{trip.total_cost}</p>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={() => deleteTrip(trip.id)}>
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                  {trips.length > 3 && (
                    <Link to="/profile">
                      <Button variant="link" className="w-full text-[#31A8E0]">
                        View All Trips →
                      </Button>
                    </Link>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border-0 shadow-xl">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-[#31A8E0]">
                <Cloud className="w-5 h-5" />
                Weather
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex justify-end mb-2">
                <Button size="sm" variant="outline" onClick={useMyLocation}>Use My Location</Button>
              </div>
              {weatherLoading ? (
                <div className="flex items-center justify-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#31A8E0]"></div>
                </div>
              ) : weather ? (
                <div>
                  <div className="text-center mb-6">
                    <p className="text-gray-600 mb-2">{weather.name}</p>
                    <div className="text-5xl font-bold text-[#31A8E0] mb-2">
                      {Math.round(weather.main.temp)}°C
                    </div>
                    <p className="text-gray-600 capitalize">
                      {weather.weather[0].description}
                    </p>
                  </div>
                  
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center gap-2">
                        <Droplets className="w-4 h-4 text-blue-500" />
                        <span className="text-sm text-gray-600">Humidity</span>
                      </div>
                      <span className="font-semibold">{weather.main.humidity}%</span>
                    </div>
                    
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center gap-2">
                        <Wind className="w-4 h-4 text-gray-500" />
                        <span className="text-sm text-gray-600">Wind Speed</span>
                      </div>
                      <span className="font-semibold">{weather.wind.speed} m/s</span>
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-gray-500 text-center py-8">Weather data unavailable</p>
              )}
            </CardContent>
          </Card>
        </div>

        <Card className="border-0 shadow-xl">
          <CardHeader>
            <CardTitle className="text-[#31A8E0]">Quick Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {quickActions.map((action) => (
                <Link key={action.path} to={action.path}>
                  <div className="group relative overflow-hidden rounded-xl p-6 bg-gradient-to-br hover:scale-105 transform transition duration-300 cursor-pointer shadow-lg hover:shadow-xl">
                    <div className={`absolute inset-0 bg-gradient-to-br ${action.color} opacity-90 group-hover:opacity-100 transition`}></div>
                    <div className="relative z-10 flex flex-col items-center text-white">
                      <action.icon className="w-8 h-8 mb-3" />
                      <span className="font-semibold">{action.label}</span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>

        {analytics && analytics.top_destinations?.length > 0 && (
          <Card className="border-0 shadow-xl mt-8">
            <CardHeader>
              <CardTitle className="text-[#31A8E0]">Top Destinations</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {analytics.top_destinations.map((d) => (
                  <div key={d.destination} className="p-4 bg-gray-50 rounded-lg flex items-center justify-between">
                    <span className="font-semibold">{d.destination}</span>
                    <span className="text-sm text-gray-600">{d.count} trips</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

      </div>
    </div>
  );
};

export default Dashboard;
