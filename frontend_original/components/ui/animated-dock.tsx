"use client"

import * as React from "react"
import { useRef } from "react"
import {
  MotionValue,
  motion,
  useMotionValue,
  useSpring,
  useTransform,
} from "motion/react"

import Link from "next/link"
import { cn } from "@/lib/utils"

export interface AnimatedDockProps {
  className?: string
  items: DockItemData[]
}

export interface DockItemData {
  link: string
  Icon: React.ReactNode
  target?: string
  label?: string
  onClick?: () => void
}

export const AnimatedDock = ({ className, items }: AnimatedDockProps) => {
  const mouseX = useMotionValue(Infinity)

  return (
    <motion.div
      onMouseMove={(e) => mouseX.set(e.pageX)}
      onMouseLeave={() => mouseX.set(Infinity)}
      className={cn(
        "mx-auto flex h-16 items-end gap-3 bg-transparent px-2 pb-2",
        className,
      )}
    >
      {items.map((item, index) => (
        <DockItem key={index} mouseX={mouseX} label={item.label}>
          {item.onClick ? (
            <button
              type="button"
              onClick={item.onClick}
              aria-label={item.label}
              className="flex h-full w-full grow items-center justify-center text-white transition-colors"
            >
              {item.Icon}
            </button>
          ) : (
            <Link
              href={item.link}
              target={item.target}
              aria-label={item.label}
              className="flex h-full w-full grow items-center justify-center text-white transition-colors"
            >
              {item.Icon}
            </Link>
          )}
        </DockItem>
      ))}
    </motion.div>
  )
}

interface DockItemProps {
  mouseX: MotionValue<number>
  children: React.ReactNode
  label?: string
}

export const DockItem = ({ mouseX, children, label }: DockItemProps) => {
  const ref = useRef<HTMLDivElement>(null)

  const distance = useTransform(mouseX, (val) => {
    const bounds = ref.current?.getBoundingClientRect() ?? { x: 0, width: 0 }
    return val - bounds.x - bounds.width / 2
  })

  const widthSync = useTransform(distance, [-150, 0, 150], [40, 80, 40])
  const width = useSpring(widthSync, {
    mass: 0.1,
    stiffness: 150,
    damping: 12,
  })

  const iconScale = useTransform(width, [40, 80], [1, 1.5])
  const iconSpring = useSpring(iconScale, {
    mass: 0.1,
    stiffness: 150,
    damping: 12,
  })

  return (
    <motion.div
      ref={ref}
      style={{ width }}
      className="group relative flex aspect-square w-10 items-center justify-center rounded-full border border-white/55 bg-black/50 text-white shadow-[0_10px_26px_rgba(0,0,0,0.22)] backdrop-blur-[2px] transition-colors hover:border-black/65 hover:bg-[#eef4f6]/88"
    >
      <motion.div
        style={{ scale: iconSpring }}
        className="flex h-full w-full grow items-center justify-center"
      >
        {children}
      </motion.div>
      {label && (
        <span className="pointer-events-none absolute -top-8 border border-black/45 bg-[#eef4f6]/80 px-2 py-1 font-sans text-[0.58rem] uppercase tracking-[0.16em] text-black opacity-0 shadow-sm backdrop-blur transition-opacity group-hover:opacity-100">
          {label}
        </span>
      )}
    </motion.div>
  )
}
