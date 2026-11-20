import { BrowserRouter, Route, Routes } from 'react-router-dom';
import BottomNav from './components/BottomNav';
import Inicio from './pages/Inicio';
import Anomalia from './pages/Anomalia';
import Conversa from './pages/Conversa';
import Historico from './pages/Historico';
import Definicoes from './pages/Definicoes';
import Calendario from './pages/Calendario';
import RemoverCalendario from './pages/RemoverCalendario';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Inicio />} />
        <Route path="/anomalias/:id" element={<Anomalia />} />
        <Route path="/conversa" element={<Conversa />} />
        <Route path="/historico" element={<Historico />} />
        <Route path="/definicoes" element={<Definicoes />} />
        <Route path="/definicoes/calendario" element={<Calendario />} />
        <Route path="/definicoes/calendario/remover" element={<RemoverCalendario />} />
      </Routes>
      <BottomNav />
    </BrowserRouter>
  );
}
