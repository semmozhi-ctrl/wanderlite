import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Download, MapPin, Calendar, Users, IndianRupee, CreditCard } from 'lucide-react';

const MyReceipts = () => {
  const navigate = useNavigate();
  const [receipts, setReceipts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchReceipts = async () => {
      try {
        const response = await api.get('/api/receipts');
        setReceipts(response.data || []);
      } catch (error) {
        console.error('Failed to fetch receipts:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchReceipts();
  }, []);

  return (
    <div className="min-h-screen pt-24 pb-16 bg-gradient-to-b from-gray-50 to-white">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-[#0077b6] to-[#48cae4] bg-clip-text text-transparent mb-2">
            My Receipts
          </h1>
          <p className="text-gray-600">View and download your payment receipts</p>
        </div>

        {loading && (
          <div className="flex justify-center items-center py-20">
            <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-[#0077b6]"></div>
          </div>
        )}

        {!loading && receipts.length === 0 && (
          <Card className="p-12 text-center">
            <p className="text-gray-600 text-lg mb-4">No receipts found</p>
            <Button onClick={() => navigate('/explore')} className="bg-gradient-to-r from-[#0077b6] to-[#48cae4]">
              Explore Destinations
            </Button>
          </Card>
        )}

        {!loading && receipts.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {receipts.map((receipt) => (
              <Card key={receipt.id} className="p-6 hover:shadow-lg transition-shadow">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="text-xl font-bold text-gray-900">
                      {receipt.destination || 'Travel Booking'}
                    </h3>
                    <Badge className="mt-2 bg-blue-100 text-blue-700 border-blue-200">
                      {receipt.booking_ref}
                    </Badge>
                  </div>
                  <Button
                    size="sm"
                    asChild
                    className="bg-gradient-to-r from-green-600 to-emerald-500 hover:from-green-700 hover:to-emerald-600"
                  >
                    <a href={receipt.receipt_url} target="_blank" rel="noreferrer">
                      <Download className="w-4 h-4 mr-2" />
                      PDF
                    </a>
                  </Button>
                </div>

                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-gray-700">
                    <CreditCard className="w-4 h-4 text-[#0077b6]" />
                    <span className="text-sm font-semibold">{receipt.full_name}</span>
                  </div>

                  <div className="flex items-center gap-2 text-gray-700">
                    <span className="text-sm">{receipt.email}</span>
                  </div>

                  {receipt.destination && (
                    <div className="flex items-center gap-2 text-gray-700">
                      <MapPin className="w-4 h-4 text-[#0077b6]" />
                      <span className="text-sm">{receipt.destination}</span>
                    </div>
                  )}

                  {receipt.start_date && receipt.end_date && (
                    <div className="flex items-center gap-2 text-gray-700">
                      <Calendar className="w-4 h-4 text-[#0077b6]" />
                      <span className="text-sm">
                        {new Date(receipt.start_date).toLocaleDateString()} to{' '}
                        {new Date(receipt.end_date).toLocaleDateString()}
                      </span>
                    </div>
                  )}

                  {receipt.travelers && (
                    <div className="flex items-center gap-2 text-gray-700">
                      <Users className="w-4 h-4 text-[#0077b6]" />
                      <span className="text-sm">{receipt.travelers} {receipt.travelers === 1 ? 'Traveler' : 'Travelers'}</span>
                    </div>
                  )}

                  <div className="flex items-center gap-2 text-gray-700">
                    <span className="text-sm">Payment: {receipt.payment_method}</span>
                  </div>

                  <div className="flex items-center gap-2 text-gray-700 pt-2 border-t">
                    <IndianRupee className="w-4 h-4 text-[#0077b6]" />
                    <span className="text-lg font-bold text-[#0077b6]">
                      ₹{Number(receipt.amount || 0).toLocaleString()}
                    </span>
                  </div>

                  <div className="text-xs text-gray-500 pt-2">
                    Paid on {new Date(receipt.created_at).toLocaleDateString()}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default MyReceipts;
