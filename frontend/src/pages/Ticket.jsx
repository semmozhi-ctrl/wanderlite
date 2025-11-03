import React, { useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';

const LabelVal = ({ label, value }) => (
  <div className="flex items-center justify-between">
    <span className="text-gray-600 text-sm">{label}</span>
    <span className="font-semibold">{value}</span>
  </div>
);

const Ticket = () => {
  const navigate = useNavigate();
  const { state, search } = useLocation();
  const params = useMemo(() => new URLSearchParams(search), [search]);
  const bookingRef = state?.bookingRef || params.get('pnr') || state?.booking?.booking_ref || 'WL';
  const serviceType = state?.serviceType || params.get('stype') || 'Flight';
  const flight = {
    airline: state?.serviceDetails?.airline || params.get('airline') || 'WanderLite',
    flight_number: state?.serviceDetails?.flight_number || params.get('fn') || 'ABC1285',
    origin: state?.serviceDetails?.origin || params.get('o') || '',
    destination: state?.serviceDetails?.destination || params.get('d') || '',
    departure_time: state?.serviceDetails?.departure_time || params.get('dt') || '',
    duration: state?.serviceDetails?.duration || params.get('dur') || '',
    gate: state?.serviceDetails?.gate || params.get('gate') || '15',
    terminal: state?.serviceDetails?.terminal || params.get('term') || 'T1',
    class: state?.serviceDetails?.class || params.get('class') || 'ECONOMY',
  };
  const passenger = {
    fullName: state?.payer?.fullName || params.get('name') || 'Passenger',
    seatNumber: state?.payer?.seatNumber || params.get('seat') || '11A',
  };

  // Derive fields consistent with the sample boarding pass image
  const airline = flight.airline || 'WanderLite';
  const flightNumber = flight.flight_number || 'ABC1285';
  const origin = (flight.origin || '').toUpperCase();
  const destination = (flight.destination || '').toUpperCase();
  const depTime = flight.departure_time
    ? new Date(flight.departure_time).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
    : '10:20';
  const seat = passenger.seatNumber || '11A';
  const gate = flight.gate || '15';
  const terminal = flight.terminal || 'T1';
  const group = flight.boarding_group || 'B';
  const zone = flight.boarding_zone || '2';
  const dateStr = flight.departure_time
    ? new Date(flight.departure_time).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' }).toUpperCase()
    : '06JUN';

  const fullName = passenger.fullName || passenger.full_name || 'Passenger';
  const eTicket = (bookingRef || '').slice(0, 6).toUpperCase();

  // Build a shareable deep link the QR will point to
  const qrLink = useMemo(() => {
    // Resolve a shareable base URL: env var > window override > localStorage hint > current origin
    let baseUrl = process.env.REACT_APP_PUBLIC_BASE_URL || (window.WANDERLITE_PUBLIC_BASE_URL || '').toString();
    if (!baseUrl) {
      const stored = localStorage.getItem('wanderlite_base_url');
      if (stored) baseUrl = stored;
    }
    if (!baseUrl) baseUrl = window.location.origin;

    const url = new URL(baseUrl.replace(/\/$/, '') + '/ticket');
    url.searchParams.set('pnr', bookingRef);
    url.searchParams.set('stype', serviceType);
    url.searchParams.set('airline', airline);
    url.searchParams.set('fn', flightNumber);
    if (origin) url.searchParams.set('o', origin);
    if (destination) url.searchParams.set('d', destination);
    if (flight.departure_time) url.searchParams.set('dt', flight.departure_time);
    if (flight.duration) url.searchParams.set('dur', flight.duration);
    url.searchParams.set('gate', gate);
    url.searchParams.set('term', terminal);
    url.searchParams.set('class', flight.class);
    url.searchParams.set('name', fullName);
    url.searchParams.set('seat', seat);
    return url.toString();
  }, [bookingRef, serviceType, airline, flightNumber, origin, destination, flight.departure_time, flight.duration, gate, terminal, flight.class, fullName, seat]);

  const updatePublicBaseUrl = () => {
    const current = localStorage.getItem('wanderlite_base_url') || '';
    const val = window.prompt('Enter public URL to use in QR (e.g., http://10.40.157.90:3001)', current);
    if (val) {
      localStorage.setItem('wanderlite_base_url', val);
      window.location.reload();
    }
  };

  return (
    <div className="min-h-screen pt-24 pb-16 bg-gradient-to-b from-gray-50 to-white">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">E‑Ticket / Boarding Pass</h1>
          <p className="text-gray-600">PNR: {bookingRef}</p>
        </div>

        <Card className="p-0 overflow-hidden shadow-lg">
          {/* Top banner - website sky blue */}
          <div className="bg-sky-500 text-white px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="font-extrabold tracking-wide text-xl">WanderLite</div>
              <div className="text-white/80 text-sm hidden md:block">BOARDING PASS</div>
            </div>
            <div className="text-xs">E‑TICKET {eTicket}</div>
          </div>

          {/* Body */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-0">
            {/* Left – barcode stub */}
            <div className="p-6 border-r md:block">
              {/* Mock barcode (offline) */}
              <div className="h-28 w-40 bg-white border border-black flex items-end gap-1 p-1 mb-4">
                {Array.from({ length: 30 }).map((_, i) => (
                  <div key={i} className={`${i % 2 === 0 ? 'bg-black' : 'bg-white'} h-full`} style={{ width: (i % 5 === 0 ? 3 : 2) }} />
                ))}
              </div>
              {/* Real-time QR Code (uses external image generator for simplicity) */}
              <div className="mb-4">
                <img
                  src={`https://api.qrserver.com/v1/create-qr-code/?size=140x140&data=${encodeURIComponent(qrLink)}`}
                  alt="Ticket QR"
                  className="border border-gray-300"
                />
                <div className="text-xs text-gray-600 mt-1">Scan to open this ticket</div>
              </div>
              <div className="space-y-2">
                <LabelVal label="FLIGHT" value={flightNumber} />
                <LabelVal label="AIRLINE" value={airline.toUpperCase()} />
                <LabelVal label="BOARDING" value={depTime} />
                <LabelVal label="GATE" value={gate} />
                <LabelVal label="TERMINAL" value={terminal} />
                <LabelVal label="SEAT" value={seat} />
                <LabelVal label="ZONE / GROUP" value={`${zone} / ${group}`} />
              </div>
            </div>

            {/* Middle – passenger and route */}
            <div className="p-6 md:col-span-2">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <LabelVal label="PASSENGER NAME" value={fullName.toUpperCase()} />
                  <LabelVal label="CLASS" value={(flight.class || 'ECONOMY').toUpperCase()} />
                </div>
                <div className="space-y-2">
                  <LabelVal label="FROM → TO" value={`${origin || '—'} → ${destination || '—'}`} />
                  <LabelVal label="DATE" value={dateStr} />
                </div>
              </div>

              {/* Route visual */}
              <div className="mt-6 flex items-center gap-3">
                <div className="text-2xl font-bold">{origin || 'ORG'}</div>
                <div className="flex-1 h-px bg-sky-500" />
                <div className="text-xl">✈</div>
                <div className="flex-1 h-px bg-sky-500" />
                <div className="text-2xl font-bold">{destination || 'DST'}</div>
              </div>

              <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <LabelVal label="PNR" value={bookingRef} />
                <LabelVal label="E‑TICKET" value={eTicket} />
                <LabelVal label="DURATION" value={flight.duration || '—'} />
                <LabelVal label="STATUS" value="CONFIRMED" />
              </div>

              <div className="mt-8 flex items-center justify-between text-gray-700">
                <div className="text-xs">Please arrive 2 hours before departure. Carry a valid photo ID.</div>
                <div className="text-xs">© WanderLite</div>
              </div>
            </div>
          </div>
        </Card>

        <div className="mt-6 flex gap-3">
          {state?.ticketUrl && (
            <Button asChild>
              <a href={`/${state.ticketUrl}`} target="_blank" rel="noreferrer">Download PDF Ticket</a>
            </Button>
          )}
          <Button variant="outline" onClick={() => navigate('/trip-history')}>Trip History</Button>
          <Button variant="outline" onClick={() => navigate('/explore')}>Explore</Button>
          {(['localhost','127.0.0.1'].includes(window.location.hostname)) && (
            <Button variant="outline" onClick={updatePublicBaseUrl}>Set Share URL</Button>
          )}
        </div>
      </div>
    </div>
  );
};

export default Ticket;


