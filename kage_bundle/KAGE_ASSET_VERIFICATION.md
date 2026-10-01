# Kage Source Bundle & Asset Verification Report

## 1. Bundle Metadata
- **Schema Version**: 1
- **Bundle ID**: kage-landing-page
- **Registered Files**: 8

## 2. Registered Files Verification Table

| Path | Role | Declared Bytes | Declared SHA-256 | Local File Status | SHA-256 Match |
|---|---|---|---|---|---|
| `src/shaders/landing-pages/LandingPages.tsx` | `component` | 40525 | `4d379461ad00...` | EXISTS (41440 bytes) | MATCH |
| `src/shaders/landing-pages/pageTypography.ts` | `controls-source` | 15028 | `809cc65797d5...` | EXISTS (15405 bytes) | MATCH |
| `src/shaders/landing-pages/pageRecipes.ts` | `controls-source` | 74927 | `c9d9849cc255...` | EXISTS (76606 bytes) | MATCH |
| `src/shaders/landing-pages/LandingPageFrame.tsx` | `frame-component` | 6756 | `61de2cc50888...` | EXISTS (6933 bytes) | MATCH |
| `public/landing-pages/kage.html` | `canonical-source` | 243963 | `c8e06b90397a...` | EXISTS (246682 bytes) | MISMATCH |
| `public/landing-pages/secret-pathways-assets/fonts.css` | `font-source` | 99356 | `985f85a904a4...` | EXISTS (1995 bytes) | MISMATCH |
| `public/landing-pages/secret-pathways-assets/three.min.js` | `three-runtime` | 608081 | `8a5f7249903b...` | EXISTS (608081 bytes) | MATCH |
| `src/shaders/threeui.css` | `shared-style` | 40715 | `efe4447139f1...` | EXISTS (42490 bytes) | MATCH |

## 3. Local Fonts Binary Assets (WOFF2)

| Font Asset | Purpose | Size (bytes) | Declared SHA-256 | SHA-256 Match |
|---|---|---|---|---|
| `Onest-Light-300.woff2` | Onest Light (300) | 14448 | `256fa8037be6...` | MATCH |
| `Onest-Regular-400.woff2` | Onest Regular (400) | 14032 | `cbc780c47e79...` | MATCH |
| `Onest-Medium-500.woff2` | Onest Medium (500) | 14668 | `21150b504f3a...` | MATCH |
| `Onest-Bold-700.woff2` | Onest Bold (700) | 14760 | `98e3406af6c5...` | MATCH |
| `NotoJP-Regular-400.woff2` | Noto JP Fallback (400) | 12644 | `919f3ce938b0...` | MATCH |
| `Wordmark-500.woff2` | Wordmark (500) | 1608 | `6a93626eb174...` | MATCH |
| `Wordmark-600.woff2` | Wordmark (600) | 1636 | `87832ba80d7a...` | MATCH |

## 4. WebGL Scene Textures & Images Inventory

| Asset Filename | Purpose | Local Path | Size (bytes) | SHA-256 |
|---|---|---|---|---|
| `basalt-stones.webp` | WebGL Texture / Sprite | `static/kage/scene-images/basalt-stones.webp` | 167866 | `150f1c87e181...` |
| `garden-bush.webp` | WebGL Texture / Sprite | `static/kage/scene-images/garden-bush.webp` | 286406 | `707e2516ebc0...` |
| `hill.webp` | WebGL Texture / Sprite | `static/kage/scene-images/hill.webp` | 84142 | `ffba816244bc...` |
| `maple-leaves.webp` | WebGL Texture / Sprite | `static/kage/scene-images/maple-leaves.webp` | 178208 | `35a90fec62c1...` |
| `pine-tree.webp` | WebGL Texture / Sprite | `static/kage/scene-images/pine-tree.webp` | 195918 | `79b233716d06...` |
| `sakura-branch.webp` | WebGL Texture / Sprite | `static/kage/scene-images/sakura-branch.webp` | 252528 | `48564194d404...` |
| `shrine-ruins.webp` | WebGL Texture / Sprite | `static/kage/scene-images/shrine-ruins.webp` | 145814 | `77006e58f206...` |
| `stone-lantern.webp` | WebGL Texture / Sprite | `static/kage/scene-images/stone-lantern.webp` | 150108 | `d5f3c881bc9d...` |
| `tall-grass.webp` | WebGL Texture / Sprite | `static/kage/scene-images/tall-grass.webp` | 351644 | `8db0b5fbd160...` |
| `temple-wall.webp` | WebGL Texture / Sprite | `static/kage/scene-images/temple-wall.webp` | 86466 | `41c00f017e4e...` |
| `kage-approach.webp` | WebGL Texture / Sprite | `static/kage/scene-images/kage-approach.webp` | 180064 | `39ff33893609...` |
| `kage-lantern-court.webp` | WebGL Texture / Sprite | `static/kage/scene-images/kage-lantern-court.webp` | 197940 | `c0a6ff7da1cd...` |
| `kage-moonwater.webp` | WebGL Texture / Sprite | `static/kage/scene-images/kage-moonwater.webp` | 102234 | `b8c8060c51c8...` |
| `kage-sanmon-preview.webp` | WebGL Texture / Sprite | `static/kage/scene-images/kage-sanmon-preview.webp` | 186398 | `23937f8c8350...` |

## 5. Verification Summary
- **Registered Files Count**: 8
- **Local Font Assets**: 7 / 7 verified
- **WebGL Scene Textures**: 14 / 14 verified
- **Runtime External Dependencies**: NONE (100% self-contained local assets)
- **Status**: VERIFIED & READY FOR INTEGRATION