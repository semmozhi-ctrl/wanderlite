import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Hotel, Star, MapPin, Wifi, Coffee, Dumbbell, UtensilsCrossed } from 'lucide-react';

const Hotels = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [hotels, setHotels] = useState([]);
  const [searchParams, setSearchParams] = useState({
    destination: '',
    check_in: '',
    check_out: '',
    guests: 1,
    min_rating: null,
    max_price: null
  });

  const amenityIcons = {
    'Free WiFi': Wifi,
    'Restaurant': UtensilsCrossed,
    'Gym': Dumbbell,
    'Breakfast': Coffee,
  };

  const searchHotels = async () => {
    if (!searchParams.destination) {
      alert('Please enter a destination');
      return;
    }

    setLoading(true);
    try {
      const response = await api.post('/api/search/hotels', searchParams);
      setHotels(response.data.hotels || []);
    } catch (error) {
      console.error('Error searching hotels:', error);
      alert('Failed to search hotels. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const bookHotel = async (hotel) => {
    // Check if user is logged in
    const token = localStorage.getItem('token');
    if (!token) {
      if (window.confirm('You need to login to book hotels. Go to login page?')) {
        navigate('/login');
      }
      return;
    }

    if (!searchParams.check_in || !searchParams.check_out) {
      alert('Please select check-in and check-out dates');
      return;
    }

    try {
      const nights = Math.ceil(
        (new Date(searchParams.check_out) - new Date(searchParams.check_in)) / (1000 * 60 * 60 * 24)
      );
      const baseFare = hotel.price_per_night * Math.max(1, nights);
      const taxes = parseFloat((baseFare * 0.15).toFixed(2));
      const finalTotal = parseFloat((baseFare + taxes).toFixed(2));

      const serviceJson = JSON.stringify({
        ...hotel,
        check_in: searchParams.check_in,
        check_out: searchParams.check_out,
        guests: searchParams.guests,
        nights: Math.max(1, nights),
        baseFare,
        taxes,
        total_price: finalTotal,
        currency: hotel.currency || 'INR'
      });

      const response = await api.post('/api/bookings/service', {
        service_type: 'Hotel',
        service_json: serviceJson,
        total_price: finalTotal,
        currency: hotel.currency || 'INR'
      });

      navigate('/payment', {
        state: {
          bookingId: response.data.id,
          bookingRef: response.data.booking_ref,
          amount: finalTotal,
          currency: hotel.currency || 'INR',
          serviceType: 'Hotel',
          serviceDetails: { ...hotel, nights: Math.max(1, nights), baseFare, taxes, total_price: finalTotal }
        }
      });
    } catch (error) {
      console.error('Error booking hotel:', error);
      alert('Failed to book hotel. Please try again.');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-pink-50 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2 flex items-center justify-center gap-2">
            <Hotel className="w-8 h-8 text-purple-600" />
            Search Hotels
          </h1>
          <p className="text-gray-600">Find the perfect stay for your trip</p>
        </div>

        {/* Search Form */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Hotel Search</CardTitle>
            <CardDescription>Enter your stay details to find available hotels</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <div className="md:col-span-3">
                <label className="block text-sm font-medium text-gray-700 mb-2">Destination</label>
                <Input
                  placeholder="Enter city or location"
                  value={searchParams.destination}
                  onChange={(e) => setSearchParams({ ...searchParams, destination: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Check-in</label>
                <Input
                  type="date"
                  value={searchParams.check_in}
                  onChange={(e) => setSearchParams({ ...searchParams, check_in: e.target.value })}
                  min={new Date().toISOString().split('T')[0]}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Check-out</label>
                <Input
                  type="date"
                  value={searchParams.check_out}
                  onChange={(e) => setSearchParams({ ...searchParams, check_out: e.target.value })}
                  min={searchParams.check_in || new Date().toISOString().split('T')[0]}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Guests</label>
                <Input
                  type="number"
                  min="1"
                  max="10"
                  value={searchParams.guests}
                  onChange={(e) => setSearchParams({ ...searchParams, guests: parseInt(e.target.value) || 1 })}
                />
              </div>
            </div>

            {/* Filters */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Minimum Rating</label>
                <Select 
                  value={searchParams.min_rating?.toString() || 'any'}
                  onValueChange={(value) => setSearchParams({ 
                    ...searchParams, 
                    min_rating: value === 'any' ? null : parseFloat(value)
                  })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Any rating" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="any">Any rating</SelectItem>
                    <SelectItem value="3">3+ Stars</SelectItem>
                    <SelectItem value="4">4+ Stars</SelectItem>
                    <SelectItem value="4.5">4.5+ Stars</SelectItem>
                    <SelectItem value="5">5 Stars</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Max Price per Night</label>
                <Select 
                  value={searchParams.max_price?.toString() || 'any'}
                  onValueChange={(value) => setSearchParams({ 
                    ...searchParams, 
                    max_price: value === 'any' ? null : parseFloat(value)
                  })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Any price" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="any">Any price</SelectItem>
                    <SelectItem value="2000">Under ₹2,000</SelectItem>
                    <SelectItem value="4000">Under ₹4,000</SelectItem>
                    <SelectItem value="6000">Under ₹6,000</SelectItem>
                    <SelectItem value="10000">Under ₹10,000</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
          <CardFooter>
            <Button onClick={searchHotels} disabled={loading} className="w-full">
              {loading ? 'Searching...' : 'Search Hotels'}
            </Button>
          </CardFooter>
        </Card>

        {/* Hotel Results */}
        {hotels.length > 0 && (
          <div className="space-y-4">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">
              Available Hotels ({hotels.length})
            </h2>
            {hotels.map((hotel) => (
              <Card key={hotel.id} className="hover:shadow-lg transition-shadow overflow-hidden">
                <div className="flex flex-col md:flex-row">
                  {/* Hotel Image */}
                  <div className="md:w-1/3 h-48 md:h-auto">
                    <img
                      src={hotel.image_url}
                      alt={hotel.name}
                      className="w-full h-full object-cover"
                    />
                  </div>

                  {/* Hotel Details */}
                  <div className="flex-1 p-6">
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <h3 className="text-2xl font-bold text-gray-900 mb-1">{hotel.name}</h3>
                        <div className="flex items-center gap-1 text-gray-600 mb-2">
                          <MapPin className="w-4 h-4" />
                          <span className="text-sm">{hotel.location}</span>
                        </div>
                        <div className="flex items-center gap-1">
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
                          <span className="ml-2 text-sm font-medium text-gray-700">
                            {hotel.rating} / 5
                          </span>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-3xl font-bold text-purple-600">
                          ₹{hotel.price_per_night.toLocaleString()}
                        </p>
                        <p className="text-sm text-gray-500">per night</p>
                      </div>
                    </div>

                    {/* Amenities */}
                    <div className="flex flex-wrap gap-2 mb-4">
                      {hotel.amenities.map((amenity, index) => {
                        const Icon = amenityIcons[amenity] || Hotel;
                        return (
                          <Badge key={index} variant="outline" className="flex items-center gap-1">
                            <Icon className="w-3 h-3" />
                            {amenity}
                          </Badge>
                        );
                      })}
                    </div>

                    <div className="flex items-center justify-between">
                      <Badge variant="secondary">
                        {hotel.rooms_available} rooms available
                      </Badge>
                      <Button onClick={() => bookHotel(hotel)}>
                        Book Now
                      </Button>
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* No Results */}
        {!loading && hotels.length === 0 && searchParams.destination && (
          <div className="text-center py-12">
            <Hotel className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">No hotels found. Try different search criteria.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Hotels;
