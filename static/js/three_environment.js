/**
 * Winter Arc — Cinematic 3D Environmental WebGL Engine (Three.js)
 * 
 * Features:
 * - 3-tier depth snow particle fields (foreground, midground, atmospheric frost dust)
 * - Atmospheric cold lighting and subtle crimson hearth illumination
 * - Depth-based cursor parallax with smooth lerp interpolation
 * - Dynamic theme adaptation (Frosted Alpine Light vs Obsidian Void Dark)
 * - 60fps target with DPR capped at 2, mobile optimization
 * - Strict accessibility (prefers-reduced-motion check)
 * - Energy-efficient: auto-pauses when off-screen or tab is hidden
 */

(function() {
    'use strict';

    function initWinterArcEnvironment() {
        var container = document.getElementById('three-env-container');
        if (!container) return;

        // 1. Accessibility Check: prefers-reduced-motion
        if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            console.log('Winter Arc: Prefers-reduced-motion active. 3D WebGL animations suspended.');
            return;
        }

        // 2. WebGL & Three.js Availability Check
        if (typeof THREE === 'undefined') {
            console.warn('Winter Arc: Three.js engine not loaded. Retaining atmospheric CSS background.');
            return;
        }

        try {
            var scene = new THREE.Scene();
            var width = container.clientWidth || window.innerWidth;
            var height = container.clientHeight || window.innerHeight;

            var camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
            camera.position.z = 20;

            var renderer = new THREE.WebGLRenderer({
                alpha: true,
                antialias: true,
                powerPreference: 'low-power'
            });

            var dpr = Math.min(window.devicePixelRatio || 1, 2);
            renderer.setPixelRatio(dpr);
            renderer.setSize(width, height);
            renderer.setClearColor(0x000000, 0);

            // Clear any existing children before attaching canvas
            while (container.firstChild) {
                container.removeChild(container.firstChild);
            }
            container.appendChild(renderer.domElement);
            renderer.domElement.style.position = 'absolute';
            renderer.domElement.style.top = '0';
            renderer.domElement.style.left = '0';
            renderer.domElement.style.width = '100%';
            renderer.domElement.style.height = '100%';
            renderer.domElement.style.pointerEvents = 'none';

            // 3. Theme Detection & Colors
            var isLight = document.documentElement.getAttribute('data-theme') === 'light';

            function getThemeColors(light) {
                return {
                    foreColor: light ? 0x465870 : 0xF4F1EC,
                    midColor: light ? 0x64748B : 0xDEE7EE,
                    dustColor: light ? 0x8FA4BF : 0x88A4BF,
                    foreOpacity: light ? 0.65 : 0.85,
                    midOpacity: light ? 0.50 : 0.70,
                    dustOpacity: light ? 0.35 : 0.50,
                    lightColor: light ? 0xCBD5E1 : 0x7E99B8,
                    hearthColor: light ? 0x991B1B : 0x580D11
                };
            }

            var colors = getThemeColors(isLight);

            // 4. Multi-Tier Snow Particles
            var isMobile = (window.innerWidth < 768);
            var foreCount = isMobile ? 35 : 90;
            var midCount  = isMobile ? 120 : 320;
            var dustCount = isMobile ? 200 : 550;

            function createParticleLayer(count, size, color, opacity, zRange, xRange, yRange) {
                var geom = new THREE.BufferGeometry();
                var pos = new Float32Array(count * 3);
                var vel = new Float32Array(count * 3);
                var phases = new Float32Array(count);

                for (var i = 0; i < count; i++) {
                    var idx = i * 3;
                    pos[idx] = (Math.random() - 0.5) * xRange;
                    pos[idx + 1] = (Math.random() - 0.5) * yRange;
                    pos[idx + 2] = zRange[0] + Math.random() * (zRange[1] - zRange[0]);

                    vel[idx] = (Math.random() - 0.5) * 0.015;             // x-drift
                    vel[idx + 1] = -(0.015 + Math.random() * 0.035);       // y-fall
                    vel[idx + 2] = (Math.random() - 0.5) * 0.005;         // z-flutter

                    phases[i] = Math.random() * Math.PI * 2;
                }

                geom.setAttribute('position', new THREE.BufferAttribute(pos, 3));

                var mat = new THREE.PointsMaterial({
                    color: color,
                    size: size,
                    transparent: true,
                    opacity: opacity,
                    blending: THREE.NormalBlending,
                    depthWrite: false
                });

                var points = new THREE.Points(geom, mat);
                scene.add(points);

                return {
                    points: points,
                    geom: geom,
                    mat: mat,
                    vel: vel,
                    phases: phases,
                    count: count,
                    xRange: xRange,
                    yRange: yRange,
                    zRange: zRange
                };
            }

            var foreLayer = createParticleLayer(foreCount, isMobile ? 0.22 : 0.28, colors.foreColor, colors.foreOpacity, [10, 18], 28, 24);
            var midLayer  = createParticleLayer(midCount,  isMobile ? 0.12 : 0.16, colors.midColor,  colors.midOpacity,  [0, 10],  36, 28);
            var dustLayer = createParticleLayer(dustCount, isMobile ? 0.06 : 0.08, colors.dustColor, colors.dustOpacity, [-15, 0],  45, 32);

            // 5. Cold Alpine Atmosphere & Crimson Hearth Lighting
            var ambientLight = new THREE.AmbientLight(colors.lightColor, 0.6);
            scene.add(ambientLight);

            var hearthLight = new THREE.PointLight(colors.hearthColor, 0.8, 40);
            hearthLight.position.set(-8, -10, 5);
            scene.add(hearthLight);

            // 6. Theme Change Listener
            window.addEventListener('winter-arc-theme-change', function(e) {
                var newIsLight = (e.detail && e.detail.theme === 'light');
                var c = getThemeColors(newIsLight);

                foreLayer.mat.color.setHex(c.foreColor);
                foreLayer.mat.opacity = c.foreOpacity;

                midLayer.mat.color.setHex(c.midColor);
                midLayer.mat.opacity = c.midOpacity;

                dustLayer.mat.color.setHex(c.dustColor);
                dustLayer.mat.opacity = c.dustOpacity;

                ambientLight.color.setHex(c.lightColor);
                hearthLight.color.setHex(c.hearthColor);
            });

            // 7. Interactive Parallax Control
            var mouseX = 0, mouseY = 0;
            var targetX = 0, targetY = 0;
            var windowHalfX = window.innerWidth / 2;
            var windowHalfY = window.innerHeight / 2;

            function onMouseMove(e) {
                mouseX = (e.clientX - windowHalfX) / windowHalfX;
                mouseY = (e.clientY - windowHalfY) / windowHalfY;
            }

            window.addEventListener('mousemove', onMouseMove, { passive: true });

            // 8. Performance Guards: Pause when off-screen or tab hidden
            var isVisible = true;
            if ('IntersectionObserver' in window) {
                var observer = new IntersectionObserver(function(entries) {
                    isVisible = entries[0].isIntersecting;
                }, { threshold: 0.05 });
                observer.observe(container);
            }

            document.addEventListener('visibilitychange', function() {
                isVisible = !document.hidden;
            });

            // 9. Resize Handling
            function onWindowResize() {
                if (!container) return;
                var w = container.clientWidth || window.innerWidth;
                var h = container.clientHeight || window.innerHeight;
                windowHalfX = w / 2;
                windowHalfY = h / 2;
                camera.aspect = w / h;
                camera.updateProjectionMatrix();
                renderer.setSize(w, h);
            }

            var resizeTimeout;
            window.addEventListener('resize', function() {
                clearTimeout(resizeTimeout);
                resizeTimeout = setTimeout(onWindowResize, 100);
            });

            // 10. Animation Loop
            var clock = new THREE.Clock();

            function updateLayer(layer, delta, time) {
                var pos = layer.geom.attributes.position.array;
                var vel = layer.vel;
                var phases = layer.phases;
                var count = layer.count;

                for (var i = 0; i < count; i++) {
                    var idx = i * 3;

                    // Fluttering wind oscillation
                    var flutter = Math.sin(time * 1.5 + phases[i]) * 0.008;

                    pos[idx] += vel[idx] + flutter;
                    pos[idx + 1] += vel[idx + 1];
                    pos[idx + 2] += vel[idx + 2];

                    // Loop boundaries
                    if (pos[idx + 1] < -layer.yRange / 2) {
                        pos[idx + 1] = layer.yRange / 2;
                        pos[idx] = (Math.random() - 0.5) * layer.xRange;
                    }
                    if (pos[idx] > layer.xRange / 2) {
                        pos[idx] = -layer.xRange / 2;
                    } else if (pos[idx] < -layer.xRange / 2) {
                        pos[idx] = layer.xRange / 2;
                    }
                }
                layer.geom.attributes.position.needsUpdate = true;
            }

            function animate() {
                requestAnimationFrame(animate);

                if (!isVisible) return;

                var delta = clock.getDelta();
                var time = clock.getElapsedTime();

                // Smooth camera parallax interpolation (lerp)
                targetX += (mouseX * 1.2 - targetX) * 0.04;
                targetY += (mouseY * 0.8 - targetY) * 0.04;

                camera.position.x = targetX;
                camera.position.y = -targetY;
                camera.rotation.y = -targetX * 0.03;
                camera.rotation.x = -targetY * 0.03;

                // Update particle layers
                updateLayer(foreLayer, delta, time);
                updateLayer(midLayer, delta, time);
                updateLayer(dustLayer, delta, time);

                renderer.render(scene, camera);
            }

            animate();
            console.log('Winter Arc: Cinematic 3D Environmental WebGL scene initialized.');

        } catch (err) {
            console.warn('Winter Arc: WebGL environment failed to initialize:', err);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initWinterArcEnvironment);
    } else {
        initWinterArcEnvironment();
    }
})();
