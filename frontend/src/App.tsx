import { NavLink, Route, Routes } from "react-router-dom";
import JobDetailPage from "./pages/JobDetail";
import Jobs from "./pages/Jobs";
import Overview from "./pages/Overview";
import Profile from "./pages/Profile";
import Resumes from "./pages/Resumes";
import Settings from "./pages/Settings";

const links = [["/", "Overview"], ["/jobs", "Jobs"], ["/resumes", "Resumes"], ["/profile", "Profile"], ["/settings", "Settings"]];

export default function App() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-4">
      <header className="mb-6 flex flex-wrap items-center gap-x-6 gap-y-2 border-b border-slate-200 pb-3 dark:border-slate-800">
        <h1 className="text-lg font-bold">Compass</h1>
        <nav className="flex flex-wrap gap-4 text-sm">
          {links.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === "/"}
              className={({ isActive }) => (isActive ? "font-semibold text-indigo-600" : "text-slate-600 hover:text-slate-900 dark:text-slate-400")}>
              {label}
            </NavLink>
          ))}
        </nav>
      </header>
      <Routes>
        <Route path="/" element={<Overview />} />
        <Route path="/jobs" element={<Jobs />} />
        <Route path="/jobs/:id" element={<JobDetailPage />} />
        <Route path="/resumes" element={<Resumes />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </div>
  );
}
