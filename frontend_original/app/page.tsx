'use client';

import CanvasLoader from "./components/common/CanvasLoader";
import ScrollWrapper from "./components/common/ScrollWrapper";
import Experience from "./components/experience";
import Hero from "./components/hero";

const Home = () => {
  return (
    <CanvasLoader>
      <ScrollWrapper>
        <Hero/>
        <Experience/>
      </ScrollWrapper>
    </CanvasLoader>
  );
};
export default Home;
