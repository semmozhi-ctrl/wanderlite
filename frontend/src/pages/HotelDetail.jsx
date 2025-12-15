import React, { useState } from 'react';
import { useParams, useLocation, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Calendar } from '../components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '../components/ui/popover';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import {
  Hotel, Star, MapPin, Wifi, Coffee, Car, Tv, Wind,
  CalendarIcon, Users, ChevronRight, Home, CheckCircle
} from 'lucide-react';
import { format, differenceInDays } from 'date-fns';
import api from '../services/api';

const HotelDetail = () => {
  const { destinationName, hotelId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const { hotel, destination } = location.state || {};

  const [bookingDetails, setBookingDetails] = useState({
    checkIn: new Date(),
    checkOut: new Date(new Date().setDate(new Date().getDate() + 1)),
    guests: 2,
    roomType: 'standard'
  });
  const [loading, setLoading] = useState(false);

  const roomTypes = [
    { value: 'standard', label: 'Standard Room', priceMultiplier: 1, description: 'Cozy room with essential amenities' },
    { value: 'deluxe', label: 'Deluxe Room', priceMultiplier: 1.5, description: 'Spacious room with premium amenities' },
    { value: 'suite', label: 'Suite', priceMultiplier: 2.5, description: 'Luxurious suite with separate living area' }
  ];

  const amenities = [
    { icon: Wifi, label: 'Free WiFi' },
    { icon: Coffee, label: 'Breakfast' },
    { icon: Car, label: 'Parking' },
    { icon: Tv, label: 'TV' },
    { icon: Wind, label: 'AC' }
  ];

  const handleBookNow = async () => {
    if (!hotel) return;

    if (!isAuthenticated) {
      alert('Please login to book this hotel');
      navigate('/login', { state: { returnTo: location.pathname } });
      return;
    }

    setLoading(true);
    try {
      const nights = differenceInDays(bookingDetails.checkOut, bookingDetails.checkIn);
      const selectedRoom = roomTypes.find(r => r.value === bookingDetails.roomType);
      const totalPrice = hotel.price_per_night * selectedRoom.priceMultiplier * nights;

      const serviceJson = JSON.stringify({
        ...hotel,
        checkIn: format(bookingDetails.checkIn, 'yyyy-MM-dd'),
        checkOut: format(bookingDetails.checkOut, 'yyyy-MM-dd'),
        nights,
        guests: bookingDetails.guests,
        roomType: selectedRoom.label,
        destination: destination?.name
      });

      const response = await api.post('/api/bookings/service', {
        service_type: 'Hotel',
        destination: hotel.location || hotel.city || 'Unknown',
        travelers: bookingDetails.guests || 1,
        amount: totalPrice,
        service_details: {
          hotel: hotel,
          check_in: format(bookingDetails.checkIn, 'yyyy-MM-dd'),
          check_out: format(bookingDetails.checkOut, 'yyyy-MM-dd'),
          guests: bookingDetails.guests,
          nights: nights,
          roomType: selectedRoom.label,
          currency: hotel.currency
        }
      });

      navigate('/payment', {
        state: {
          bookingId: response.data.id,
          bookingRef: response.data.booking_ref,
          amount: totalPrice,
          currency: hotel.currency || 'INR',
          serviceType: 'Hotel',
          serviceDetails: {
            ...hotel,
            checkIn: format(bookingDetails.checkIn, 'MMM dd, yyyy'),
            checkOut: format(bookingDetails.checkOut, 'MMM dd, yyyy'),
            nights,
            guests: bookingDetails.guests,
            roomType: selectedRoom.label,
            destination: destination?.name
          }
        }
      });
    } catch (error) {
      console.error('Error creating booking:', error);
      const errorMsg = error.response?.data?.detail || 'Failed to create booking. Please try again.';
      alert(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  if (!hotel) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-2">Hotel not found</h2>
          <Button onClick={() => navigate(`/destination/${destinationName}`)}>
            Back to Destination
          </Button>
        </div>
      </div>
    );
  }

  const nights = differenceInDays(bookingDetails.checkOut, bookingDetails.checkIn);
  const selectedRoom = roomTypes.find(r => r.value === bookingDetails.roomType);
  const basePrice = hotel.price_per_night * selectedRoom.priceMultiplier;
  const totalPrice = basePrice * nights;

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-pink-50 pt-24 pb-8 px-4">
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
            <span className="text-gray-900 font-medium">Hotels</span>
            <ChevronRight className="w-4 h-4" />
            <span className="text-gray-900 font-medium">{hotel.name}</span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Hotel Details */}
          <div className="lg:col-span-2 space-y-6">
            {/* Hero Image */}
            <Card>
              <img 
                src={hotel.image_url} 
                alt={hotel.name}
                className="w-full h-80 object-cover rounded-t-lg"
              />
              <CardContent className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h1 className="text-3xl font-bold mb-2">{hotel.name}</h1>
                    <div className="flex items-center gap-1 mb-2">
                      {[...Array(5)].map((_, i) => (
                        <Star
                          key={i}
                          className={`w-5 h-5 ${
                            i < Math.floor(hotel.rating)
                              ? 'fill-yellow-400 text-yellow-400'
                              : 'text-gray-300'
                          }`}
                        />
                      ))}
                      <span className="text-sm ml-2 text-gray-600">{hotel.rating} / 5</span>
                    </div>
                    <div className="flex items-center gap-2 text-gray-600">
                      <MapPin className="w-4 h-4" />
                      <span>{hotel.location}</span>
                    </div>
                  </div>
                  <Badge variant="secondary" className="text-lg px-4 py-2">
                    {hotel.category}
                  </Badge>
                </div>

                <p className="text-gray-700 mb-6">
                  {hotel.description || `Experience luxury and comfort at ${hotel.name}. Perfect for families and couples seeking a memorable stay.`}
                </p>

                {/* Amenities */}
                <div>
                  <h3 className="font-semibold text-lg mb-3">Amenities</h3>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                    {amenities.map((amenity, index) => (
                      <div key={index} className="flex items-center gap-2 text-gray-700">
                        <amenity.icon className="w-5 h-5 text-purple-600" />
                        <span className="text-sm">{amenity.label}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Room Types */}
            <Card>
              <CardHeader>
                <CardTitle>Choose Your Room</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {roomTypes.map((room) => (
                  <div
                    key={room.value}
                    className={`border-2 rounded-lg p-4 cursor-pointer transition-all ${
                      bookingDetails.roomType === room.value
                        ? 'border-purple-600 bg-purple-50'
                        : 'border-gray-200 hover:border-purple-300'
                    }`}
                    onClick={() => setBookingDetails({ ...bookingDetails, roomType: room.value })}
                  >
                    <div className="flex justify-between items-center">
                      <div>
                        <h4 className="font-semibold text-lg">{room.label}</h4>
                        <p className="text-sm text-gray-600">{room.description}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-2xl font-bold text-purple-600">
                          ₹{(hotel.price_per_night * room.priceMultiplier).toLocaleString()}
                        </p>
                        <p className="text-xs text-gray-500">per night</p>
                      </div>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          {/* Booking Form */}
          <div className="lg:col-span-1">
            <Card className="sticky top-24">
              <CardHeader>
                <CardTitle>Book Your Stay</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Check-in Date */}
                <div>
                  <Label>Check-in Date</Label>
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button variant="outline" className="w-full justify-start text-left">
                        <CalendarIcon className="mr-2 h-4 w-4" />
                        {format(bookingDetails.checkIn, 'PPP')}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0">
                      <Calendar
                        mode="single"
                        selected={bookingDetails.checkIn}
                        onSelect={(date) => date && setBookingDetails({ ...bookingDetails, checkIn: date })}
                        disabled={(date) => date < new Date()}
                      />
                    </PopoverContent>
                  </Popover>
                </div>

                {/* Check-out Date */}
                <div>
                  <Label>Check-out Date</Label>
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button variant="outline" className="w-full justify-start text-left">
                        <CalendarIcon className="mr-2 h-4 w-4" />
                        {format(bookingDetails.checkOut, 'PPP')}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0">
                      <Calendar
                        mode="single"
                        selected={bookingDetails.checkOut}
                        onSelect={(date) => date && setBookingDetails({ ...bookingDetails, checkOut: date })}
                        disabled={(date) => date <= bookingDetails.checkIn}
                      />
                    </PopoverContent>
                  </Popover>
                </div>

                {/* Guests */}
                <div>
                  <Label>Number of Guests</Label>
                  <Input
                    type="number"
                    min="1"
                    max="10"
                    value={bookingDetails.guests}
                    onChange={(e) => setBookingDetails({ ...bookingDetails, guests: parseInt(e.target.value) })}
                  />
                </div>

                {/* Nights Info */}
                <div className="bg-purple-50 p-4 rounded-lg">
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-gray-600">Duration</span>
                    <span className="font-medium">{nights} {nights === 1 ? 'night' : 'nights'}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Guests</span>
                    <span className="font-medium">{bookingDetails.guests}</span>
                  </div>
                </div>

                {/* Price Summary */}
                <div className="border-t pt-4 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">₹{basePrice.toLocaleString()} x {nights} {nights === 1 ? 'night' : 'nights'}</span>
                    <span className="font-medium">₹{totalPrice.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Taxes & Fees</span>
                    <span className="font-medium">Included</span>
                  </div>
                  <div className="flex justify-between text-lg font-bold border-t pt-2">
                    <span>Total</span>
                    <span className="text-purple-600">₹{totalPrice.toLocaleString()}</span>
                  </div>
                </div>

                {/* Book Button */}
                <Button
                  className="w-full bg-purple-600 hover:bg-purple-700"
                  size="lg"
                  onClick={handleBookNow}
                  disabled={loading || nights < 1}
                >
                  {loading ? 'Processing...' : 'Book Now'}
                </Button>

                <p className="text-xs text-center text-gray-500">
                  Free cancellation up to 24 hours before check-in
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HotelDetail;
