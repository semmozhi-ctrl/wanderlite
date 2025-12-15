import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Bus,
  User,
  MapPin,
  Calendar,
  Clock,
  Phone,
  Mail,
  CreditCard,
  ChevronRight,
  AlertCircle,
  Check,
  X,
  Loader2,
  ArrowLeft,
  Info
} from 'lucide-react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Helper function to extract error message from API response
const getErrorMessage = (err, defaultMsg) => {
  const detail = err.response?.data?.detail;
  if (!detail) return defaultMsg;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    // FastAPI validation errors are arrays of objects with 'msg' field
    return detail.map(e => e.msg || e.message || JSON.stringify(e)).join(', ');
  }
  if (typeof detail === 'object' && detail.msg) return detail.msg;
  return defaultMsg;
};

const BusBooking = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, token } = useAuth();
  const { bus, fromCity, toCity, journeyDate } = location.state || {};

  const [step, setStep] = useState(1); // 1: Seats, 2: Details, 3: Payment
  const [seatData, setSeatData] = useState(null);
  const [selectedSeats, setSelectedSeats] = useState([]);
  const [passengers, setPassengers] = useState([]);
  const [boardingPoint, setBoardingPoint] = useState(null);
  const [droppingPoint, setDroppingPoint] = useState(null);
  const [contactDetails, setContactDetails] = useState({
    name: user?.name || '',
    email: user?.email || '',
    phone: user?.phone || ''
  });
  const [loading, setLoading] = useState(true);
  const [booking, setBooking] = useState(false);
  const [error, setError] = useState('');
  const [lockedSeats, setLockedSeats] = useState([]);

  // Fetch seat data
  useEffect(() => {
    const fetchSeats = async () => {
      if (!bus || !journeyDate) {
        console.log('Missing bus or journeyDate:', { bus, journeyDate });
        return;
      }
      
      try {
        setLoading(true);
        setError('');
        console.log('Fetching seats for:', { schedule_id: bus.schedule_id, journeyDate });
        const response = await axios.get(
          `${API_URL}/api/bus/seats/${bus.schedule_id}/${journeyDate}`
        );
        console.log('Seat data received:', response.data);
        setSeatData(response.data);
      } catch (err) {
        console.error('Error fetching seats:', err);
        console.error('Error details:', err.response?.data);
        setError(getErrorMessage(err, 'Failed to load seat information'));
      } finally {
        setLoading(false);
      }
    };
    fetchSeats();
  }, [bus, journeyDate]);

  // Initialize passengers when seats change
  useEffect(() => {
    setPassengers(selectedSeats.map(seat => ({
      seat_id: seat.id,
      seat_number: seat.seat_number,
      name: '',
      age: '',
      gender: 'male',
      id_type: 'aadhar',
      id_number: ''
    })));
  }, [selectedSeats]);

  // Calculate total price
  const totalPrice = selectedSeats.reduce((sum, seat) => sum + seat.price, 0);

  // Handle seat selection
  const toggleSeat = async (seat) => {
    if (seat.status === 'booked' || seat.status === 'locked') return;
    
    const isSelected = selectedSeats.find(s => s.id === seat.id);
    
    if (isSelected) {
      setSelectedSeats(prev => prev.filter(s => s.id !== seat.id));
    } else {
      if (selectedSeats.length >= 6) {
        setError('Maximum 6 seats can be selected');
        return;
      }
      setSelectedSeats(prev => [...prev, seat]);
    }
    setError('');
  };

  // Lock seats when proceeding
  const lockSeats = async () => {
    if (selectedSeats.length === 0) {
      setError('Please select at least one seat');
      return;
    }

    try {
      const response = await axios.post(
        `${API_URL}/api/bus/seats/lock`,
        {
          schedule_id: bus.schedule_id,
          journey_date: journeyDate,
          seat_ids: selectedSeats.map(s => s.id)
        },
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );
      setLockedSeats(response.data.locked_seats);
      setStep(2);
      setError('');
    } catch (err) {
      console.error('Error locking seats:', err);
      setError(getErrorMessage(err, 'Failed to lock seats'));
    }
  };

  // Update passenger details
  const updatePassenger = (index, field, value) => {
    setPassengers(prev => prev.map((p, i) => 
      i === index ? { ...p, [field]: value } : p
    ));
  };

  // Validate passenger details
  const validatePassengers = () => {
    for (const p of passengers) {
      if (!p.name.trim()) return 'Please enter name for all passengers';
      if (!p.age || p.age < 1 || p.age > 120) return 'Please enter valid age for all passengers';
    }
    if (!boardingPoint) return 'Please select a boarding point';
    if (!droppingPoint) return 'Please select a dropping point';
    if (!contactDetails.name || !contactDetails.name.trim()) return 'Please enter contact name';
    if (!contactDetails.phone || contactDetails.phone.length < 10) return 'Please enter a valid phone number';
    if (!contactDetails.email) return 'Please enter email address';
    return null;
  };

  // Proceed to payment
  const proceedToPayment = () => {
    const validationError = validatePassengers();
    if (validationError) {
      setError(validationError);
      return;
    }
    setError('');
    setStep(3);
  };

  // Complete booking
  const completeBooking = async () => {
    setBooking(true);
    setError('');

    try {
      const response = await axios.post(
        `${API_URL}/api/bus/book`,
        {
          schedule_id: bus.schedule_id,
          journey_date: journeyDate,
          passengers: passengers.map(p => ({
            seat_id: p.seat_id,
            name: p.name,
            age: parseInt(p.age),
            gender: p.gender,
            id_type: p.id_type,
            id_number: p.id_number || null
          })),
          boarding_point_id: boardingPoint.id,
          dropping_point_id: droppingPoint.id,
          contact_name: contactDetails.name,
          contact_email: contactDetails.email,
          contact_phone: contactDetails.phone
        },
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      // Navigate to ticket page
      navigate('/bus-ticket', {
        state: {
          bookingId: response.data.booking_id,
          pnr: response.data.pnr
        }
      });
    } catch (err) {
      console.error('Booking error:', err);
      setError(getErrorMessage(err, 'Failed to complete booking'));
    } finally {
      setBooking(false);
    }
  };

  // Get seat color
  const getSeatColor = (seat) => {
    if (selectedSeats.find(s => s.id === seat.id)) {
      return 'bg-green-500 text-white border-green-600';
    }
    if (seat.status === 'booked') {
      return 'bg-gray-400 text-white cursor-not-allowed';
    }
    if (seat.status === 'locked') {
      return 'bg-yellow-400 text-white cursor-not-allowed';
    }
    if (seat.is_female_only) {
      return 'bg-pink-100 text-pink-700 border-pink-300 hover:bg-pink-200';
    }
    return 'bg-white text-gray-700 border-gray-300 hover:bg-orange-50 hover:border-orange-400';
  };

  // Format date
  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      year: 'numeric'
    });
  };

  if (!bus) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="container mx-auto px-4 py-20 text-center">
          <Bus className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-600 mb-2">No Bus Selected</h2>
          <button
            onClick={() => navigate('/buses')}
            className="px-6 py-3 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition"
          >
            Search Buses
          </button>
        </div>
      </div>
    );
  }

  // Organize seats by deck and row
  const organizeSeats = () => {
    if (!seatData?.seats) return { lower: [], upper: [] };
    
    const lower = {};
    const upper = {};
    
    seatData.seats.forEach(seat => {
      const target = seat.deck === 'upper' ? upper : lower;
      if (!target[seat.row]) target[seat.row] = [];
      target[seat.row].push(seat);
    });

    // Sort seats within each row by column
    Object.keys(lower).forEach(row => {
      lower[row].sort((a, b) => a.column - b.column);
    });
    Object.keys(upper).forEach(row => {
      upper[row].sort((a, b) => a.column - b.column);
    });

    return { lower, upper };
  };

  const organizedSeats = organizeSeats();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Progress Steps */}
      <div className="bg-white border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-center gap-4">
            {[
              { num: 1, label: 'Select Seats' },
              { num: 2, label: 'Passenger Details' },
              { num: 3, label: 'Payment' }
            ].map((s, idx) => (
              <React.Fragment key={s.num}>
                <div className={`flex items-center gap-2 ${step >= s.num ? 'text-orange-600' : 'text-gray-400'}`}>
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center font-medium ${
                    step > s.num ? 'bg-green-500 text-white' :
                    step === s.num ? 'bg-orange-500 text-white' : 'bg-gray-200'
                  }`}>
                    {step > s.num ? <Check className="w-5 h-5" /> : s.num}
                  </div>
                  <span className="hidden sm:inline font-medium">{s.label}</span>
                </div>
                {idx < 2 && (
                  <ChevronRight className={`w-5 h-5 ${step > s.num ? 'text-green-500' : 'text-gray-300'}`} />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      </div>

      {/* Journey Info */}
      <div className="bg-gradient-to-r from-orange-600 to-red-600 text-white py-4">
        <div className="container mx-auto px-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="font-bold text-lg">{bus.operator_name}</h2>
              <p className="text-orange-100 text-sm">{bus.bus_type}</p>
            </div>
            <div className="flex items-center gap-6">
              <div className="text-center">
                <p className="font-bold text-xl">{bus.departure_time}</p>
                <p className="text-sm text-orange-100">{fromCity?.name}</p>
              </div>
              <div className="text-orange-200">→</div>
              <div className="text-center">
                <p className="font-bold text-xl">{bus.arrival_time}</p>
                <p className="text-sm text-orange-100">{toCity?.name}</p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm text-orange-100">Journey Date</p>
              <p className="font-medium">{formatDate(journeyDate)}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-600 flex items-center gap-2">
            <AlertCircle className="w-5 h-5" />
            {error}
          </div>
        )}

        {/* Step 1: Seat Selection */}
        {step === 1 && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Seat Layout */}
            <div className="lg:col-span-2 bg-white rounded-xl shadow-sm p-6">
              <h3 className="font-bold text-gray-800 mb-4">Select Your Seats</h3>
              
              {loading ? (
                <div className="flex items-center justify-center py-20">
                  <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
                </div>
              ) : (
                <div className="space-y-8">
                  {/* Seat Legend */}
                  <div className="flex flex-wrap items-center gap-4 pb-4 border-b">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 bg-white border-2 border-gray-300 rounded"></div>
                      <span className="text-sm text-gray-600">Available</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 bg-green-500 rounded"></div>
                      <span className="text-sm text-gray-600">Selected</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 bg-gray-400 rounded"></div>
                      <span className="text-sm text-gray-600">Booked</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 bg-pink-100 border border-pink-300 rounded"></div>
                      <span className="text-sm text-gray-600">Ladies</span>
                    </div>
                  </div>

                  {/* Lower Deck */}
                  <div>
                    <h4 className="font-medium text-gray-700 mb-4 flex items-center gap-2">
                      <Bus className="w-4 h-4" />
                      {seatData?.has_upper_deck ? 'Lower Deck' : 'Seats'}
                    </h4>
                    <div className="border-2 border-gray-200 rounded-xl p-4 bg-gray-50">
                      {/* Driver */}
                      <div className="flex justify-end mb-4 pb-4 border-b border-dashed">
                        <div className="w-10 h-10 bg-gray-300 rounded-full flex items-center justify-center text-xs text-gray-600">
                          Driver
                        </div>
                      </div>
                      
                      {/* Seats Grid */}
                      <div className="space-y-3">
                        {Object.keys(organizedSeats.lower).sort((a, b) => a - b).map(row => (
                          <div key={row} className="flex items-center gap-2">
                            <span className="w-6 text-xs text-gray-400">{row}</span>
                            <div className="flex-1 flex justify-center gap-2">
                              {organizedSeats.lower[row].map((seat, idx) => {
                                // Add aisle gap
                                const layout = seatData?.seat_layout || '2+2';
                                const [left] = layout.split('+').map(Number);
                                const showGap = idx === left;
                                
                                return (
                                  <React.Fragment key={seat.id}>
                                    {showGap && <div className="w-8" />}
                                    <button
                                      onClick={() => toggleSeat(seat)}
                                      disabled={seat.status === 'booked' || seat.status === 'locked'}
                                      className={`w-10 h-10 rounded-lg border-2 text-xs font-medium transition ${getSeatColor(seat)}`}
                                      title={`${seat.seat_number} - ₹${seat.price.toFixed(0)}`}
                                    >
                                      {seat.seat_number}
                                    </button>
                                  </React.Fragment>
                                );
                              })}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Upper Deck */}
                  {seatData?.has_upper_deck === 1 && Object.keys(organizedSeats.upper).length > 0 && (
                    <div>
                      <h4 className="font-medium text-gray-700 mb-4 flex items-center gap-2">
                        <Bus className="w-4 h-4" />
                        Upper Deck
                      </h4>
                      <div className="border-2 border-gray-200 rounded-xl p-4 bg-gray-50">
                        <div className="space-y-3">
                          {Object.keys(organizedSeats.upper).sort((a, b) => a - b).map(row => (
                            <div key={row} className="flex items-center gap-2">
                              <span className="w-6 text-xs text-gray-400">{row}</span>
                              <div className="flex-1 flex justify-center gap-2">
                                {organizedSeats.upper[row].map((seat, idx) => {
                                  const layout = seatData?.seat_layout || '2+1';
                                  const [left] = layout.split('+').map(Number);
                                  const showGap = idx === left;
                                  
                                  return (
                                    <React.Fragment key={seat.id}>
                                      {showGap && <div className="w-8" />}
                                      <button
                                        onClick={() => toggleSeat(seat)}
                                        disabled={seat.status === 'booked' || seat.status === 'locked'}
                                        className={`w-10 h-10 rounded-lg border-2 text-xs font-medium transition ${getSeatColor(seat)}`}
                                        title={`${seat.seat_number} - ₹${seat.price.toFixed(0)}`}
                                      >
                                        {seat.seat_number}
                                      </button>
                                    </React.Fragment>
                                  );
                                })}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Booking Summary */}
            <div className="lg:col-span-1">
              <div className="bg-white rounded-xl shadow-sm p-6 sticky top-4">
                <h3 className="font-bold text-gray-800 mb-4">Booking Summary</h3>
                
                {selectedSeats.length > 0 ? (
                  <>
                    <div className="space-y-3 mb-4 pb-4 border-b">
                      {selectedSeats.map(seat => (
                        <div key={seat.id} className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="w-8 h-8 bg-green-100 text-green-600 rounded flex items-center justify-center text-sm font-medium">
                              {seat.seat_number}
                            </span>
                            <span className="text-sm text-gray-600">
                              {seat.deck === 'upper' ? 'Upper' : 'Lower'} - {seat.position}
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium">₹{seat.price.toFixed(0)}</span>
                            <button
                              onClick={() => toggleSeat(seat)}
                              className="text-gray-400 hover:text-red-500"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                    
                    <div className="flex items-center justify-between mb-6">
                      <span className="font-medium text-gray-700">Total</span>
                      <span className="text-2xl font-bold text-orange-600">
                        ₹{totalPrice.toFixed(0)}
                      </span>
                    </div>

                    <button
                      onClick={lockSeats}
                      className="w-full py-3 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition font-medium"
                    >
                      Continue
                    </button>
                  </>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    <Bus className="w-12 h-12 mx-auto mb-2 text-gray-300" />
                    <p>Select seats to continue</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Passenger Details */}
        {step === 2 && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              {/* Passenger Forms */}
              {passengers.map((passenger, index) => (
                <div key={index} className="bg-white rounded-xl shadow-sm p-6">
                  <h3 className="font-bold text-gray-800 mb-4 flex items-center gap-2">
                    <User className="w-5 h-5 text-orange-500" />
                    Passenger {index + 1} - Seat {passenger.seat_number}
                  </h3>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Full Name *
                      </label>
                      <input
                        type="text"
                        value={passenger.name}
                        onChange={(e) => updatePassenger(index, 'name', e.target.value)}
                        placeholder="Enter full name"
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Age *
                      </label>
                      <input
                        type="number"
                        value={passenger.age}
                        onChange={(e) => updatePassenger(index, 'age', e.target.value)}
                        placeholder="Enter age"
                        min="1"
                        max="120"
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Gender *
                      </label>
                      <select
                        value={passenger.gender}
                        onChange={(e) => updatePassenger(index, 'gender', e.target.value)}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                      >
                        <option value="male">Male</option>
                        <option value="female">Female</option>
                        <option value="other">Other</option>
                      </select>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        ID Type
                      </label>
                      <select
                        value={passenger.id_type}
                        onChange={(e) => updatePassenger(index, 'id_type', e.target.value)}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                      >
                        <option value="aadhar">Aadhar Card</option>
                        <option value="pan">PAN Card</option>
                        <option value="passport">Passport</option>
                        <option value="voter_id">Voter ID</option>
                      </select>
                    </div>
                  </div>
                </div>
              ))}

              {/* Boarding & Dropping Points */}
              <div className="bg-white rounded-xl shadow-sm p-6">
                <h3 className="font-bold text-gray-800 mb-4">Boarding & Dropping Points</h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      <MapPin className="inline w-4 h-4 text-green-500 mr-1" />
                      Boarding Point *
                    </label>
                    <div className="space-y-2">
                      {bus.boarding_points?.map(point => (
                        <label
                          key={point.id}
                          className={`flex items-start gap-3 p-3 border rounded-lg cursor-pointer transition ${
                            boardingPoint?.id === point.id
                              ? 'border-green-500 bg-green-50'
                              : 'border-gray-200 hover:border-green-300'
                          }`}
                        >
                          <input
                            type="radio"
                            name="boarding"
                            checked={boardingPoint?.id === point.id}
                            onChange={() => setBoardingPoint(point)}
                            className="mt-1 text-green-500"
                          />
                          <div>
                            <p className="font-medium text-gray-800">{point.name}</p>
                            <p className="text-sm text-gray-500">{point.time}</p>
                            <p className="text-xs text-gray-400">{point.address}</p>
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      <MapPin className="inline w-4 h-4 text-red-500 mr-1" />
                      Dropping Point *
                    </label>
                    <div className="space-y-2">
                      {bus.dropping_points?.map(point => (
                        <label
                          key={point.id}
                          className={`flex items-start gap-3 p-3 border rounded-lg cursor-pointer transition ${
                            droppingPoint?.id === point.id
                              ? 'border-red-500 bg-red-50'
                              : 'border-gray-200 hover:border-red-300'
                          }`}
                        >
                          <input
                            type="radio"
                            name="dropping"
                            checked={droppingPoint?.id === point.id}
                            onChange={() => setDroppingPoint(point)}
                            className="mt-1 text-red-500"
                          />
                          <div>
                            <p className="font-medium text-gray-800">{point.name}</p>
                            <p className="text-sm text-gray-500">{point.time}</p>
                            <p className="text-xs text-gray-400">{point.address}</p>
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Contact Details */}
              <div className="bg-white rounded-xl shadow-sm p-6">
                <h3 className="font-bold text-gray-800 mb-4">Contact Details</h3>
                <p className="text-sm text-gray-500 mb-4">
                  Ticket details will be sent to this contact
                </p>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      <User className="inline w-4 h-4 mr-1" />
                      Contact Name *
                    </label>
                    <input
                      type="text"
                      value={contactDetails.name}
                      onChange={(e) => setContactDetails(prev => ({ ...prev, name: e.target.value }))}
                      placeholder="Enter contact name"
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                    />
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        <Mail className="inline w-4 h-4 mr-1" />
                        Email *
                      </label>
                      <input
                        type="email"
                        value={contactDetails.email}
                        onChange={(e) => setContactDetails(prev => ({ ...prev, email: e.target.value }))}
                        placeholder="Enter email"
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        <Phone className="inline w-4 h-4 mr-1" />
                        Phone *
                      </label>
                      <input
                        type="tel"
                        value={contactDetails.phone}
                        onChange={(e) => setContactDetails(prev => ({ ...prev, phone: e.target.value }))}
                        placeholder="Enter 10-digit phone"
                        maxLength={10}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Summary Sidebar */}
            <div className="lg:col-span-1">
              <div className="bg-white rounded-xl shadow-sm p-6 sticky top-4">
                <h3 className="font-bold text-gray-800 mb-4">Booking Summary</h3>
                
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">{bus.operator_name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Bus Type</span>
                    <span className="font-medium">{bus.bus_type}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Route</span>
                    <span className="font-medium">{fromCity?.name} → {toCity?.name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Date</span>
                    <span className="font-medium">{formatDate(journeyDate)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Time</span>
                    <span className="font-medium">{bus.departure_time} - {bus.arrival_time}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Seats</span>
                    <span className="font-medium">{selectedSeats.map(s => s.seat_number).join(', ')}</span>
                  </div>
                </div>
                
                <div className="mt-4 pt-4 border-t">
                  <div className="flex items-center justify-between mb-4">
                    <span className="font-medium text-gray-700">Total Fare</span>
                    <span className="text-2xl font-bold text-orange-600">
                      ₹{totalPrice.toFixed(0)}
                    </span>
                  </div>
                </div>

                <div className="space-y-3">
                  <button
                    onClick={proceedToPayment}
                    className="w-full py-3 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition font-medium"
                  >
                    Proceed to Payment
                  </button>
                  <button
                    onClick={() => setStep(1)}
                    className="w-full py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition"
                  >
                    Back to Seats
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Payment */}
        {step === 3 && (
          <div className="max-w-2xl mx-auto">
            <div className="bg-white rounded-xl shadow-sm p-8">
              <h3 className="font-bold text-xl text-gray-800 mb-6 text-center">Payment</h3>
              
              {/* Mock Payment Options */}
              <div className="space-y-4 mb-8">
                <label className="flex items-center gap-4 p-4 border-2 border-orange-500 rounded-xl cursor-pointer bg-orange-50">
                  <input type="radio" name="payment" defaultChecked className="text-orange-500" />
                  <CreditCard className="w-6 h-6 text-orange-500" />
                  <div>
                    <p className="font-medium">Mock Payment (Demo)</p>
                    <p className="text-sm text-gray-500">Instant confirmation</p>
                  </div>
                </label>
              </div>

              {/* Final Summary */}
              <div className="bg-gray-50 rounded-lg p-4 mb-6">
                <h4 className="font-medium text-gray-800 mb-3">Final Summary</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Base Fare ({selectedSeats.length} seats)</span>
                    <span>₹{totalPrice.toFixed(0)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Tax & Service Fee</span>
                    <span>₹0</span>
                  </div>
                  <div className="flex justify-between font-bold text-lg pt-2 border-t">
                    <span>Total Amount</span>
                    <span className="text-orange-600">₹{totalPrice.toFixed(0)}</span>
                  </div>
                </div>
              </div>

              {/* Info */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-6 flex items-start gap-2">
                <Info className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-blue-700">
                  This is a demo payment. No actual charges will be made. Click &quot;Pay Now&quot; to complete the booking.
                </p>
              </div>

              {/* Actions */}
              <div className="space-y-3">
                <button
                  onClick={completeBooking}
                  disabled={booking}
                  className="w-full py-4 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-xl hover:from-orange-600 hover:to-red-600 transition font-semibold text-lg disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {booking ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      Pay ₹{totalPrice.toFixed(0)}
                    </>
                  )}
                </button>
                <button
                  onClick={() => setStep(2)}
                  disabled={booking}
                  className="w-full py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition"
                >
                  Back to Details
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default BusBooking;
