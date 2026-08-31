import { HashRouter, Route, Routes } from "react-router-dom";
import { SiteChrome } from "@/components/SiteChrome";
import { LandingPage } from "@/components/LandingPage";
import { DetectPage } from "@/pages/DetectPage";
import { ArchitecturePage } from "@/pages/ArchitecturePage";
import { LedgerPage } from "@/pages/LedgerPage";
import { ResearchPage } from "@/pages/ResearchPage";
import { ColabPage } from "@/pages/ColabPage";

export default function App() {
  return (
    <HashRouter>
      <SiteChrome>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/detect" element={<DetectPage />} />
          <Route path="/architecture" element={<ArchitecturePage />} />
          <Route path="/ledger" element={<LedgerPage />} />
          <Route path="/research" element={<ResearchPage />} />
          <Route path="/colab" element={<ColabPage />} />
        </Routes>
      </SiteChrome>
    </HashRouter>
  );
}
