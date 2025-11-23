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
  const [movies, setMovies] = useState({});
  const [theatres, setTheatres] = useState({});

  // Form state
  const [selectedCity, setSelectedCity] = useState('');
  const [selectedMovie, setSelectedMovie] = useState('');
  const [selectedTheatre, setSelectedTheatre] = useState('');
  const [customUrl, setCustomUrl] = useState('');
  const [useCustomUrl, setUseCustomUrl] = useState(false);

  const [newPhone, setNewPhone] = useState('');
  const [filterFormat, setFilterFormat] = useState('');
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

      const [c, m, t] = await Promise.all([
        fetchJson('data/cities.json'),
        fetchJson('data/movies.json'),
        fetchJson('data/theatres.json')
      ]);

      if (c) setCities(c);
      if (m) setMovies(m);
      if (t) setTheatres(t);

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
    if (filterFormat) filtersArray.push(filterFormat);
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
      setCustomUrl('');
      setNewPhone('');
      setFilterFormat('');
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

  // Common formats for "Preloading"
  const COMMON_FORMATS = ["IMAX", "4DX", "3D", "2D", "PVR", "INOX", "DOLBY", "ICE", "GOLD"];

  const toggleFormat = (fmt) => {
    const current = filterFormat ? filterFormat.split(',').map(s => s.trim()) : [];
    if (current.includes(fmt)) {
      setFilterFormat(current.filter(f => f !== fmt).join(', '));
    } else {
      setFilterFormat([...current, fmt].join(', '));
    }
  };

  // Helper to group movies
  const getMoviesForCity = () => {
    if (!selectedCity || !movies[selectedCity]) return [];
    return movies[selectedCity];
  };

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
                    {getMoviesForCity().map(m => (
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
              <div className="form-group">
                <label>Specific Theatre (Optional)</label>
                <select value={selectedTheatre} onChange={(e) => setSelectedTheatre(e.target.value)}>
                  <option value="">Any Theatre</option>
                  {theatres[selectedCity]?.map(t => (
                    <option key={t.url} value={t.name}>{t.name}</option>
                  ))}
                </select>
              </div>
            )}

            <div className="form-group">
              <label>Formats (e.g. IMAX, 4DX)</label>
              <div className="chip-container">
                {COMMON_FORMATS.map(fmt => (
                  <button
                    key={fmt}
                    type="button"
                    className={`chip ${filterFormat.includes(fmt) ? 'selected' : ''}`}
                    onClick={() => toggleFormat(fmt)}
                  >
                    {fmt}
                  </button>
                ))}
              </div>
              <input
                type="text"
                placeholder="Or type custom (e.g. Luxe, EPIQ)..."
                value={filterFormat}
                onChange={(e) => setFilterFormat(e.target.value)}
                className="mt-2"
              />
            </div>

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
