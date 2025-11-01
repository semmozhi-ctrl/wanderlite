import React, { useState } from 'react';
import { sampleItineraries, destinations, mockCurrencyRates } from '../data/mock';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { MapPin, Calendar, DollarSign, Sparkles, Clock } from 'lucide-react';

const TripPlanner = () => {
  const [destination, setDestination] = useState('');
  const [days, setDays] = useState('');
  const [budget, setBudget] = useState('');
  const [currency, setCurrency] = useState('INR');
  const [generatedPlan, setGeneratedPlan] = useState(null);

  const budgetRanges = [
    { value: 'low', label: 'Budget (Low)', inr: '< ₹15,000' },
    { value: 'medium', label: 'Moderate (Medium)', inr: '₹15,000 - ₹40,000' },
    { value: 'high', label: 'Luxury (High)', inr: '> ₹40,000' }
  ];

  const convertCurrency = (amount, fromCurrency, toCurrency) => {
    if (fromCurrency === toCurrency) return amount;
    const inUSD = amount / mockCurrencyRates[fromCurrency];
    return Math.round(inUSD * mockCurrencyRates[toCurrency]);
  };

  const generateItinerary = async () => {
    if (!destination || !budget) {
      alert('Please select a destination and budget');
      return;
    }

    const destKey = destination.toLowerCase().split(',')[0];
    const itineraries = sampleItineraries[destKey] || sampleItineraries['default'];
    const plan = itineraries.budget[budget];

    const convertedTotal = convertCurrency(plan.total, 'INR', currency);

    const tripData = {
      ...plan,
      destination,
      budget,
      currency,
      convertedTotal
    };

    setGeneratedPlan(tripData);

    // Save to backend if user is authenticated
    try {
      const base = process.env.REACT_APP_BACKEND_URL || '';
      const response = await fetch(`${base}/api/trips`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          destination,
          days: plan.days,
          budget,
          currency,
          itinerary: plan.itinerary
        })
      });

      if (response.ok) {
        console.log('Trip saved successfully');
      }
    } catch (error) {
      console.error('Error saving trip:', error);
    }
  };

  const getCurrencySymbol = (curr) => {
    const symbols = {
      USD: '$',
      EUR: '€',
      GBP: '£',
      INR: '₹',
      JPY: '¥',
      AED: 'AED'
    };
    return symbols[curr] || curr;
  };

  return (
    <div className="min-h-screen pt-24 pb-16 bg-gradient-to-b from-gray-50 to-white">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-12 space-y-4">
          <h1 className="text-5xl md:text-6xl font-bold bg-gradient-to-r from-[#0077b6] to-[#48cae4] bg-clip-text text-transparent">
            Trip Planner
          </h1>
          <p className="text-gray-600 text-lg">
            Create your personalized travel itinerary in seconds
          </p>
        </div>

        {/* Planning Form */}
        <Card className="p-8 shadow-xl border-0 bg-white mb-8">
          <div className="space-y-6">
            {/* Destination Selection */}
            <div className="space-y-2">
              <Label className="text-base font-semibold text-gray-700 flex items-center space-x-2">
                <MapPin className="w-5 h-5 text-[#0077b6]" />
                <span>Select Destination</span>
              </Label>
              <Select value={destination} onValueChange={setDestination}>
                <SelectTrigger className="w-full h-12 border-2 border-gray-200 focus:border-[#0077b6]">
                  <SelectValue placeholder="Choose your destination" />
                </SelectTrigger>
                <SelectContent>
                  {destinations.map((dest) => (
                    <SelectItem key={dest.id} value={dest.name}>
                      {dest.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Budget Selection */}
            <div className="space-y-2">
              <Label className="text-base font-semibold text-gray-700 flex items-center space-x-2">
                <DollarSign className="w-5 h-5 text-[#0077b6]" />
                <span>Budget Range</span>
              </Label>
              <Select value={budget} onValueChange={setBudget}>
                <SelectTrigger className="w-full h-12 border-2 border-gray-200 focus:border-[#0077b6]">
                  <SelectValue placeholder="Select your budget" />
                </SelectTrigger>
                <SelectContent>
                  {budgetRanges.map((range) => (
                    <SelectItem key={range.value} value={range.value}>
                      {range.label} - {range.inr}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Currency Selection */}
            <div className="space-y-2">
              <Label className="text-base font-semibold text-gray-700 flex items-center space-x-2">
                <DollarSign className="w-5 h-5 text-[#0077b6]" />
                <span>Preferred Currency</span>
              </Label>
              <Select value={currency} onValueChange={setCurrency}>
                <SelectTrigger className="w-full h-12 border-2 border-gray-200 focus:border-[#0077b6]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.keys(mockCurrencyRates).map((curr) => (
                    <SelectItem key={curr} value={curr}>
                      {curr} - {getCurrencySymbol(curr)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Generate Button */}
            <Button
              onClick={generateItinerary}
              className="w-full h-12 bg-gradient-to-r from-[#0077b6] to-[#48cae4] hover:from-[#005f8f] hover:to-[#3ab5d9] text-white text-lg font-semibold rounded-lg shadow-lg transform transition-all duration-300 hover:scale-[1.02]"
            >
              <Sparkles className="w-5 h-5 mr-2" />
              Generate Itinerary
            </Button>
          </div>
        </Card>

        {/* Generated Itinerary */}
        {generatedPlan && (
          <Card className="p-8 shadow-xl border-0 bg-gradient-to-br from-white to-blue-50 animate-fade-in">
            <div className="space-y-6">
              {/* Header */}
              <div className="border-b-2 border-[#0077b6]/20 pb-4">
                <h2 className="text-3xl font-bold text-gray-800 mb-2">
                  Your {generatedPlan.days}-Day Trip to {generatedPlan.destination}
                </h2>
                <div className="flex items-center space-x-4 text-gray-600">
                  <div className="flex items-center space-x-2">
                    <Clock className="w-5 h-5 text-[#0077b6]" />
                    <span className="font-semibold">{generatedPlan.days} Days</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <DollarSign className="w-5 h-5 text-[#0077b6]" />
                    <span className="font-semibold">
                      {getCurrencySymbol(generatedPlan.currency)}
                      {generatedPlan.convertedTotal.toLocaleString()}
                    </span>
                  </div>
                </div>
              </div>

              {/* Daily Itinerary */}
              <div className="space-y-4">
                <h3 className="text-xl font-bold text-gray-800 flex items-center space-x-2">
                  <Calendar className="w-5 h-5 text-[#0077b6]" />
                  <span>Day-by-Day Plan</span>
                </h3>
                {generatedPlan.itinerary.map((dayPlan, index) => (
                  <Card
                    key={index}
                    className="p-5 bg-white border-l-4 border-[#0077b6] hover:shadow-lg transition-shadow duration-300"
                  >
                    <div className="flex items-start space-x-4">
                      <div className="flex-shrink-0 w-12 h-12 bg-gradient-to-r from-[#0077b6] to-[#48cae4] rounded-full flex items-center justify-center">
                        <span className="text-white font-bold text-lg">{dayPlan.day}</span>
                      </div>
                      <div className="flex-1">
                        <h4 className="text-lg font-semibold text-gray-800 mb-2">
                          Day {dayPlan.day}
                        </h4>
                        <p className="text-gray-600 leading-relaxed">{dayPlan.activities}</p>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>

              {/* Note */}
              <div className="bg-blue-50 border-l-4 border-[#0077b6] p-4 rounded">
                <p className="text-sm text-gray-700">
                  <span className="font-semibold">Note:</span> This is a sample itinerary based
                  on your preferences. Actual costs may vary. Weather and currency data are
                  currently mocked and will be updated with real-time data soon.
                </p>
              </div>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
};

export default TripPlanner;