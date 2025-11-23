import { useState, useEffect } from 'react'
import { Octokit } from "@octokit/rest";
import './App.css'

function App() {
  const [token, setToken] = useState(localStorage.getItem('github_token') || '');
  const [repo, setRepo] = useState(localStorage.getItem('github_repo') || '');
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [newUrl, setNewUrl] = useState('');
  const [newPhone, setNewPhone] = useState('');
  const [newFilters, setNewFilters] = useState('');
  const [movieName, setMovieName] = useState('');

  useEffect(() => {
    if (token && repo) {
      fetchAlerts();
    }
  }, [token, repo]);

  const saveCredentials = () => {
    localStorage.setItem('github_token', token);
    localStorage.setItem('github_repo', repo);
    fetchAlerts();
  };

  const getOctokit = () => {
    return new Octokit({ auth: token });
  };

  const fetchAlerts = async () => {
    setLoading(true);
    try {
      const octokit = getOctokit();
      const [owner, repoName] = repo.split('/');
      const { data } = await octokit.repos.getContent({
        owner,
        repo: repoName,
        path: 'alerts.json',
      });

      const content = atob(data.content);
      setAlerts(JSON.parse(content));
    } catch (error) {
      console.error("Error fetching alerts:", error);
      alert("Failed to fetch alerts. Check your token and repo name.");
    } finally {
      setLoading(false);
    }
  };

  const addAlert = async (e) => {
    e.preventDefault();
    if (!newUrl || !movieName) return;

    setLoading(true);
    try {
      const octokit = getOctokit();
      const [owner, repoName] = repo.split('/');

      // 1. Get current SHA
      const { data: currentFile } = await octokit.repos.getContent({
        owner,
        repo: repoName,
        path: 'alerts.json',
      });

      // 2. Process filters
      const filtersArray = newFilters.split(',').map(f => f.trim()).filter(f => f.length > 0);

      // 3. Append new alert
      const updatedAlerts = [...alerts, {
        name: movieName,
        url: newUrl,
        phone: newPhone || undefined,
        filters: filtersArray.length > 0 ? filtersArray : undefined
      }];

      // 4. Update file
      await octokit.repos.createOrUpdateFileContents({
        owner,
        repo: repoName,
        path: 'alerts.json',
        message: `Add alert for ${movieName}`,
        content: btoa(JSON.stringify(updatedAlerts, null, 2)),
        sha: currentFile.sha,
      });

      setAlerts(updatedAlerts);
      setNewUrl('');
      setMovieName('');
      setNewPhone('');
      setNewFilters('');
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

      // 1. Get current SHA
      const { data: currentFile } = await octokit.repos.getContent({
        owner,
        repo: repoName,
        path: 'alerts.json',
      });

      // 2. Filter out alert
      const updatedAlerts = alerts.filter((_, index) => index !== indexToDelete);

      // 3. Update file
      await octokit.repos.createOrUpdateFileContents({
        owner,
        repo: repoName,
        path: 'alerts.json',
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

  if (!token || !repo) {
    return (
      <div className="container">
        <h1>🎬 Movie Alert Setup</h1>
        <div className="card">
          <label>GitHub Personal Access Token</label>
          <input
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="ghp_..."
          />
          <label>Repository (username/repo)</label>
          <input
            type="text"
            value={repo}
            onChange={(e) => setRepo(e.target.value)}
            placeholder="phanindrasai27/movie-alerts"
          />
          <button onClick={saveCredentials}>Connect</button>
          <p className="help-text">Token needs 'repo' scope.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container">
      <header>
        <h1>🎬 Movie Alerts</h1>
        <button className="secondary" onClick={() => {
          localStorage.clear();
          window.location.reload();
        }}>Logout</button>
      </header>

      <div className="card">
        <h2>Add New Alert</h2>
        <form onSubmit={addAlert}>
          <input
            type="text"
            placeholder="Movie Name (e.g. Gladiator 2)"
            value={movieName}
            onChange={(e) => setMovieName(e.target.value)}
            required
          />
          <input
            type="url"
            placeholder="BookMyShow URL (https://...)"
            value={newUrl}
            onChange={(e) => setNewUrl(e.target.value)}
            required
          />
          <input
            type="text"
            placeholder="Filters (e.g. IMAX, PVR, 4DX)"
            value={newFilters}
            onChange={(e) => setNewFilters(e.target.value)}
          />
          <input
            type="text"
            placeholder="WhatsApp Number (Optional override)"
            value={newPhone}
            onChange={(e) => setNewPhone(e.target.value)}
          />
          <button type="submit" disabled={loading}>
            {loading ? 'Saving...' : 'Track Movie'}
          </button>
        </form>
      </div>

      <div className="alerts-list">
        <h2>Active Alerts ({alerts.length})</h2>
        {loading && <p>Loading...</p>}
        {alerts.map((alert, index) => (
          <div key={index} className="alert-item">
            <div>
              <h3>{alert.name}</h3>
              <a href={alert.url} target="_blank" rel="noreferrer">{alert.url}</a>
              {alert.filters && alert.filters.length > 0 && (
                <p className="filters">🔍 {alert.filters.join(', ')}</p>
              )}
              {alert.phone && <p>📞 {alert.phone}</p>}
            </div>
            <button className="delete-btn" onClick={() => deleteAlert(index)}>🗑️</button>
          </div>
        ))}
        {alerts.length === 0 && !loading && <p>No alerts active.</p>}
      </div>
    </div>
  )
}

export default App
