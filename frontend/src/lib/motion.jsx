import { LazyMotion, m } from 'framer-motion';

// Re-export m as motion to allow seamless drop-in replacement
export { m as motion };

const loadFeatures = () => import('framer-motion').then(res => res.domMax);

export function MotionProvider({ children }) {
    return (
        <LazyMotion features={loadFeatures} strict>
            {children}
        </LazyMotion>
    );
}
