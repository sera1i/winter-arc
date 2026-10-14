/**
 * Winter Arc — Master Cinematic 3D Environmental WebGL Engine (Three.js)
 * 
 * Inspired by award-winning Awwwards 3D experiences, Lapa Ninja, Skiper UI, and VengeanceUI.
 * 
 * Capabilities:
 * 1. Multi-Tier Spatial Snow & Blizzard Particle Systems (Foreground, Midground, Atmospheric Dust)
 * 2. 3D Tumbling Crystalline Ice Shards with Specular Lighting
 * 3. Dynamic Dual Lighting: Cold Alpine Skylight + Breathing Crimson Hearth Light
 * 4. Scroll-Driven Camera Choreography (Translating depth & pan on page scroll)
 * 5. Smooth Cursor Parallax with Exponential Interpolation (lerp)
 * 6. Interactive Card Spotlight & Sheen (Dynamic CSS variables --mouse-x, --mouse-y)
 * 7. Real-Time Theme Adaptation (Obsidian Void Dark vs Frosted Alpine Light)
 * 8. Performance & Accessibility: 60fps target, DPR capped at 2, mobile optimization,
 *    strict prefers-reduced-motion check, and automatic lifecycle pause.
 */

(function() {
    'use strict';

    function initWinterArcEnvironment() {
        var container = document.getElementById('three-env-container');
        if (!container) return;

        // 1. Accessibility Guard: prefers-reduced-motion
        if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            console.log('Winter Arc: Prefers-reduced-motion enabled. 3D WebGL loop suspended.');
            return;
        }

        // 2. WebGL & Three.js Availability Guard
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
                powerPreference: 'high-performance'
            });

            var dpr = Math.min(window.devicePixelRatio || 1, 2);
            renderer.setPixelRatio(dpr);
            renderer.setSize(width, height);
            renderer.setClearColor(0x000000, 0);

            // Clean previous children if any
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

            // 3. Theme Detection & Palette Configuration
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
                    hearthColor: light ? 0x991B1B : 0x7F1D1D,
                    shardColor: light ? 0x94A3B8 : 0xE2EAF2,
                    shardEmissive: light ? 0x334155 : 0x1E293B,
                    shardOpacity: light ? 0.40 : 0.65
                };
            }

            var colors = getThemeColors(isLight);
            var isMobile = (window.innerWidth < 768);

            // 4. Multi-Tier Snow Particles
            var foreCount = isMobile ? 35 : 95;
            var midCount  = isMobile ? 120 : 340;
            var dustCount = isMobile ? 220 : 580;

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

                    vel[idx] = (Math.random() - 0.5) * 0.018;             // drift x
                    vel[idx + 1] = -(0.018 + Math.random() * 0.038);       // fall y
                    vel[idx + 2] = (Math.random() - 0.5) * 0.006;         // flutter z

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

            var foreLayer = createParticleLayer(foreCount, isMobile ? 0.22 : 0.30, colors.foreColor, colors.foreOpacity, [10, 18], 30, 26);
            var midLayer  = createParticleLayer(midCount,  isMobile ? 0.12 : 0.16, colors.midColor,  colors.midOpacity,  [0, 10],  38, 30);
            var dustLayer = createParticleLayer(dustCount, isMobile ? 0.06 : 0.08, colors.dustColor, colors.dustOpacity, [-15, 0],  48, 36);

            // 5. 3D Tumbling Crystalline Ice Shards
            var shardGroup = new THREE.Group();
            var shardCount = isMobile ? 8 : 24;
            var shardGeom = new THREE.OctahedronGeometry(0.20, 0);
            var shardMat = new THREE.MeshPhongMaterial({
                color: colors.shardColor,
                emissive: colors.shardEmissive,
                specular: 0xFFFFFF,
                shininess: 90,
                transparent: true,
                opacity: colors.shardOpacity,
                flatShading: true
            });

            var shards = [];
            for (var s = 0; s < shardCount; s++) {
                var shard = new THREE.Mesh(shardGeom, shardMat);
                shard.position.set(
                    (Math.random() - 0.5) * 32,
                    (Math.random() - 0.5) * 24,
                    -4 + Math.random() * 16
                );
                var scale = 0.5 + Math.random() * 0.7;
                shard.scale.set(scale, scale * (0.8 + Math.random() * 0.6), scale);
                shard.rotSpeed = {
                    x: (Math.random() - 0.5) * 0.02,
                    y: (Math.random() - 0.5) * 0.02,
                    z: (Math.random() - 0.5) * 0.015
                };
                shard.driftSpeed = {
                    x: (Math.random() - 0.5) * 0.008,
                    y: -0.008 - Math.random() * 0.014
                };
                shards.push(shard);
                shardGroup.add(shard);
            }
            scene.add(shardGroup);

            // 6. Dual Cinematic Lighting: Cold Ambient + Pulsing Crimson Hearth
            var ambientLight = new THREE.AmbientLight(colors.lightColor, 0.7);
            scene.add(ambientLight);

            var dirLight = new THREE.DirectionalLight(0xE2EAF2, 0.5);
            dirLight.position.set(10, 15, 10);
            scene.add(dirLight);

            var hearthLight = new THREE.PointLight(colors.hearthColor, 1.0, 45);
            hearthLight.position.set(-10, -12, 6);
            scene.add(hearthLight);

            // 7. Theme Change Listener
            window.addEventListener('winter-arc-theme-change', function(e) {
                var newIsLight = (e.detail && e.detail.theme === 'light');
                var c = getThemeColors(newIsLight);

                foreLayer.mat.color.setHex(c.foreColor);
                foreLayer.mat.opacity = c.foreOpacity;

                midLayer.mat.color.setHex(c.midColor);
                midLayer.mat.opacity = c.midOpacity;

                dustLayer.mat.color.setHex(c.dustColor);
                dustLayer.mat.opacity = c.dustOpacity;

                shardMat.color.setHex(c.shardColor);
                shardMat.emissive.setHex(c.shardEmissive);
                shardMat.opacity = c.shardOpacity;

                ambientLight.color.setHex(c.lightColor);
                hearthLight.color.setHex(c.hearthColor);
            });

            // 8. Interactive Cursor Parallax
            var mouseX = 0, mouseY = 0;
            var targetX = 0, targetY = 0;
            var windowHalfX = window.innerWidth / 2;
            var windowHalfY = window.innerHeight / 2;

            function onMouseMove(e) {
                mouseX = (e.clientX - windowHalfX) / windowHalfX;
                mouseY = (e.clientY - windowHalfY) / windowHalfY;
            }

            window.addEventListener('mousemove', onMouseMove, { passive: true });

            // 9. Scroll-Driven Camera Dynamics
            var scrollY = window.scrollY || 0;
            var targetScrollY = 0;

            function onScroll() {
                targetScrollY = window.scrollY || 0;
            }

            window.addEventListener('scroll', onScroll, { passive: true });

            // 10. Performance & Lifecycle Controls
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

            // 11. Responsive Viewport Resize
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

            // 12. Animation Loop
            var clock = new THREE.Clock();

            function updateParticleLayer(layer, time) {
                var pos = layer.geom.attributes.position.array;
                var vel = layer.vel;
                var phases = layer.phases;
                var count = layer.count;

                for (var i = 0; i < count; i++) {
                    var idx = i * 3;
                    var flutter = Math.sin(time * 1.5 + phases[i]) * 0.009;

                    pos[idx] += vel[idx] + flutter;
                    pos[idx + 1] += vel[idx + 1];
                    pos[idx + 2] += vel[idx + 2];

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

            function updateShards(delta) {
                for (var s = 0; s < shards.length; s++) {
                    var sh = shards[s];
                    sh.rotation.x += sh.rotSpeed.x;
                    sh.rotation.y += sh.rotSpeed.y;
                    sh.rotation.z += sh.rotSpeed.z;

                    sh.position.x += sh.driftSpeed.x;
                    sh.position.y += sh.driftSpeed.y;

                    if (sh.position.y < -14) {
                        sh.position.y = 14;
                        sh.position.x = (Math.random() - 0.5) * 32;
                    }
                    if (sh.position.x > 18) sh.position.x = -18;
                    else if (sh.position.x < -18) sh.position.x = 18;
                }
            }

            function animate() {
                requestAnimationFrame(animate);

                if (!isVisible) return;

                var delta = clock.getDelta();
                var time = clock.getElapsedTime();

                // Parallax Camera Interpolation (lerp)
                targetX += (mouseX * 1.4 - targetX) * 0.04;
                targetY += (mouseY * 0.9 - targetY) * 0.04;

                // Scroll Interpolation
                scrollY += (targetScrollY - scrollY) * 0.06;
                var scrollFactor = Math.min(scrollY / 1800, 1.8);

                // Smooth forward dolly and spatial pan on scroll
                camera.position.x = targetX;
                camera.position.y = -targetY - (scrollFactor * 2.2);
                camera.position.z = 20 - (scrollFactor * 3.8);
                camera.rotation.y = -targetX * 0.03;
                camera.rotation.x = -targetY * 0.03 - (scrollFactor * 0.06);

                // Crimson Hearth breathing light oscillation
                hearthLight.intensity = (isLight ? 0.6 : 0.9) + Math.sin(time * 1.6) * 0.25;

                // Update particle layers & 3D shards
                updateParticleLayer(foreLayer, time);
                updateParticleLayer(midLayer, time);
                updateParticleLayer(dustLayer, time);
                updateShards(delta);

                renderer.render(scene, camera);
            }

            animate();
            console.log('Winter Arc: Master Cinematic 3D Spatial WebGL environment active.');

        } catch (err) {
            console.warn('Winter Arc: WebGL environment initialization failed:', err);
        }
    }

    // 13. Interactive Card Spotlight & Pointer Feedback (Skiper UI & VengeanceUI inspired)
    function initCardSpotlight() {
        document.addEventListener('pointermove', function(e) {
            var target = e.target;
            if (!target || !target.closest) return;
            var card = target.closest('.wa-card, .wa-sanctum-slab, .wa-card-primary, .wa-form-card, .btn-primary');
            if (card) {
                var rect = card.getBoundingClientRect();
                card.style.setProperty('--mouse-x', (e.clientX - rect.left) + 'px');
                card.style.setProperty('--mouse-y', (e.clientY - rect.top) + 'px');
            }
        }, { passive: true });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            initWinterArcEnvironment();
            initCardSpotlight();
        });
    } else {
        initWinterArcEnvironment();
        initCardSpotlight();
    }
})();
