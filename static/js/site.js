/* TANPA — interactions. Crafted by JamiiTek. No dependencies. */
(function () {
  "use strict";
  var d = document, root = d.documentElement;
  root.classList.remove("no-js");
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* nav state + reading progress */
  var shell = d.querySelector(".nav-shell"), bar = d.querySelector(".progress-bar");
  function onScroll() {
    var y = window.scrollY;
    if (shell) shell.classList.toggle("scrolled", y > 40);
    if (bar) {
      var h = d.body.scrollHeight - window.innerHeight;
      bar.style.width = (h > 0 ? (y / h) * 100 : 0) + "%";
    }
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  var burger = d.querySelector("[data-burger]");
  if (burger) burger.addEventListener("click", function () {
    var open = d.body.classList.toggle("nav-open");
    burger.setAttribute("aria-expanded", open);
  });
  d.querySelectorAll(".nav-links a").forEach(function (a) {
    a.addEventListener("click", function () { d.body.classList.remove("nav-open"); });
  });

  /* toasts */
  d.querySelectorAll(".toast").forEach(function (t, i) {
    var close = function () { t.style.transition = ".4s"; t.style.opacity = 0; t.style.transform = "translateY(-10px)"; setTimeout(function () { t.remove(); }, 400); };
    t.querySelector("button").addEventListener("click", close);
    setTimeout(close, 7000 + i * 800);
  });

  /* reveal on scroll */
  var io = "IntersectionObserver" in window ? new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) { e.target.classList.add("revealed"); io.unobserve(e.target); if (e.target.hasAttribute("data-count")) count(e.target); }
    });
  }, { threshold: 0.15, rootMargin: "0px 0px -40px 0px" }) : null;
  d.querySelectorAll("[data-reveal],[data-count],.journey").forEach(function (el) {
    if (io && !reduce) io.observe(el); else { el.classList.add("revealed"); if (el.hasAttribute("data-count")) count(el); }
  });

  /* counters */
  function count(el) {
    var target = parseInt(el.getAttribute("data-count"), 10) || 0, start = null, dur = 1600;
    if (reduce || target === 0) { el.textContent = target.toLocaleString(); return; }
    function step(ts) {
      if (!start) start = ts;
      var p = Math.min((ts - start) / dur, 1), eased = 1 - Math.pow(1 - p, 4);
      el.textContent = Math.round(target * eased).toLocaleString();
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  /* word rotator */
  d.querySelectorAll(".rotator").forEach(function (r) {
    var items = r.children, i = 0;
    if (items.length < 2 || reduce) return;
    setInterval(function () {
      items[i].classList.remove("on"); i = (i + 1) % items.length; items[i].classList.add("on");
    }, 2600);
  });

  /* countdowns */
  d.querySelectorAll("[data-countdown]").forEach(function (c) {
    var end = new Date(c.getAttribute("data-countdown")).getTime();
    var els = c.querySelectorAll("b");
    function tick() {
      var s = Math.max(0, Math.floor((end - Date.now()) / 1000));
      var v = [Math.floor(s / 86400), Math.floor(s % 86400 / 3600), Math.floor(s % 3600 / 60), s % 60];
      v.forEach(function (n, i) { if (els[i]) els[i].textContent = (i && n < 10 ? "0" : "") + n; });
    }
    tick(); setInterval(tick, 1000);
  });

  /* spotlight tiles */
  d.querySelectorAll(".tile").forEach(function (t) {
    t.addEventListener("pointermove", function (e) {
      var r = t.getBoundingClientRect();
      t.style.setProperty("--mx", (e.clientX - r.left) + "px");
      t.style.setProperty("--my", (e.clientY - r.top) + "px");
    });
  });

  /* 3D tilt card */
  d.querySelectorAll(".card3d").forEach(function (c) {
    if (reduce) return;
    var stage = c.parentElement, auto = true, t0 = performance.now();
    function idle(ts) {
      if (!auto) return;
      var a = (ts - t0) / 1000;
      c.style.setProperty("--ry", (Math.sin(a * .8) * 12).toFixed(2) + "deg");
      c.style.setProperty("--rx", (Math.cos(a * .6) * 6).toFixed(2) + "deg");
      c.style.setProperty("--shine", (Math.sin(a * .8) * 80).toFixed(0) + "%");
      requestAnimationFrame(idle);
    }
    requestAnimationFrame(idle);
    stage.addEventListener("pointermove", function (e) {
      auto = false;
      var r = c.getBoundingClientRect(), x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5;
      c.style.setProperty("--ry", (x * 26).toFixed(2) + "deg");
      c.style.setProperty("--rx", (-y * 18).toFixed(2) + "deg");
      c.style.setProperty("--shine", (x * 160).toFixed(0) + "%");
    });
    stage.addEventListener("pointerleave", function () { auto = true; t0 = performance.now(); requestAnimationFrame(idle); });
  });

  /* lightbox */
  var lb = d.querySelector(".lightbox");
  if (lb) {
    var items = Array.prototype.slice.call(d.querySelectorAll("[data-lightbox]")), idx = 0;
    var img = lb.querySelector("img"), cap = lb.querySelector("p");
    function show(i) { idx = (i + items.length) % items.length; img.src = items[idx].getAttribute("data-lightbox"); cap.textContent = items[idx].getAttribute("data-caption") || ""; }
    items.forEach(function (it, i) { it.addEventListener("click", function (e) { e.preventDefault(); show(i); lb.classList.add("open"); d.body.style.overflow = "hidden"; }); });
    function close() { lb.classList.remove("open"); d.body.style.overflow = ""; }
    lb.querySelector(".lb-close").addEventListener("click", close);
    lb.querySelector(".lb-prev").addEventListener("click", function () { show(idx - 1); });
    lb.querySelector(".lb-next").addEventListener("click", function () { show(idx + 1); });
    lb.addEventListener("click", function (e) { if (e.target === lb) close(); });
    d.addEventListener("keydown", function (e) {
      if (!lb.classList.contains("open")) return;
      if (e.key === "Escape") close(); if (e.key === "ArrowLeft") show(idx - 1); if (e.key === "ArrowRight") show(idx + 1);
    });
  }

  /* registration wizard */
  var wiz = d.querySelector("[data-wizard]");
  if (wiz) {
    var steps = wiz.querySelectorAll(".wstep"), tabs = wiz.querySelectorAll(".steps-bar button"), cur = 0;
    function go(n) {
      cur = Math.max(0, Math.min(n, steps.length - 1));
      steps.forEach(function (s, i) { s.classList.toggle("on", i === cur); });
      tabs.forEach(function (t, i) { t.classList.toggle("on", i === cur); t.classList.toggle("done", i < cur); });
      var top = wiz.getBoundingClientRect().top + window.scrollY - 110;
      if (window.scrollY > top) window.scrollTo({ top: top, behavior: reduce ? "auto" : "smooth" });
    }
    function valid(step) {
      var ok = true;
      step.querySelectorAll("input,select,textarea").forEach(function (f) {
        if (!f.checkValidity()) { ok = false; f.closest(".field") && f.closest(".field").classList.add("has-error"); }
      });
      if (!ok) { var bad = step.querySelector(":invalid"); if (bad) bad.reportValidity(); }
      return ok;
    }
    wiz.querySelectorAll("[data-next]").forEach(function (b) { b.addEventListener("click", function () { if (valid(steps[cur])) go(cur + 1); }); });
    wiz.querySelectorAll("[data-prev]").forEach(function (b) { b.addEventListener("click", function () { go(cur - 1); }); });
    tabs.forEach(function (t, i) { t.addEventListener("click", function () { if (i < cur || valid(steps[cur])) go(i); }); });
    var firstErr = -1;
    steps.forEach(function (s, i) { if (firstErr < 0 && s.querySelector(".has-error,.non-field")) firstErr = i; });
    go(firstErr > 0 ? firstErr : 0);
    wiz.querySelectorAll("input,select").forEach(function (f) { f.addEventListener("input", function () { f.closest(".field") && f.closest(".field").classList.remove("has-error"); }); });
  }

  /* photo preview */
  d.querySelectorAll("[data-uploader]").forEach(function (u) {
    var input = u.querySelector("input[type=file]"), pv = u.querySelector(".pv"), name = u.querySelector("[data-name]");
    input.addEventListener("change", function () {
      var f = input.files && input.files[0];
      if (!f) return;
      if (name) name.textContent = f.name;
      if (f.type.indexOf("image") === 0) { var url = URL.createObjectURL(f); pv.style.backgroundImage = "url(" + url + ")"; pv.innerHTML = ""; }
    });
  });

  /* password strength */
  d.querySelectorAll("[data-strength]").forEach(function (meter) {
    var input = d.getElementById(meter.getAttribute("data-strength")), fill = meter.querySelector("i");
    if (!input) return;
    input.addEventListener("input", function () {
      var v = input.value, s = 0;
      if (v.length >= 8) s++; if (v.length >= 12) s++; if (/[A-Z]/.test(v) && /[a-z]/.test(v)) s++; if (/\d/.test(v)) s++; if (/[^A-Za-z0-9]/.test(v)) s++;
      var colors = ["#ef4444", "#ef4444", "#f59e0b", "#eab308", "#22c55e", "#0a8f3c"];
      fill.style.width = (s / 5 * 100) + "%"; fill.style.background = colors[s];
    });
  });

  /* copy to clipboard */
  d.querySelectorAll("[data-copy]").forEach(function (b) {
    b.addEventListener("click", function () {
      navigator.clipboard && navigator.clipboard.writeText(b.getAttribute("data-copy")).then(function () {
        var t = b.textContent; b.textContent = "Copied ✓"; setTimeout(function () { b.textContent = t; }, 1600);
      });
    });
  });

  /* magnetic buttons */
  if (!reduce && window.matchMedia("(pointer:fine)").matches) {
    d.querySelectorAll("[data-magnetic]").forEach(function (b) {
      b.addEventListener("pointermove", function (e) {
        var r = b.getBoundingClientRect();
        b.style.transform = "translate(" + ((e.clientX - r.left - r.width / 2) * .18) + "px," + ((e.clientY - r.top - r.height / 2) * .28) + "px)";
      });
      b.addEventListener("pointerleave", function () { b.style.transform = ""; });
    });
  }
})();
/* flip cards: tap/click or Enter to turn */
(function () {
  document.querySelectorAll("[data-flip]").forEach(function (f) {
    function turn() {
      var inner = f.querySelector(".idc-flip-in");
      if (!f.classList.contains("manual")) {
        // freeze the auto animation on the side currently showing
        var m = getComputedStyle(inner).transform, showingBack = false;
        if (m && m !== "none") { var v = m.split("(")[1].split(")")[0].split(","); showingBack = parseFloat(v[0]) < 0; }
        f.classList.add("manual"); f.classList.toggle("turned", !showingBack);
      } else { f.classList.toggle("turned"); }
    }
    f.addEventListener("click", turn);
    f.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); turn(); } });
  });
})();
