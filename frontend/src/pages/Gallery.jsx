import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';

const Gallery = () => {
  const [posts, setPosts] = useState([]);
  const [file, setFile] = useState(null);
  const [caption, setCaption] = useState('');
  const [location, setLocation] = useState('');
  const [uploading, setUploading] = useState(false);

  const fetchPosts = async () => {
    try {
      const res = await axios.get('/api/gallery');
      setPosts(res.data || []);
    } catch (e) {
      console.error('Failed to load gallery', e);
    }
  };

  useEffect(() => {
    fetchPosts();
  }, []);

  const onUpload = async (e) => {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    try {
      const form = new FormData();
      form.append('file', file);
      if (caption) form.append('caption', caption);
      if (location) form.append('location', location);
      form.append('tags', JSON.stringify([]));
      await axios.post('/api/gallery', form, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setCaption('');
      setLocation('');
      setFile(null);
      await fetchPosts();
    } catch (e) {
      console.error('Upload failed', e);
      alert('Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const onLike = async (id) => {
    try {
      const res = await axios.post(`/api/gallery/${id}/like`);
      setPosts((prev) => prev.map((p) => (p.id === id ? { ...p, likes: res.data.likes } : p)));
    } catch (e) {
      console.error('Like failed', e);
    }
  };

  return (
    <div className="min-h-screen pt-24 pb-16 bg-gradient-to-b from-gray-50 to-white">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-[#0077b6] to-[#48cae4] bg-clip-text text-transparent">Travel Moments</h1>
          <p className="text-gray-600">Share photos from your adventures</p>
        </div>

        <Card className="p-6 mb-10">
          <form onSubmit={onUpload} className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
            <div className="md:col-span-2 space-y-2">
              <Label>Image</Label>
              <Input type="file" accept="image/*" onChange={(e) => setFile(e.target.files?.[0] || null)} />
            </div>
            <div className="space-y-2">
              <Label>Caption</Label>
              <Input value={caption} onChange={(e) => setCaption(e.target.value)} placeholder="Say something..." />
            </div>
            <div className="space-y-2">
              <Label>Location</Label>
              <Input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="City, Country" />
            </div>
            <div className="md:col-span-4">
              <Button disabled={uploading || !file} className="w-full md:w-auto">
                {uploading ? 'Uploading...' : 'Upload'}
              </Button>
            </div>
          </form>
        </Card>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
          {posts.map((post) => (
            <Card key={post.id} className="overflow-hidden">
              <img src={post.image_url} alt={post.caption || 'Travel photo'} className="w-full h-56 object-cover" />
              <div className="p-4">
                {post.caption && <p className="text-gray-800 mb-1">{post.caption}</p>}
                <div className="flex items-center justify-between text-sm text-gray-500">
                  <span>{post.location || ''}</span>
                  <button onClick={() => onLike(post.id)} className="text-[#0077b6] hover:underline">
                    ❤ {post.likes}
                  </button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Gallery;
