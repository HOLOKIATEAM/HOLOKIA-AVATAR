import { Canvas } from "@react-three/fiber";
import { Suspense, useEffect, useState } from "react";
import { Experience } from "./Experience";

const examples = [
  {
    label: "Visualizer",
    href: "#",
  },
  {
    label: "3D model",
    href: "#model",
  },
];

export const UI = () => {
  const [currentHash, setCurrentHash] = useState(
    window.location.hash.replace("#", "")
  );

  useEffect(() => {
    // When hash in the url changes, update the href state
    const handleHashChange = () => {
      setCurrentHash(window.location.hash.replace("#", ""));
    };
    window.addEventListener("hashchange", handleHashChange);

    // Cleanup the event listener on component unmount
    return () => {
      window.removeEventListener("hashchange", handleHashChange);
    };
  }, []);

  return (
    <section className="flex flex-col-reverse lg:flex-row overflow-hidden h-full w-full">

      <div className="flex-1 ">
        <Canvas shadows camera={{ position: [12, 8, 26], fov: 30 }}>
          <Suspense>
            <Experience />
          </Suspense>
        </Canvas>
      </div>
    </section>
  );
};
