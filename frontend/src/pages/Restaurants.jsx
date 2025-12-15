import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { UtensilsCrossed, Star, MapPin, Clock, DollarSign } from 'lucide-react';

const Restaurants = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [restaurants, setRestaurants] = useState([]);
  const [searchParams, setSearchParams] = useState({
    destination: '',
    cuisine: null,
    budget: null
  });

  const searchRestaurants = async () => {
    if (!searchParams.destination) {
      alert('Please enter a destination');
      return;
    }

    setLoading(true);
    try {
      const response = await api.post('/api/search/restaurants', searchParams);
      setRestaurants(response.data.restaurants || []);
    } catch (error) {
      console.error('Error searching restaurants:', error);
      alert('Failed to search restaurants. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const bookRestaurant = async (restaurant) => {
    try {
      const response = await api.post('/api/bookings/service', {
        service_type: 'Restaurant',
        destination: restaurant.location || restaurant.city || 'Unknown',
        travelers: 1,
        amount: restaurant.average_cost || 0,
        service_details: {
          restaurant: restaurant
        }
      });

      navigate('/payment', {
        state: {
          bookingId: response.data.id,
          bookingRef: response.data.booking_ref,
          amount: restaurant.average_cost,
          currency: restaurant.currency,
          serviceType: 'Restaurant',
          serviceDetails: restaurant
        }
      });
    } catch (error) {
      console.error('Error booking restaurant:', error);
      alert('Failed to book restaurant. Please try again.');
    }
  };

  const getBudgetBadgeColor = (category) => {
    switch (category) {
      case 'budget':
        return 'bg-green-100 text-green-800';
      case 'mid-range':
        return 'bg-blue-100 text-blue-800';
      case 'fine-dining':
        return 'bg-purple-100 text-purple-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 via-white to-red-50 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2 flex items-center justify-center gap-2">
            <UtensilsCrossed className="w-8 h-8 text-orange-600" />
            Search Restaurants
          </h1>
          <p className="text-gray-600">Discover amazing dining experiences</p>
        </div>

        {/* Search Form */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Restaurant Search</CardTitle>
            <CardDescription>Find the perfect restaurant for your meal</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Destination</label>
                <Input
                  placeholder="Enter city or location"
                  value={searchParams.destination}
                  onChange={(e) => setSearchParams({ ...searchParams, destination: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Cuisine Type</label>
                <Select 
                  value={searchParams.cuisine || 'any'}
                  onValueChange={(value) => setSearchParams({ 
                    ...searchParams, 
                    cuisine: value === 'any' ? null : value
                  })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="All cuisines" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="any">All cuisines</SelectItem>
                    <SelectItem value="Indian">Indian</SelectItem>
                    <SelectItem value="Chinese">Chinese</SelectItem>
                    <SelectItem value="Italian">Italian</SelectItem>
                    <SelectItem value="Continental">Continental</SelectItem>
                    <SelectItem value="Seafood">Seafood</SelectItem>
                    <SelectItem value="Mexican">Mexican</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Budget</label>
                <Select 
                  value={searchParams.budget || 'any'}
                  onValueChange={(value) => setSearchParams({ 
                    ...searchParams, 
                    budget: value === 'any' ? null : value
                  })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Any budget" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="any">Any budget</SelectItem>
                    <SelectItem value="budget">Budget-friendly</SelectItem>
                    <SelectItem value="mid-range">Mid-range</SelectItem>
                    <SelectItem value="fine-dining">Fine Dining</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
          <CardFooter>
            <Button onClick={searchRestaurants} disabled={loading} className="w-full">
              {loading ? 'Searching...' : 'Search Restaurants'}
            </Button>
          </CardFooter>
        </Card>

        {/* Restaurant Results */}
        {restaurants.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {restaurants.map((restaurant) => (
              <Card key={restaurant.id} className="hover:shadow-lg transition-shadow overflow-hidden">
                {/* Restaurant Image */}
                <div className="h-48 w-full">
                  <img
                    src={restaurant.image_url}
                    alt={restaurant.name}
                    className="w-full h-full object-cover"
                  />
                </div>

                <CardContent className="p-6">
                  <div className="mb-4">
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="text-2xl font-bold text-gray-900">{restaurant.name}</h3>
                      <Badge className={getBudgetBadgeColor(restaurant.budget_category)}>
                        {restaurant.budget_category.replace('-', ' ')}
                      </Badge>
                    </div>

                    <div className="flex items-center gap-1 mb-2">
                      {[...Array(5)].map((_, i) => (
                        <Star
                          key={i}
                          className={`w-4 h-4 ${
                            i < Math.floor(restaurant.rating)
                              ? 'fill-yellow-400 text-yellow-400'
                              : 'text-gray-300'
                          }`}
                        />
                      ))}
                      <span className="ml-2 text-sm font-medium text-gray-700">
                        {restaurant.rating}
                      </span>
                    </div>

                    <Badge variant="outline" className="mb-3">{restaurant.cuisine}</Badge>
                  </div>

                  {/* Specialty Dish */}
                  <div className="mb-4">
                    <p className="text-sm font-medium text-gray-700 mb-1">Specialty:</p>
                    <p className="text-gray-600">{restaurant.specialty_dish}</p>
                  </div>

                  {/* Details Grid */}
                  <div className="grid grid-cols-2 gap-3 mb-4 text-sm">
                    <div className="flex items-center gap-2 text-gray-600">
                      <Clock className="w-4 h-4" />
                      <span>{restaurant.timings}</span>
                    </div>
                    <div className="flex items-center gap-2 text-gray-600">
                      <MapPin className="w-4 h-4" />
                      <span>{restaurant.distance}</span>
                    </div>
                    <div className="flex items-center gap-2 text-gray-600 col-span-2">
                      <DollarSign className="w-4 h-4" />
                      <span className="font-semibold text-orange-600">
                        ₹{restaurant.average_cost.toLocaleString()}
                      </span>
                      <span className="text-gray-500">avg. cost for two</span>
                    </div>
                  </div>
                </CardContent>

                <CardFooter className="bg-gray-50 p-4">
                  <Button onClick={() => bookRestaurant(restaurant)} className="w-full">
                    Reserve Table
                  </Button>
                </CardFooter>
              </Card>
            ))}
          </div>
        )}

        {/* No Results */}
        {!loading && restaurants.length === 0 && searchParams.destination && (
          <div className="text-center py-12">
            <UtensilsCrossed className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">No restaurants found. Try different search criteria.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Restaurants;
