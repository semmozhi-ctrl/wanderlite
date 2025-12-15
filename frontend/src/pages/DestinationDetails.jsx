import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import destinationService from '../services/destinationService';
import { mockFlights, mockHotels, mockRestaurants } from '../data/services';
import { slugify } from '../lib/utils';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Badge } from '../components/ui/badge';
import { 
  MapPin, Cloud, Droplets, Star, Plane, Hotel, UtensilsCrossed, 
  Activity, ChevronRight, Home, Calendar, Users, IndianRupee, AlertCircle 
} from 'lucide-react';
import { useToast } from '../components/Toast';
import MapView from '../components/MapView';

const DestinationDetails = () => {
  const { destinationName } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [destination, setDestination] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [services, setServices] = useState({
    flights: [],
    hotels: [],
    restaurants: [],
    activities: []
  });

  useEffect(() => {
    fetchDestinationDetails();
  }, [destinationName]);

  const fetchDestinationDetails = async () => {
    setLoading(true);
    setError(null);
    
    // Try to find destination by name/slug
    const result = await destinationService.getDestinationByName(destinationName);
    
    if (result.success && result.destination) {
      setDestination(result.destination);
      // Pre-fetch service counts for this destination
      fetchServiceCounts(result.destination.name);
      
      // Show info if using cached data
      if (result.fromCache || result.fromSession) {
        console.info('Using cached destination data');
      } else if (result.fromMock) {
        toast?.info?.('Viewing offline destination data');
      }
    } else {
      setError(result.error || 'Destination not found');
      setDestination(null);
      
      if (result.status !== 404) {
        toast?.error?.(result.error || 'Failed to load destination');
      }
    }
    
    setLoading(false);
  };

  const fetchServiceCounts = async (destName) => {
    try {
      // Use mock data instead of API calls for reliability
      setServices({
        flights: mockFlights.map(flight => ({ ...flight, destination: destName })),
        hotels: mockHotels.map(hotel => ({ ...hotel, destination: destName, location: `${hotel.location}, ${destName}` })),
        restaurants: mockRestaurants.map(restaurant => ({ ...restaurant, destination: destName })),
        activities: destination?.activities || []
      });
    } catch (error) {
      console.error('Error setting services:', error);
      // Fallback to empty arrays
      setServices({
        flights: [],
        hotels: [],
        restaurants: [],
        activities: []
      });
    }
  };

  const handleServiceClick = (serviceType) => {
    navigate(`/destination/${destinationName}/${serviceType}`, {
      state: { destination: destination }
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center pt-24">
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="text-gray-600">Loading destination details...</p>
        </div>
      </div>
    );
  }

  if (!destination || error) {
    return (
      <div className="min-h-screen flex items-center justify-center pt-24">
        <div className="text-center space-y-4">
          <AlertCircle className="w-16 h-16 text-gray-400 mx-auto" />
          <h2 className="text-2xl font-bold text-gray-900">{error || 'Destination not found'}</h2>
          <p className="text-gray-600">
            The destination you&apos;re looking for doesn&apos;t exist or couldn&apos;t be loaded.
          </p>
          <div className="flex gap-3 justify-center">
            <Button onClick={() => navigate('/explore')} variant="default">
              Back to Explore
            </Button>
            <Button onClick={() => fetchDestinationDetails()} variant="outline">
              Retry
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 pt-16">
      {/* Breadcrumbs */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <Link to="/" className="hover:text-blue-600 flex items-center gap-1">
              <Home className="w-4 h-4" />
              Home
            </Link>
            <ChevronRight className="w-4 h-4" />
            <Link to="/explore" className="hover:text-blue-600">Explore</Link>
            <ChevronRight className="w-4 h-4" />
            <span className="text-gray-900 font-medium">{destination.name}</span>
          </div>
        </div>
      </div>

      {/* Hero Section */}
      <div className="relative h-96 overflow-hidden">
        <img
          src={destination.image}
          alt={destination.name}
          className="w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 to-transparent"></div>
        <div className="absolute bottom-0 left-0 right-0 p-8">
          <div className="max-w-7xl mx-auto">
            <Badge className="mb-3 bg-white/20 backdrop-blur-sm text-white">
              {destination.category}
            </Badge>
            <h1 className="text-5xl font-bold text-white mb-2">{destination.name}</h1>
            <p className="text-xl text-white/90 mb-4">{destination.shortDescription}</p>
            <div className="flex items-center gap-6 text-white/90">
              <div className="flex items-center gap-2">
                <MapPin className="w-5 h-5" />
                <span>{destination.category} Destination</span>
              </div>
              {destination.weather && (
                <>
                  <div className="flex items-center gap-2">
                    <Cloud className="w-5 h-5" />
                    <span>{destination.weather.temp}°C, {destination.weather.condition}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Droplets className="w-5 h-5" />
                    <span>{destination.weather.humidity}% Humidity</span>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Services Summary Bar */}
      <div className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-8">
              <button
                onClick={() => setActiveTab('flights')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                  activeTab === 'flights' ? 'bg-blue-100 text-blue-600' : 'hover:bg-gray-100'
                }`}
              >
                <Plane className="w-5 h-5" />
                <span className="font-medium">Flights</span>
                <Badge variant="secondary">{services.flights.length}</Badge>
              </button>
              <button
                onClick={() => setActiveTab('hotels')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                  activeTab === 'hotels' ? 'bg-purple-100 text-purple-600' : 'hover:bg-gray-100'
                }`}
              >
                <Hotel className="w-5 h-5" />
                <span className="font-medium">Hotels</span>
                <Badge variant="secondary">{services.hotels.length}</Badge>
              </button>
              <button
                onClick={() => setActiveTab('restaurants')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                  activeTab === 'restaurants' ? 'bg-orange-100 text-orange-600' : 'hover:bg-gray-100'
                }`}
              >
                <UtensilsCrossed className="w-5 h-5" />
                <span className="font-medium">Restaurants</span>
                <Badge variant="secondary">{services.restaurants.length}</Badge>
              </button>
              <button
                onClick={() => setActiveTab('overview')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                  activeTab === 'overview' ? 'bg-green-100 text-green-600' : 'hover:bg-gray-100'
                }`}
              >
                <Activity className="w-5 h-5" />
                <span className="font-medium">Overview</span>
              </button>
            </div>
            <Button onClick={() => navigate('/planner', { state: { destination: destination.name } })}>
              Plan Your Trip
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 py-8">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          {/* Overview Tab */}
          <TabsContent value="overview">
            <div className="space-y-6">
              {/* Description */}
              <Card>
                <CardHeader>
                  <CardTitle>About {destination.name}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-700 leading-relaxed mb-4">{destination.description}</p>
                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <Calendar className="w-4 h-4" />
                    <span className="font-medium">Best Time to Visit:</span>
                    <span>{destination.best_time}</span>
                  </div>
                </CardContent>
              </Card>

              {/* Attractions */}
              {destination.attractions && destination.attractions.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Top Attractions</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {destination.attractions.map((attraction, index) => (
                        <div key={index} className="flex items-start gap-3 p-4 border rounded-lg hover:shadow-md transition-shadow">
                          <Star className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-1" />
                          <div>
                            <h4 className="font-semibold text-gray-900">{attraction.name}</h4>
                            <p className="text-sm text-gray-600">{attraction.description}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Activities */}
              {destination.activities && destination.activities.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Things to Do</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {destination.activities.map((activity, index) => (
                        <Badge key={index} variant="outline" className="text-sm py-2 px-4">
                          {activity}
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </TabsContent>

          {/* Flights Tab */}
          <TabsContent value="flights">
            <Card>
              <CardHeader>
                <CardTitle>Available Flights to {destination.name}</CardTitle>
                <CardDescription>Choose from the best flight options</CardDescription>
              </CardHeader>
              <CardContent>
                {services.flights.length > 0 ? (
                  <div className="space-y-4">
                    {services.flights.slice(0, 3).map((flight) => (
                      <div
                        key={flight.id}
                        className="border rounded-lg p-4 hover:shadow-lg transition-shadow cursor-pointer"
                        onClick={() => navigate(`/destination/${destinationName}/flights/${flight.id}`, {
                          state: { flight, destination }
                        })}
                      >
                        <div className="flex justify-between items-center">
                          <div>
                            <h3 className="text-lg font-bold">{flight.airline}</h3>
                            <p className="text-sm text-gray-600">{flight.flight_number}</p>
                            <div className="flex items-center gap-4 mt-2">
                              <span className="font-medium">
                                {new Date(flight.departure_time).toLocaleTimeString('en-US', { 
                                  hour: '2-digit', minute: '2-digit' 
                                })}
                              </span>
                              <span className="text-gray-500">→</span>
                              <span className="font-medium">
                                {new Date(flight.arrival_time).toLocaleTimeString('en-US', { 
                                  hour: '2-digit', minute: '2-digit' 
                                })}
                              </span>
                              <Badge variant="outline">{flight.duration}</Badge>
                            </div>
                          </div>
                          <div className="text-right">
                            <p className="text-2xl font-bold text-blue-600">₹{flight.price.toLocaleString()}</p>
                            <Button size="sm" className="mt-2">View Details</Button>
                          </div>
                        </div>
                      </div>
                    ))}
                    <Button 
                      variant="outline" 
                      className="w-full"
                      onClick={() => handleServiceClick('flights')}
                    >
                      View All Flights ({services.flights.length})
                    </Button>
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    <Plane className="w-12 h-12 mx-auto mb-2 opacity-50" />
                    <p>Loading flights...</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Hotels Tab */}
          <TabsContent value="hotels">
            <Card>
              <CardHeader>
                <CardTitle>Hotels in {destination.name}</CardTitle>
                <CardDescription>Find your perfect stay</CardDescription>
              </CardHeader>
              <CardContent>
                {services.hotels.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {services.hotels.slice(0, 4).map((hotel) => (
                      <div
                        key={hotel.id}
                        className="border rounded-lg overflow-hidden hover:shadow-lg transition-shadow cursor-pointer"
                        onClick={() => navigate(`/destination/${destinationName}/hotels/${hotel.id}`, {
                          state: { hotel, destination }
                        })}
                      >
                        <img src={hotel.image_url} alt={hotel.name} className="w-full h-40 object-cover" />
                        <div className="p-4">
                          <h3 className="font-bold text-lg mb-1">{hotel.name}</h3>
                          <div className="flex items-center gap-1 mb-2">
                            {[...Array(5)].map((_, i) => (
                              <Star
                                key={i}
                                className={`w-4 h-4 ${
                                  i < Math.floor(hotel.rating)
                                    ? 'fill-yellow-400 text-yellow-400'
                                    : 'text-gray-300'
                                }`}
                              />
                            ))}
                            <span className="text-sm ml-1">{hotel.rating}</span>
                          </div>
                          <p className="text-sm text-gray-600 mb-2">{hotel.location}</p>
                          <div className="flex justify-between items-center">
                            <span className="text-xl font-bold text-purple-600">
                              ₹{hotel.price_per_night.toLocaleString()}
                            </span>
                            <Button 
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                navigate(`/destination/${destinationName}/hotels/${hotel.id}`, {
                                  state: { hotel, destination }
                                });
                              }}
                            >
                              View Details
                            </Button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    <Hotel className="w-12 h-12 mx-auto mb-2 opacity-50" />
                    <p>Loading hotels...</p>
                  </div>
                )}
                {services.hotels.length > 4 && (
                  <Button 
                    variant="outline" 
                    className="w-full mt-4"
                    onClick={() => handleServiceClick('hotels')}
                  >
                    View All Hotels ({services.hotels.length})
                  </Button>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Restaurants Tab */}
          <TabsContent value="restaurants">
            <Card>
              <CardHeader>
                <CardTitle>Restaurants in {destination.name}</CardTitle>
                <CardDescription>Discover amazing dining experiences</CardDescription>
              </CardHeader>
              <CardContent>
                {services.restaurants.length > 0 ? (
                  <div className="space-y-4">
                    {services.restaurants.slice(0, 4).map((restaurant) => (
                      <div
                        key={restaurant.id}
                        className="border rounded-lg p-4 hover:shadow-lg transition-shadow cursor-pointer"
                        onClick={() => navigate(`/destination/${destinationName}/restaurants/${restaurant.id}`, {
                          state: { restaurant, destination }
                        })}
                      >
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <h3 className="text-lg font-bold">{restaurant.name}</h3>
                            <Badge variant="outline" className="mb-2">{restaurant.cuisine}</Badge>
                            <p className="text-sm text-gray-600 mb-2">
                              Specialty: {restaurant.specialty_dish}
                            </p>
                            <div className="flex items-center gap-4 text-sm text-gray-500">
                              <span>{restaurant.timings}</span>
                              <span>•</span>
                              <span>{restaurant.distance}</span>
                            </div>
                          </div>
                          <div className="text-right">
                            <p className="text-xl font-bold text-orange-600">
                              ₹{restaurant.average_cost.toLocaleString()}
                            </p>
                            <p className="text-xs text-gray-500 mb-2">for two</p>
                            <Button 
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                navigate(`/destination/${destinationName}/restaurants/${restaurant.id}`, {
                                  state: { restaurant, destination }
                                });
                              }}
                            >
                              Reserve
                            </Button>
                          </div>
                        </div>
                      </div>
                    ))}
                    {services.restaurants.length > 4 && (
                      <Button 
                        variant="outline" 
                        className="w-full"
                        onClick={() => handleServiceClick('restaurants')}
                      >
                        View All Restaurants ({services.restaurants.length})
                      </Button>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    <UtensilsCrossed className="w-12 h-12 mx-auto mb-2 opacity-50" />
                    <p>Loading restaurants...</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default DestinationDetails;
