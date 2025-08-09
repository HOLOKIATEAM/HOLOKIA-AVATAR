import { Loader } from "@react-three/drei";
import { Lipsync } from "wawa-lipsync";
import { UI } from "./components/UI";
import { Visualizer } from "./components/Visualizer";
import { ChatInterface } from "./components/ChatInterface";

export const lipsyncManager = new Lipsync({});

function App() {
  return (
    <>
      <Loader />
      <div className="flex h-screen w-screen bg-gradient-to-b from-blue-400 to-blue-200 relative">
        {/* Chatbox à gauche */}
        <ChatInterface />
        {/* Avatar à droite */}
        <div className="fixed top-0 right-0 w-1/2 h-full">
            <UI />
        </div>
      </div>
    </>
  );
}

export default App;
