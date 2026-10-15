/* TIGON Webhook Flows — LSV DEALER lead forms ("Contact form").
 * Sends every .tigon-lead-form on the site to this website's own webhook, and adds
 * a "Get a Quote" pop-up form plus a Call Now / Financing bar to every page.
 * Signatures are optional for this webhook, so the browser posts directly
 * (no secret is, or ever should be, in this file). */
(function () {
  "use strict";

  var ENDPOINT = "https://tigoniot.com/hooks/XQDekbofU7YcQQbGLWgsE6stV2ggHHGH";
  var FORM_NAME = "Contact form";
  var PHONE_HREF = "tel:18448446638";
  var PHONE_TEXT = "1-844-844-6638";
  var HONEYPOT = "website";
  var SUCCESS_TEXT = "Thank you! We received your message and will contact you shortly.";
  var ERROR_TEXT = "Sorry, something went wrong. Please try again or call us at " + PHONE_TEXT + ".";
  var RATE_TEXT = "Too many tries. Please wait a minute and try again.";
  var MAX_FILE_MB = 10;
  var IMAGE_EXT = /\.(jpe?g|png|gif|webp|heic|heif)$/i;
  var IMAGE_TYPE = /^image\/(jpeg|png|gif|webp|heic|heif)$/i;
  var TRACK = ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid", "fbclid"];
  var HIDDEN = ["url", "referrer"].concat(TRACK, ["ga_client_id"]);
  var STORE_KEY = "tigon_first_touch";
  var MAX_AGE_MS = 30 * 24 * 60 * 60 * 1000;
  var CART_FIELDS = ["brand", "model", "vin_number", "sku_number"];
  var formCount = 0;

  // ---- Tracking -----------------------------------------------------------

  // First-touch attribution: the first utm_*/gclid/fbclid seen are kept for 30 days.
  function firstTouch() {
    var current = {}, found = false, q = null, saved = null;
    try { q = new URLSearchParams(window.location.search); } catch (e) { q = null; }
    TRACK.forEach(function (k) { var v = q && q.get(k); if (v) { current[k] = v; found = true; } });
    try { saved = JSON.parse(window.localStorage.getItem(STORE_KEY) || "null"); } catch (e) { saved = null; }
    if (saved && (!saved.ts || Date.now() - saved.ts > MAX_AGE_MS)) saved = null;
    if (!saved && found) {
      saved = { ts: Date.now(), v: current };
      try { window.localStorage.setItem(STORE_KEY, JSON.stringify(saved)); } catch (e) { /* private mode */ }
    }
    var out = {};
    TRACK.forEach(function (k) { out[k] = (saved && saved.v && saved.v[k]) || current[k] || ""; });
    return out;
  }

  // Google Analytics client id from the _ga cookie: GA1.1.123456.789012 -> 123456.789012
  function gaClientId() {
    var m = document.cookie.match(/(?:^|;\s*)_ga=([^;]+)/);
    if (!m) return "";
    var parts = decodeURIComponent(m[1]).split(".");
    return parts.length >= 4 ? parts.slice(-2).join(".") : "";
  }

  function tracking() {
    var t = firstTouch();
    t.url = window.location.href;
    t.referrer = document.referrer || "";
    t.ga_client_id = gaClientId();
    return t;
  }

  // ---- Form markup ----------------------------------------------------------

  function field(id, name, label, opts) {
    opts = opts || {};
    var req = opts.required ? " required" : "";
    var attrs = (opts.attrs || "") + req;
    var star = opts.required ? '<span class="tgn-req" aria-hidden="true">*</span>' : "";
    var input;
    if (opts.type === "textarea") {
      input = '<textarea name="' + name + '" id="' + id + '-' + name + '" rows="4"' + attrs + "></textarea>";
    } else {
      input = '<input type="' + (opts.type || "text") + '" name="' + name + '" id="' + id + '-' + name + '"' + attrs + ">";
    }
    return '<div class="tgn-field' + (opts.half ? " tgn-half" : "") + '">' +
      '<label for="' + id + '-' + name + '">' + label + star + "</label>" + input +
      '<span class="tgn-error" aria-live="polite"></span></div>';
  }

  // Builds a complete lead form with every TIGON field, using the exact field names.
  function formHtml(id) {
    var img = ' accept="image/*,.heic,.heif"';
    var hidden = HIDDEN.map(function (k) { return '<input type="hidden" name="' + k + '" value="">'; }).join("");
    return '<form id="' + id + '" class="tigon-lead-form" method="post" action="' + ENDPOINT + '" enctype="multipart/form-data" novalidate>' +
      '<div class="tgn-grid">' +
      field(id, "first_name", "First name", { half: true, required: true, attrs: ' autocomplete="given-name"' }) +
      field(id, "last_name", "Last name", { half: true, required: true, attrs: ' autocomplete="family-name"' }) +
      field(id, "email", "Email", { type: "email", half: true, required: true, attrs: ' autocomplete="email"' }) +
      field(id, "phone1", "Phone", { type: "tel", half: true, required: true, attrs: ' autocomplete="tel"' }) +
      field(id, "phone2", "Alternate phone", { type: "tel", half: true }) +
      field(id, "zip_code", "ZIP code", { half: true, attrs: ' inputmode="numeric" autocomplete="postal-code"' }) +
      field(id, "address", "Address", { attrs: ' autocomplete="street-address"' }) +
      field(id, "brand", "Brand", { half: true, attrs: ' placeholder="e.g. TIGON"' }) +
      field(id, "model", "Model you are interested in", { half: true }) +
      field(id, "vin_number", "VIN (optional)", { half: true }) +
      field(id, "sku_number", "Stock # / SKU (optional)", { half: true }) +
      field(id, "comments", "Message", { type: "textarea", attrs: ' placeholder="How can we help?"' }) +
      field(id, "image_1", "Photo 1 (optional)", { type: "file", attrs: img }) +
      field(id, "image_2", "Photo 2 (optional)", { type: "file", attrs: img }) +
      field(id, "image_3", "Photo 3 (optional)", { type: "file", attrs: img }) +
      "</div>" +
      '<p class="tgn-note">Photos: up to 10 MB each (jpg, png, gif, webp or heic).</p>' +
      '<div class="tgn-hp" aria-hidden="true"><label for="' + id + '-hp">Leave this field empty</label>' +
      '<input type="text" name="' + HONEYPOT + '" id="' + id + '-hp" tabindex="-1" autocomplete="off" value=""></div>' +
      '<input type="hidden" name="form_name" value="' + FORM_NAME + '">' + hidden +
      '<button type="submit" class="tgn-submit">Send Message</button>' +
      '<p class="tigon-msg" role="status" aria-live="polite"></p>' +
      "</form>";
  }

  // ---- Pre-fill ---------------------------------------------------------------

  // Pre-fills the cart a page (or the clicked button) is about. Any element with
  // data-tigon-cart and data-brand / data-model / data-vin / data-sku works, so
  // future listing pages only need those attributes.
  function cartFrom(el) {
    if (!el || !el.getAttribute) return null;
    var map = { brand: "data-brand", model: "data-model", vin_number: "data-vin", sku_number: "data-sku" };
    var out = null;
    CART_FIELDS.forEach(function (k) {
      var v = el.getAttribute(map[k]);
      if (v) { out = out || {}; out[k] = v; }
    });
    return out;
  }

  function applyCart(form, cart) {
    CART_FIELDS.forEach(function (k) {
      var el = form.elements[k];
      if (!el) return;
      if (cart && cart[k]) { el.value = cart[k]; el.readOnly = true; }
      else if (el.readOnly) { el.value = ""; el.readOnly = false; }
    });
  }

  // On dealer listing pages, record which dealer the lead came from (stored as an extra field).
  function dealerName() {
    var h = document.querySelector(".dealer-header h1");
    return h ? h.textContent.replace(/\s+/g, " ").trim() : "";
  }

  function prepare(form) {
    if (form.dataset.tgnReady) return;
    form.dataset.tgnReady = "1";
    form.setAttribute("novalidate", "");
    if (!form.querySelector('[name="' + HONEYPOT + '"]')) {
      var wrap = document.createElement("div");
      wrap.className = "tgn-hp";
      wrap.setAttribute("aria-hidden", "true");
      wrap.innerHTML = '<input type="text" name="' + HONEYPOT + '" tabindex="-1" autocomplete="off" value="">';
      form.appendChild(wrap);
    }
    var dealer = dealerName();
    if (dealer && !form.elements.dealer) {
      var d = document.createElement("input");
      d.type = "hidden"; d.name = "dealer"; d.value = dealer;
      form.appendChild(d);
    }
    var pageCart = cartFrom(document.querySelector("[data-tigon-cart]"));
    if (pageCart) applyCart(form, pageCart);
    fillHidden(form);
  }

  function fillHidden(form) {
    var t = tracking();
    Object.keys(t).forEach(function (k) {
      var el = form.querySelector('input[type="hidden"][name="' + k + '"]');
      if (el) el.value = t[k];
    });
  }

  // ---- Validation ------------------------------------------------------------

  function setError(input, text) {
    var wrap = input.closest(".tgn-field, .form-group");
    var box = wrap && wrap.querySelector(".tgn-error");
    if (box) box.textContent = text || "";
    if (text) input.setAttribute("aria-invalid", "true"); else input.removeAttribute("aria-invalid");
  }

  function validate(form) {
    var first = null;
    function check(input, text) {
      setError(input, text);
      if (text && !first) first = input;
    }
    var labels = { first_name: "first name", last_name: "last name", email: "email address", phone1: "phone number" };
    Object.keys(labels).forEach(function (k) {
      var el = form.elements[k];
      if (!el) return;
      var v = el.value.trim();
      var msg = "";
      if (!v) msg = "Please enter your " + labels[k] + ".";
      else if (k === "email" && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v)) msg = "Please enter a valid email address.";
      else if (k === "phone1" && v.replace(/\D/g, "").length < 10) msg = "Please enter a phone number with at least 10 digits.";
      check(el, msg);
    });
    var phone2 = form.elements.phone2;
    if (phone2) {
      var p2 = phone2.value.trim();
      check(phone2, p2 && p2.replace(/\D/g, "").length < 10 ? "Please enter at least 10 digits, or leave this blank." : "");
    }
    var zip = form.elements.zip_code;
    if (zip) {
      var z = zip.value.trim();
      check(zip, z && !/^\d{5}(-?\d{4})?$/.test(z) ? "Please enter a 5-digit ZIP code." : "");
    }
    var files = form.querySelectorAll('input[type="file"]');
    for (var i = 0; i < files.length; i++) {
      var f = files[i].files && files[i].files[0];
      var msg = "";
      if (f && f.size > MAX_FILE_MB * 1024 * 1024) msg = "This photo is larger than " + MAX_FILE_MB + " MB. Please choose a smaller one.";
      else if (f && !IMAGE_TYPE.test(f.type) && !IMAGE_EXT.test(f.name)) msg = "Please choose a jpg, png, gif, webp or heic photo.";
      check(files[i], msg);
    }
    if (first) first.focus();
    return !first;
  }

  // ---- Sending ---------------------------------------------------------------

  function show(form, text, ok) {
    var el = form.querySelector(".tigon-msg");
    if (!el) {
      el = document.createElement("p");
      el.className = "tigon-msg";
      el.setAttribute("role", "status");
      el.setAttribute("aria-live", "polite");
      form.appendChild(el);
    }
    el.textContent = text;
    el.className = "tigon-msg " + (ok ? "tgn-ok" : "tgn-bad");
  }

  function buildData(form) {
    var fd = new FormData(form);
    // Leave out empty file inputs so no blank images are sent.
    var files = form.querySelectorAll('input[type="file"]');
    for (var i = 0; i < files.length; i++) {
      if (files[i].name && !(files[i].files && files[i].files.length)) fd.delete(files[i].name);
    }
    var t = tracking();
    Object.keys(t).forEach(function (k) { fd.set(k, t[k]); });
    fd.set("form_name", FORM_NAME);
    if (!fd.has(HONEYPOT)) fd.set(HONEYPOT, "");
    return fd;
  }

  function send(form) {
    if (form.dataset.tgnSending) return;
    if (!validate(form)) { show(form, "Please fix the highlighted fields.", false); return; }
    var button = form.querySelector('button[type="submit"], input[type="submit"]');
    var label = button ? (button.tagName === "INPUT" ? button.value : button.textContent) : "";
    var fd = buildData(form);
    form.dataset.tgnSending = "1";
    if (button) { button.disabled = true; if (button.tagName === "INPUT") button.value = "Sending…"; else button.textContent = "Sending…"; }
    show(form, "Sending…", true);
    fetch(ENDPOINT, { method: "POST", body: fd, mode: "cors" })
      .then(function (res) {
        return res.text().then(function (body) {
          var data = null;
          try { data = JSON.parse(body); } catch (e) { data = null; }
          if (res.status === 429) throw new Error(RATE_TEXT);
          if (!res.ok || !data || data.ok !== true) throw new Error((data && (data.error || data.message)) || ERROR_TEXT);
        });
      })
      .then(function () {
        form.reset();
        var pageCart = cartFrom(document.querySelector("[data-tigon-cart]"));
        applyCart(form, form.dataset.tgnCart ? JSON.parse(form.dataset.tgnCart) : pageCart);
        fillHidden(form);
        show(form, SUCCESS_TEXT, true);
      })
      .catch(function (err) {
        var text = err && err.message;
        show(form, text && text !== "Failed to fetch" && text !== "Load failed" ? text : ERROR_TEXT, false);
      })
      .then(function () {
        delete form.dataset.tgnSending;
        if (button) { button.disabled = false; if (button.tagName === "INPUT") button.value = label; else button.textContent = label; }
      });
  }

  // ---- Modal + call bar ----------------------------------------------------------

  var modal = null, lastFocus = null;

  function buildModal() {
    modal = document.createElement("div");
    modal.className = "tgn-modal";
    modal.id = "tigon-lead-modal";
    modal.hidden = true;
    modal.innerHTML =
      '<div class="tgn-backdrop" data-tigon-close></div>' +
      '<div class="tgn-dialog" role="dialog" aria-modal="true" aria-labelledby="tigon-modal-title">' +
      '<button type="button" class="tgn-close" data-tigon-close aria-label="Close">&times;</button>' +
      '<h2 id="tigon-modal-title">Get a Quote</h2>' +
      '<p class="tgn-sub">Tell us what you are looking for and a dealer will contact you. Prefer to talk? ' +
      'Call <a href="' + PHONE_HREF + '">' + PHONE_TEXT + "</a>.</p>" +
      formHtml("tigon-modal-form") +
      "</div>";
    document.body.appendChild(modal);
    prepare(modal.querySelector("form"));
  }

  function openModal(opener) {
    if (!modal) buildModal();
    var form = modal.querySelector("form");
    var title = opener && opener.getAttribute("data-tigon-title");
    modal.querySelector("#tigon-modal-title").textContent = title || "Get a Quote";
    var cart = cartFrom(opener && opener.closest ? opener.closest("[data-brand],[data-model],[data-vin],[data-sku]") : null) ||
      cartFrom(document.querySelector("[data-tigon-cart]"));
    if (cart) form.dataset.tgnCart = JSON.stringify(cart); else delete form.dataset.tgnCart;
    applyCart(form, cart);
    var topic = opener && opener.getAttribute("data-tigon-message");
    if (topic && !form.elements.comments.value) form.elements.comments.value = topic;
    fillHidden(form);
    lastFocus = document.activeElement;
    modal.hidden = false;
    document.documentElement.classList.add("tgn-lock");
    setTimeout(function () { form.elements.first_name.focus(); }, 30);
  }

  function closeModal() {
    if (!modal || modal.hidden) return;
    modal.hidden = true;
    document.documentElement.classList.remove("tgn-lock");
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  function buildBar() {
    if (document.querySelector(".tgn-bar")) return;
    var bar = document.createElement("div");
    bar.className = "tgn-bar";
    bar.innerHTML =
      '<a class="tgn-btn tgn-call" href="' + PHONE_HREF + '">Call Now</a>' +
      '<button type="button" class="tgn-btn" data-tigon-open>Get a Quote</button>' +
      '<button type="button" class="tgn-btn tgn-alt" data-tigon-open data-tigon-title="Apply for Financing" ' +
      'data-tigon-message="I would like to apply for financing.">Financing</button>';
    document.body.appendChild(bar);
    document.body.classList.add("tgn-has-bar");
  }

  // Dealer listing pages: Call Now / Get a Quote / Apply for Financing right under the dealer name.
  function buildDealerCta() {
    var header = document.querySelector(".dealer-header");
    if (!header || header.querySelector(".tgn-cta")) return;
    var row = document.createElement("div");
    row.className = "tgn-cta";
    row.innerHTML =
      '<a class="btn" href="' + PHONE_HREF + '">Call Now: ' + PHONE_TEXT + "</a>" +
      '<button type="button" class="btn" data-tigon-open>Get a Quote</button>' +
      '<button type="button" class="btn tgn-alt" data-tigon-open data-tigon-title="Apply for Financing" ' +
      'data-tigon-message="I would like to apply for financing.">Apply for Financing</button>';
    header.appendChild(row);
  }

  // ---- Wiring ----------------------------------------------------------------

  // Capture phase: runs before any other submit handlers on the page.
  document.addEventListener("submit", function (e) {
    var form = e.target;
    if (!form || !form.classList || !form.classList.contains("tigon-lead-form")) return;
    e.preventDefault();
    e.stopImmediatePropagation();
    prepare(form);
    send(form);
  }, true);

  document.addEventListener("click", function (e) {
    var t = e.target.closest ? e.target : e.target.parentElement;
    if (!t) return;
    var opener = t.closest("[data-tigon-open]");
    if (opener) { e.preventDefault(); openModal(opener); return; }
    if (t.closest("[data-tigon-close]")) closeModal();
  });

  document.addEventListener("input", function (e) {
    if (e.target.getAttribute && e.target.getAttribute("aria-invalid")) setError(e.target, "");
  });
  document.addEventListener("change", function (e) {
    if (e.target.type === "file" && e.target.getAttribute("aria-invalid")) setError(e.target, "");
  });

  document.addEventListener("keydown", function (e) {
    if (!modal || modal.hidden) return;
    if (e.key === "Escape") { closeModal(); return; }
    if (e.key !== "Tab") return;
    // Keep keyboard focus inside the open dialog.
    var f = modal.querySelectorAll('a[href], button:not([disabled]), input:not([type="hidden"]):not([tabindex="-1"]), textarea');
    if (!f.length) return;
    var first = f[0], last = f[f.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  });

  function init() {
    firstTouch(); // remember first-touch UTMs even if the visitor never opens a form on this page
    var forms = document.querySelectorAll("form.tigon-lead-form");
    for (var i = 0; i < forms.length; i++) prepare(forms[i]);
    buildBar();
    buildDealerCta();
    if (/[#&]get-a-quote\b/.test(window.location.hash)) openModal(null);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
