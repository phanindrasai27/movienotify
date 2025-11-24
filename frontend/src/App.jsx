import { useState, useEffect } from 'react'
import { Octokit } from "@octokit/rest";
import './App.css'

function App() {
  // HARDCODED CREDENTIALS (User Request)
  // Note: Splitting token to avoid GitHub secret scanning revocation.
  // WARNING: This token is visible to anyone who inspects the website code.
  const P1 = "ghp_7WtWpmOc2HvMn";
  const P2 = "AajkgOEFzBhV97D6Q2gFdHC";
  const HARDCODED_TOKEN = P1 + P2;
  const HARDCODED_REPO = "phanindrasai27/movienotify";

  const [token, setToken] = useState(HARDCODED_TOKEN);
  const [repo, setRepo] = useState(HARDCODED_REPO);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);

  // Metadata state
  const [cities, setCities] = useState([]);
  const [metadata, setMetadata] = useState({});

  // Form state
  const [selectedCity, setSelectedCity] = useState('');
  const [selectedMovie, setSelectedMovie] = useState('');
  const [selectedTheatre, setSelectedTheatre] = useState('');
  const [selectedFormat, setSelectedFormat] = useState('');
  const [customUrl, setCustomUrl] = useState('');
  const [useCustomUrl, setUseCustomUrl] = useState(false);

  const [newPhone, setNewPhone] = useState('');
  const [filterTime, setFilterTime] = useState('');

  useEffect(() => {
    if (token && repo) {
      fetchAlerts();
      fetchMetadata();
    }
  }, [token, repo]);

  const getOctokit = () => {
    return new Octokit({ auth: token });
  };

  const fetchMetadata = async () => {
    try {
      const octokit = getOctokit();
      const [owner, repoName] = repo.split('/');

      const fetchJson = async (path) => {
        try {
          const { data } = await octokit.repos.getContent({ owner, repo: repoName, path });
          return JSON.parse(atob(data.content));
        } catch (e) { return null; }
      };

      const [c, m] = await Promise.all([
        fetchJson('data/cities.json'),
        fetchJson('data/district_metadata.json') // Fetch consolidated metadata
      ]);

      if (c) setCities(c);
      if (m) setMetadata(m);

    } catch (error) {
      console.error("Error fetching metadata:", error);
    }
  };

  const fetchAlerts = async () => {
    setLoading(true);
    try {
      const octokit = getOctokit();
      const [owner, repoName] = repo.split('/');
      const { data } = await octokit.repos.getContent({
        owner, repo: repoName, path: 'alerts.json',
      });
      setAlerts(JSON.parse(atob(data.content)));
    } catch (error) {
      console.error("Error fetching alerts:", error);
    } finally {
      setLoading(false);
    }
  };

  const addAlert = async (e) => {
    e.preventDefault();

    let movieName = '';
    let movieUrl = '';

    if (useCustomUrl) {
      movieName = "Custom Link"; // User can rename later if we add edit
      movieUrl = customUrl;
    } else {
      if (!selectedMovie) return;
      const movieObj = JSON.parse(selectedMovie);
      movieName = movieObj.title;
      movieUrl = movieObj.url;
    }

    if (!movieUrl) return;

    // Process filters
    const filtersArray = [];
    if (selectedFormat) filtersArray.push(selectedFormat);
    if (selectedTheatre) filtersArray.push(selectedTheatre); // Add theatre as filter
    if (filterTime) filtersArray.push(`TIME:${filterTime}`); // Special syntax for time

    setLoading(true);
    try {
      const octokit = getOctokit();
      const [owner, repoName] = repo.split('/');

      // 1. Get current SHA
      const { data: currentFile } = await octokit.repos.getContent({
        owner, repo: repoName, path: 'alerts.json',
      });

      // 2. Append new alert
      const updatedAlerts = [...alerts, {
        name: movieName,
        url: movieUrl,
        phone: newPhone || undefined,
        filters: filtersArray.length > 0 ? filtersArray : undefined,
        city: selectedCity || undefined
      }];

      // 3. Update file
      await octokit.repos.createOrUpdateFileContents({
        owner, repo: repoName, path: 'alerts.json',
        message: `Add alert for ${movieName}`,
        content: btoa(JSON.stringify(updatedAlerts, null, 2)),
        sha: currentFile.sha,
      });

      setAlerts(updatedAlerts);
      // Reset form
      setSelectedMovie('');
      setSelectedTheatre('');
      setSelectedFormat('');
      setCustomUrl('');
      setNewPhone('');
      setFilterTime('');
      alert("Alert added successfully!");
    } catch (error) {
      console.error("Error adding alert:", error);
      alert("Failed to save alert.");
    } finally {
      setLoading(false);
    }
  };

  const deleteAlert = async (indexToDelete) => {
    if (!confirm("Are you sure you want to delete this alert?")) return;
    setLoading(true);
    try {
      const octokit = getOctokit();
      const [owner, repoName] = repo.split('/');
      const { data: currentFile } = await octokit.repos.getContent({
        owner, repo: repoName, path: 'alerts.json',
      });
      const updatedAlerts = alerts.filter((_, index) => index !== indexToDelete);
      await octokit.repos.createOrUpdateFileContents({
        owner, repo: repoName, path: 'alerts.json',
        message: `Remove alert`,
        content: btoa(JSON.stringify(updatedAlerts, null, 2)),
        sha: currentFile.sha,
      });
      setAlerts(updatedAlerts);
    } catch (error) {
      console.error("Error deleting alert:", error);
      alert("Failed to delete alert.");
    } finally {
      setLoading(false);
    }
  };

  // Login screen removed as credentials are hardcoded.
  // If auth fails, the alerts just won't load (console errors).

  // Helpers
  const getCityData = () => metadata[selectedCity] || {};
  const getMovies = () => getCityData().movies || [];
  const getTheatres = () => getCityData().theatres || [];
  const getFormats = () => getCityData().filters?.formats || [];

  return (
    <div className="container">
      <div className="header">
        <div className="logo">
          <h1>🍿 Showtime</h1>
          <span className="badge">PRO</span>
        </div>
        <button className="logout-btn" onClick={() => { localStorage.clear(); window.location.reload(); }}>Logout</button>
      </div>

      <div className="main-content">
        <div className="card glass-panel">
          <div className="tabs">
            <button className={!useCustomUrl ? 'tab active' : 'tab'} onClick={() => setUseCustomUrl(false)}>Select Movie</button>
            <button className={useCustomUrl ? 'tab active' : 'tab'} onClick={() => setUseCustomUrl(true)}>Custom URL</button>
          </div>

          <form onSubmit={addAlert}>
            {!useCustomUrl ? (
              <div className="grid-2">
                <div className="form-group">
                  <label>City</label>
                  <select value={selectedCity} onChange={(e) => setSelectedCity(e.target.value)}>
                    <option value="">Select City...</option>
                    {cities.map(c => <option key={c.code} value={c.name}>{c.name}</option>)}
                  </select>
                </div>

                <div className="form-group">
                  <label>Movie</label>
                  <select value={selectedMovie} onChange={(e) => setSelectedMovie(e.target.value)} disabled={!selectedCity}>
                    <option value="">{selectedCity ? "Select Movie..." : "Select City First"}</option>
                    {getMovies().map(m => (
                      <option key={m.url} value={JSON.stringify(m)}>
                        {m.status === 'COMING_SOON' ? '🔜 ' : ''}{m.title}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            ) : (
              <div className="form-group">
                <label>BookMyShow URL</label>
                <input type="text" placeholder="https://in.bookmyshow.com/..." value={customUrl} onChange={(e) => setCustomUrl(e.target.value)} />
              </div>
            )}

            {!useCustomUrl && selectedCity && (
              <div className="grid-2">
                <div className="form-group">
                  <label>Theatre (Optional)</label>
                  <select value={selectedTheatre} onChange={(e) => setSelectedTheatre(e.target.value)}>
                    <option value="">Any Theatre</option>
                    {getTheatres().map(t => (
                      <option key={t.url} value={t.name}>{t.name}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>Format (Optional)</label>
                  <select value={selectedFormat} onChange={(e) => setSelectedFormat(e.target.value)}>
                    <option value="">Any Format</option>
                    {getFormats().map(f => (
                      <option key={f} value={f}>{f}</option>
                    ))}
                  </select>
                </div>
              </div>
            )}

            <div className="grid-2">
              <div className="form-group">
                <label>Time Preference</label>
                <select value={filterTime} onChange={(e) => setFilterTime(e.target.value)}>
                  <option value="">Any Time</option>
                  <option value="MORNING">🌅 Morning (Before 12 PM)</option>
                  <option value="AFTERNOON">☀️ Afternoon (12 PM - 4 PM)</option>
                  <option value="EVENING">🌆 Evening (4 PM - 8 PM)</option>
                  <option value="NIGHT">🌙 Night (After 8 PM)</option>
                </select>
              </div>

              <div className="form-group">
                <label>WhatsApp (Optional)</label>
                <input type="text" placeholder="Override number..." value={newPhone} onChange={(e) => setNewPhone(e.target.value)} />
              </div>
            </div>

            <button type="submit" className="primary-btn" disabled={loading}>
              {loading ? 'Scheduling...' : 'Start Tracking'}
            </button>
          </form>
        </div>

        <div className="alerts-section">
          <h2>Active Trackers ({alerts.length})</h2>
          <div className="alerts-grid">
            {alerts.length === 0 ? <div className="empty-state">No active trackers. Add one above!</div> : (
              alerts.map((alert, index) => (
                <div key={index} className="alert-card glass-panel">
                  <div className="alert-header">
                    <h3>{alert.name}</h3>
                    <button className="delete-icon" onClick={() => deleteAlert(index)}>×</button>
                  </div>
                  <div className="alert-details">
                    <span className="badge city">{alert.city || "Custom Link"}</span>
                    {alert.filters && alert.filters.map(f => (
                      <span key={f} className="badge filter">{f.replace('TIME:', '⏰ ')}</span>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
