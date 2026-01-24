import type { ReactElement } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import MainPage from "./pages/MainPage";
import Onboarding from "./pages/Onboarding";

function App(): ReactElement {
  return (
    <BrowserRouter>
      <div className="bg-slate-900">
        <Routes>
          <Route path="/" element={<Onboarding />} />
          <Route path="/main" element={<MainPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
