// Winter Arc — Master Three.js Hero Parallax Scene
// Specifications: 60fps target, DPR capped at 2, Pause when off-screen, Prefers-reduced-motion check, multi-plane depth.

(function() {
    function initHeroScene() {
        const container = document.getElementById('three-hero-container');
        const fallback = document.getElementById('hero-fallback');
        if (!container) return;

        // 1. Accessibility Check: prefers-reduced-motion
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            console.log('Winter Arc: Prefers-reduced-motion enabled. Retaining still image artwork.');
            return;
        }

        // 2. WebGL Support Check
        if (typeof THREE === 'undefined') {
            console.warn('Winter Arc: Three.js not loaded. Falling back to static artwork.');
            return;
        }

        try {
            const scene = new THREE.Scene();
            const width = container.clientWidth || window.innerWidth;
            const height = container.clientHeight || 600;

            const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);
            camera.position.z = 10;

            const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: 'high-performance' });
            const dpr = Math.min(window.devicePixelRatio || 1, 2);
            renderer.setPixelRatio(dpr);
            renderer.setSize(width, height);
            container.appendChild(renderer.domElement);

            // Reveal container with Three.js
            container.classList.remove('hidden');

            // 3. Multi-Plane Snow & Atmospheric Particle Field
            const particleCount = window.innerWidth < 768 ? 200 : 500;
            const geometry = new THREE.BufferGeometry();
            const positions = new Float32Array(particleCount * 3);
            const velocities = new Float32Array(particleCount * 3);

            for (let i = 0; i < particleCount * 3; i += 3) {
                positions[i] = (Math.random() - 0.5) * 20;     // x
                positions[i + 1] = (Math.random() - 0.5) * 20; // y
                positions[i + 2] = (Math.random() - 0.5) * 15; // z

                velocities[i] = (Math.random() - 0.5) * 0.01;  // drift x
                velocities[i + 1] = -0.02 - Math.random() * 0.03; // fall y
                velocities[i + 2] = 0;
            }

            geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

            // Soft white/ice snow material
            const pMaterial = new THREE.PointsMaterial({
                color: 0xF4F1EC,
                size: 0.08,
                transparent: true,
                opacity: 0.75,
                blending: THREE.AdditiveBlending
            });

            const particles = new THREE.Points(geometry, pMaterial);
            scene.add(particles);

            // 4. Parallax Tracking
            let mouseX = 0;
            let mouseY = 0;
            let targetX = 0;
            let targetY = 0;

            window.addEventListener('mousemove', (e) => {
                const windowHalfX = window.innerWidth / 2;
                const windowHalfY = window.innerHeight / 2;
                mouseX = (e.clientX - windowHalfX) / windowHalfX;
                mouseY = (e.clientY - windowHalfY) / windowHalfY;
            });

            // 5. Visibility / Performance Control (Pause when out of view)
            let isVisible = true;
            const observer = new IntersectionObserver((entries) => {
                isVisible = entries[0].isIntersecting;
            }, { threshold: 0.1 });
            observer.observe(container);

            document.addEventListener('visibilitychange', () => {
                isVisible = !document.hidden;
            });

            // 6. Responsive Resize Handling
            window.addEventListener('resize', () => {
                const w = container.clientWidth;
                const h = container.clientHeight;
                camera.aspect = w / h;
                camera.updateProjectionMatrix();
                renderer.setSize(w, h);
            });

            // 7. Animation Loop
            function animate() {
                requestAnimationFrame(animate);

                if (!isVisible) return;

                targetX += (mouseX * 0.5 - targetX) * 0.05;
                targetY += (mouseY * 0.5 - targetY) * 0.05;

                // Move camera slightly for smooth parallax depth
                camera.position.x = targetX;
                camera.position.y = -targetY;
                camera.lookAt(scene.position);

                // Update falling snow particles
                const pos = geometry.attributes.position.array;
                for (let i = 0; i < particleCount * 3; i += 3) {
                    pos[i + 1] += velocities[i + 1];
                    pos[i] += velocities[i];

                    // Reset if below view
                    if (pos[i + 1] < -10) {
                        pos[i + 1] = 10;
                        pos[i] = (Math.random() - 0.5) * 20;
                    }
                }
                geometry.attributes.position.needsUpdate = true;

                renderer.render(scene, camera);
            }

            animate();
            console.log('Winter Arc: Three.js ambient snow parallax initialized.');

        } catch (err) {
            console.warn('Winter Arc: WebGL initialization encountered an error:', err);
            // Retain fallback image
        }
    }

    function loadAndInit() {
        if (typeof THREE !== 'undefined') {
            initHeroScene();
            return;
        }
        const currentScript = document.querySelector('script[data-three-src]');
        const threeSrc = currentScript ? currentScript.getAttribute('data-three-src') : '/static/js/vendor/three.min.js';
        
        const script = document.createElement('script');
        script.src = threeSrc;
        script.async = true;
        script.onload = initHeroScene;
        script.onerror = function() {
            console.warn('Winter Arc: Could not load three.min.js');
        };
        document.head.appendChild(script);
    }

    function scheduleInit() {
        if ('requestIdleCallback' in window) {
            requestIdleCallback(loadAndInit, { timeout: 2000 });
        } else {
            setTimeout(loadAndInit, 200);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', scheduleInit);
    } else {
        scheduleInit();
    }
})();
