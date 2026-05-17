import { Navigate, Route, Routes } from "react-router-dom";

import { useAuth } from "./auth/AuthContext";
import DemoApp from "./demo-app/DemoApp";
import Login from "./pages/Login";
import Signup from "./pages/Signup";

export default function App() {
  const { loading } = useAuth();

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center text-slate-500">
        Chargement...
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/" element={<DemoApp />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
