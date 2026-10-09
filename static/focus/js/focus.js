/**
 * Focus Mode — Cinematic Monolith Clock & Countdown Timer
 * Extracted verbatim from Focus mode.html prototype.
 */
(function() {
  'use strict';

  // ---------- 3D drum digits ----------
  function Drum(solo) {
    var el = document.createElement('div');
    el.className = 'drum' + (solo ? ' solo' : '');
    var faces = [];
    for (var i = 0; i < 10; i++) {
      var f = document.createElement('div');
      f.className = 'face';
      f.style.setProperty('--i', i);
      f.textContent = i;
      if (solo) f.style.opacity = 0;
      faces.push(f);
      el.appendChild(f);
    }
    var angle = 0, cur = null;
    return {
      el: el,
      set: function(d) {
        if (cur === d) return;
        if (cur === null) angle = -d * 36;
        else angle -= ((d - cur + 10) % 10) * 36;
        cur = d;
        faces.forEach(function(f, i) {
          var dd = Math.min((i - d + 10) % 10, (d - i + 10) % 10);
          f.style.opacity = solo ? (dd === 0 ? 1 : 0) : ([1, .28, .1][dd] || 0);
        });
        el.style.transform = 'translateZ(-1.54em) rotateX(' + angle + 'deg)';
      }
    };
  }

  function build(root, groups, solo) {
    var ds = [];
    groups.forEach(function(n, gi) {
      if (gi) {
        var s = document.createElement('div');
        s.className = 'sep s' + gi;
        s.textContent = ':';
        root.appendChild(s);
      }
      var g = document.createElement('div');
      g.className = 'grp ' + (gi === 2 && groups.length === 3 ? 'sec' : '');
      for (var k = 0; k < 2; k++) {
        var d = Drum(solo);
        g.appendChild(d.el);
        ds.push(d);
      }
      root.appendChild(g);
    });
    return function(vals) {
      var s = vals.map(function(v) {
        return (v < 10 ? '0' : '') + v;
      }).join('');
      for (var i = 0; i < ds.length; i++) ds[i].set(+s[i]);
    };
  }

  var mainClockEl = document.getElementById('mainClock');
  var cdEl = document.getElementById('cd');
  if (!mainClockEl || !cdEl) return;

  var mainSet = build(mainClockEl, [0, 0, 0]);
  var cdSet = build(cdEl, [0, 0], true);

  // ---------- Countdown ----------
  var minutes = 25, remain = minutes * 60, running = false, endAt = 0;
  var go = document.getElementById('go'), timerEl = document.getElementById('timer');

  function drawCd() {
    cdSet([Math.floor(remain / 60), remain % 60]);
  }

  function setMin(m) {
    var newM = Math.max(5, Math.min(95, m));
    var deltaSec = (newM - minutes) * 60;
    minutes = newM;
    if (!running) {
      remain = minutes * 60;
      if (timerEl) timerEl.classList.remove('done');
      drawCd();
    } else {
      endAt += deltaSec * 1000;
      remain = Math.max(0, Math.ceil((endAt - Date.now()) / 1000));
      if (timerEl) timerEl.classList.remove('done');
      drawCd();
    }
  }

  if (go) {
    go.onclick = function() {
      if (running) {
        running = false;
        go.textContent = 'Resume';
      } else {
        if (remain <= 0) remain = minutes * 60;
        if (timerEl) timerEl.classList.remove('done');
        endAt = Date.now() + remain * 1000;
        running = true;
        go.textContent = 'Pause';
      }
    };
  }

  var plusBtn = document.getElementById('plus');
  if (plusBtn) {
    plusBtn.onclick = function() {
      setMin(minutes + 5);
    };
  }

  var minusBtn = document.getElementById('minus');
  if (minusBtn) {
    minusBtn.onclick = function() {
      setMin(minutes - 5);
    };
  }

  var resetBtn = document.getElementById('reset');
  if (resetBtn) {
    resetBtn.onclick = function() {
      running = false;
      if (go) go.textContent = 'Start';
      remain = minutes * 60;
      if (timerEl) timerEl.classList.remove('done');
      drawCd();
    };
  }

  drawCd();

  // ---------- Fullscreen ----------
  var fsBtn = document.getElementById('fullscreen-btn');
  var fsEnterIcon = document.getElementById('fs-enter-icon');
  var fsExitIcon = document.getElementById('fs-exit-icon');
  var fsLabel = document.getElementById('fs-label');

  function isFullscreen() {
    return !!(
      document.fullscreenElement ||
      document.webkitFullscreenElement ||
      document.mozFullScreenElement ||
      document.msFullscreenElement
    );
  }

  function updateFullscreenUI() {
    var inFs = isFullscreen();
    if (fsEnterIcon) fsEnterIcon.classList.toggle('hidden', inFs);
    if (fsExitIcon) fsExitIcon.classList.toggle('hidden', !inFs);
    if (fsLabel) fsLabel.textContent = inFs ? 'Exit Fullscreen' : 'Fullscreen';
    if (fsBtn) {
      var label = inFs ? 'Exit Fullscreen' : 'Enter Fullscreen';
      fsBtn.setAttribute('aria-label', label);
      fsBtn.setAttribute('title', label);
    }
  }

  if (fsBtn) {
    fsBtn.addEventListener('click', function(e) {
      e.preventDefault();
      if (!isFullscreen()) {
        var elem = document.documentElement;
        if (elem.requestFullscreen) {
          elem.requestFullscreen().catch(function() {});
        } else if (elem.webkitRequestFullscreen) {
          elem.webkitRequestFullscreen();
        } else if (elem.mozRequestFullScreen) {
          elem.mozRequestFullScreen();
        } else if (elem.msRequestFullscreen) {
          elem.msRequestFullscreen();
        }
      } else {
        if (document.exitFullscreen) {
          document.exitFullscreen().catch(function() {});
        } else if (document.webkitExitFullscreen) {
          document.webkitExitFullscreen();
        } else if (document.mozCancelFullScreen) {
          document.mozCancelFullScreen();
        } else if (document.msExitFullscreen) {
          document.msExitFullscreen();
        }
      }
    });
  }

  ['fullscreenchange', 'webkitfullscreenchange', 'mozfullscreenchange', 'MSFullscreenChange'].forEach(function(ev) {
    document.addEventListener(ev, updateFullscreenUI);
  });
  updateFullscreenUI();

  // ---------- Tick ----------
  var lastSec = -1;
  var ampmEl = document.getElementById('ampm');
  function tick() {
    var n = new Date(), s = n.getSeconds();
    if (s !== lastSec) {
      lastSec = s;
      var h = n.getHours();
      mainSet([h % 12 || 12, n.getMinutes(), s]);
      if (ampmEl) ampmEl.textContent = h < 12 ? 'AM' : 'PM';
      if (n.getMinutes() % 5 === 0 && s === 0) rainStart();
    }
    if (running) {
      var r = Math.max(0, Math.ceil((endAt - Date.now()) / 1000));
      if (r !== remain) {
        remain = r;
        drawCd();
      }
      if (r <= 0) {
        running = false;
        if (go) go.textContent = 'Start';
        timerEl.classList.add('done');
      }
    }
  }
  setInterval(tick, 200);
  tick();

  // ---------- 3D tilt (pointer + device) ----------
  var stage = document.getElementById('stage'), tx = 0, ty = 0, cx = 0, cy = 0, t0 = performance.now();
  addEventListener('pointermove', function(e) {
    tx = (e.clientX / innerWidth - .5) * 2;
    ty = (e.clientY / innerHeight - .5) * 2;
  });
  addEventListener('pointerdown', function() {
    if (window.DeviceOrientationEvent && DeviceOrientationEvent.requestPermission) {
      DeviceOrientationEvent.requestPermission().catch(function() {});
    }
  }, { once: true });
  addEventListener('deviceorientation', function(e) {
    if (e.gamma == null) return;
    tx = Math.max(-1, Math.min(1, e.gamma / 30));
    ty = Math.max(-1, Math.min(1, (e.beta - 45) / 30));
  });

  // ---------- Digital rain ----------
  var cv = document.getElementById('rain');
  if (!cv) return;
  var ctx = cv.getContext('2d'), W = 0, H = 0, dpr = 1;
  var streams = [], rainT = 0, rainOn = false, clockEl = document.getElementById('mainClock');

  function size() {
    dpr = Math.min(devicePixelRatio || 1, 2);
    W = innerWidth;
    H = innerHeight;
    cv.width = W * dpr;
    cv.height = H * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  addEventListener('resize', size);
  size();

  function rainStart() {
    streams = [];
    rainT = 0;
    rainOn = true;
    var count = Math.round(W / 14);
    for (var i = 0; i < count; i++) {
      var z = .25 + Math.random() * .75, fs = 9 + z * 24, len = 8 + Math.floor(Math.random() * 14);
      streams.push({
        x: Math.random() * W,
        z: z,
        fs: fs,
        len: len,
        sp: 140 + z * 620,
        delay: Math.random() * 2.6,
        y: -len * fs,
        g: [],
        gt: 0
      });
    }
    if (clockEl) {
      clockEl.classList.remove('glitch');
      void clockEl.offsetWidth;
      clockEl.classList.add('glitch');
    }
  }

  addEventListener('keydown', function(e) {
    if (e.key === 'r' || e.key === 'R') rainStart();
  });

  var last = performance.now();
  function frame(now) {
    var dt = Math.min(.05, (now - last) / 1000);
    last = now;
    var rm = matchMedia('(prefers-reduced-motion:reduce)').matches;
    var sway = rm ? 0 : Math.sin((now - t0) / 2600);
    cx += ((tx * 9 + sway * 2.5) - cx) * .06;
    cy += ((-ty * 7 + Math.cos((now - t0) / 3100) * 2) - cy) * .06;
    if (!rm && stage) stage.style.transform = 'rotateY(' + cx + 'deg) rotateX(' + cy + 'deg)';
    ctx.clearRect(0, 0, W, H);
    if (rainOn) {
      rainT += dt;
      var alive = 0;
      ctx.textAlign = 'center';
      streams.forEach(function(s) {
        if (rainT < s.delay) {
          alive++;
          return;
        }
        s.y += s.sp * dt;
        s.gt -= dt;
        if (s.gt <= 0) {
          s.gt = .07;
          s.g = [];
          for (var k = 0; k < s.len; k++) s.g.push((Math.random() * 10) | 0);
        }
        if (s.y - s.len * s.fs < H) alive++;
        ctx.font = '200 ' + s.fs + 'px Isometra,"Barlow Condensed",monospace';
        for (var k = 0; k < s.len; k++) {
          var y = s.y - k * s.fs;
          if (y < -s.fs || y > H + s.fs) continue;
          var a = (1 - k / s.len);
          a = a * a * s.z;
          ctx.fillStyle = 'rgba(255,255,255,' + (k === 0 ? Math.min(1, s.z + .3) : a * .8) + ')';
          ctx.fillText(s.g[k], s.x, y);
        }
      });
      if (!alive) rainOn = false;
    }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
})();
