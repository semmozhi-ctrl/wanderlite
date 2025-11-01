import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Switch } from '../components/ui/switch';
import { useAuth } from '../contexts/AuthContext';
import { Camera, Save, X, Edit3, Trash2 } from 'lucide-react';

const Profile = () => {
  const { token, logout } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [trips, setTrips] = useState([]);
  const [editMode, setEditMode] = useState(false);
  const [preview, setPreview] = useState(null);
  const [profile, setProfile] = useState({
    id: '', email: '', username: '', name: '', phone: '', profile_image: '',
    favorite_travel_type: '', preferred_budget_range: '', climate_preference: '',
    food_preference: '', language_preference: '', notifications_enabled: 1,
  });

  const travelTypes = ['Adventure', 'Beach', 'Heritage', 'Urban', 'Nature'];
  const budgetRanges = ['₹20k–₹50k', '₹50k–₹100k', '₹100k–₹200k'];
  const climates = ['Cool', 'Warm', 'Moderate'];
  const foods = ['Veg', 'Non-Veg', 'Vegan'];
  const languages = ['English', 'Hindi', 'Tamil', 'Telugu', 'Malayalam'];

  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  useEffect(() => {
    const init = async () => {
      try {
        const me = await axios.get('/api/auth/me', { headers });
        setProfile({ ...profile, ...me.data });
        const t = await axios.get('/api/trips', { headers });
        setTrips(t.data || []);
      } catch (e) {
        console.error('Failed to load profile', e);
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  const onFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    // preview
    const reader = new FileReader();
    reader.onload = () => setPreview(reader.result);
    reader.readAsDataURL(file);
    // upload
    const form = new FormData();
    form.append('file', file);
    try {
      const resp = await axios.post('/api/profile/avatar', form, {
        headers: { ...headers, 'Content-Type': 'multipart/form-data' },
      });
      setProfile((p) => ({ ...p, profile_image: resp.data.image_url }));
    } catch (err) {
      console.error('Image upload failed', err);
      alert('Image upload failed');
    }
  };

  const saveProfile = async () => {
    setSaving(true);
    try {
      const payload = {
        name: profile.name,
        username: profile.username,
        phone: profile.phone,
        favorite_travel_type: profile.favorite_travel_type,
        preferred_budget_range: profile.preferred_budget_range,
        climate_preference: profile.climate_preference,
        food_preference: profile.food_preference,
        language_preference: profile.language_preference,
        notifications_enabled: !!profile.notifications_enabled,
      };
      const resp = await axios.put('/api/profile', payload, { headers });
      setProfile((p) => ({ ...p, ...resp.data }));
      setEditMode(false);
    } catch (e) {
      console.error('Failed to save profile', e);
      alert('Failed to save profile');
    } finally {
      setSaving(false);
    }
  };

  const deleteAccount = async () => {
    if (!window.confirm('Are you sure you want to delete your account? This cannot be undone.')) return;
    try {
      await axios.delete('/api/auth/account', { headers });
      logout();
    } catch (e) {
      console.error('Delete account failed', e);
      alert('Delete account failed');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen pt-24 pb-16 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#31A8E0]"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen pt-24 pb-16 bg-gradient-to-b from-[#E1F0FD] to-white">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
        {/* Profile Overview */}
        <Card className="p-6 md:p-8 shadow-xl border-0 bg-white">
          <div className="flex flex-col md:flex-row items-start md:items-center gap-6">
            <div className="relative w-32 h-32">
              <img
                src={preview || profile.profile_image || 'https://via.placeholder.com/150'}
                alt="Profile"
                className="w-32 h-32 rounded-full object-cover border-4 border-white shadow-md"
              />
              <label className="absolute bottom-0 right-0 bg-[#31A8E0] hover:bg-[#2492c7] text-white p-2 rounded-full cursor-pointer shadow">
                <Camera className="w-4 h-4" />
                <input type="file" accept="image/*" className="hidden" onChange={onFileChange} />
              </label>
            </div>
            <div className="flex-1 w-full space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label>Name</Label>
                  <Input value={profile.name || ''} disabled={!editMode} onChange={(e) => setProfile({ ...profile, name: e.target.value })} />
                </div>
                <div>
                  <Label>Username</Label>
                  <Input value={profile.username || ''} disabled={!editMode} onChange={(e) => setProfile({ ...profile, username: e.target.value })} />
                </div>
                <div>
                  <Label>Email</Label>
                  <Input value={profile.email || ''} disabled readOnly />
                </div>
                <div>
                  <Label>Phone Number</Label>
                  <Input value={profile.phone || ''} disabled={!editMode} onChange={(e) => setProfile({ ...profile, phone: e.target.value })} />
                </div>
              </div>
              <div className="pt-2">
                {!editMode ? (
                  <Button onClick={() => setEditMode(true)} className="bg-[#31A8E0] text-white">
                    <Edit3 className="w-4 h-4 mr-2" /> Edit Profile
                  </Button>
                ) : (
                  <div className="flex gap-3">
                    <Button onClick={saveProfile} disabled={saving} className="bg-[#31A8E0] text-white">
                      <Save className="w-4 h-4 mr-2" /> {saving ? 'Saving...' : 'Save Changes'}
                    </Button>
                    <Button variant="outline" onClick={() => { setEditMode(false); setPreview(null); }}>
                      <X className="w-4 h-4 mr-2" /> Cancel
                    </Button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </Card>

        {/* Travel Preferences */}
        <Card className="p-6 md:p-8 shadow-xl border-0 bg-white">
          <h2 className="text-2xl font-bold text-[#31A8E0] mb-6">Travel Preferences</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <Label>Favorite Travel Type</Label>
              <Select value={profile.favorite_travel_type || ''} onValueChange={(v) => setProfile({ ...profile, favorite_travel_type: v })}>
                <SelectTrigger className="h-12">
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  {travelTypes.map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Preferred Budget Range</Label>
              <Select value={profile.preferred_budget_range || ''} onValueChange={(v) => setProfile({ ...profile, preferred_budget_range: v })}>
                <SelectTrigger className="h-12">
                  <SelectValue placeholder="Select budget" />
                </SelectTrigger>
                <SelectContent>
                  {budgetRanges.map(b => <SelectItem key={b} value={b}>{b}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Climate Preference</Label>
              <Select value={profile.climate_preference || ''} onValueChange={(v) => setProfile({ ...profile, climate_preference: v })}>
                <SelectTrigger className="h-12">
                  <SelectValue placeholder="Select climate" />
                </SelectTrigger>
                <SelectContent>
                  {climates.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Food Preference</Label>
              <Select value={profile.food_preference || ''} onValueChange={(v) => setProfile({ ...profile, food_preference: v })}>
                <SelectTrigger className="h-12">
                  <SelectValue placeholder="Select food" />
                </SelectTrigger>
                <SelectContent>
                  {foods.map(f => <SelectItem key={f} value={f}>{f}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Language Preference</Label>
              <Select value={profile.language_preference || ''} onValueChange={(v) => setProfile({ ...profile, language_preference: v })}>
                <SelectTrigger className="h-12">
                  <SelectValue placeholder="Select language" />
                </SelectTrigger>
                <SelectContent>
                  {languages.map(l => <SelectItem key={l} value={l}>{l}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
        </Card>

        {/* Saved Trips */}
        <Card className="p-6 md:p-8 shadow-xl border-0 bg-white">
          <h2 className="text-2xl font-bold text-[#31A8E0] mb-6">Your Trips</h2>
          {trips.length === 0 ? (
            <div className="text-gray-600">No trips yet. Plan your first adventure!</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {trips.map((trip) => (
                <div key={trip.id} className="rounded-xl overflow-hidden bg-white shadow hover:shadow-lg transform hover:scale-[1.01] transition">
                  <div className="h-40 bg-gray-200">
                    {/* If you store images in trip.images, you can show the first one */}
                    {trip.images && trip.images.length > 0 ? (
                      <img src={trip.images[0]} alt={trip.destination} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-gray-500">{trip.destination}</div>
                    )}
                  </div>
                  <div className="p-4">
                    <div className="font-semibold text-gray-800">{trip.destination}</div>
                    <div className="text-sm text-gray-600">{trip.days} days • {trip.budget}</div>
                    <div className="pt-2">
                      <Button variant="outline" className="text-[#31A8E0] border-[#31A8E0]">View Details</Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Account Settings */}
        <Card className="p-6 md:p-8 shadow-xl border-0 bg-white">
          <h2 className="text-2xl font-bold text-[#31A8E0] mb-6">Account Settings</h2>
          <div className="flex flex-col md:flex-row md:items-center gap-4 justify-between">
            <div className="flex items-center gap-3">
              <Switch checked={!!profile.notifications_enabled} onCheckedChange={(v) => setProfile({ ...profile, notifications_enabled: v ? 1 : 0 })} />
              <span className="text-gray-700">Email Notifications</span>
            </div>
            <div className="flex items-center gap-3">
              <Button variant="outline" onClick={() => alert('Open change password UI')}>Change Password</Button>
              <Button variant="destructive" onClick={deleteAccount} className="bg-red-600 text-white hover:bg-red-700">
                <Trash2 className="w-4 h-4 mr-2" /> Delete Account
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default Profile;
