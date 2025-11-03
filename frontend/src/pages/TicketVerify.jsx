import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';

const Field = ({ label, value }) => (
  <div className="flex items-center justify-between">
    <span className="text-gray-600 text-sm">{label}</span>
    <span className="font-semibold">{value ?? '—'}</span>
  </div>
);

const TicketVerify = () => {
  const { search } = useLocation();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);

  useEffect(() => {
    const params = new URLSearchParams(search);
    const token = params.get('token');
    if (!token) {
      setError('Missing token');
      setLoading(false);
      return;
    }
    (async () => {
      try {
        const res = await fetch(`/api/tickets/verify?token=${encodeURIComponent(token)}`);
        if (!res.ok) throw new Error(await res.text());
        const json = await res.json();
        setData(json);
      } catch (e) {
        setError('Verification failed');
      } finally {
        setLoading(false);
      }
    })();
  }, [search]);

  return (
    <div className="min-h-screen pt-24 pb-16 bg-gradient-to-b from-gray-50 to-white">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 className="text-3xl font-bold mb-4">Ticket Verification</h1>
        {loading && <p>Verifying…</p>}
        {error && <p className="text-red-600">{error}</p>}
        {data && (
          <Card className="p-6 space-y-4">
            <Field label="Status" value={data.status?.toUpperCase()} />
            <Field label="Booking Ref" value={data.booking_ref} />
            <Field label="Service Type" value={data.service_type} />
            {data.service && (
              <>
                <Field label="Airline/Name" value={data.service.airline || data.service.name} />
                <Field label="Flight No." value={data.service.flight_number} />
                <Field label="From → To" value={data.service.origin && data.service.destination ? `${data.service.origin} → ${data.service.destination}` : undefined} />
                <Field label="Departure" value={data.service.departure_time} />
              </>
            )}
            {data.receipt && (
              <>
                <Field label="Passenger" value={data.receipt.full_name} />
                <Field label="Email" value={data.receipt.email} />
                <Field label="Phone" value={data.receipt.phone} />
                <Field label="Destination" value={data.receipt.destination} />
                <Field label="Dates" value={data.receipt.start_date && data.receipt.end_date ? `${data.receipt.start_date} → ${data.receipt.end_date}` : undefined} />
                <Field label="Travelers" value={data.receipt.travelers} />
                <Field label="Amount" value={data.receipt.amount} />
              </>
            )}
            <div className="pt-2 flex gap-3">
              <Button variant="outline" onClick={() => navigate('/explore')}>Explore</Button>
              <Button onClick={() => navigate('/trip-history')}>Trip History</Button>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
};

export default TicketVerify;


