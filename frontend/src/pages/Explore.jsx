import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { destinations as mockDestinations, mockWeather } from '../data/mock';
import axios from 'axios';
import { jsPDF } from 'jspdf';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { Card } from '../components/ui/card';
import { slugify } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { MapPin, Cloud, Droplets, Calendar, Activity, X, Search, CheckCircle, Users, IndianRupee } from 'lucide-react';
import { MessageCircle } from 'lucide-react';

const Explore = () => {
  const navigate = useNavigate();
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [selectedDestination, setSelectedDestination] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isBookingModalOpen, setIsBookingModalOpen] = useState(false);
  const [isConfirmationModalOpen, setIsConfirmationModalOpen] = useState(false);
  const [destinations, setDestinations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [bookingData, setBookingData] = useState({
    destination: '',
    startDate: null,
    endDate: null,
    travelers: 1,
    budgetRange: ''
  });
  const [confirmedBooking, setConfirmedBooking] = useState(null);
  const [bookingLoading, setBookingLoading] = useState(false);

  const categories = ['All', 'Beach', 'Heritage'];

  useEffect(() => {
    const fetchDestinations = async () => {
      try {
        const response = await axios.get('/api/destinations');
        setDestinations(response.data);
      } catch (error) {
        console.error('Error fetching destinations:', error);
        // Fallback to mock data
        setDestinations(mockDestinations);
      } finally {
        setLoading(false);
      }
    };

    fetchDestinations();
  }, []);

  const filteredDestinations = destinations.filter((dest) => {
    const matchesCategory = selectedCategory === 'All' || dest.category === selectedCategory;
    const matchesSearch = dest.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         dest.shortDescription.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         dest.attractions.some(attr => attr.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesCategory && matchesSearch;
  });

  const openModal = (destination) => {
    setSelectedDestination(destination);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setTimeout(() => setSelectedDestination(null), 300);
  };

  const openBookingModal = (destination) => {
    setBookingData({
      destination: destination.name,
      startDate: null,
      endDate: null,
      travelers: 1,
      budgetRange: ''
    });
    setSelectedDestination(destination);
    setIsBookingModalOpen(true);
    setIsModalOpen(false);
  };

  const closeBookingModal = () => {
    setIsBookingModalOpen(false);
  };

  const budgetRanges = [
    { value: '20k-40k', label: '₹20,000 - ₹40,000', min: 20000, max: 40000 },
    { value: '40k-80k', label: '₹40,000 - ₹80,000', min: 40000, max: 80000 },
    { value: '80k-140k', label: '₹80,000 - ₹1,40,000', min: 80000, max: 140000 }
  ];

  const handleBookingSubmit = async (e) => {
    e.preventDefault();
    
    if (!bookingData.startDate || !bookingData.endDate || !bookingData.budgetRange) {
      alert('Please fill all required fields');
      return;
    }

    setBookingLoading(true);
    try {
      const selectedBudget = budgetRanges.find(r => r.value === bookingData.budgetRange);
      const avgPrice = (selectedBudget.min + selectedBudget.max) / 2;

      const response = await axios.post('/api/bookings', {
        destination: bookingData.destination,
        start_date: bookingData.startDate.toISOString(),
        end_date: bookingData.endDate.toISOString(),
        travelers: bookingData.travelers,
        package_type: selectedBudget.label,
        total_price: avgPrice,
        currency: 'INR'
      });

      // Navigate directly to Payment page with booking info
      setConfirmedBooking(response.data);
      setIsBookingModalOpen(false);
      navigate('/payment', { state: { booking: response.data } });
    } catch (error) {
      console.error('Booking failed:', error);
      alert(error.response?.data?.detail || 'Booking failed. Please try again.');
    } finally {
      setBookingLoading(false);
    }
  };

  const downloadBookingPDF = () => {
    if (!confirmedBooking) return;

    const doc = new jsPDF();
    
    // Header
    doc.setFillColor(0, 119, 182);
    doc.rect(0, 0, 210, 40, 'F');
    doc.setTextColor(255, 255, 255);
    doc.setFontSize(24);
    doc.text('WanderLite', 105, 20, { align: 'center' });
    doc.setFontSize(14);
    doc.text('Booking Confirmation', 105, 30, { align: 'center' });

    // Booking details
    doc.setTextColor(0, 0, 0);
    doc.setFontSize(12);
    let y = 55;

    const details = [
      ['Booking Reference:', confirmedBooking.booking_ref],
      ['Status:', 'CONFIRMED'],
      ['Destination:', confirmedBooking.destination],
      ['Start Date:', new Date(confirmedBooking.start_date).toLocaleDateString() || '-'],
      ['End Date:', new Date(confirmedBooking.end_date).toLocaleDateString() || '-'],
      ['Number of Travelers:', confirmedBooking.travelers.toString()],
      ['Package Type:', confirmedBooking.package_type || 'Standard'],
      ['Total Amount:', `₹${confirmedBooking.total_price.toLocaleString()}`],
      ['Booking Date:', new Date(confirmedBooking.created_at).toLocaleDateString()]
    ];

    details.forEach(([label, value]) => {
      doc.setFont(undefined, 'bold');
      doc.text(label, 20, y);
      doc.setFont(undefined, 'normal');
      doc.text(value, 80, y);
      y += 10;
    });

    // Footer
    y += 20;
    doc.setFontSize(10);
    doc.setTextColor(100, 100, 100);
    doc.text('Thank you for booking with WanderLite!', 105, y, { align: 'center' });
    doc.text('For any queries, contact us at support@wanderlite.com', 105, y + 7, { align: 'center' });

    doc.save(`WanderLite_Booking_${confirmedBooking.booking_ref}.pdf`);
  };

  return (
    <div className="min-h-screen pt-24 pb-16 bg-gradient-to-b from-gray-50 to-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-12 space-y-4">
          <h1 className="text-5xl md:text-6xl font-bold bg-gradient-to-r from-[#0077b6] to-[#48cae4] bg-clip-text text-transparent">
            Explore Destinations
          </h1>
          <p className="text-gray-600 text-lg max-w-2xl mx-auto">
            Discover your next adventure from our handpicked collection of stunning destinations
          </p>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="flex justify-center items-center py-20">
            <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-[#0077b6]"></div>
          </div>
        )}

        {/* Content - only show when not loading */}
        {!loading && (
        <div>
        {/* Search and Filter Bar */}
        <div className="mb-12 space-y-6">
          {/* Search Bar */}
          <div className="flex justify-center">
            <div className="relative w-full max-w-md">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <Input
                type="text"
                placeholder="Search destinations, attractions..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 pr-4 py-3 rounded-full border-2 border-[#0077b6]/20 focus:border-[#0077b6] focus:ring-0"
              />
            </div>
          </div>

          {/* Filter Buttons */}
          <div className="flex flex-wrap justify-center gap-3">
            {categories.map((category) => (
              <Button
                key={category}
                onClick={() => setSelectedCategory(category)}
                variant={selectedCategory === category ? 'default' : 'outline'}
                className={`px-6 py-2 rounded-full font-medium transition-all duration-300 ${
                  selectedCategory === category
                    ? 'bg-gradient-to-r from-[#0077b6] to-[#48cae4] text-white shadow-lg scale-105'
                    : 'border-2 border-[#0077b6] text-[#0077b6] hover:bg-[#0077b6] hover:text-white'
                }`}
              >
                {category}
              </Button>
            ))}
          </div>
        </div>

        {/* Destination Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {filteredDestinations.map((destination) => {
            const weather = mockWeather[destination.name] || { temp: 25, condition: "Pleasant", humidity: 60 };
            const destinationSlug = slugify(destination.name);
            return (
              <Card
                key={destination.id}
                className="overflow-hidden group cursor-pointer border-0 shadow-lg hover:shadow-2xl transition-all duration-300 transform hover:-translate-y-2"
                onClick={() => navigate(`/destination/${destinationSlug}`)}
              >
                <div className="relative h-64 overflow-hidden">
                  <img
                    src={destination.image}
                    alt={destination.name}
                    className="w-full h-full object-cover transform group-hover:scale-110 transition-transform duration-500"
                  />
                  <div className="absolute top-4 right-4">
                    <Badge className="bg-white/95 text-[#0077b6] font-semibold px-3 py-1">
                      {destination.category}
                    </Badge>
                  </div>
                  <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent" />
                </div>
                <div className="p-6 space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-2xl font-bold text-gray-800 mb-1">
                        {destination.name}
                      </h3>
                      <p className="text-gray-600">{destination.shortDescription}</p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between pt-2">
                    <div className="flex items-center space-x-2 text-sm text-gray-500">
                      <Cloud className="w-4 h-4" />
                      <span>
                        {weather.temp}°C · {weather.condition}
                      </span>
                    </div>
                    <Button
                      size="sm"
                      className="bg-gradient-to-r from-[#0077b6] to-[#48cae4] hover:from-[#005f8f] hover:to-[#3ab5d9] text-white rounded-full"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/destination/${destinationSlug}`);
                      }}
                    >
                      Explore
                    </Button>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
        </div>
        )}
      </div>

      {/* Destination Details Modal */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          {selectedDestination && (
            <div className="space-y-6">
              {/* Header Image */}
              <div className="relative -m-6 mb-0 h-64 overflow-hidden rounded-t-lg">
                <img
                  src={selectedDestination.image}
                  alt={selectedDestination.name}
                  className="w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
                <DialogTitle className="absolute bottom-4 left-6 text-3xl font-bold text-white">
                  {selectedDestination.name}
                </DialogTitle>
              </div>

              <DialogDescription className="text-gray-700 text-base leading-relaxed">
                {selectedDestination.description}
              </DialogDescription>

              {/* Weather & Best Time */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card className="p-4 bg-gradient-to-br from-blue-50 to-cyan-50 border-0">
                  <div className="flex items-center space-x-3">
                    <div className="p-2 bg-white rounded-lg">
                      <Cloud className="w-5 h-5 text-[#0077b6]" />
                    </div>
                    <div>
                      <p className="text-sm text-gray-600 font-medium">Current Weather</p>
                      <p className="text-lg font-bold text-gray-800">
                        {mockWeather[selectedDestination.name]?.temp}°C ·{' '}
                        {mockWeather[selectedDestination.name]?.condition}
                      </p>
                    </div>
                  </div>
                </Card>
                <Card className="p-4 bg-gradient-to-br from-green-50 to-emerald-50 border-0">
                  <div className="flex items-center space-x-3">
                    <div className="p-2 bg-white rounded-lg">
                      <Calendar className="w-5 h-5 text-[#0077b6]" />
                    </div>
                    <div>
                      <p className="text-sm text-gray-600 font-medium">Best Time to Visit</p>
                      <p className="text-lg font-bold text-gray-800">
                        {selectedDestination.bestTime}
                      </p>
                    </div>
                  </div>
                </Card>
              </div>

              {/* Top Attractions */}
              <div>
                <div className="flex items-center space-x-2 mb-3">
                  <MapPin className="w-5 h-5 text-[#0077b6]" />
                  <h3 className="text-xl font-bold text-gray-800">Top Attractions</h3>
                </div>
                <div className="flex flex-wrap gap-2">
                  {selectedDestination.attractions.map((attraction, index) => (
                    <Badge
                      key={index}
                      variant="secondary"
                      className="px-3 py-1 bg-gradient-to-r from-[#0077b6]/10 to-[#48cae4]/10 text-[#0077b6] border border-[#0077b6]/20"
                    >
                      {attraction}
                    </Badge>
                  ))}
                </div>
              </div>

              {/* Activities */}
              <div>
                <div className="flex items-center space-x-2 mb-3">
                  <Activity className="w-5 h-5 text-[#0077b6]" />
                  <h3 className="text-xl font-bold text-gray-800">Popular Activities</h3>
                </div>
                <div className="flex flex-wrap gap-2">
                  {selectedDestination.activities.map((activity, index) => (
                    <Badge
                      key={index}
                      variant="outline"
                      className="px-3 py-1 border-[#48cae4] text-[#0077b6]"
                    >
                      {activity}
                    </Badge>
                  ))}
                </div>
              </div>

              {/* Book Now Button */}
              <div className="pt-4 border-t">
                <Button
                  onClick={() => openBookingModal(selectedDestination)}
                  className="w-full h-12 bg-gradient-to-r from-[#0077b6] to-[#48cae4] hover:from-[#005f8f] hover:to-[#3ab5d9] text-white text-lg font-semibold rounded-lg shadow-lg"
                >
                  Book Now
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Booking Form Modal */}
      <Dialog open={isBookingModalOpen} onOpenChange={setIsBookingModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold text-[#0077b6]">Book Your Trip</DialogTitle>
            <DialogDescription>
              Complete the form below to book your adventure
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleBookingSubmit} className="space-y-4 mt-4">
            {/* Destination (Read-only) */}
            <div className="space-y-2">
              <Label className="text-base font-semibold flex items-center gap-2">
                <MapPin className="w-4 h-4 text-[#0077b6]" />
                Destination
              </Label>
              <Input
                value={bookingData.destination}
                readOnly
                className="bg-gray-50 border-2 border-gray-200"
              />
            </div>

            {/* Start Date */}
            <div className="space-y-2">
              <Label className="text-base font-semibold flex items-center gap-2">
                <Calendar className="w-4 h-4 text-[#0077b6]" />
                Start Date *
              </Label>
              <DatePicker
                selected={bookingData.startDate}
                onChange={(date) => setBookingData({ ...bookingData, startDate: date })}
                minDate={new Date()}
                placeholderText="Select start date"
                className="w-full h-10 px-3 border-2 border-gray-200 rounded-md focus:border-[#0077b6] focus:outline-none"
              />
            </div>

            {/* End Date */}
            <div className="space-y-2">
              <Label className="text-base font-semibold flex items-center gap-2">
                <Calendar className="w-4 h-4 text-[#0077b6]" />
                End Date *
              </Label>
              <DatePicker
                selected={bookingData.endDate}
                onChange={(date) => setBookingData({ ...bookingData, endDate: date })}
                minDate={bookingData.startDate || new Date()}
                placeholderText="Select end date"
                className="w-full h-10 px-3 border-2 border-gray-200 rounded-md focus:border-[#0077b6] focus:outline-none"
              />
            </div>

            {/* Number of Travelers */}
            <div className="space-y-2">
              <Label className="text-base font-semibold flex items-center gap-2">
                <Users className="w-4 h-4 text-[#0077b6]" />
                Number of Travelers *
              </Label>
              <Select 
                value={bookingData.travelers.toString()} 
                onValueChange={(val) => setBookingData({ ...bookingData, travelers: parseInt(val) })}
              >
                <SelectTrigger className="border-2 border-gray-200">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[1, 2, 3, 4, 5, 6, 7, 8].map((num) => (
                    <SelectItem key={num} value={num.toString()}>
                      {num} {num === 1 ? 'Traveler' : 'Travelers'}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Budget Range */}
            <div className="space-y-2">
              <Label className="text-base font-semibold flex items-center gap-2">
                <IndianRupee className="w-4 h-4 text-[#0077b6]" />
                Budget Range *
              </Label>
              <Select 
                value={bookingData.budgetRange} 
                onValueChange={(val) => setBookingData({ ...bookingData, budgetRange: val })}
              >
                <SelectTrigger className="border-2 border-gray-200">
                  <SelectValue placeholder="Select budget range" />
                </SelectTrigger>
                <SelectContent>
                  {budgetRanges.map((range) => (
                    <SelectItem key={range.value} value={range.value}>
                      {range.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Submit Button */}
            <div className="pt-4">
              <Button
                type="submit"
                disabled={bookingLoading}
                className="w-full h-12 bg-gradient-to-r from-[#0077b6] to-[#48cae4] hover:from-[#005f8f] hover:to-[#3ab5d9] text-white text-lg font-semibold rounded-lg shadow-lg"
              >
                {bookingLoading ? 'Processing...' : 'Confirm Booking'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Confirmation Modal */}
      <Dialog open={isConfirmationModalOpen} onOpenChange={setIsConfirmationModalOpen}>
        <DialogContent className="max-w-lg">
          <div className="text-center space-y-6">
            {/* Success Icon */}
            <div className="flex justify-center">
              <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center">
                <CheckCircle className="w-12 h-12 text-green-600" />
              </div>
            </div>

            <DialogHeader>
              <DialogTitle className="text-3xl font-bold text-gray-900">
                Booking Confirmed!
              </DialogTitle>
              <DialogDescription className="text-base text-gray-600">
                Your trip has been successfully booked
              </DialogDescription>
            </DialogHeader>

            {confirmedBooking && (
              <div className="bg-gradient-to-br from-blue-50 to-cyan-50 rounded-xl p-6 space-y-4 text-left">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-600 font-medium">Booking ID</p>
                    <p className="text-lg font-bold text-[#0077b6]">{confirmedBooking.booking_ref}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600 font-medium">Status</p>
                    <Badge className="bg-green-100 text-green-700 border-green-200">
                      CONFIRMED
                    </Badge>
                  </div>
                </div>

                <div className="border-t border-gray-200 pt-4 space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Destination:</span>
                    <span className="font-semibold">{confirmedBooking.destination}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Start Date:</span>
                    <span className="font-semibold">
                      {confirmedBooking.start_date ? new Date(confirmedBooking.start_date).toLocaleDateString() : '-'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">End Date:</span>
                    <span className="font-semibold">
                      {confirmedBooking.end_date ? new Date(confirmedBooking.end_date).toLocaleDateString() : '-'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Travelers:</span>
                    <span className="font-semibold">{confirmedBooking.travelers}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Package:</span>
                    <span className="font-semibold">{confirmedBooking.package_type || 'Standard'}</span>
                  </div>
                  <div className="flex justify-between text-lg border-t border-gray-200 pt-3">
                    <span className="text-gray-800 font-bold">Total Amount:</span>
                    <span className="text-[#0077b6] font-bold">
                      ₹{confirmedBooking.total_price.toLocaleString()}
                    </span>
                  </div>
                </div>
              </div>
            )}

            <div className="space-y-3">
              <Button
                onClick={downloadBookingPDF}
                className="w-full h-12 bg-gradient-to-r from-green-600 to-emerald-500 hover:from-green-700 hover:to-emerald-600 text-white font-semibold rounded-lg shadow-lg"
              >
                Download Booking Ticket (PDF)
              </Button>
              <Button
                onClick={() => setIsConfirmationModalOpen(false)}
                variant="outline"
                className="w-full h-12 border-2 border-[#0077b6] text-[#0077b6] hover:bg-[#0077b6] hover:text-white font-semibold rounded-lg"
              >
                Close
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
      {/* Floating AI Assistant Button */}
      <button
        onClick={() => navigate('/assistant')}
        aria-label="Open assistant"
        className="fixed bottom-6 right-6 z-50 rounded-full bg-sky-500 hover:bg-sky-600 text-white shadow-xl p-4"
      >
        <MessageCircle className="w-6 h-6" />
      </button>
    </div>
  );
};

export default Explore;