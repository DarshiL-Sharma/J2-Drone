import Navbar from './components/Navbar';
import Hero from './components/Hero';
import ProjectOverview from './components/ProjectOverview';
import ExplodedDrone from './components/ExplodedDrone';
import SystemArchitecture from './components/SystemArchitecture';
import Simulation from './components/Simulation';
import ComputerVision from './components/ComputerVision';
import ReverseEngineering from './components/ReverseEngineering';
import Roadmap from './components/Roadmap';
import Team from './components/Team';
import TechStack from './components/TechStack';
import Impact from './components/Impact';
import FutureSystem from './components/FutureSystem';
import SimulationCTA from './components/SimulationCTA';
import Footer from './components/Footer';

export default function App() {
  return (
    <>
      <Navbar />
      <main>
        <Hero />
        <ProjectOverview />
        <ExplodedDrone />
        <SystemArchitecture />
        <Simulation />
        <ComputerVision />
        <ReverseEngineering />
        <Roadmap />
        <Team />
        <TechStack />
        <Impact />
        <FutureSystem />
        <SimulationCTA />
      </main>
      <Footer />
    </>
  );
}
