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
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { 
  Plane, Clock, Users, Luggage, CalendarIcon, ChevronRight, 
  Home, User, Mail, Phone, CreditCard, MapPin, Info, CheckCircle, AlertCircle
} from 'lucide-react';
import { format } from 'date-fns';
import api from '../services/api';

const FlightDetail = () => {
  const { destinationName, flightId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const { flight, destination } = location.state || {};

  const [showBookingForm, setShowBookingForm] = useState(false);
  const [bookingDetails, setBookingDetails] = useState({
    travelers: 1,
    date: new Date(),
    selectedClass: 'economy'
  });
  
  const [passengerDetails, setPassengerDetails] = useState({
    fullName: '',
    gender: '',
    dateOfBirth: '',
    email: '',
    mobile: '',
    passportNumber: '',
    nationality: '',
    seatNumber: ''
  });
  
  const [loading, setLoading] = useState(false);

  // Early return if flight data is not available
  if (!flight) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex items-center justify-center">
        <Card className="max-w-md w-full mx-4">
          <CardContent className="p-8 text-center">
            <Plane className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Flight Not Found</h2>
            <p className="text-gray-600 mb-6">The flight you&apos;re looking for could not be found.</p>
            <Button onClick={() => navigate('/explore')} className="w-full">
              Back to Explore
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Generate available seats
  const generateSeats = () => {
    const rows = ['A', 'B', 'C', 'D', 'E', 'F'];
    const seats = [];
    for (let i = 1; i <= 30; i++) {
      rows.forEach(row => {
        seats.push(`${row}${i}`);
      });
    }
    return seats;
  };

  const availableSeats = generateSeats();

  const handleBookNowClick = () => {
    if (!isAuthenticated) {
      alert('Please login to book this flight');
      navigate('/login', { state: { returnTo: location.pathname, flight, destination } });
      return;
    }
    setShowBookingForm(true);
  };

  const handlePassengerChange = (field, value) => {
    setPassengerDetails(prev => ({ ...prev, [field]: value }));
  };

  const handleConfirmBooking = async () => {
    // Validation
    if (!passengerDetails.fullName || !passengerDetails.email || !passengerDetails.mobile || 
        !passengerDetails.gender || !passengerDetails.seatNumber) {
      alert('Please fill in all required fields');
      return;
    }

    if (!isAuthenticated) {
      alert('Please login to book this flight');
      navigate('/login', { state: { returnTo: location.pathname } });
      return;
    }

    setLoading(true);
    try {
      const totalPrice = flight.price * bookingDetails.travelers;
      const baseFare = flight.price;
      const taxes = totalPrice * 0.18; // 18% tax
      const finalTotal = baseFare * bookingDetails.travelers + taxes;
      
      const serviceJson = JSON.stringify({
        ...flight,
        travelers: bookingDetails.travelers,
        travelDate: format(bookingDetails.date, 'yyyy-MM-dd'),
        class: bookingDetails.selectedClass,
        destination: destination?.name,
        passenger: passengerDetails,
        boardingTime: new Date(flight.departure_time).toLocaleTimeString('en-US', { 
          hour: '2-digit', 
          minute: '2-digit',
          hour12: false
        }),
        gate: Math.floor(Math.random() * 30) + 1, // Random gate number
        departureDate: format(new Date(flight.departure_time), 'dd MMM yyyy'),
        baseFare: baseFare,
        taxes: taxes,
        total_price: finalTotal
      });

      const response = await api.post('/api/bookings/service', {
        service_type: 'Flight',
        service_json: serviceJson,
        total_price: finalTotal,
        currency: flight.currency || 'INR'
      });

      navigate('/payment', {
        state: {
          bookingId: response.data.id,
          bookingRef: response.data.booking_ref,
          amount: finalTotal,
          currency: flight.currency || 'INR',
          serviceType: 'Flight',
          serviceDetails: {
            ...flight,
            travelers: bookingDetails.travelers,
            travelDate: format(bookingDetails.date, 'MMM dd, yyyy'),
            class: bookingDetails.selectedClass,
            destination: destination?.name,
            passenger: passengerDetails,
            baseFare: baseFare,
            taxes: taxes,
            total_price: finalTotal
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

  if (!flight) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-2">Flight not found</h2>
          <Button onClick={() => navigate(`/destination/${destinationName}`)}>
            Back to Destination
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 pt-24 pb-8 px-4">
      <div className="max-w-5xl mx-auto">
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
            <span className="text-gray-900 font-medium">Flights</span>
            <ChevronRight className="w-4 h-4" />
            <span className="text-gray-900 font-medium">{flight.airline}</span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Flight Details */}
          <div className="lg:col-span-2 space-y-6">
            {/* Main Card */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-2xl">{flight.airline}</CardTitle>
                    <p className="text-gray-600">{flight.flight_number}</p>
                  </div>
                  <div className="bg-blue-100 p-3 rounded-lg">
                    <Plane className="w-8 h-8 text-blue-600" />
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Route */}
                <div className="bg-gray-50 rounded-lg p-6">
                  <div className="flex items-center justify-between">
                    <div className="text-center">
                      <p className="text-3xl font-bold text-gray-900">
                        {new Date(flight.departure_time).toLocaleTimeString('en-US', { 
                          hour: '2-digit', 
                          minute: '2-digit' 
                        })}
                      </p>
                      <p className="text-gray-600 font-medium mt-1">{flight.origin}</p>
                      <p className="text-sm text-gray-500">
                        {format(new Date(flight.departure_time), 'MMM dd, yyyy')}
                      </p>
                    </div>

                    <div className="flex-1 flex flex-col items-center px-4">
                      <div className="flex items-center gap-2 text-gray-500 w-full">
                        <div className="h-px bg-gray-300 flex-1"></div>
                        <Clock className="w-5 h-5" />
                        <span className="text-sm font-medium">{flight.duration}</span>
                        <div className="h-px bg-gray-300 flex-1"></div>
                      </div>
                      <p className="text-xs text-gray-500 mt-2">Direct Flight</p>
                    </div>

                    <div className="text-center">
                      <p className="text-3xl font-bold text-gray-900">
                        {new Date(flight.arrival_time).toLocaleTimeString('en-US', { 
                          hour: '2-digit', 
                          minute: '2-digit' 
                        })}
                      </p>
                      <p className="text-gray-600 font-medium mt-1">{flight.destination}</p>
                      <p className="text-sm text-gray-500">
                        {format(new Date(flight.arrival_time), 'MMM dd, yyyy')}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Flight Details */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex items-start gap-3 p-4 bg-blue-50 rounded-lg">
                    <Luggage className="w-5 h-5 text-blue-600 mt-1" />
                    <div>
                      <p className="font-semibold text-gray-900">Baggage</p>
                      <p className="text-sm text-gray-600">{flight.baggage}</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 p-4 bg-green-50 rounded-lg">
                    <Users className="w-5 h-5 text-green-600 mt-1" />
                    <div>
                      <p className="font-semibold text-gray-900">Seats Available</p>
                      <p className="text-sm text-gray-600">{flight.seats_available} seats</p>
                    </div>
                  </div>
                </div>

                {/* Policies */}
                <div className="border-t pt-4">
                  <h3 className="font-semibold mb-3 flex items-center gap-2">
                    <Info className="w-5 h-5 text-gray-600" />
                    Cancellation Policy
                  </h3>
                  <div className="flex items-start gap-2 bg-yellow-50 p-3 rounded-lg">
                    {flight?.refund_policy?.includes('Free') ? (
                      <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                    ) : (
                      <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                    )}
                    <p className="text-sm text-gray-700">{flight?.refund_policy || 'Refund policy not available'}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Booking Panel */}
          <div className="lg:col-span-1">
            <Card className="sticky top-4">
              <CardHeader>
                <CardTitle>Book Your Flight</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Travel Date */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Travel Date
                  </label>
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button variant="outline" className="w-full justify-start text-left font-normal">
                        <CalendarIcon className="mr-2 h-4 w-4" />
                        {format(bookingDetails.date, 'PPP')}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0">
                      <Calendar
                        mode="single"
                        selected={bookingDetails.date}
                        onSelect={(date) => date && setBookingDetails({ ...bookingDetails, date })}
                        initialFocus
                      />
                    </PopoverContent>
                  </Popover>
                </div>

                {/* Number of Travelers */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Number of Travelers
                  </label>
                  <Input
                    type="number"
                    min="1"
                    max="9"
                    value={bookingDetails.travelers}
                    onChange={(e) => setBookingDetails({ 
                      ...bookingDetails, 
                      travelers: parseInt(e.target.value) || 1 
                    })}
                  />
                </div>

                {/* Class Selection */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Class
                  </label>
                  <div className="space-y-2">
                    {['economy', 'business', 'first'].map((cls) => (
                      <button
                        key={cls}
                        onClick={() => setBookingDetails({ ...bookingDetails, selectedClass: cls })}
                        className={`w-full p-3 border rounded-lg text-left transition-colors ${
                          bookingDetails.selectedClass === cls
                            ? 'border-blue-600 bg-blue-50 text-blue-900'
                            : 'hover:bg-gray-50'
                        }`}
                      >
                        <p className="font-medium capitalize">{cls}</p>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Price Summary */}
                <div className="border-t pt-4 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Base Fare (x{bookingDetails.travelers})</span>
                    <span className="font-medium">₹{(flight.price * bookingDetails.travelers).toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Taxes & Fees</span>
                    <span className="font-medium">Included</span>
                  </div>
                  <div className="flex justify-between text-lg font-bold border-t pt-2">
                    <span>Total</span>
                    <span className="text-blue-600">
                      ₹{(flight.price * bookingDetails.travelers).toLocaleString()}
                    </span>
                  </div>
                </div>

                {/* Book Button */}
                <Button 
                  className="w-full" 
                  size="lg"
                  onClick={handleBookNowClick}
                  disabled={loading}
                >
                  {loading ? 'Processing...' : 'Book Now'}
                </Button>

                <p className="text-xs text-center text-gray-500">
                  You&apos;ll need to fill passenger details next
                </p>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Booking Form Modal */}
        <Dialog open={showBookingForm} onOpenChange={setShowBookingForm}>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="text-2xl">Passenger Details</DialogTitle>
              <DialogDescription className="text-sm text-gray-600">
                Please fill in the passenger information
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4 mt-4">
              {/* Flight Summary */}
              <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 border-0">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Plane className="w-5 h-5 text-blue-600" />
                      <span className="font-semibold">{flight.airline} - {flight.flight_number}</span>
                    </div>
                    <Badge>{bookingDetails.selectedClass.toUpperCase()}</Badge>
                  </div>
                  <div className="text-sm text-gray-700">
                    <span className="font-medium">{flight.origin}</span> → <span className="font-medium">{flight.destination}</span>
                  </div>
                  <div className="text-sm text-gray-600 mt-1">
                    {format(bookingDetails.date, 'MMM dd, yyyy')} • {bookingDetails.travelers} Traveler(s)
                  </div>
                </CardContent>
              </Card>

              {/* Passenger Information Form */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <User className="w-4 h-4 text-blue-600" />
                    Full Name *
                  </Label>
                  <Input
                    placeholder="John Doe"
                    value={passengerDetails.fullName}
                    onChange={(e) => handlePassengerChange('fullName', e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Gender *</Label>
                  <Select 
                    value={passengerDetails.gender}
                    onValueChange={(value) => handlePassengerChange('gender', value)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select gender" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="male">Male</SelectItem>
                      <SelectItem value="female">Female</SelectItem>
                      <SelectItem value="other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Date of Birth</Label>
                  <Input
                    type="date"
                    value={passengerDetails.dateOfBirth}
                    onChange={(e) => handlePassengerChange('dateOfBirth', e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Mail className="w-4 h-4 text-blue-600" />
                    Email *
                  </Label>
                  <Input
                    type="email"
                    placeholder="john@example.com"
                    value={passengerDetails.email}
                    onChange={(e) => handlePassengerChange('email', e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Phone className="w-4 h-4 text-blue-600" />
                    Mobile Number *
                  </Label>
                  <Input
                    type="tel"
                    placeholder="+91 XXXXX XXXXX"
                    value={passengerDetails.mobile}
                    onChange={(e) => handlePassengerChange('mobile', e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <CreditCard className="w-4 h-4 text-blue-600" />
                    Passport / ID Number
                  </Label>
                  <Input
                    placeholder="A12345678"
                    value={passengerDetails.passportNumber}
                    onChange={(e) => handlePassengerChange('passportNumber', e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <MapPin className="w-4 h-4 text-blue-600" />
                    Nationality
                  </Label>
                  <Input
                    placeholder="Indian"
                    value={passengerDetails.nationality}
                    onChange={(e) => handlePassengerChange('nationality', e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Seat Selection *</Label>
                  <Select 
                    value={passengerDetails.seatNumber}
                    onValueChange={(value) => handlePassengerChange('seatNumber', value)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Choose your seat" />
                    </SelectTrigger>
                    <SelectContent className="max-h-60">
                      {availableSeats.map(seat => (
                        <SelectItem key={seat} value={seat}>{seat}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Price Summary */}
              <Card className="bg-gray-50 border-0">
                <CardContent className="p-4 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Base Fare (x{bookingDetails.travelers})</span>
                    <span className="font-medium">₹{(flight.price * bookingDetails.travelers).toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Taxes & Fees</span>
                    <span className="font-medium">Included</span>
                  </div>
                  <div className="flex justify-between text-lg font-bold border-t pt-2">
                    <span>Total Amount</span>
                    <span className="text-blue-600">₹{(flight.price * bookingDetails.travelers).toLocaleString()}</span>
                  </div>
                </CardContent>
              </Card>

              {/* Action Buttons */}
              <div className="flex gap-3 pt-4">
                <Button 
                  variant="outline" 
                  className="flex-1"
                  onClick={() => setShowBookingForm(false)}
                >
                  Cancel
                </Button>
                <Button 
                  className="flex-1 bg-blue-600 hover:bg-blue-700"
                  onClick={handleConfirmBooking}
                  disabled={loading}
                >
                  {loading ? 'Processing...' : 'Proceed to Payment'}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
};

export default FlightDetail;
