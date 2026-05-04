import React from "react";
import { Timeline } from "@/components/ui/timeline";

export default function TimelineDemo() {
  const data = [
    {
      title: "2024",
      content: (
        <div>
          <p className="mb-8 text-xs font-normal text-neutral-800 dark:text-neutral-200 md:text-sm">
            Built and launched Aceternity UI and Aceternity UI Pro from scratch
          </p>
          <div className="grid grid-cols-2 gap-4">
            {[
              "https://assets.aceternity.com/templates/startup-1.webp",
              "https://assets.aceternity.com/templates/startup-2.webp",
              "https://assets.aceternity.com/templates/startup-3.webp",
              "https://assets.aceternity.com/templates/startup-4.webp",
            ].map((src) => (
              <img
                key={src}
                src={src}
                alt="startup template"
                width={500}
                height={500}
                className="h-20 w-full rounded-lg object-cover shadow-[0_0_24px_rgba(34,_42,_53,_0.06),_0_1px_1px_rgba(0,_0,_0,_0.05),_0_0_0_1px_rgba(34,_42,_53,_0.04),_0_0_4px_rgba(34,_42,_53,_0.08),_0_16px_68px_rgba(47,_48,_55,_0.05),_0_1px_0_rgba(255,_255,_255,_0.1)_inset] md:h-44 lg:h-60"
              />
            ))}
          </div>
        </div>
      ),
    },
    {
      title: "Early 2023",
      content: (
        <div>
          <p className="mb-8 text-xs font-normal text-neutral-800 dark:text-neutral-200 md:text-sm">
            I usually run out of copy, but when I see content this big, I try to integrate lorem ipsum.
          </p>
          <p className="mb-8 text-xs font-normal text-neutral-800 dark:text-neutral-200 md:text-sm">
            Lorem ipsum is for people who are too lazy to write copy. But we are not. Here are some more example of beautiful designs I built.
          </p>
          <div className="grid grid-cols-2 gap-4">
            {[
              "https://assets.aceternity.com/pro/hero-sections.png",
              "https://assets.aceternity.com/features-section.png",
              "https://assets.aceternity.com/pro/bento-grids.png",
              "https://assets.aceternity.com/cards.png",
            ].map((src) => (
              <img
                key={src}
                src={src}
                alt="template"
                width={500}
                height={500}
                className="h-20 w-full rounded-lg object-cover shadow-[0_0_24px_rgba(34,_42,_53,_0.06),_0_1px_1px_rgba(0,_0,_0,_0.05),_0_0_0_1px_rgba(34,_42,_53,_0.04),_0_0_4px_rgba(34,_42,_53,_0.08),_0_16px_68px_rgba(47,_48,_55,_0.05),_0_1px_0_rgba(255,_255,_255,_0.1)_inset] md:h-44 lg:h-60"
              />
            ))}
          </div>
        </div>
      ),
    },
    {
      title: "Changelog",
      content: (
        <div>
          <p className="mb-4 text-xs font-normal text-neutral-800 dark:text-neutral-200 md:text-sm">
            Deployed 5 new components on Aceternity today
          </p>
          <div className="mb-8">
            {[
              "Card grid component",
              "Startup template Aceternity",
              "Random file upload lol",
              "Himesh Reshammiya Music CD",
              "Salman Bhai Fan Club registrations open",
            ].map((item) => (
              <div key={item} className="flex items-center gap-2 text-xs text-neutral-700 dark:text-neutral-300 md:text-sm">
                OK {item}
              </div>
            ))}
          </div>
          <div className="grid grid-cols-2 gap-4">
            {[
              "https://assets.aceternity.com/pro/hero-sections.png",
              "https://assets.aceternity.com/features-section.png",
              "https://assets.aceternity.com/pro/bento-grids.png",
              "https://assets.aceternity.com/cards.png",
            ].map((src) => (
              <img
                key={src}
                src={src}
                alt="template"
                width={500}
                height={500}
                className="h-20 w-full rounded-lg object-cover shadow-[0_0_24px_rgba(34,_42,_53,_0.06),_0_1px_1px_rgba(0,_0,_0,_0.05),_0_0_0_1px_rgba(34,_42,_53,_0.04),_0_0_4px_rgba(34,_42,_53,_0.08),_0_16px_68px_rgba(47,_48,_55,_0.05),_0_1px_0_rgba(255,_255,_255,_0.1)_inset] md:h-44 lg:h-60"
              />
            ))}
          </div>
        </div>
      ),
    },
  ];

  return (
    <div className="relative w-full overflow-clip">
      <Timeline data={data} />
    </div>
  );
}
