import './App.css'
import lufthansaLogo from './assets/Lufthansa_Group_2025.svg.png'

function App() {
  return (
    <div className="app">
      <header className="header">
        <div className="header-top">
          <img src={lufthansaLogo} alt="Lufthansa Group Logo" className="logo" />
          <button className="language-button">Deutsch</button>
        </div>

        <nav className="main-nav">
          <a href="#" className="active">Home</a>
          <a href="#">Learning Path</a>
          <a href="#">Missions</a>
          <a href="#">Progress</a>
          <a href="#">Leaderboard</a>
          <a href="#">Resources</a>
        </nav>
      </header>

      <main>
        <section className="hero">
          <div className="hero-box">
            <h1>Welcome!</h1>
            <p>
              Build the AI skills of tomorrow. Learn, apply, and grow with
              role-specific AI enablement across Lufthansa Group.
            </p>
            <button className="hero-button">Start learning</button>
          </div>
        </section>
      </main>
    </div>
  )
}

export default App