import { useRef, useState } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import NovelaCard from './NovelaCard'
import clsx from 'clsx'

export default function Carousel({ title, items = [] }) {
  const scrollRef = useRef(null)
  const [canScrollLeft, setCanScrollLeft] = useState(false)
  const [canScrollRight, setCanScrollRight] = useState(true)

  const scroll = (dir) => {
    const el = scrollRef.current
    if (!el) return
    const amount = el.clientWidth * 0.8
    el.scrollBy({ left: dir === 'right' ? amount : -amount, behavior: 'smooth' })
  }

  const handleScroll = () => {
    const el = scrollRef.current
    if (!el) return
    setCanScrollLeft(el.scrollLeft > 0)
    setCanScrollRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 10)
  }

  if (!items.length) return null

  return (
    <div className="relative group/carousel">
      <h2 className="text-xl font-bold text-white mb-4">{title}</h2>

      <div className="relative">
        {/* Left button */}
        <button
          onClick={() => scroll('left')}
          className={clsx(
            'absolute left-0 top-0 bottom-0 z-10 w-12 bg-gradient-to-r from-novelai-bg to-transparent flex items-center justify-center transition-opacity',
            canScrollLeft ? 'opacity-100' : 'opacity-0 pointer-events-none'
          )}
        >
          <div className="w-8 h-8 bg-black/70 rounded-full flex items-center justify-center hover:bg-novelai-accent transition-colors">
            <ChevronLeft size={18} className="text-white" />
          </div>
        </button>

        {/* Scroll container */}
        <div
          ref={scrollRef}
          onScroll={handleScroll}
          className="flex gap-3 overflow-x-auto carousel-scroll pb-2"
        >
          {items.map((novela) => (
            <div key={novela.id} className="flex-shrink-0 w-36 md:w-44">
              <NovelaCard novela={novela} />
            </div>
          ))}
        </div>

        {/* Right button */}
        <button
          onClick={() => scroll('right')}
          className={clsx(
            'absolute right-0 top-0 bottom-0 z-10 w-12 bg-gradient-to-l from-novelai-bg to-transparent flex items-center justify-center transition-opacity',
            canScrollRight ? 'opacity-100' : 'opacity-0 pointer-events-none'
          )}
        >
          <div className="w-8 h-8 bg-black/70 rounded-full flex items-center justify-center hover:bg-novelai-accent transition-colors">
            <ChevronRight size={18} className="text-white" />
          </div>
        </button>
      </div>
    </div>
  )
}
