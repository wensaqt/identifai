import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Header } from "./components/layout/Header";
import { LandingPage } from "./components/landing/LandingPage";
import { AnalyzePage } from "./components/analyze/AnalyzePage";
import { HistoryPage } from "./components/history/HistoryPage";
import { ProcessPage } from "./components/process/ProcessPage";
import "./App.css";

export function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        <Header />
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/analyze/:demarcheId" element={<AnalyzePage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/process/:processId" element={<ProcessPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
