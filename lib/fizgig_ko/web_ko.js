/* Fizgig 한글화 — 웹 UI(Fizgig 8+) 번역기.
 *
 * fizgig_ko.web 이 서버가 내보내는 메인 페이지(index.html)에 이 스크립트와 사전(window.__KO_CAT)을
 * 끼워 넣습니다. Fizgig 의 파일은 한 글자도 바꾸지 않습니다.
 *
 * 사전 조회 규칙은 lib/fizgig_ko/catalog.py 와 같습니다(정확 일치 → 앞뒤 공백 무시 → {0} 템플릿 →
 * 끝 구두점 → 줄/" · " 단위 조각). tests/test_web_ko.py 가 두 구현이 같은 결과를 내는지 대조합니다.
 *
 * 번역하는 것: 화면의 텍스트 노드, title / placeholder / alt / aria-label / label 속성.
 * 번역하지 않는 것: 입력창의 값(앱이 읽어 가는 값), <pre>(로그, ComfyUI 설정 값), <textarea>,
 *   translate="no" 또는 class="notranslate" 인 곳.
 *
 * 끄기: 주소 끝에 ?ko=off  (또는 서버를 FIZGIG_LANG=en 으로 실행)
 */
(function () {
  "use strict";
  var W = (typeof window !== "undefined") ? window : globalThis;     // globalThis: the node parity test
  if (W.__ko) return;
  try { if (/[?&]ko=off(&|$)/.test(location.search)) return; } catch (e) { /* no location: carry on */ }

  var DATA = (W.__KO_CAT && W.__KO_CAT.m) || {};

  // ---- 사전 (catalog.py 와 같은 규칙) ----------------------------------------------------------------
  var PH = /\{(\d+)\}/;
  var PH_G = /\{(\d+)\}/g;
  var SEG = /(\n|\s+[·|]\s+)/;
  var SEG_ANY = /\n|\s+[·|]\s+/;
  var TRAIL = /(\s*(?::|：|…|\.\.\.|\*|!|\?))+\s*$/;
  var COUNT_LEAD = /^[~+\-–]?\d/;
  var CACHE_MAX = 4096;

  function esc(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }

  function splitWs(s) {
    var core = s.trim();
    if (!core) return ["", s, ""];
    var start = s.length - s.trimStart().length;
    var end = s.trimEnd().length;
    return [s.slice(0, start), s.slice(start, end), s.slice(end)];
  }

  function Tpl(en, ko) {
    this.en = en;
    this.ko = ko;
    var parts = en.split(PH);                       // [lit0, idx0, lit1, idx1, ..., litN]
    var pat = "^", seen = {}, no = {}, n = 0;
    this.order = [];
    this.allowsSep = false;
    for (var i = 0; i < parts.length; i++) {
      if (i % 2 === 0) {
        pat += esc(parts[i]);
        if (SEG_ANY.test(parts[i])) this.allowsSep = true;
      } else if (seen[parts[i]]) {
        pat += "(?:\\" + no[parts[i]] + ")";
      } else {
        seen[parts[i]] = true;
        no[parts[i]] = ++n;
        this.order.push(parts[i]);
        pat += "([\\s\\S]*?)";
      }
    }
    this.re = new RegExp(pat + "$");
    this.prefix = parts[0];
    // "{0} clip{1}", "{0} files{1}{2}": a placeholder, ONE lowercase word, nothing else is a count
    // ("3 clips"); its first capture has to start like a number, or it would swallow "Save clip"
    this.first = parts.length > 2 ? parts[1] : null;
    var rest = true;
    for (var k = 4; k < parts.length; k += 2) if (parts[k] !== "") rest = false;
    this.countLead = !parts[0] && parts.length > 2 && /^ [a-z]+$/.test(parts[2]) && rest;
  }

  Tpl.prototype.apply = function (s, inner) {
    var m = this.re.exec(s);
    if (!m) return null;
    var g = {}, i, k;
    for (i = 0; i < this.order.length; i++) g[this.order[i]] = m[i + 1];
    if (this.countLead && !COUNT_LEAD.test(g[this.first] || "")) return null;
    // a template whose own text has no line break / " · " must not swallow one inside a placeholder
    if (!this.allowsSep) {
      for (k in g) if (g[k] && SEG_ANY.test(g[k])) return null;
    }
    if (inner) for (k in g) g[k] = inner(g[k]);
    return this.ko.replace(PH_G, function (mm, num) { return g[num] !== undefined ? g[num] : ""; });
  };

  var exact = new Map(), byPrefix = new Map(), wild = [], cache = new Map();

  function register(en, ko, derived) {
    if (PH.test(en)) {
      var t = new Tpl(en, ko);
      if (t.prefix) {
        var key = t.prefix.slice(0, 3);
        if (!byPrefix.has(key)) byPrefix.set(key, []);
        byPrefix.get(key).push(t);
      } else {
        wild.push(t);
      }
    } else if (en !== ko) {
      if (derived) { if (!exact.has(en)) exact.set(en, ko); } else exact.set(en, ko);
    }
  }

  (function build() {
    var pairs = [], en;
    for (en in DATA) {
      if (typeof en === "string" && typeof DATA[en] === "string" && DATA[en]) pairs.push([en, DATA[en]]);
    }
    pairs.forEach(function (p) { register(p[0], p[1], false); });
    // a key carrying its own line breaks is never looked up whole (the lookup splits on them):
    // register the stripped form too, in a second pass so an explicit entry always wins
    pairs.forEach(function (p) {
      var ce = p[0].trim(), ck = p[1].trim();
      if (ce !== p[0] && ce && ck) register(ce, ck, true);
    });
  })();

  function lookup(s, depth) {
    var hit = cache.get(s);
    if (hit !== undefined) return hit;
    var inner = null;
    if (depth < 3) {
      inner = function (v) {
        if (!v || v.length > 400) return v;
        try { return lookup(v, depth + 1); } catch (e) { return v; }
      };
    }
    var out = exact.get(s);
    if (out === undefined) {
      var w = splitWs(s), lead = w[0], core = w[1], trail = w[2];
      if (core && core !== s) {
        var ch = exact.get(core);
        if (ch !== undefined) out = lead + ch + trail;
      }
      if (out === undefined) {
        var cands = [s, core];
        for (var ci = 0; ci < 2 && out === undefined; ci++) {
          var cand = cands[ci];
          if (!cand) continue;
          // a template is bucketed under the first 3 chars of its literal prefix, or the whole
          // prefix when shorter: probe the 3-, 2- and 1-char keys, most specific first
          for (var n = 3; n >= 1 && out === undefined; n--) {
            var bucket = byPrefix.get(cand.slice(0, n));
            if (!bucket) continue;
            for (var bi = 0; bi < bucket.length; bi++) {
              var t = bucket[bi];
              if (n < 3 && t.prefix.length !== n) continue;
              var r = t.apply(cand, inner);
              if (r !== null) { out = cand === s ? r : lead + r + trail; break; }
            }
          }
          if (out !== undefined) break;
          for (var wi = 0; wi < wild.length; wi++) {
            var r2 = wild[wi].apply(cand, inner);
            if (r2 !== null) { out = cand === s ? r2 : lead + r2 + trail; break; }
          }
        }
      }
    }
    if (out === undefined && depth < 4) {
      var m = TRAIL.exec(s);
      if (m && m.index > 0) {
        var bare = s.slice(0, m.index);
        var rb = lookup(bare, depth + 1);
        if (rb !== bare) out = rb + s.slice(m.index);
      }
    }
    if (out === undefined && depth < 4) {
      var parts = s.split(SEG);
      if (parts.length > 1) {
        var changed = false;
        var done = parts.map(function (p, i) {
          if (i % 2 || !p.trim()) return p;
          var q = lookup(p, depth + 1);
          if (q !== p) changed = true;
          return q;
        });
        if (changed) out = done.join("");
      }
    }
    if (out === undefined) out = s;
    if (cache.size >= CACHE_MAX) cache.clear();
    cache.set(s, out);
    return out;
  }

  function tr(s) {
    if (typeof s !== "string" || !s) return s;
    try { return lookup(s, 0); } catch (e) { return s; }
  }

  // HTML collapses whitespace, so a sentence the page's source wraps over several lines is the same
  // sentence as the one in the catalog: retry on the whitespace-collapsed core, keeping the margins
  function trDom(s) {
    var o = tr(s);
    if (o !== s) return o;
    var w = splitWs(s), flat = w[1].replace(/\s+/g, " ");
    if (flat !== w[1]) {
      var o2 = tr(flat);
      if (o2 !== flat) return w[0] + o2 + w[2];
    }
    return s;
  }

  // ---- 화면(DOM) ------------------------------------------------------------------------------------
  var ATTRS = ["title", "placeholder", "alt", "aria-label", "label"];
  var DONE = new WeakMap();       // text node -> the Korean we wrote (so our own write is not re-read)
  var ORIG = new WeakMap();       // text node -> the English it came from
  var ADONE = new WeakMap();      // element -> {attr: the Korean we wrote}
  var MISSING = new Map();
  var COLLECT = !!W.__KO_COLLECT;

  function skippedTag(e) {
    var t = e.tagName;
    return t === "SCRIPT" || t === "STYLE" || t === "NOSCRIPT" || t === "TEXTAREA" || t === "PRE" ||
      t === "TEMPLATE" || (e.getAttribute && e.getAttribute("translate") === "no") ||
      (e.classList && e.classList.contains("notranslate"));
  }

  function inSkipped(e) {
    for (; e && e.nodeType === 1; e = e.parentElement) if (skippedTag(e)) return true;
    return false;
  }

  function note(v) {
    if (!COLLECT || MISSING.size > 20000) return;
    var k = v.trim();
    if (k.length > 2) MISSING.set(k, (MISSING.get(k) || 0) + 1);
  }

  function doText(n) {
    var v = n.nodeValue;
    if (!v || DONE.get(n) === v || !/[A-Za-z]/.test(v)) return;
    if (inSkipped(n.parentElement)) return;
    var o = trDom(v);
    if (o !== v) {
      ORIG.set(n, v);
      DONE.set(n, o);
      n.nodeValue = o;
    } else {
      note(v);
    }
  }

  function doAttr(e, a) {
    var v = e.getAttribute(a);
    if (!v) return;
    var d = ADONE.get(e);
    if (d && d[a] === v) return;
    var o = trDom(v);
    if (o !== v) {
      if (!d) { d = {}; ADONE.set(e, d); }
      d[a] = o;
      e.setAttribute(a, o);
    } else if (/[A-Za-z]/.test(v)) {
      note(v);
    }
  }

  function doAttrs(e) {
    for (var i = 0; i < ATTRS.length; i++) if (e.hasAttribute(ATTRS[i])) doAttr(e, ATTRS[i]);
  }

  var FILTER = {
    acceptNode: function (n) {
      if (n.nodeType === 1 && skippedTag(n)) return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    }
  };

  function walk(root) {
    if (!root) return;
    if (root.nodeType === 3) { doText(root); return; }
    if (root.nodeType !== 1 || inSkipped(root)) return;
    doAttrs(root);
    var tw = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, FILTER);
    var n;
    while ((n = tw.nextNode())) {
      if (n.nodeType === 3) doText(n); else doAttrs(n);
    }
  }

  // The app compares the text of a couple of elements it wrote itself (a regexp on #rmLoraInfo). Those
  // read the English back, as the Tk layer's cget() did.
  function english(el) {
    var s = "";
    for (var c = el.firstChild; c; c = c.nextSibling) {
      if (c.nodeType === 3) {
        var o = ORIG.get(c);
        s += (o !== undefined && DONE.get(c) === c.nodeValue) ? o : c.nodeValue;
      } else if (c.nodeType === 1) {
        s += english(c);
      }
    }
    return s;
  }

  function protect() {
    var el = document.getElementById("rmLoraInfo");
    if (!el || el.__koProtected) return;
    var d = Object.getOwnPropertyDescriptor(Node.prototype, "textContent");
    if (!d) return;
    try {
      Object.defineProperty(el, "textContent", {
        configurable: true,
        get: function () { return english(el); },
        set: function (v) { d.set.call(el, v); }
      });
      el.__koProtected = true;
    } catch (e) { /* leave it */ }
  }

  function start() {
    protect();
    walk(document.documentElement);
    var mo = new MutationObserver(function (recs) {
      for (var i = 0; i < recs.length; i++) {
        var r = recs[i];
        if (r.type === "characterData") {
          doText(r.target);
        } else if (r.type === "childList") {
          for (var j = 0; j < r.addedNodes.length; j++) walk(r.addedNodes[j]);
        } else if (r.type === "attributes" && r.target.nodeType === 1 && !inSkipped(r.target)) {
          doAttr(r.target, r.attributeName);
        }
      }
    });
    mo.observe(document.documentElement, {
      subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATTRS
    });
    document.addEventListener("DOMContentLoaded", function () { protect(); walk(document.documentElement); });
  }

  W.__ko = {
    version: 1,
    tr: tr,
    trDom: trDom,
    entries: exact.size,
    templates: wild.length + (function () { var c = 0; byPrefix.forEach(function (v) { c += v.length; }); return c; })(),
    missing: function () { return Array.from(MISSING.entries()); },
    rescan: function () { walk(document.documentElement); }
  };

  if (typeof document !== "undefined") start();
})();
