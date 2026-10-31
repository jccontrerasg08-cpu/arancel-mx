import { useEffect, useRef, useState } from 'react';

const prefersReducedMotion = () => typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
// A hidden page (background tab, preview, print) never paints frames, so it gets the final number.
const skipsAnimation = () => prefersReducedMotion() || document.visibilityState === 'hidden' || typeof IntersectionObserver === 'undefined';
const easeOut = (progress) => 1 - (1 - progress) ** 4;

// Counts up to `value` once it is on screen. Screen readers get the final number only, people who
// ask for reduced motion (or whose page is hidden) see it immediately, and a timer guarantees the
// final number even if animation frames stall.
export function CountUp({ value, language = 'es', duration = 900 }) {
  const format = (amount) => Math.round(amount).toLocaleString(language === 'en' ? 'en-US' : 'es-MX');
  const [shown, setShown] = useState(() => (skipsAnimation() ? value : 0));
  const ref = useRef(null);
  useEffect(() => {
    if (skipsAnimation()) {
      setShown(value);
      return undefined;
    }
    let frame = 0;
    let safety = 0;
    let observer = null;
    const step = (timestamp, origin) => {
      const progress = Math.min((timestamp - origin) / duration, 1);
      setShown(value * easeOut(progress));
      if (progress < 1) frame = requestAnimationFrame((next) => step(next, origin));
    };
    const begin = () => {
      frame = requestAnimationFrame((timestamp) => step(timestamp, timestamp));
      safety = window.setTimeout(() => setShown(value), duration + 500);
    };
    const rect = ref.current.getBoundingClientRect();
    if (rect.top < window.innerHeight && rect.bottom > 0) {
      begin();
    } else {
      observer = new IntersectionObserver(([entry]) => {
        if (!entry.isIntersecting) return;
        observer.disconnect();
        begin();
      }, { threshold: 0.4 });
      observer.observe(ref.current);
    }
    return () => {
      observer?.disconnect();
      cancelAnimationFrame(frame);
      window.clearTimeout(safety);
    };
  }, [duration, value]);
  return <><span ref={ref} aria-hidden="true">{format(shown)}</span><span className="sr-only">{format(value)}</span></>;
}
