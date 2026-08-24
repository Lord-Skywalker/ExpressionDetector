import { useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { wakeUpServers } from './api';
import Sidebar from './Sidebar';
import DashboardPage from './DashboardPage';
import UploadPage from './UploadPage';
import VideosPage from './VideosPage';
import AnalyticsPage from './AnalyticsPage';
import EventsPage from './EventsPage';
import LivePage from './LivePage';
import { useToast, ToastContainer } from './Toast';

export default function App() {
  const { toasts, addToast } = useToast();

  useEffect(() => {
    // Silently wake up the Cloud Run ML worker in the background
    // so it's warm and ready by the time the user uploads a video or starts Live Mode.
    wakeUpServers();
  }, []);

  return (
    <BrowserRouter>
      <div className="app-layout">
        <Sidebar />
        <main className="main-content">
          <Routes>
            <Route path="/"           element={<DashboardPage />} />
            <Route path="/upload"     element={<UploadPage addToast={addToast} />} />
            <Route path="/videos"     element={<VideosPage />} />
            <Route path="/videos/:id" element={<AnalyticsPage />} />
            <Route path="/events"     element={<EventsPage addToast={addToast} />} />
            <Route path="/live"       element={<LivePage />} />
          </Routes>
        </main>
      </div>
      <ToastContainer toasts={toasts} />
    </BrowserRouter>
  );
}
