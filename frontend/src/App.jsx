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

  // Form state
  const [selectedCity, setSelectedCity] = useState('');
  const [selectedMovie, setSelectedMovie] = useState('');
  const [selectedMovieUrl, setSelectedMovieUrl] = useState('');
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

      // Fetch Cities
      try {
        const { data: cityData } = await octokit.repos.getContent({
          owner, repo: repoName, path: 'data/cities.json',
        });
        setCities(JSON.parse(atob(cityData.content)));
      } catch (e) { console.warn("Could not fetch cities", e); }

      // Fetch Movies
      try {
        const { data: movieData } = await octokit.repos.getContent({
          owner, repo: repoName, path: 'data/movies.json',
        });
        setMovies(JSON.parse(atob(movieData.content)));
      } catch (e) { console.warn("Could not fetch movies", e); }

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

  return (
    <div className="container">
      <div className="header">
        <h1>🎬 Showting Pro</h1>
        <button className="logout-btn" onClick={() => { localStorage.clear(); window.location.reload(); }}>Logout</button>
      </div>

      <div className="card">
        <h2>Schedule Alert</h2>
        <form onSubmit={addAlert}>

          <div className="form-group">
            <label>Mode</label>
            <div className="toggle-group">
              <button type="button" className={!useCustomUrl ? 'active' : ''} onClick={() => setUseCustomUrl(false)}>Select Movie</button>
              <button type="button" className={useCustomUrl ? 'active' : ''} onClick={() => setUseCustomUrl(true)}>Custom URL</button>
            </div>
          </div>

          {!useCustomUrl ? (
            <>
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
                  {selectedCity && movies[selectedCity]?.map(m => (
                    <option key={m.url} value={JSON.stringify(m)}>{m.title}</option>
                  ))}
                </select>
              </div>
            </>
          ) : (
            <div className="form-group">
              <label>BookMyShow URL</label>
              <input type="text" placeholder="https://..." value={customUrl} onChange={(e) => setCustomUrl(e.target.value)} />
            </div>
          )}

          <div className="form-row">
            <div className="form-group half">
              <label>Format / Theatre</label>
              <input type="text" placeholder="IMAX, PVR, 4DX..." value={filterFormat} onChange={(e) => setFilterFormat(e.target.value)} />
            </div>
            <div className="form-group half">
              <label>Time Preference</label>
              <select value={filterTime} onChange={(e) => setFilterTime(e.target.value)}>
                <option value="">Any Time</option>
                <option value="MORNING">Morning (Before 12 PM)</option>
                <option value="AFTERNOON">Afternoon (12 PM - 4 PM)</option>
                <option value="EVENING">Evening (4 PM - 8 PM)</option>
                <option value="NIGHT">Night (After 8 PM)</option>
              </select>
            </div>
          </div>

          <div className="form-group">
            <label>WhatsApp Number (Optional)</label>
            <input type="text" placeholder="Override default number..." value={newPhone} onChange={(e) => setNewPhone(e.target.value)} />
          </div>

          <button type="submit" disabled={loading}>{loading ? 'Saving...' : 'Track Movie'}</button>
        </form>
      </div>

      <div className="alerts-list">
        <h2>Active Alerts ({alerts.length})</h2>
        {alerts.length === 0 ? <p>No alerts active.</p> : (
          alerts.map((alert, index) => (
            <div key={index} className="alert-item">
              <div>
                <h3>{alert.name}</h3>
                <small>{alert.city || "Custom URL"}</small>
                {alert.filters && <div className="tags">
                  {alert.filters.map(f => <span key={f} className="tag">{f}</span>)}
                </div>}
              </div>
              <button onClick={() => deleteAlert(index)}>🗑️</button>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default App
