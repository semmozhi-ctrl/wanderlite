import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Calendar } from '../components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '../components/ui/popover';
import { CalendarIcon, Plane, Clock, Users, ArrowRight } from 'lucide-react';
import { format } from 'date-fns';

const Flights = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [flights, setFlights] = useState([]);
  const [searchParams, setSearchParams] = useState({
    origin: '',
    destination: '',
    date: new Date(),
    travelers: 1
  });

  const searchFlights = async () => {
    if (!searchParams.origin || !searchParams.destination) {
      alert('Please enter origin and destination');
      return;
    }

    setLoading(true);
    try {
        const response = await api.post('/api/search/flights', {
        origin: searchParams.origin,
        destination: searchParams.destination,
        date: format(searchParams.date, 'yyyy-MM-dd'),
        travelers: searchParams.travelers
      });
      setFlights(response.data.flights || []);
    } catch (error) {
      console.error('Error searching flights:', error);
      alert('Failed to search flights. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const bookFlight = async (flight) => {
    try {
        const response = await api.post('/api/bookings/service', {
        service_type: 'Flight',
        destination: flight.to || 'Unknown',
        travelers: searchParams.travelers || 1,
        amount: flight.price * searchParams.travelers,
        service_details: {
          flight: flight,
          travelDate: searchParams.date,
          travelers: searchParams.travelers
        }
      });

      // Navigate to payment with booking details
      navigate('/payment', {
        state: {
          bookingId: response.data.id,
          bookingRef: response.data.booking_ref,
          amount: flight.price * searchParams.travelers,
          currency: flight.currency,
          serviceType: 'Flight',
          serviceDetails: flight
        }
      });
    } catch (error) {
      console.error('Error booking flight:', error);
      alert('Failed to book flight. Please try again.');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2 flex items-center justify-center gap-2">
            <Plane className="w-8 h-8 text-blue-600" />
            Search Flights
          </h1>
          <p className="text-gray-600">Find the best flights for your journey</p>
        </div>

        {/* Search Form */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Flight Search</CardTitle>
            <CardDescription>Enter your travel details to find available flights</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">From</label>
                <Input
                  placeholder="Origin City"
                  value={searchParams.origin}
                  onChange={(e) => setSearchParams({ ...searchParams, origin: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">To</label>
                <Input
                  placeholder="Destination City"
                  value={searchParams.destination}
                  onChange={(e) => setSearchParams({ ...searchParams, destination: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Date</label>
                <Popover>
                  <PopoverTrigger asChild>
                    <Button variant="outline" className="w-full justify-start text-left font-normal">
                      <CalendarIcon className="mr-2 h-4 w-4" />
                      {format(searchParams.date, 'PPP')}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-0">
                    <Calendar
                      mode="single"
                      selected={searchParams.date}
                      onSelect={(date) => date && setSearchParams({ ...searchParams, date })}
                      initialFocus
                    />
                  </PopoverContent>
                </Popover>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Travelers</label>
                <Input
                  type="number"
                  min="1"
                  max="9"
                  value={searchParams.travelers}
                  onChange={(e) => setSearchParams({ ...searchParams, travelers: parseInt(e.target.value) || 1 })}
                />
              </div>
            </div>
          </CardContent>
          <CardFooter>
            <Button onClick={searchFlights} disabled={loading} className="w-full">
              {loading ? 'Searching...' : 'Search Flights'}
            </Button>
          </CardFooter>
        </Card>

        {/* Flight Results */}
        {flights.length > 0 && (
          <div className="space-y-4">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">
              Available Flights ({flights.length})
            </h2>
            {flights.map((flight) => (
              <Card key={flight.id} className="hover:shadow-lg transition-shadow">
                <CardContent className="p-6">
                  <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                    {/* Flight Info */}
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-3">
                        <div className="bg-blue-100 p-3 rounded-lg">
                          <Plane className="w-6 h-6 text-blue-600" />
                        </div>
                        <div>
                          <h3 className="text-xl font-bold text-gray-900">{flight.airline}</h3>
                          <p className="text-sm text-gray-500">{flight.flight_number}</p>
                        </div>
                      </div>

                      {/* Route and Timing */}
                      <div className="flex items-center gap-4 mb-3">
                        <div className="text-center">
                          <p className="text-2xl font-bold text-gray-900">
                            {new Date(flight.departure_time).toLocaleTimeString('en-US', { 
                              hour: '2-digit', 
                              minute: '2-digit' 
                            })}
                          </p>
                          <p className="text-sm text-gray-600">{flight.origin}</p>
                        </div>
                        <div className="flex-1 flex flex-col items-center">
                          <div className="flex items-center gap-2 text-gray-500">
                            <div className="h-px bg-gray-300 flex-1"></div>
                            <Clock className="w-4 h-4" />
                            <span className="text-sm">{flight.duration}</span>
                            <div className="h-px bg-gray-300 flex-1"></div>
                          </div>
                          <ArrowRight className="w-5 h-5 text-gray-400 mt-1" />
                        </div>
                        <div className="text-center">
                          <p className="text-2xl font-bold text-gray-900">
                            {new Date(flight.arrival_time).toLocaleTimeString('en-US', { 
                              hour: '2-digit', 
                              minute: '2-digit' 
                            })}
                          </p>
                          <p className="text-sm text-gray-600">{flight.destination}</p>
                        </div>
                      </div>

                      {/* Additional Info */}
                      <div className="flex flex-wrap gap-2">
                        <Badge variant="outline">{flight.baggage}</Badge>
                        <Badge variant={flight.refund_policy.includes('Free') ? 'default' : 'secondary'}>
                          {flight.refund_policy}
                        </Badge>
                        <Badge variant="outline">
                          <Users className="w-3 h-3 mr-1" />
                          {flight.seats_available} seats left
                        </Badge>
                      </div>
                    </div>

                    {/* Price and Book Button */}
                    <div className="flex flex-col items-center gap-3 md:border-l md:pl-6">
                      <div className="text-center">
                        <p className="text-3xl font-bold text-blue-600">
                          ₹{(flight.price * searchParams.travelers).toLocaleString()}
                        </p>
                        <p className="text-sm text-gray-500">
                          ₹{flight.price.toLocaleString()} per person
                        </p>
                      </div>
                      <Button 
                        onClick={() => bookFlight(flight)}
                        className="w-full md:w-auto"
                      >
                        Book Now
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* No Results */}
        {!loading && flights.length === 0 && searchParams.origin && searchParams.destination && (
          <div className="text-center py-12">
            <Plane className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">No flights found. Try different search criteria.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Flights;
