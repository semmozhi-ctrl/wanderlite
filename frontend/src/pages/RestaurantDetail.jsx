import React, { useState } from 'react';
import { useParams, useLocation, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
import { Calendar } from '../components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '../components/ui/popover';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import {
  UtensilsCrossed, Star, MapPin, Clock, Phone, Mail,
  CalendarIcon, Users, ChevronRight, Home, CheckCircle
} from 'lucide-react';
import { format } from 'date-fns';
import api from '../services/api';

const RestaurantDetail = () => {
  const { destinationName, restaurantId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const { restaurant, destination } = location.state || {};

  const [bookingDetails, setBookingDetails] = useState({
    date: new Date(),
    timeSlot: '',
    guests: 2,
    fullName: '',
    email: '',
    phone: '',
    specialRequest: ''
  });
  const [loading, setLoading] = useState(false);

  const timeSlots = [
    '11:00 AM', '11:30 AM', '12:00 PM', '12:30 PM',
    '1:00 PM', '1:30 PM', '2:00 PM', '2:30 PM',
    '6:00 PM', '6:30 PM', '7:00 PM', '7:30 PM',
    '8:00 PM', '8:30 PM', '9:00 PM', '9:30 PM', '10:00 PM'
  ];

  const handleReserve = async () => {
    if (!restaurant) {
      alert('Restaurant information is missing. Please go back and select the restaurant again.');
      navigate(`/destination/${destinationName}`);
      return;
    }

    if (!isAuthenticated) {
      alert('Please login to make a reservation');
      navigate('/login', { state: { returnTo: location.pathname, restaurant, destination } });
      return;
    }

    if (!bookingDetails.fullName || !bookingDetails.email || !bookingDetails.phone || !bookingDetails.timeSlot) {
      alert('Please fill in all required fields');
      return;
    }

    setLoading(true);
    try {
      const totalPrice = restaurant.average_cost || 1000; // Default cost for reservation

      const serviceJson = JSON.stringify({
        ...restaurant,
        reservationDate: format(bookingDetails.date, 'yyyy-MM-dd'),
        timeSlot: bookingDetails.timeSlot,
        guests: bookingDetails.guests,
        guestName: bookingDetails.fullName,
        guestEmail: bookingDetails.email,
        guestPhone: bookingDetails.phone,
        specialRequest: bookingDetails.specialRequest,
        destination: destination?.name
      });

      const response = await api.post('/api/bookings/service', {
        service_type: 'Restaurant',
        destination: destination?.name || restaurant.location || 'Unknown',
        travelers: bookingDetails.guests || 1,
        amount: totalPrice,
        service_details: {
          restaurant: restaurant,
          date: bookingDetails.date,
          time: bookingDetails.time,
          guests: bookingDetails.guests,
          specialRequest: bookingDetails.specialRequest,
          currency: restaurant.currency || 'INR'
        }
      });

      navigate('/payment', {
        state: {
          bookingId: response.data.id,
          bookingRef: response.data.booking_ref,
          amount: totalPrice,
          currency: restaurant.currency || 'INR',
          serviceType: 'Restaurant',
          serviceDetails: {
            ...restaurant,
            reservationDate: format(bookingDetails.date, 'MMM dd, yyyy'),
            timeSlot: bookingDetails.timeSlot,
            guests: bookingDetails.guests,
            guestName: bookingDetails.fullName,
            destination: destination?.name
          }
        }
      });
    } catch (error) {
      console.error('Error creating reservation:', error);
      console.error('Error details:', error.response);
      const errorMsg = error.response?.data?.detail || 'Failed to create reservation. Please try again.';
      alert(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  if (!restaurant) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-2">Restaurant not found</h2>
          <Button onClick={() => navigate(`/destination/${destinationName}`)}>
            Back to Destination
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 via-white to-yellow-50 pt-24 pb-8 px-4">
      <div className="max-w-6xl mx-auto">
        {/* Breadcrumbs */}
        <div className="mb-6">
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <Link to="/" className="hover:text-blue-600 flex items-center gap-1">
              <Home className="w-4 h-4" />
              Home
            </Link>
            <ChevronRight className="w-4 h-4" />
            <Link to="/explore" className="hover:text-blue-600">Explore</Link>
            <ChevronRight className="w-4 h-4" />
            <Link to={`/destination/${destinationName}`} className="hover:text-blue-600">
              {destination?.name || destinationName}
            </Link>
            <ChevronRight className="w-4 h-4" />
            <span className="text-gray-900 font-medium">Restaurants</span>
            <ChevronRight className="w-4 h-4" />
            <span className="text-gray-900 font-medium">{restaurant.name}</span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Restaurant Details */}
          <div className="lg:col-span-2 space-y-6">
            {/* Hero Image */}
            <Card>
              <img 
                src={restaurant.image_url || 'https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=800'}
                alt={restaurant.name}
                className="w-full h-80 object-cover rounded-t-lg"
              />
              <CardContent className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h1 className="text-3xl font-bold mb-2">{restaurant.name}</h1>
                    <div className="flex items-center gap-4 mb-3">
                      <Badge variant="secondary" className="text-sm">
                        {restaurant.cuisine}
                      </Badge>
                      <div className="flex items-center gap-1">
                        <Star className="w-5 h-5 fill-yellow-400 text-yellow-400" />
                        <span className="font-semibold">{restaurant.rating || 4.5}</span>
                      </div>
                    </div>
                    <div className="space-y-2 text-gray-600">
                      <div className="flex items-center gap-2">
                        <MapPin className="w-4 h-4" />
                        <span>{restaurant.location || destination?.name}</span>
                        {restaurant.distance && <span className="text-sm">({restaurant.distance})</span>}
                      </div>
                      <div className="flex items-center gap-2">
                        <Clock className="w-4 h-4" />
                        <span>{restaurant.timings || '11:00 AM - 10:00 PM'}</span>
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-3xl font-bold text-orange-600">
                      ₹{restaurant.average_cost?.toLocaleString() || '1,200'}
                    </p>
                    <p className="text-sm text-gray-500">for two people</p>
                  </div>
                </div>

                <p className="text-gray-700 mb-6">
                  {restaurant.description || `Experience authentic ${restaurant.cuisine} cuisine at ${restaurant.name}. Known for our signature dishes and warm hospitality.`}
                </p>

                {/* Specialty Dish */}
                {restaurant.specialty_dish && (
                  <div className="bg-orange-50 p-4 rounded-lg">
                    <h3 className="font-semibold text-lg mb-2">Specialty Dish</h3>
                    <p className="text-orange-800 font-medium">{restaurant.specialty_dish}</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Menu Highlights */}
            <Card>
              <CardHeader>
                <CardTitle>Menu Highlights</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {[
                    { name: 'Appetizers', items: ['Crispy Spring Rolls', 'Soup of the Day', 'Bruschetta'] },
                    { name: 'Main Course', items: ['Grilled Fish', 'Butter Chicken', 'Pasta Alfredo'] },
                    { name: 'Desserts', items: ['Chocolate Lava Cake', 'Ice Cream', 'Fresh Fruit Platter'] },
                    { name: 'Beverages', items: ['Fresh Juices', 'Mocktails', 'Hot Beverages'] }
                  ].map((category, idx) => (
                    <div key={idx} className="border rounded-lg p-4">
                      <h4 className="font-semibold mb-2">{category.name}</h4>
                      <ul className="text-sm text-gray-600 space-y-1">
                        {category.items.map((item, i) => (
                          <li key={i}>• {item}</li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Reservation Form */}
          <div className="lg:col-span-1">
            <Card className="sticky top-24">
              <CardHeader>
                <CardTitle>Reserve a Table</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Date */}
                <div>
                  <Label>Reservation Date *</Label>
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button variant="outline" className="w-full justify-start text-left">
                        <CalendarIcon className="mr-2 h-4 w-4" />
                        {format(bookingDetails.date, 'PPP')}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0">
                      <Calendar
                        mode="single"
                        selected={bookingDetails.date}
                        onSelect={(date) => date && setBookingDetails({ ...bookingDetails, date })}
                        disabled={(date) => date < new Date()}
                      />
                    </PopoverContent>
                  </Popover>
                </div>

                {/* Time Slot */}
                <div>
                  <Label>Time Slot *</Label>
                  <Select 
                    value={bookingDetails.timeSlot}
                    onValueChange={(value) => setBookingDetails({ ...bookingDetails, timeSlot: value })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select time" />
                    </SelectTrigger>
                    <SelectContent>
                      {timeSlots.map((slot) => (
                        <SelectItem key={slot} value={slot}>{slot}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Number of Guests */}
                <div>
                  <Label>Number of Guests *</Label>
                  <Input
                    type="number"
                    min="1"
                    max="20"
                    value={bookingDetails.guests}
                    onChange={(e) => setBookingDetails({ ...bookingDetails, guests: parseInt(e.target.value) })}
                  />
                </div>

                {/* Full Name */}
                <div>
                  <Label>Full Name *</Label>
                  <Input
                    type="text"
                    placeholder="Enter your full name"
                    value={bookingDetails.fullName}
                    onChange={(e) => setBookingDetails({ ...bookingDetails, fullName: e.target.value })}
                  />
                </div>

                {/* Email */}
                <div>
                  <Label>Email *</Label>
                  <Input
                    type="email"
                    placeholder="your@email.com"
                    value={bookingDetails.email}
                    onChange={(e) => setBookingDetails({ ...bookingDetails, email: e.target.value })}
                  />
                </div>

                {/* Phone */}
                <div>
                  <Label>Phone Number *</Label>
                  <Input
                    type="tel"
                    placeholder="+91 XXXXX XXXXX"
                    value={bookingDetails.phone}
                    onChange={(e) => setBookingDetails({ ...bookingDetails, phone: e.target.value })}
                  />
                </div>

                {/* Special Request */}
                <div>
                  <Label>Special Requests (Optional)</Label>
                  <Textarea
                    placeholder="Any dietary restrictions or special occasions?"
                    rows={3}
                    value={bookingDetails.specialRequest}
                    onChange={(e) => setBookingDetails({ ...bookingDetails, specialRequest: e.target.value })}
                  />
                </div>

                {/* Reservation Summary */}
                <div className="bg-orange-50 p-4 rounded-lg space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Date</span>
                    <span className="font-medium">{format(bookingDetails.date, 'MMM dd, yyyy')}</span>
                  </div>
                  {bookingDetails.timeSlot && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Time</span>
                      <span className="font-medium">{bookingDetails.timeSlot}</span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-gray-600">Guests</span>
                    <span className="font-medium">{bookingDetails.guests} {bookingDetails.guests === 1 ? 'person' : 'people'}</span>
                  </div>
                </div>

                {/* Reserve Button */}
                <Button
                  className="w-full bg-orange-600 hover:bg-orange-700"
                  size="lg"
                  onClick={handleReserve}
                  disabled={loading || !bookingDetails.timeSlot}
                >
                  {loading ? 'Processing...' : 'Reserve Table'}
                </Button>

                <p className="text-xs text-center text-gray-500">
                  Free cancellation up to 2 hours before reservation
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RestaurantDetail;
