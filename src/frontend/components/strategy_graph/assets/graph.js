// node_modules/svelte/src/internal/shared/utils.js
var e = Array.isArray, t = Array.prototype.indexOf, n = Array.prototype.includes, r = Array.from, i = Object.defineProperty, a = Object.getOwnPropertyDescriptor, o = Object.getOwnPropertyDescriptors, s = Object.prototype, c = Array.prototype, l = Object.getPrototypeOf, u = Object.isExtensible;
function d(e) {
	return typeof e == "function";
}
var f = () => {};
function p(e) {
	return e();
}
function m(e) {
	for (var t = 0; t < e.length; t++) e[t]();
}
function h() {
	var e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
function g(e, t, n = !1) {
	return e === void 0 ? n ? t() : t : e;
}
function _(e, t) {
	if (Array.isArray(e)) return e;
	if (t === void 0 || !(Symbol.iterator in e)) return Array.from(e);
	let n = [];
	for (let r of e) if (n.push(r), n.length === t) break;
	return n;
}
function v(e, t) {
	var n = {};
	for (var r in e) t.includes(r) || (n[r] = e[r]);
	for (var i of Object.getOwnPropertySymbols(e)) Object.propertyIsEnumerable.call(e, i) && !t.includes(i) && (n[i] = e[i]);
	return n;
}
// node_modules/svelte/src/internal/client/constants.js
var y = 1 << 24, b = 1024, x = 2048, S = 4096, C = 8192, w = 16384, T = 32768, ee = 1 << 25, E = 65536, D = 1 << 19, te = 1 << 20, ne = 1 << 25, re = 1 << 21, ie = 1 << 22, ae = 1 << 23, oe = Symbol("$state"), se = Symbol("component"), ce = Symbol("legacy props"), le = Symbol(""), ue = Symbol("attributes"), de = Symbol("class"), fe = Symbol("style"), pe = Symbol("text"), me = Symbol("form reset"), he = new class extends Error {
	name = "StaleReactionError";
	message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}(), ge = !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml"), _e = {}, ve = Symbol("uninitialized"), ye = "http://www.w3.org/1999/xhtml";
function be() {
	console.warn("https://svelte.dev/e/derived_inert");
}
function xe(e) {
	console.warn("https://svelte.dev/e/hydration_mismatch");
}
function Se() {
	console.warn("https://svelte.dev/e/select_multiple_invalid_value");
}
function Ce() {
	console.warn("https://svelte.dev/e/svelte_boundary_reset_noop");
}
// node_modules/svelte/src/internal/client/dom/hydration.js
var O = !1;
function we(e) {
	O = e;
}
var k;
function Te(e) {
	if (e === null) throw xe(), _e;
	return k = e;
}
function Ee() {
	return Te(/* @__PURE__ */ _n(k));
}
function A(e) {
	if (O) {
		if (/* @__PURE__ */ _n(k) !== null) throw xe(), _e;
		k = e;
	}
}
function De(e = 1) {
	if (O) {
		for (var t = e, n = k; t--;) n = /* @__PURE__ */ _n(n);
		k = n;
	}
}
function Oe(e = !0) {
	for (var t = 0, n = k;;) {
		if (n.nodeType === 8) {
			var r = n.data;
			if (r === "]") {
				if (t === 0) return n;
				--t;
			} else (r === "[" || r === "[!" || r[0] === "[" && !isNaN(Number(r.slice(1)))) && (t += 1);
		}
		var i = /* @__PURE__ */ _n(n);
		e && n.remove(), n = i;
	}
}
function ke(e) {
	if (!e || e.nodeType !== 8) throw xe(), _e;
	return e.data;
}
// node_modules/svelte/src/internal/client/reactivity/equality.js
function Ae(e) {
	return e === this.v;
}
function je(e, t) {
	return e == e ? e !== t || typeof e == "object" && !!e || typeof e == "function" : t == t;
}
function Me(e) {
	return !je(e, this.v);
}
function Ne(e) {
	throw Error("https://svelte.dev/e/lifecycle_outside_component");
}
// node_modules/svelte/src/internal/client/errors.js
function Pe() {
	throw Error("https://svelte.dev/e/async_derived_orphan");
}
function Fe(e, t, n) {
	throw Error("https://svelte.dev/e/each_key_duplicate");
}
function Ie(e) {
	throw Error("https://svelte.dev/e/effect_in_teardown");
}
function Le() {
	throw Error("https://svelte.dev/e/effect_in_unowned_derived");
}
function Re(e) {
	throw Error("https://svelte.dev/e/effect_orphan");
}
function ze() {
	throw Error("https://svelte.dev/e/effect_update_depth_exceeded");
}
function Be(e) {
	throw Error("https://svelte.dev/e/props_invalid_value");
}
function Ve() {
	throw Error("https://svelte.dev/e/state_descriptors_fixed");
}
function He() {
	throw Error("https://svelte.dev/e/state_prototype_fixed");
}
function Ue() {
	throw Error("https://svelte.dev/e/state_unsafe_mutation");
}
function We() {
	throw Error("https://svelte.dev/e/svelte_boundary_reset_onerror");
}
// node_modules/svelte/src/internal/flags/index.js
var Ge = !1;
function Ke() {
	Ge = !0;
}
// node_modules/svelte/src/internal/shared/clone.js
var qe = [];
function Je(e, t = !1, n = !1) {
	return Ye(e, /* @__PURE__ */ new Map(), "", qe, null, n);
}
function Ye(t, n, r, i, a = null, o = !1) {
	if (typeof t == "object" && t) {
		var c = n.get(t);
		if (c !== void 0) return c;
		if (t instanceof Map) return new Map(t);
		if (t instanceof Set) return new Set(t);
		if (e(t)) {
			var u = Array(t.length);
			n.set(t, u), a !== null && n.set(a, u);
			for (var d = 0; d < t.length; d += 1) {
				var f = t[d];
				d in t && (u[d] = Ye(f, n, r, i, null, o));
			}
			return u;
		}
		if (l(t) === s) {
			u = {}, n.set(t, u), a !== null && n.set(a, u);
			for (var p of Object.keys(t)) u[p] = Ye(t[p], n, r, i, null, o);
			return u;
		}
		if (t instanceof Date) return t.getTime(), structuredClone(t);
		if (typeof t.toJSON == "function" && !o) return Ye(t.toJSON(), n, r, i, t);
	}
	if (t instanceof EventTarget) return t;
	try {
		return structuredClone(t);
	} catch {
		return t;
	}
}
// node_modules/svelte/src/internal/shared/context.js
function Xe(e) {
	let t = e.p;
	for (; t !== null && t.c === null;) t = t.p;
	return t?.c ?? null;
}
function Ze(e, t) {
	return e === null && Ne(t), e.c ??= new Map(Xe(e) || void 0);
}
// node_modules/svelte/src/internal/client/context.js
var j = null;
function Qe(e) {
	j = e;
}
function $e(e) {
	return Ze(j, "getContext").get(e);
}
function et(e, t) {
	return Ze(j, "setContext").set(e, t), t;
}
function tt(e) {
	return Ze(j, "hasContext").has(e);
}
function M(e, t = !1, n) {
	j = {
		p: j,
		i: !1,
		c: null,
		e: null,
		s: e,
		x: null,
		r: W,
		l: Ge && !t ? {
			s: null,
			u: null,
			$: []
		} : null
	};
}
function N(e) {
	var t = j, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) An(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, j = t.p, nt(e);
}
function nt(e = {}) {
	return i(e, se, { value: !0 }), e;
}
function rt() {
	return !Ge || j !== null && j.l === null;
}
// node_modules/svelte/src/internal/client/dom/task.js
var it = [];
function at() {
	var e = it;
	it = [], m(e);
}
function ot(e) {
	if (it.length === 0 && !Ft) {
		var t = it;
		queueMicrotask(() => {
			t === it && at();
		});
	}
	it.push(e);
}
function st() {
	for (; it.length > 0;) at();
}
// node_modules/svelte/src/internal/client/reactivity/status.js
var ct = ~(x | S | b);
function lt(e, t) {
	e.f = e.f & ct | t;
}
function ut(e) {
	e.f & 512 || e.deps === null ? lt(e, b) : lt(e, S);
}
// node_modules/svelte/src/internal/client/reactivity/utils.js
function dt(e, t, n) {
	e.f & 2048 ? t.add(e) : e.f & 4096 && n.add(e), lt(e, b);
}
// node_modules/svelte/src/internal/client/dom/elements/misc.js
function ft(e, t) {
	if (t) {
		let t = document.body;
		e.autofocus = !0, ot(() => {
			document.activeElement === t && e.focus();
		});
	}
}
function pt(e) {
	O && /* @__PURE__ */ gn(e) !== null && vn(e);
}
var mt = !1;
function ht() {
	mt || (mt = !0, document.addEventListener("reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t[me]?.();
		});
	}, { capture: !0 }));
}
// node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function gt(e) {
	var t = U, n = W;
	tr(null), nr(null);
	try {
		return e();
	} finally {
		tr(t), nr(n);
	}
}
function _t(e, t, n, r = n) {
	e.addEventListener(t, () => gt(n));
	let i = e[me];
	e[me] = i ? () => {
		i(), r(!0);
	} : () => r(!0), ht();
}
// node_modules/svelte/src/internal/client/reactivity/async.js
function vt(e, t, n, r) {
	let i = rt() ? St : Tt;
	var a = e.filter((e) => !e.settled), o = t.map(i);
	if (n.length === 0 && a.length === 0) {
		r(o);
		return;
	}
	var s = W, c = yt(), l = a.length === 1 ? a[0].promise : a.length > 1 ? Promise.all(a.map((e) => e.promise)) : null;
	function u(e) {
		if (!(s.f & 16384)) {
			c();
			try {
				r([...o, ...e]);
			} catch (e) {
				Cn(e, s);
			}
			bt();
		}
	}
	var d = xt();
	if (n.length === 0) {
		l.then(() => u([])).finally(d);
		return;
	}
	function f() {
		Promise.all(n.map((e) => /* @__PURE__ */ wt(e))).then(u).catch((e) => Cn(e, s)).finally(d);
	}
	l ? l.then(() => {
		s.f & 16384 ? d() : (c(), f(), bt());
	}) : f();
}
function yt() {
	var e = W, t = U, n = j, r = F;
	return function(i = !0) {
		nr(e), tr(t), Qe(n), i && !(e.f & 16384) && (r?.activate(), r?.apply());
	};
}
function bt(e = !0) {
	nr(null), tr(null), Qe(null), e && F?.deactivate();
}
function xt() {
	var e = W, t = e.b, n = F, r = !!t?.is_rendered();
	return t?.update_pending_count(1, n), n.increment(r, e), () => {
		t?.update_pending_count(-1, n), n.decrement(r, e);
	};
}
/*#__NO_SIDE_EFFECTS__*/
function St(e) {
	var t = 2 | x;
	return W !== null && (W.f |= D), {
		ctx: j,
		deps: null,
		effects: null,
		equals: Ae,
		f: t,
		fn: e,
		reactions: null,
		rv: 0,
		v: ve,
		wv: 0,
		parent: W,
		ac: null
	};
}
var Ct = Symbol("obsolete");
/*#__NO_SIDE_EFFECTS__*/
function wt(e, t, n) {
	let r = W;
	r === null && Pe();
	var i = void 0, a = Qt(ve), o = !U, s = /* @__PURE__ */ new Set();
	return Fn(() => {
		var t = W, n = h();
		i = n.promise;
		try {
			Promise.resolve(e()).then(n.resolve, (e) => {
				e !== he && n.reject(e);
			}).finally(bt);
		} catch (e) {
			n.reject(e), bt();
		}
		var c = F;
		if (o) {
			if (t.f & 32768) var l = xt();
			if (r.b?.is_rendered()) c.async_deriveds.get(t)?.reject(Ct);
			else for (let e of s.values()) e.reject(Ct);
			s.add(n), c.async_deriveds.set(t, n);
		}
		let u = (e, t = void 0) => {
			l?.(), s.delete(n), t !== Ct && (c.activate(), t ? (a.f |= ae, nn(a, t)) : (a.f & 8388608 && (a.f ^= ae), nn(a, e)), c.deactivate());
		};
		n.promise.then(u, (e) => u(null, e || "unknown"));
	}), On(() => {
		for (let e of s) e.reject(Ct);
	}), new Promise((e) => {
		function t(n) {
			function r() {
				n === i ? e(a) : t(i);
			}
			n.then(r, r);
		}
		t(i);
	});
}
/*#__NO_SIDE_EFFECTS__*/
function P(e) {
	let t = /* @__PURE__ */ St(e);
	return ir(t), t;
}
/*#__NO_SIDE_EFFECTS__*/
function Tt(e) {
	let t = /* @__PURE__ */ St(e);
	return t.equals = Me, t;
}
function Et(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) Un(t[n]);
	}
}
function Dt(e) {
	var t, n = W, r = e.parent;
	if (!Qn && r !== null && e.v !== ve && r.f & 24576) return be(), e.v;
	nr(r);
	try {
		Et(e), t = gr(e);
	} finally {
		nr(n);
	}
	return t;
}
function Ot(e) {
	var t = Dt(e);
	!e.equals(t) && (e.wv = pr(), (!F?.is_fork || e.deps === null) && (F === null ? e.v = t : (F.capture(e, t, !0), Mt?.capture(e, t, !0)), e.deps === null)) ? lt(e, b) : Qn || (Nt === null ? ut(e) : (Dn() || F?.is_fork) && Nt.set(e, t));
}
function kt(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.ac) && (t.teardown?.(), t.ac !== null && gt(() => {
		t.ac.abort(he), t.ac = null;
	}), t.fn !== null && (t.teardown = f), yr(t, 0), Vn(t));
}
function At(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && t.fn !== null && br(t);
}
// node_modules/svelte/src/internal/client/reactivity/batch.js
var jt = null, F = null, Mt = null, Nt = null, Pt = null, Ft = !1, It = !1, Lt = null, Rt = null, zt = 0, Bt = 1, Vt = class e {
	id = Bt++;
	#e = !1;
	linked = !0;
	#t = null;
	#n = null;
	async_deriveds = /* @__PURE__ */ new Map();
	current = /* @__PURE__ */ new Map();
	previous = /* @__PURE__ */ new Map();
	#r = /* @__PURE__ */ new Set();
	#i = /* @__PURE__ */ new Set();
	#a = 0;
	#o = /* @__PURE__ */ new Map();
	#s = null;
	#c = [];
	#l = [];
	#u = /* @__PURE__ */ new Set();
	#d = /* @__PURE__ */ new Set();
	#f = /* @__PURE__ */ new Map();
	#p = /* @__PURE__ */ new Set();
	is_fork = !1;
	#m = !1;
	constructor() {
		jt === null ? jt = this : (jt.#n = this, this.#t = jt), jt = this;
	}
	#h() {
		if (this.is_fork) return !0;
		for (let n of this.#o.keys()) {
			for (var e = n, t = !1; e.parent !== null;) {
				if (this.#f.has(e)) {
					t = !0;
					break;
				}
				e = e.parent;
			}
			if (!t) return !0;
		}
		return !1;
	}
	skip_effect(e) {
		this.#f.has(e) || this.#f.set(e, {
			d: [],
			m: []
		}), this.#p.delete(e);
	}
	unskip_effect(e, t = (e) => this.schedule(e)) {
		var n = this.#f.get(e);
		if (n) {
			this.#f.delete(e);
			for (var r of n.d) lt(r, x), t(r);
			for (r of n.m) lt(r, S), t(r);
		}
		this.#p.add(e);
	}
	#g() {
		var e = [];
		for (let i of this.#c) if (!(i.f & 16384 || !(i.f & 6144))) {
			for (var t = i, n = !1; t.parent !== null;) {
				t = t.parent;
				var r = t.f;
				if (r & 96) {
					if (!(r & 1024)) {
						n = !0;
						break;
					}
					t.f ^= b;
				}
			}
			n || e.push(t);
		}
		return this.#c = [], e;
	}
	#_() {
		this.#e = !0;
		for (let e of this.#u) this.#d.delete(e), lt(e, x), this.schedule(e);
		for (let e of this.#d) lt(e, S), this.schedule(e);
		this.apply();
		for (var t = Lt = [], n = [], r = Rt = []; this.#c.length > 0;) {
			zt++ > 1e3 && (this.#S(), Ut());
			for (let e of this.#g()) try {
				this.#v(e, t, n);
			} catch (t) {
				throw Jt(e), this.#h() || this.discard(), t;
			}
		}
		if (F = null, r.length > 0) {
			var i = e.ensure();
			for (let e of r) i.schedule(e);
		}
		if (Lt = null, Rt = null, this.#h()) {
			this.#x(n), this.#x(t);
			for (let [e, t] of this.#f) qt(e, t);
			r.length > 0 && F.#_();
			return;
		}
		let a = this.#y();
		if (a) this.#x(n), this.#x(t), a.#b(this);
		else {
			this.#u.clear(), this.#d.clear();
			for (let e of this.#r) e(this);
			this.#r.clear(), Mt = this, Gt(n), Gt(t), Mt = null, this.#s?.resolve();
			var o = F;
			if (this.#a === 0 && (this.#c.length === 0 || o !== null) && this.#S(), this.#c.length > 0) {
				if (o !== null) {
					for (let e of this.#c) o.#c.push(e);
					this.#c = [];
				} else o = this;
			}
			o !== null && (Xt.clear(), o.#_());
		}
	}
	#v(e, t, n) {
		e.f ^= b;
		for (var r = e.first; r !== null;) {
			var i = r.f, a = !!(i & 96);
			if (!(a && i & 1024 || i & 8192 || this.#f.has(r)) && r.fn !== null) {
				a ? r.f ^= b : i & 4 ? t.push(r) : mr(r) && (i & 16 && this.#d.add(r), br(r));
				var o = r.first;
				if (o !== null) {
					r = o;
					continue;
				}
			}
			for (; r !== null;) {
				var s = r.next;
				if (s !== null) {
					r = s;
					break;
				}
				r = r.parent;
			}
		}
	}
	#y() {
		for (var e = this.#t; e !== null;) {
			if (!e.is_fork) {
				for (let [t, [, n]] of this.current) if (e.current.has(t) && !n) return e;
			}
			e = e.#t;
		}
		return null;
	}
	#b(e) {
		for (let [t, n] of e.current) !this.previous.has(t) && e.previous.has(t) && this.previous.set(t, e.previous.get(t)), this.current.set(t, n);
		for (let [t, n] of e.async_deriveds) {
			let e = this.async_deriveds.get(t);
			e && n.promise.then(e.resolve).catch(e.reject);
		}
		e.async_deriveds.clear(), this.transfer_effects(e.#u, e.#d);
		let t = (e) => {
			var n = e.reactions;
			if (n !== null && !(e.f & 2 && !(e.f & 6144))) for (let e of n) {
				var r = e.f;
				if (r & 2) t(e);
				else {
					var i = e;
					r & 4194320 && !this.async_deriveds.has(i) && (this.#d.delete(i), lt(i, x), this.schedule(i));
				}
			}
		};
		for (let e of this.current.keys()) t(e);
		this.oncommit(() => e.discard()), e.#S(), F = this, this.#_();
	}
	#x(e) {
		for (var t = 0; t < e.length; t += 1) dt(e[t], this.#u, this.#d);
	}
	capture(e, t, n = !1) {
		e.v !== ve && !this.previous.has(e) && this.previous.set(e, e.v), e.f & 8388608 || (this.current.set(e, [t, n]), Nt?.set(e, t)), this.is_fork || (e.v = t);
	}
	activate() {
		F = this;
	}
	deactivate() {
		F = null, Nt = null;
	}
	flush() {
		try {
			It = !0, F = this, this.#_();
		} finally {
			zt = 0, Pt = null, Lt = null, Rt = null, It = !1, F = null, Nt = null, Xt.clear();
		}
	}
	discard() {
		for (let e of this.#i) e(this);
		this.#i.clear();
		for (let e of this.async_deriveds.values()) e.reject(Ct);
		this.#S(), this.#s?.resolve();
	}
	register_created_effect(e) {
		this.#l.push(e);
	}
	increment(e, t) {
		if (this.#a += 1, e) {
			let e = this.#o.get(t) ?? 0;
			this.#o.set(t, e + 1);
		}
	}
	decrement(e, t) {
		if (--this.#a, e) {
			let e = this.#o.get(t) ?? 0;
			e === 1 ? this.#o.delete(t) : this.#o.set(t, e - 1);
		}
		this.#m || (this.#m = !0, ot(() => {
			this.#m = !1, this.linked && this.flush();
		}));
	}
	transfer_effects(e, t) {
		for (let t of e) this.#u.add(t);
		for (let e of t) this.#d.add(e);
		e.clear(), t.clear();
	}
	oncommit(e) {
		this.#r.add(e);
	}
	ondiscard(e) {
		this.#i.add(e);
	}
	settled() {
		return (this.#s ??= h()).promise;
	}
	static ensure() {
		if (F === null) {
			let t = F = new e();
			!It && !Ft && ot(() => {
				t.#e || t.flush();
			});
		}
		return F;
	}
	apply() {
		Nt = null;
	}
	schedule(e) {
		Pt = e, e.b?.is_pending && e.f & 16777228 && !(e.f & 32768) ? e.b.defer_effect(e) : this.#c.push(e);
	}
	#S() {
		if (this.linked) {
			var e = this.#t, t = this.#n;
			e === null || (e.#n = t), t === null ? jt = e : t.#t = e, this.linked = !1;
		}
	}
};
function Ht(e) {
	var t = Ft, n = Mt;
	Mt = null, Ft = !0;
	try {
		var r;
		for (e && (Ht(), r = e());;) {
			if (st(), F === null) return r;
			F.flush();
		}
	} finally {
		Ft = t, Mt = n;
	}
}
function Ut() {
	try {
		ze();
	} catch (e) {
		Cn(e, Pt);
	}
}
var Wt = null;
function Gt(e) {
	var t = e.length;
	if (t !== 0) {
		for (var n = 0; n < t;) {
			var r = e[n++];
			if (!(r.f & 24576) && mr(r) && (Wt = /* @__PURE__ */ new Set(), br(r), r.deps === null && r.first === null && r.nodes === null && r.teardown === null && r.ac === null && Gn(r), Wt?.size > 0)) {
				Xt.clear();
				for (let e of Wt) {
					if (e.f & 24576) continue;
					let t = [e], n = e.parent;
					for (; n !== null;) Wt.has(n) && (Wt.delete(n), t.push(n)), n = n.parent;
					for (let e = t.length - 1; e >= 0; e--) {
						let n = t[e];
						n.f & 24576 || br(n);
					}
				}
				Wt.clear();
			}
		}
		Wt = null;
	}
}
function Kt(e) {
	F.schedule(e);
}
function qt(e, t) {
	if (!(e.f & 32 && e.f & 1024)) {
		e.f & 2048 ? t.d.push(e) : e.f & 4096 && t.m.push(e), lt(e, b);
		for (var n = e.first; n !== null;) qt(n, t), n = n.next;
	}
}
function Jt(e) {
	lt(e, b);
	for (var t = e.first; t !== null;) Jt(t), t = t.next;
}
// node_modules/svelte/src/internal/client/reactivity/sources.js
var Yt = /* @__PURE__ */ new Set(), Xt = /* @__PURE__ */ new Map(), Zt = !1;
function Qt(e, t) {
	return {
		f: 0,
		v: e,
		reactions: null,
		equals: Ae,
		rv: 0,
		wv: 0
	};
}
/*#__NO_SIDE_EFFECTS__*/
function I(e, t) {
	let n = Qt(e, t);
	return ir(n), n;
}
/*#__NO_SIDE_EFFECTS__*/
function $t(e, t = !1, n = !0) {
	let r = Qt(e);
	return t || (r.equals = Me), Ge && n && j !== null && j.l !== null && (j.l.s ??= []).push(r), r;
}
function L(e, t, n = !1) {
	return U !== null && (!er || U.f & 131072) && rt() && U.f & 4325394 && (rr === null || !rr.has(e)) && Ue(), nn(e, n ? sn(t) : t, Rt);
}
var en = null, tn = 0;
function nn(e, t, n = null) {
	if (!e.equals(t)) {
		Qn ? Xt.set(e, t) : Xt.has(e) || Xt.set(e, e.v);
		var r = Vt.ensure();
		if (r.capture(e, t), e.f & 2) {
			let t = e;
			e.f & 2048 && Dt(t), Nt === null && ut(t);
		}
		e.wv = pr(), en = null, tn = 0, on(e, x, n), en = null, rt() && W !== null && W.f & 1024 && !(W.f & 96) && (sr === null ? cr([e]) : sr.push(e)), !r.is_fork && Yt.size > 0 && !Zt && rn();
	}
	return t;
}
function rn() {
	Zt = !1;
	for (let e of Yt) {
		e.f & 1024 && lt(e, S);
		let t;
		try {
			t = mr(e);
		} catch {
			t = !0;
		}
		t && br(e);
	}
	Yt.clear();
}
function an(e) {
	L(e, e.v + 1);
}
function on(e, t, n) {
	var r = e.reactions;
	if (r !== null) {
		var i = rt(), a = r.length;
		if (tn += a, tn > 1e5 && en === null && (en = /* @__PURE__ */ new Set()), en !== null) {
			if (en.has(e)) return;
			en.add(e);
		}
		for (var o = 0; o < a; o++) {
			var s = r[o], c = s.f;
			if (i || s !== W) {
				var l = (c & x) === 0;
				if (l && lt(s, t), c & 131072) Yt.add(s);
				else if (c & 2) {
					var u = s;
					Nt?.delete(u), on(u, S, n);
				} else if (l) {
					var d = s;
					c & 16 && Wt !== null && Wt.add(d), n === null ? Kt(d) : n.push(d);
				}
			}
		}
	}
}
function sn(t) {
	if (typeof t != "object" || !t || oe in t || se in t) return t;
	let n = l(t);
	if (n !== s && n !== c) return t;
	var r = /* @__PURE__ */ new Map(), i = e(t), o = /* @__PURE__ */ I(0), u = null, d = dr, f = (e) => {
		if (dr === d) return e();
		var t = U, n = dr;
		tr(null), fr(d);
		var r = e();
		return tr(t), fr(n), r;
	};
	return i && r.set("length", /* @__PURE__ */ I(t.length, u)), new Proxy(t, {
		defineProperty(e, t, n) {
			"value" in n && n.configurable !== !1 && n.enumerable !== !1 && n.writable !== !1 || Ve();
			var i = r.get(t);
			return i === void 0 ? f(() => {
				var e = /* @__PURE__ */ I(n.value, u);
				return r.set(t, e), e;
			}) : L(i, n.value, !0), !0;
		},
		deleteProperty(e, t) {
			var n = r.get(t);
			if (n === void 0) {
				if (t in e) {
					let e = f(() => /* @__PURE__ */ I(ve, u));
					r.set(t, e), an(o);
				}
			} else L(n, ve), an(o);
			return !0;
		},
		get(e, n, i) {
			if (n === oe) return t;
			var o = r.get(n), s = n in e;
			if (o === void 0 && (!s || a(e, n)?.writable) && (o = f(() => /* @__PURE__ */ I(sn(s ? e[n] : ve), u)), r.set(n, o)), o !== void 0) {
				var c = G(o);
				return c === ve ? void 0 : c;
			}
			return Reflect.get(e, n, i);
		},
		getOwnPropertyDescriptor(e, t) {
			this.has?.(e, t);
			var n = Reflect.getOwnPropertyDescriptor(e, t), i = r.get(t);
			if (i !== void 0) {
				var a = G(i);
				if (a === ve) return;
				if (n && "value" in n) n.value = a;
				else return {
					enumerable: !0,
					configurable: !0,
					value: a,
					writable: !0
				};
			}
			return n;
		},
		has(e, t) {
			if (t === oe) return !0;
			var n = r.get(t), i = n !== void 0 && n.v !== ve || Reflect.has(e, t);
			return (n !== void 0 || W !== null && (!i || a(e, t)?.writable)) && (n === void 0 && (n = f(() => /* @__PURE__ */ I(i ? sn(e[t]) : ve, u)), r.set(t, n)), G(n) === ve) ? !1 : i;
		},
		set(e, t, n, s) {
			var c = r.get(t), l = t in e;
			if (i && t === "length") for (var d = n; d < c.v; d += 1) {
				var p = r.get(d + "");
				p === void 0 ? d in e && (p = f(() => /* @__PURE__ */ I(ve, u)), r.set(d + "", p)) : L(p, ve);
			}
			if (c === void 0) (!l || a(e, t)?.writable) && (c = f(() => /* @__PURE__ */ I(void 0, u)), L(c, sn(n)), r.set(t, c));
			else {
				l = c.v !== ve;
				var m = f(() => sn(n));
				L(c, m);
			}
			var h = Reflect.getOwnPropertyDescriptor(e, t);
			if (h?.set && h.set.call(s, n), !l) {
				if (i && typeof t == "string") {
					var g = r.get("length"), _ = Number(t);
					Number.isInteger(_) && _ >= g.v && L(g, _ + 1);
				}
				an(o);
			}
			return !0;
		},
		ownKeys(e) {
			G(o);
			var t = Reflect.ownKeys(e).filter((e) => {
				var t = r.get(e);
				return t === void 0 || t.v !== ve;
			});
			for (var [n, i] of r) i.v !== ve && !(n in e) && t.push(n);
			return t;
		},
		setPrototypeOf() {
			He();
		}
	});
}
function cn(e) {
	try {
		if (typeof e == "object" && e && oe in e) return e[oe];
	} catch {}
	return e;
}
function ln(e, t) {
	return Object.is(cn(e), cn(t));
}
var un, dn, fn, pn;
function mn() {
	if (un === void 0) {
		un = window, dn = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		fn = a(t, "firstChild").get, pn = a(t, "nextSibling").get, u(e) && (e[de] = void 0, e[ue] = null, e[fe] = void 0, e.__e = void 0), u(n) && (n[pe] = void 0);
	}
}
function hn(e = "") {
	return document.createTextNode(e);
}
/*@__NO_SIDE_EFFECTS__*/
function gn(e) {
	return fn.call(e);
}
/*@__NO_SIDE_EFFECTS__*/
function _n(e) {
	return pn.call(e);
}
function R(e, t) {
	if (!O) return /* @__PURE__ */ gn(e);
	var n = /* @__PURE__ */ gn(k);
	if (n === null) n = k.appendChild(hn());
	else if (t && n.nodeType !== 3) {
		var r = hn();
		return n?.before(r), Te(r), r;
	}
	return t && xn(n), Te(n), n;
}
function z(e, t = !1) {
	if (!O) {
		var n = /* @__PURE__ */ gn(e);
		return n instanceof Comment && n.data === "" ? /* @__PURE__ */ _n(n) : n;
	}
	if (t) {
		if (k?.nodeType !== 3) {
			var r = hn();
			return k?.before(r), Te(r), r;
		}
		xn(k);
	}
	return k;
}
function B(e, t = !1) {
	if (!O) return /* @__PURE__ */ gn(e);
	var n = R(e, t);
	return A(e), n;
}
function V(e, t = 1, n = !1) {
	let r = O ? k : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ _n(r);
	if (!O) return r;
	if (n) {
		if (r?.nodeType !== 3) {
			var a = hn();
			return r === null ? i?.after(a) : r.before(a), Te(a), a;
		}
		xn(r);
	}
	return Te(r), r;
}
function vn(e) {
	e.textContent = "";
}
function yn() {
	return !1;
}
function bn(e, t, n) {
	return t == null || t === "http://www.w3.org/1999/xhtml" ? n ? document.createElement(e, { is: n }) : document.createElement(e) : n ? document.createElementNS(t, e, { is: n }) : document.createElementNS(t, e);
}
function xn(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && t.nodeType === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
function Sn(e) {
	var t = W;
	if (t === null) return U.f |= ae, e;
	if (!(t.f & 32768) && !(t.f & 4)) throw e;
	Cn(e, t);
}
function Cn(e, t) {
	if (e === _e) throw e;
	if (!(t !== null && t.f & 16384)) {
		for (; t !== null;) {
			if (t.f & 128 && !(t.f & 33570816)) {
				if (!(t.f & 32768)) throw e;
				try {
					t.b.error(e);
					return;
				} catch (t) {
					e = t;
				}
			}
			t = t.parent;
		}
		throw e;
	}
}
// node_modules/svelte/src/internal/client/reactivity/effects.js
function wn(e) {
	W === null && (U === null && Re(e), Le()), Qn && Ie(e);
}
function Tn(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function En(e, t) {
	var n = W;
	n !== null && n.f & 8192 && (e |= C);
	var r = {
		ctx: j,
		deps: null,
		nodes: null,
		f: e | x | 512,
		first: null,
		fn: t,
		last: null,
		next: null,
		parent: n,
		b: n && n.b,
		prev: null,
		teardown: null,
		wv: 0,
		ac: null
	};
	F?.register_created_effect(r);
	var i = r;
	if (e & 4) Lt === null ? Vt.ensure().schedule(r) : Lt.push(r);
	else if (t !== null) {
		try {
			br(r);
		} catch (e) {
			throw Un(r), e;
		}
		i.deps === null && i.teardown === null && i.nodes === null && i.first === i.last && !(i.f & 524288) && (i = i.first, e & 16 && e & 65536 && i !== null && (i.f |= E));
	}
	if (i !== null && (i.parent = n, n !== null && Tn(i, n), U !== null && U.f & 2 && !(e & 64))) {
		var a = U;
		(a.effects ??= []).push(i);
	}
	return r;
}
function Dn() {
	return U !== null && !er;
}
function On(e) {
	let t = En(8, null);
	return lt(t, b), t.teardown = e, t;
}
function kn(e) {
	wn("$effect");
	var t = W.f;
	if (!U && t & 32 && j !== null && !j.i) {
		var n = j;
		(n.e ??= []).push(e);
	} else return An(e);
}
function An(e) {
	return En(4 | te, e);
}
function jn(e) {
	return wn("$effect.pre"), En(8 | te, e);
}
function Mn(e) {
	Vt.ensure();
	let t = En(64 | D, e);
	return () => {
		Un(t);
	};
}
function Nn(e) {
	Vt.ensure();
	let t = En(64 | D, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? Kn(t, () => {
			Un(t), n(void 0);
		}) : (Un(t), n(void 0));
	});
}
function Pn(e) {
	return En(4, e);
}
function Fn(e) {
	return En(ie | D, e);
}
function In(e, t = 0) {
	return En(8 | t, e);
}
function H(e, t = [], n = [], r = []) {
	vt(r, t, n, (t) => {
		En(8, () => {
			e(...t.map(G));
		});
	});
}
function Ln(e, t = 0) {
	return En(16 | t, e);
}
function Rn(e, t = 0) {
	return En(y | t, e);
}
function zn(e) {
	return En(32 | D, e);
}
function Bn(e) {
	var t = e.teardown;
	if (t !== null) {
		let n = Qn, r = U;
		$n(!0), tr(null);
		try {
			t.call(null);
		} catch (t) {
			Cn(t, e.parent);
		} finally {
			$n(n), tr(r);
		}
	}
}
function Vn(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		let e = n.ac;
		e !== null && gt(() => {
			e.abort(he);
		});
		var r = n.next;
		n.f & 64 ? n.parent = null : Un(n, t), n = r;
	}
}
function Hn(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || Un(t), t = n;
	}
}
function Un(e, t = !0) {
	var n = !1;
	(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (Wn(e.nodes.start, e.nodes.end), n = !0), e.f |= ee, Vn(e, t && !n), yr(e, 0);
	var r = e.nodes && e.nodes.t;
	if (r !== null) for (let e of r) e.stop();
	Bn(e), e.f ^= ee, e.f |= w;
	var i = e.parent;
	i !== null && i.first !== null && Gn(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.fn = e.nodes = e.ac = e.b = null;
}
function Wn(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ _n(e);
		e.remove(), e = n;
	}
}
function Gn(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function Kn(e, t, n = !0) {
	var r = [];
	e.f |= 256, qn(e, r, !0);
	var i = () => {
		n && Un(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = () => --a || i();
		for (var s of r) s.out(o);
	} else i();
}
function qn(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= C;
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) (e.is_global || n) && t.push(e);
		for (var i = e.first; i !== null;) {
			var a = i.next;
			if (!(i.f & 64)) {
				var o = !!(i.f & 65536) || !!(i.f & 32) && !!(e.f & 16);
				qn(i, t, o ? n : !1);
			}
			i = a;
		}
	}
}
function Jn(e) {
	e.f &= -257, Yn(e, !0);
}
function Yn(e, t) {
	if (!(e.f & 256) && e.f & 8192) {
		e.f ^= C, e.f & 1024 || (lt(e, x), Vt.ensure().schedule(e));
		for (var n = e.first; n !== null;) {
			var r = n.next, i = !!(n.f & 65536) || !!(n.f & 32);
			Yn(n, i ? t : !1), n = r;
		}
		var a = e.nodes && e.nodes.t;
		if (a !== null) for (let e of a) (e.is_global || t) && e.in();
	}
}
function Xn(e, t) {
	if (e.nodes) for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
		var i = n === r ? null : /* @__PURE__ */ _n(n);
		t.append(n), n = i;
	}
}
// node_modules/svelte/src/internal/client/legacy.js
var Zn = null, Qn = !1;
function $n(e) {
	Qn = e;
}
var U = null, er = !1;
function tr(e) {
	U = e;
}
var W = null;
function nr(e) {
	W = e;
}
var rr = null;
function ir(e) {
	U !== null && (U.f & 2097152 || U.f & 2) && (rr ??= /* @__PURE__ */ new Set()).add(e);
}
var ar = null, or = 0, sr = null;
function cr(e) {
	sr = e;
}
var lr = 1, ur = 0, dr = ur;
function fr(e) {
	dr = e;
}
function pr() {
	return ++lr;
}
function mr(e) {
	var t = e.f;
	if (t & 2048) return !0;
	if (t & 4096) {
		for (var n = e.deps, r = n.length, i = 0; i < r; i++) {
			var a = n[i];
			if (mr(a) && Ot(a), a.wv > e.wv) return !0;
		}
		t & 512 && Nt === null && lt(e, b);
	}
	return !1;
}
function hr(e, t, n = !0) {
	var r = e.reactions;
	if (r !== null && !(rr !== null && rr.has(e))) for (var i = 0; i < r.length; i++) {
		var a = r[i];
		a.f & 2 ? hr(a, t, !1) : t === a && (n ? lt(a, x) : a.f & 1024 && lt(a, S), Kt(a));
	}
}
function gr(e) {
	var t = ar, n = or, r = sr, i = U, a = rr, o = j, s = er, c = dr, l = e.f;
	ar = null, or = 0, sr = null, U = l & 96 ? null : e, rr = null, Qe(e.ctx), er = !1, dr = ++ur, e.ac !== null && (gt(() => {
		e.ac.abort(he);
	}), e.ac = null);
	try {
		e.f |= re;
		var u = e.fn, d = u();
		e.f |= T;
		var f = _r(e);
		if (rt() && sr !== null && !er && f !== null && !(e.f & 6146)) for (var p = 0; p < sr.length; p++) hr(sr[p], e);
		if (i !== null && i !== e) {
			if (ur++, i.deps !== null) for (let e = 0; e < n; e += 1) i.deps[e].rv = ur;
			if (t !== null) for (let e of t) e.rv = ur;
			sr !== null && (r === null ? r = sr : r.push(...sr));
		}
		return e.f & 8388608 && (e.f ^= ae), d;
	} catch (t) {
		return _r(e), Sn(t);
	} finally {
		e.f ^= re, ar = t, or = n, sr = r, U = i, rr = a, Qe(o), er = s, dr = c;
	}
}
function _r(e) {
	var t = e.deps, n = F?.is_fork;
	if (ar !== null) {
		var r;
		if (n || yr(e, or), t !== null && or > 0) for (t.length = or + ar.length, r = 0; r < ar.length; r++) t[or + r] = ar[r];
		else e.deps = t = ar;
		if (Dn() && e.f & 512) for (r = or; r < t.length; r++) (t[r].reactions ??= []).push(e);
	} else !n && t !== null && or < t.length && (yr(e, or), t.length = or);
	return t;
}
function vr(e, r) {
	let i = r.reactions;
	if (i !== null) {
		var a = t.call(i, e);
		if (a !== -1) {
			var o = i.length - 1;
			o === 0 ? i = r.reactions = null : (i[a] = i[o], i.pop());
		}
	}
	if (i === null && r.f & 2 && (ar === null || !n.call(ar, r))) {
		var s = r;
		s.f & 512 && (s.f ^= 512), s.v !== ve && ut(s), s.ac !== null && gt(() => {
			s.ac.abort(he), s.ac = null, lt(s, x);
		}), kt(s), yr(s, 0);
	}
}
function yr(e, t) {
	var n = e.deps;
	if (n !== null) for (var r = t; r < n.length; r++) vr(e, n[r]);
}
function br(e) {
	var t = e.f;
	if (!(t & 16384)) {
		lt(e, b);
		var n = W;
		W = e;
		try {
			t & 16777232 ? Hn(e) : Vn(e), Bn(e);
			var r = gr(e);
			e.teardown = typeof r == "function" ? r : null, e.wv = lr;
		} finally {
			W = n;
		}
	}
}
async function xr() {
	await Promise.resolve(), Ht();
}
function G(e) {
	var t = !!(e.f & 2);
	if (Zn?.add(e), U !== null && !er && !(W !== null && W.f & 16384) && (rr === null || !rr.has(e))) {
		var r = U.deps;
		if (U.f & 2097152) e.rv < ur && (e.rv = ur, ar === null && r !== null && r[or] === e ? or++ : ar === null ? ar = [e] : ar.push(e));
		else {
			U.deps ??= [], n.call(U.deps, e) || U.deps.push(e);
			var i = e.reactions;
			i === null ? e.reactions = [U] : n.call(i, U) || i.push(U);
		}
	}
	if (Qn && Xt.has(e)) return Xt.get(e);
	if (t) {
		var a = e;
		if (Qn) {
			var o = a.v;
			return (!(a.f & 1024) && a.reactions !== null || Cr(a)) && (o = Dt(a)), Xt.set(a, o), o;
		}
		var s = !(a.f & 512) && !er && U !== null && !!(U.f & 512), c = (a.f & T) === 0;
		mr(a) && (s && (a.f |= 512), Ot(a)), s && !c && (At(a), Sr(a));
	}
	if (Nt?.has(e)) return Nt.get(e);
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function Sr(e) {
	if (e.f |= 512, e.deps !== null) for (let r of e.deps) {
		var t = r.reactions;
		t === null ? r.reactions = [e] : n.call(t, e) || t.push(e), r.f & 2 && !(r.f & 512) && (At(r), Sr(r));
	}
}
function Cr(e) {
	if (e.v === ve) return !0;
	if (e.deps === null) return !1;
	for (let t of e.deps) if (Xt.has(t) || t.f & 2 && Cr(t)) return !0;
	return !1;
}
function wr(e) {
	var t = er;
	try {
		return er = !0, e();
	} finally {
		er = t;
	}
}
function Tr(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (oe in e) Er(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && oe in n && Er(n);
		}
	}
}
function Er(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			Er(e[n], t);
		} catch {}
		let n = l(e);
		if (n !== Object.prototype && n !== Array.prototype && n !== Map.prototype && n !== Set.prototype && n !== Date.prototype) {
			let t = o(n);
			for (let n in t) {
				let r = t[n].get;
				if (r) try {
					r.call(e);
				} catch {}
			}
		}
	}
}
// node_modules/svelte/src/utils.js
function Dr(e) {
	return e.endsWith("capture") && e !== "gotpointercapture" && e !== "lostpointercapture";
}
var Or = [
	"beforeinput",
	"click",
	"change",
	"dblclick",
	"contextmenu",
	"focusin",
	"focusout",
	"input",
	"keydown",
	"keyup",
	"mousedown",
	"mousemove",
	"mouseout",
	"mouseover",
	"mouseup",
	"pointerdown",
	"pointermove",
	"pointerout",
	"pointerover",
	"pointerup",
	"touchend",
	"touchmove",
	"touchstart"
];
function kr(e) {
	return Or.includes(e);
}
var Ar = /* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split("."), jr = {
	formnovalidate: "formNoValidate",
	ismap: "isMap",
	nomodule: "noModule",
	playsinline: "playsInline",
	readonly: "readOnly",
	defaultvalue: "defaultValue",
	defaultchecked: "defaultChecked",
	srcobject: "srcObject",
	novalidate: "noValidate",
	allowfullscreen: "allowFullscreen",
	disablepictureinpicture: "disablePictureInPicture",
	disableremoteplayback: "disableRemotePlayback"
};
function Mr(e) {
	return e = e.toLowerCase(), jr[e] ?? e;
}
[...Ar];
var Nr = ["touchstart", "touchmove"];
function Pr(e) {
	return Nr.includes(e);
}
// node_modules/svelte/src/internal/client/dom/elements/events.js
var Fr = Symbol("events"), Ir = /* @__PURE__ */ new Set(), Lr = /* @__PURE__ */ new Set();
function Rr(e, t, n, r = {}) {
	function i(e) {
		if (r.capture || Wr.call(t, e), !e.cancelBubble) return gt(() => n?.call(this, e));
	}
	return e.startsWith("pointer") || e.startsWith("touch") || e === "wheel" ? (i.__removed = !1, ot(() => {
		i.__removed || t.addEventListener(e, i, r);
	})) : t.addEventListener(e, i, r), i;
}
function zr(e, t, n, r = {}) {
	var i = Rr(t, e, n, r);
	return () => {
		i.__removed = !0, e.removeEventListener(t, i, r);
	};
}
function Br(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = Rr(e, t, n, a);
	(t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && On(() => {
		o.__removed = !0, t.removeEventListener(e, o, a);
	});
}
function K(e, t, n) {
	(t[Fr] ??= {})[e] = n;
}
function Vr(e) {
	for (var t = 0; t < e.length; t++) Ir.add(e[t]);
	for (var n of Lr) n(e);
}
var Hr = null, Ur = !1;
function Wr(e) {
	var t = this, n = t.ownerDocument, r = e.type, a = e.composedPath?.() || [], o = a[0] || e.target;
	Hr = e, Ur || (Ur = !0, setTimeout(() => {
		Ur = !1, Hr = null;
	}));
	var s = 0, c = Hr === e && e[Fr];
	if (c) {
		var l = a.indexOf(c);
		if (l !== -1 && (t === document || t === window)) {
			e[Fr] = t;
			return;
		}
		var u = a.indexOf(t);
		if (u === -1) return;
		l <= u && (s = l);
	}
	if (o = a[s] || e.target, o !== t) {
		i(e, "currentTarget", {
			configurable: !0,
			get() {
				return o || n;
			}
		});
		var d = U, f = W;
		tr(null), nr(null);
		try {
			for (var p, m = []; o !== null && o !== t;) {
				try {
					var h = o[Fr]?.[r];
					h == null || o.disabled && e.target !== o || h.call(o, e);
				} catch (e) {
					p ? m.push(e) : p = e;
				}
				if (e.cancelBubble) break;
				s++, o = s < a.length ? a[s] : null;
			}
			if (p) {
				for (let e of m) queueMicrotask(() => {
					throw e;
				});
				throw p;
			}
		} finally {
			e[Fr] = t, delete e.currentTarget, tr(d), nr(f);
		}
	}
}
// node_modules/svelte/src/internal/client/dom/reconciler.js
var Gr = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function Kr(e) {
	return Gr?.createHTML(e) ?? e;
}
function qr(e) {
	var t = bn("template");
	return t.innerHTML = Kr(e.replaceAll("<!>", "<!---->")), t.content;
}
// node_modules/svelte/src/internal/client/dom/template.js
function Jr(e, t) {
	var n = W;
	n.nodes === null && (n.nodes = {
		start: e,
		end: t,
		a: null,
		t: null
	});
}
/*#__NO_SIDE_EFFECTS__*/
function q(e, t) {
	var n = !!(t & 1), r = !!(t & 2), i, a = !e.startsWith("<!>");
	return () => {
		if (O) return Jr(k, null), k;
		i === void 0 && (i = qr(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ gn(i)));
		var t = r || dn ? document.importNode(i, !0) : i.cloneNode(!0);
		if (n) {
			var o = /* @__PURE__ */ gn(t), s = t.lastChild;
			Jr(o, s);
		} else Jr(t, t);
		return t;
	};
}
/*#__NO_SIDE_EFFECTS__*/
function Yr(e, t, n = "svg") {
	var r = !e.startsWith("<!>"), i = !!(t & 1), a = `<${n}>${r ? e : "<!>" + e}</${n}>`, o;
	return () => {
		if (O) return Jr(k, null), k;
		if (!o) {
			var e = /* @__PURE__ */ gn(qr(a));
			if (i) for (o = document.createDocumentFragment(); /* @__PURE__ */ gn(e);) o.appendChild(/* @__PURE__ */ gn(e));
			else o = /* @__PURE__ */ gn(e);
		}
		var t = o.cloneNode(!0);
		if (i) {
			var n = /* @__PURE__ */ gn(t), r = t.lastChild;
			Jr(n, r);
		} else Jr(t, t);
		return t;
	};
}
/*#__NO_SIDE_EFFECTS__*/
function Xr(e, t) {
	return /* @__PURE__ */ Yr(e, t, "svg");
}
function Zr(e = "") {
	if (!O) {
		var t = hn(e + "");
		return Jr(t, t), t;
	}
	var n = k;
	return n.nodeType === 3 ? xn(n) : (n.before(n = hn()), Te(n)), Jr(n, n), n;
}
function Qr() {
	if (O) return Jr(k, null), k;
	var e = document.createDocumentFragment(), t = document.createComment(""), n = hn();
	return e.append(t, n), Jr(t, n), e;
}
function J(e, t) {
	if (O) {
		var n = W;
		n.f & 32768 && n.nodes.end !== null || (n.nodes.end = k), Ee();
	} else e !== null && e.before(t);
}
// node_modules/svelte/src/reactivity/create-subscriber.js
function $r(e) {
	let t = 0, n = Qt(0), r;
	return () => {
		Dn() && (G(n), In(() => (t === 0 && (r = wr(() => e(() => an(n)))), t += 1, () => {
			ot(() => {
				--t, t === 0 && (r?.(), r = void 0, an(n));
			});
		})));
	};
}
// node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var ei = E | D;
function ti(e, t, n, r) {
	new ni(e, t, n, r);
}
var ni = class {
	parent;
	is_pending = !1;
	transform_error;
	#e;
	#t = O ? k : null;
	#n;
	#r;
	#i;
	#a = null;
	#o = null;
	#s = null;
	#c = null;
	#l = 0;
	#u = 0;
	#d = !1;
	#f = /* @__PURE__ */ new Set();
	#p = /* @__PURE__ */ new Set();
	#m = null;
	#h = $r(() => (this.#m = Qt(this.#l), () => {
		this.#m = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = W;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = W.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = Ln(() => {
			if (O) {
				let e = ke(this.#t);
				Ee();
				let t = e === "[!";
				if (e.startsWith("[?")) {
					let t = JSON.parse(e.slice(2));
					this.#_(t);
				} else t ? this.#b() : this.#g();
			} else this.#x();
		}, ei), O && (this.#e = k);
	}
	#g() {
		try {
			this.#a = zn(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#_(e) {
		let t = this.#n.failed, { reset: n, invoke_onerror: r } = this.#v(e);
		ot(r), t && (this.#s = zn(() => {
			t(this.#e, () => e, () => n);
		}));
	}
	#v(e) {
		var t = !1, n = !1;
		let r = () => {
			this.#y() || (t ? Ce() : (t = !0, n && We(), this.#s !== null && Kn(this.#s, () => {
				this.#s = null;
			}), this.#C(() => {
				this.#x();
			})));
		};
		return {
			reset: r,
			invoke_onerror: () => {
				if (!this.#y()) try {
					n = !0, this.#n.onerror?.(e, r), n = !1;
				} catch (e) {
					Cn(e, this.#i && this.#i.parent);
				}
			}
		};
	}
	#y() {
		return (this.#i.f & (w | ee)) !== 0;
	}
	#b() {
		let e = this.#n.pending;
		e && (this.is_pending = !0, this.#o = zn(() => e(this.#e)), ot(() => {
			if (!this.#y()) {
				var e = this.#c = document.createDocumentFragment(), t = hn(), n = !1;
				e.append(t), this.#a = this.#C(() => {
					try {
						return zn(() => this.#r(t));
					} catch (e) {
						try {
							this.error(e), n = !0;
						} catch (e) {
							Cn(e, this.#i.parent);
						}
						return null;
					}
				}), this.#a === null ? (this.#c = null, n && this.#S(F)) : this.#u === 0 && (this.#e.before(e), this.#c = null, Kn(this.#o, () => {
					this.#o = null;
				}), this.#S(F));
			}
		}));
	}
	#x() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#u = 0, this.#l = 0, this.#a = zn(() => {
				this.#r(this.#e);
			}), this.#u > 0) {
				var e = this.#c = document.createDocumentFragment();
				Xn(this.#a, e);
				let t = this.#n.pending;
				this.#o = zn(() => t(this.#e));
			} else this.#S(F);
		} catch (e) {
			this.error(e);
		}
	}
	#S(e) {
		this.is_pending = !1, e.transfer_effects(this.#f, this.#p);
	}
	defer_effect(e) {
		dt(e, this.#f, this.#p);
	}
	is_rendered() {
		return !this.is_pending && (!this.parent || this.parent.is_rendered());
	}
	has_pending_snippet() {
		return !!this.#n.pending;
	}
	#C(e) {
		var t = W, n = U, r = j;
		nr(this.#i), tr(this.#i), Qe(this.#i.ctx);
		try {
			return Vt.ensure(), e();
		} finally {
			nr(t), tr(n), Qe(r);
		}
	}
	#w(e, t) {
		this.has_pending_snippet() ? (this.#u += e, this.#u === 0 && (this.#S(t), this.#o && Kn(this.#o, () => {
			this.#o = null;
		}), this.#c &&= (this.#e.before(this.#c), null))) : this.parent && this.parent.#w(e, t);
	}
	update_pending_count(e, t) {
		this.#w(e, t), this.#l += e, !(!this.#m || this.#d) && (this.#d = !0, ot(() => {
			this.#d = !1, this.#m && nn(this.#m, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#h(), G(this.#m);
	}
	error(e) {
		if (e === _e || !this.#n.onerror && !this.#n.failed) throw e;
		F?.is_fork ? (this.#a && F.skip_effect(this.#a), this.#o && F.skip_effect(this.#o), this.#s && F.skip_effect(this.#s), F.oncommit(() => {
			this.#y() || this.#T(e);
		})) : this.#T(e);
	}
	#T(e) {
		this.#a &&= (Un(this.#a), null), this.#o &&= (Un(this.#o), null), this.#s &&= (Un(this.#s), null), O && (Te(this.#t), De(), Te(Oe()));
		let t = this.#n.failed, n = (e) => {
			if (this.#y()) return;
			let { reset: n, invoke_onerror: r } = this.#v(e);
			r(), t && !this.#y() && (this.#s = this.#C(() => {
				try {
					return zn(() => {
						var r = W;
						r.b = this, r.f |= 128, t(this.#e, () => e, () => n);
					});
				} catch (e) {
					return Cn(e, this.#i.parent), null;
				}
			}));
		};
		ot(() => {
			if (!this.#y()) {
				var t;
				try {
					t = this.transform_error(e);
				} catch (e) {
					Cn(e, this.#i && this.#i.parent);
					return;
				}
				typeof t == "object" && t && typeof t.then == "function" ? t.then(n, (e) => Cn(e, this.#i && this.#i.parent)) : n(t);
			}
		});
	}
};
function Y(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e[pe] ??= e.nodeValue) && (e[pe] = n, e.nodeValue = `${n}`);
}
function ri(e, t) {
	return ai(e, t);
}
var ii = /* @__PURE__ */ new Map();
function ai(e, { target: t, anchor: n, props: i = {}, events: a, context: o, intro: s = !0, transformError: c }) {
	mn();
	var l = void 0, u = Nn(() => {
		var s = n ?? t.appendChild(hn());
		ti(s, { pending: () => {} }, (t) => {
			M({});
			var n = j;
			if (o && (n.c = o), a && (i.$$events = a), O && Jr(t, null), l = e(t, i) || nt(), O && (W.nodes.end = k, k === null || k.nodeType !== 8 || k.data !== "]")) throw xe(), _e;
			N();
		}, c);
		var u = /* @__PURE__ */ new Set(), d = (e) => {
			for (var n = 0; n < e.length; n++) {
				var r = e[n];
				if (!u.has(r)) {
					u.add(r);
					var i = Pr(r);
					for (let e of [t, document]) {
						var a = ii.get(e);
						a === void 0 && (a = /* @__PURE__ */ new Map(), ii.set(e, a));
						var o = a.get(r);
						o === void 0 ? (e.addEventListener(r, Wr, { passive: i }), a.set(r, 1)) : a.set(r, o + 1);
					}
				}
			}
		};
		return d(r(Ir)), Lr.add(d), () => {
			for (var e of u) for (let n of [t, document]) {
				var r = ii.get(n), i = r.get(e);
				--i == 0 ? (n.removeEventListener(e, Wr), r.delete(e), r.size === 0 && ii.delete(n)) : r.set(e, i);
			}
			Lr.delete(d), s !== n && s.parentNode?.removeChild(s);
		};
	});
	return oi.set(l, u), l;
}
var oi = /* @__PURE__ */ new WeakMap();
function si(e, t) {
	let n = oi.get(e);
	return n ? (oi.delete(e), n(t)) : Promise.resolve();
}
// node_modules/svelte/src/internal/client/dom/blocks/branches.js
var ci = class {
	anchor;
	#e = /* @__PURE__ */ new Map();
	#t = /* @__PURE__ */ new Map();
	#n = /* @__PURE__ */ new Map();
	#r = /* @__PURE__ */ new Set();
	#i = !0;
	constructor(e, t = !0) {
		this.anchor = e, this.#i = t;
	}
	#a = (e) => {
		if (this.#e.has(e)) {
			var t = this.#e.get(e), n = this.#t.get(t);
			if (n) Jn(n), this.#r.delete(t);
			else {
				var r = this.#n.get(t);
				r && (Jn(r.effect), this.#t.set(t, r.effect), this.#n.delete(t), r.fragment.lastChild.remove(), this.anchor.before(r.fragment), n = r.effect);
			}
			for (let [t, n] of this.#e) {
				if (this.#e.delete(t), t === e) break;
				let r = this.#n.get(n);
				r && (Un(r.effect), this.#n.delete(n));
			}
			for (let [e, r] of this.#t) {
				if (e === t || this.#r.has(e)) continue;
				let i = () => {
					if (Array.from(this.#e.values()).includes(e)) {
						var t = document.createDocumentFragment();
						Xn(r, t), t.append(hn()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else Un(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), Kn(r, i, !1)) : i();
			}
		}
	};
	#o = (e) => {
		this.#e.delete(e);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (Un(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = F, r = yn();
		if (t && !this.#t.has(e) && !this.#n.has(e)) {
			if (r) {
				var i = document.createDocumentFragment(), a = hn();
				i.append(a), this.#n.set(e, {
					effect: zn(() => t(a)),
					fragment: i
				});
			} else this.#t.set(e, zn(() => t(this.anchor)));
		}
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#a), n.ondiscard(this.#o);
		} else O && (this.anchor = k), this.#a(n);
	}
};
// node_modules/svelte/src/internal/client/dom/blocks/if.js
function X(e, t, n = !1) {
	var r;
	O && (r = k, Ee());
	var i = new ci(e), a = n ? E : 0;
	function o(e, t) {
		if (O) {
			var n = ke(r);
			if (e !== parseInt(n.substring(1))) {
				var a = Oe();
				Te(a), i.anchor = a, we(!1), i.ensure(e, t), we(!0);
				return;
			}
		}
		i.ensure(e, t);
	}
	Ln(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, o(n, t);
		}), e || o(-1, null);
	}, a);
}
// node_modules/svelte/src/internal/client/dom/blocks/css-props.js
function li(e, t) {
	O && Te(/* @__PURE__ */ gn(e)), In(() => {
		var n = t();
		for (var r in n) {
			var i = n[r];
			i == null || i === "" ? e.style.removeProperty(r) : e.style.setProperty(r, i);
		}
	});
}
// node_modules/svelte/src/internal/client/dom/blocks/each.js
function ui(e, t) {
	return t;
}
function di(e, t, n) {
	for (var i = [], a = t.length, o, s = t.length, c = 0; c < a; c++) {
		let n = t[c];
		Kn(n, () => {
			if (o) {
				if (o.pending.delete(n), o.done.add(n), o.pending.size === 0) {
					var t = e.outrogroups;
					fi(e, r(o.done)), t.delete(o), t.size === 0 && (e.outrogroups = null);
				}
			} else --s;
		}, !1);
	}
	if (s === 0) {
		var l = i.length === 0 && n !== null && e.pending.size === 0;
		if (l) {
			var u = n, d = u.parentNode;
			vn(d), d.append(u), e.items.clear();
		}
		fi(e, t, !l);
	} else o = {
		pending: new Set(t),
		done: /* @__PURE__ */ new Set()
	}, (e.outrogroups ??= /* @__PURE__ */ new Set()).add(o);
}
function fi(e, t, n = !0) {
	var r;
	if (e.pending.size > 0) {
		r = /* @__PURE__ */ new Set();
		for (let t of e.pending.values()) for (let n of t) r.add(e.items.get(n).e);
	}
	for (var i = 0; i < t.length; i++) {
		var a = t[i];
		r?.has(a) ? (a.f |= ne, Xn(a, document.createDocumentFragment())) : Un(t[i], n);
	}
}
var pi;
function mi(t, n, i, a, o, s = null) {
	var c = t, l = /* @__PURE__ */ new Map();
	if (n & 4) {
		var u = t;
		c = O ? Te(/* @__PURE__ */ gn(u)) : u.appendChild(hn());
	}
	O && Ee();
	var d = null, f = /* @__PURE__ */ Tt(() => {
		var t = i();
		return e(t) ? t : t == null ? [] : r(t);
	}), p = /* @__PURE__ */ new Map(), m = !0;
	function h(e) {
		if (!(_.effect.f & 16384)) {
			_.pending.delete(e);
			var t = G(f);
			_.fallback = d, gi(_, t, c, n, a), d !== null && (t.length === 0 ? d.f & 33554432 ? (d.f ^= ne, vi(d, null, c)) : Jn(d) : Kn(d, () => {
				d = null;
			}));
		}
	}
	function g(e) {
		_.pending.delete(e);
	}
	var _ = {
		effect: Ln(() => {
			var e = G(f), t = e.length;
			let r = !1;
			O && ke(c) === "[!" != (t === 0) && (c = Oe(), Te(c), we(!1), r = !0);
			for (var u = /* @__PURE__ */ new Set(), _ = F, v = yn(), y = 0; y < t; y += 1) {
				O && k.nodeType === 8 && k.data === "]" && (c = k, r = !0, we(!1));
				var b = e[y], x = a(b, y), S = m ? null : l.get(x);
				S ? (S.v && nn(S.v, b), S.i && nn(S.i, y), v && _.unskip_effect(S.e)) : (S = _i(l, m ? c : pi ??= hn(), b, x, y, o, n, i), m || (S.e.f |= ne), l.set(x, S)), u.add(x);
			}
			if (t === 0 && s && !d && (m ? d = zn(() => s(c)) : (d = zn(() => s(pi ??= hn())), d.f |= ne)), t > u.size && Fe("", "", ""), O && t > 0 && Te(Oe()), !m) {
				if (p.set(_, u), v) {
					for (let [e, t] of l) u.has(e) || _.skip_effect(t.e);
					_.oncommit(h), _.ondiscard(g);
				} else h(_);
			}
			r && we(!0), G(f);
		}),
		flags: n,
		items: l,
		pending: p,
		outrogroups: null,
		fallback: d
	};
	m = !1, O && (c = k);
}
function hi(e) {
	for (; e !== null && !(e.f & 32);) e = e.next;
	return e;
}
function gi(e, t, n, i, a) {
	var o = !!(i & 8), s = t.length, c = e.items, l = hi(e.effect.first), u, d = null, f, p = [], m = [], h, g, _, v;
	if (o) for (v = 0; v < s; v += 1) h = t[v], g = a(h, v), _ = c.get(g).e, _.f & 33554432 || (_.nodes?.a?.measure(), (f ??= /* @__PURE__ */ new Set()).add(_));
	for (v = 0; v < s; v += 1) {
		if (h = t[v], g = a(h, v), _ = c.get(g).e, e.outrogroups !== null) for (let t of e.outrogroups) t.pending.delete(_), t.done.delete(_);
		if (_.f & 8192 && (Jn(_), o && (_.nodes?.a?.unfix(), (f ??= /* @__PURE__ */ new Set()).delete(_))), _.f & 33554432) {
			if (_.f ^= ne, _ === l) vi(_, null, n);
			else {
				var y = d ? d.next : l;
				_ === e.effect.last && (e.effect.last = _.prev), _.prev && (_.prev.next = _.next), _.next && (_.next.prev = _.prev), yi(e, d, _), yi(e, _, y), vi(_, y, n), d = _, p = [], m = [], l = hi(d.next);
				continue;
			}
		}
		if (_ !== l) {
			if (u !== void 0 && u.has(_)) {
				if (p.length < m.length) {
					var b = m[0], x;
					d = b.prev;
					var S = p[0], C = p[p.length - 1];
					for (x = 0; x < p.length; x += 1) vi(p[x], b, n);
					for (x = 0; x < m.length; x += 1) u.delete(m[x]);
					yi(e, S.prev, C.next), yi(e, d, S), yi(e, C, b), l = b, d = C, --v, p = [], m = [];
				} else u.delete(_), vi(_, l, n), yi(e, _.prev, _.next), yi(e, _, d === null ? e.effect.first : d.next), yi(e, d, _), d = _;
				continue;
			}
			for (p = [], m = []; l !== null && l !== _;) (u ??= /* @__PURE__ */ new Set()).add(l), m.push(l), l = hi(l.next);
			if (l === null) continue;
		}
		_.f & 33554432 || p.push(_), d = _, l = hi(_.next);
	}
	if (e.outrogroups !== null) {
		for (let t of e.outrogroups) t.pending.size === 0 && (fi(e, r(t.done)), e.outrogroups?.delete(t));
		e.outrogroups.size === 0 && (e.outrogroups = null);
	}
	if (l !== null || u !== void 0) {
		var w = [];
		if (u !== void 0) for (_ of u) _.f & 8192 || w.push(_);
		for (; l !== null;) !(l.f & 8192) && l !== e.fallback && w.push(l), l = hi(l.next);
		var T = w.length;
		if (T > 0) {
			var ee = i & 4 && s === 0 ? n : null;
			if (o) {
				for (v = 0; v < T; v += 1) w[v].nodes?.a?.measure();
				for (v = 0; v < T; v += 1) w[v].nodes?.a?.fix();
			}
			di(e, w, ee);
		}
	}
	o && ot(() => {
		if (f !== void 0) for (_ of f) _.nodes?.a?.apply();
	});
}
function _i(e, t, n, r, i, a, o, s) {
	var c = o & 1 ? o & 16 ? Qt(n) : /* @__PURE__ */ $t(n, !1, !1) : null, l = o & 2 ? Qt(i) : null;
	return {
		v: c,
		i: l,
		e: zn(() => (a(t, c ?? n, l ?? i, s), () => {
			e.delete(r);
		}))
	};
}
function vi(e, t, n) {
	if (e.nodes) for (var r = e.nodes.start, i = e.nodes.end, a = t && !(t.f & 33554432) ? t.nodes.start : n; r !== null;) {
		var o = /* @__PURE__ */ _n(r);
		if (a.before(r), r === i) return;
		r = o;
	}
}
function yi(e, t, n) {
	t === null ? e.effect.first = n : t.next = n, n === null ? e.effect.last = t : n.prev = t;
}
// node_modules/svelte/src/internal/client/dom/blocks/snippet.js
function bi(e, t, ...n) {
	var r = new ci(e);
	Ln(() => {
		let e = t() ?? null;
		r.ensure(e, e && ((t) => e(t, ...n)));
	}, E);
}
// node_modules/svelte/src/internal/client/dom/blocks/svelte-component.js
function xi(e, t, n) {
	var r;
	O && (r = k, Ee());
	var i = new ci(e);
	Ln(() => {
		var e = t() ?? null;
		if (O && ke(r) === "[" != (e !== null)) {
			var a = Oe();
			Te(a), i.anchor = a, we(!1), i.ensure(e, e && ((t) => n(t, e))), we(!0);
		} else i.ensure(e, e && ((t) => n(t, e)));
	}, E);
}
// node_modules/svelte/src/internal/client/dom/elements/actions.js
function Si(e, t, n) {
	Pn(() => {
		var r = wr(() => t(e, n?.()) || {});
		if (n && r?.update) {
			var i = !1, a = {};
			In(() => {
				var e = n();
				Tr(e), i && je(a, e) && (a = e, r.update(e));
			}), i = !0;
		}
		if (r?.destroy) return () => r.destroy();
	});
}
// node_modules/svelte/src/internal/client/dom/elements/attachments.js
function Ci(e, t) {
	var n = void 0, r;
	Rn(() => {
		n !== (n = t()) && (r &&= (Un(r), null), n && (r = zn(() => {
			Pn(() => n(e));
		})));
	});
}
// node_modules/clsx/dist/clsx.mjs
function wi(e) {
	var t, n, r = "";
	if (typeof e == "string" || typeof e == "number") r += e;
	else if (typeof e == "object") {
		if (Array.isArray(e)) {
			var i = e.length;
			for (t = 0; t < i; t++) e[t] && (n = wi(e[t])) && (r && (r += " "), r += n);
		} else for (n in e) e[n] && (r && (r += " "), r += n);
	}
	return r;
}
function Ti() {
	for (var e, t, n = 0, r = "", i = arguments.length; n < i; n++) (e = arguments[n]) && (t = wi(e)) && (r && (r += " "), r += t);
	return r;
}
// node_modules/svelte/src/internal/shared/attributes.js
function Ei(e) {
	return typeof e == "object" ? Ti(e) : e ?? "";
}
var Di = [..." 	\n\r\f\xA0\v﻿"];
function Oi(e, t, n) {
	var r = e == null ? "" : "" + e;
	if (t && (r = r ? r + " " + t : t), n) {
		for (var i of Object.keys(n)) if (n[i]) r = r ? r + " " + i : i;
		else if (r.length) for (var a = i.length, o = 0; (o = r.indexOf(i, o)) >= 0;) {
			var s = o + a;
			(o === 0 || Di.includes(r[o - 1])) && (s === r.length || Di.includes(r[s])) ? r = (o === 0 ? "" : r.substring(0, o)) + r.substring(s + 1) : o = s;
		}
	}
	return r === "" ? null : r;
}
function ki(e, t = !1) {
	var n = t ? " !important;" : ";", r = "";
	for (var i of Object.keys(e)) {
		var a = e[i];
		a != null && a !== "" && (r += " " + i + ": " + a + n);
	}
	return r;
}
function Ai(e) {
	return e[0] !== "-" || e[1] !== "-" ? e.toLowerCase() : e;
}
function ji(e, t) {
	if (t) {
		var n = "", r, i;
		if (Array.isArray(t) ? (r = t[0], i = t[1]) : r = t, e) {
			e = String(e).replaceAll(/\/\*.*?\*\//g, "").trim();
			var a = !1, o = 0, s = !1, c = [];
			r && c.push(...Object.keys(r).map(Ai)), i && c.push(...Object.keys(i).map(Ai));
			var l = 0, u = -1;
			let t = e.length;
			for (var d = 0; d < t; d++) {
				var f = e[d];
				if (s ? f === "/" && e[d - 1] === "*" && (s = !1) : a ? a === f && (a = !1) : f === "/" && e[d + 1] === "*" ? s = !0 : f === "\"" || f === "'" ? a = f : f === "(" ? o++ : f === ")" && o--, !s && a === !1 && o === 0) {
					if (f === ":" && u === -1) u = d;
					else if (f === ";" || d === t - 1) {
						if (u !== -1) {
							var p = Ai(e.substring(l, u).trim());
							if (!c.includes(p)) {
								f !== ";" && d++;
								var m = e.substring(l, d).trim();
								n += " " + m + ";";
							}
						}
						l = d + 1, u = -1;
					}
				}
			}
		}
		return r && (n += ki(r)), i && (n += ki(i, !0)), n = n.trim(), n === "" ? null : n;
	}
	return e == null ? null : String(e);
}
// node_modules/svelte/src/internal/client/dom/elements/class.js
function Mi(e, t, n, r, i, a) {
	var o = e[de];
	if (O || o !== n || o === void 0) {
		var s = Oi(n, r, a);
		O && s === e.getAttribute("class") || (s == null ? e.removeAttribute("class") : t ? e.className = s : e.setAttribute("class", s)), e[de] = n;
	} else if (a && i !== a) for (var c in a) {
		var l = !!a[c];
		(i == null || l !== !!i[c]) && e.classList.toggle(c, l);
	}
	return a;
}
// node_modules/svelte/src/internal/client/dom/elements/style.js
function Ni(e, t = {}, n, r) {
	for (var i in n) {
		var a = n[i];
		t[i] !== a && (n[i] == null ? e.style.removeProperty(i) : e.style.setProperty(i, a, r));
	}
}
function Pi(e, t, n, r) {
	var i = e[fe];
	if (O || i !== t) {
		var a = ji(t, r);
		O && a === e.getAttribute("style") || (a == null ? e.removeAttribute("style") : e.style.cssText = a), e[fe] = t;
	} else r && (Array.isArray(r) ? (Ni(e, n?.[0], r[0]), Ni(e, n?.[1], r[1], "important")) : Ni(e, n, r));
	return r;
}
// node_modules/svelte/src/internal/client/dom/elements/bindings/select.js
function Fi(e, t) {
	t ? e.hasAttribute("selected") || e.setAttribute("selected", "") : e.removeAttribute("selected");
}
function Ii(e, t) {
	var n = !("__defaultValue" in e);
	(n || e.__defaultValue !== t) && (e.__defaultValue = t, Li(e, !n || "__value" in e));
}
function Li(t, n) {
	var r = t.__defaultValue, i = t.multiple, a = i ? r ?? [] : null;
	if (!i || e(a)) {
		var o = t.selectedIndex, s = n && i ? new Set(t.selectedOptions) : null;
		for (var c of t.options) {
			var l = Vi(c);
			Fi(c, i ? a.includes(l) : ln(l, r));
		}
		if (n) {
			if (s !== null) for (c of t.options) {
				var u = s.has(c);
				c.selected !== u && (c.selected = u);
			}
			else t.selectedIndex !== o && (t.selectedIndex = o);
		}
	}
}
function Ri(t, n, r = !1) {
	if (t.multiple) {
		if (n == null) return;
		if (!e(n)) return Se();
		for (var i of t.options) i.selected = n.includes(Vi(i));
	} else {
		for (i of t.options) if (ln(Vi(i), n)) {
			i.selected = !0;
			return;
		}
		r && n === void 0 || (t.selectedIndex = -1);
	}
}
function zi(e) {
	var t = new MutationObserver((t) => {
		t.every(Hi) || ("__defaultValue" in e && Li(e, !1), "__value" in e && Ri(e, e.__value));
	});
	t.observe(e, {
		childList: !0,
		subtree: !0,
		attributes: !0,
		attributeFilter: ["value"]
	}), On(() => {
		t.disconnect();
	});
}
function Bi(e, t, n = t) {
	var r = /* @__PURE__ */ new WeakSet(), i = !0;
	_t(e, "change", (t) => {
		var i = t ? "[selected]" : ":checked", a;
		if (e.multiple) a = [].map.call(e.querySelectorAll(i), Vi);
		else {
			var o = e.querySelector(i) ?? e.querySelector("option:not([disabled])");
			a = o && Vi(o);
		}
		n(a), e.__value = a, F !== null && r.add(F);
	}), Pn(() => {
		var a = t();
		if (e === document.activeElement) {
			var o = F;
			if (r.has(o)) return;
		}
		if (Ri(e, a, i), i && a === void 0) {
			var s = e.querySelector(":checked");
			s !== null && (a = Vi(s), n(a));
		}
		e.__value = a, i = !1;
	});
}
function Vi(e) {
	return "__value" in e ? e.__value : e.value;
}
function Hi(e) {
	if (e.target.closest("selectedcontent") !== null) return !0;
	if (e.type === "childList") {
		var t = [...e.addedNodes, ...e.removedNodes];
		return t.length > 0 && t.every((e) => e.nodeName === "SELECTEDCONTENT");
	}
	return !1;
}
// node_modules/svelte/src/internal/client/dom/elements/attributes.js
var Ui = Symbol("class"), Wi = Symbol("style"), Gi = Symbol("is custom element"), Ki = Symbol("is html"), qi = ge ? "link" : "LINK", Ji = ge ? "input" : "INPUT", Yi = ge ? "option" : "OPTION", Xi = ge ? "select" : "SELECT", Zi = ge ? "progress" : "PROGRESS";
function Qi(e) {
	if (O) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, e.hasAttribute("value")) {
					var n = e.value;
					Z(e, "value", null), e.value = n;
				}
				if (e.hasAttribute("checked")) {
					var r = e.checked;
					Z(e, "checked", null), e.checked = r;
				}
			}
		};
		e[me] = n, ot(n), ht();
	}
}
function $i(e, t) {
	var n = ra(e);
	n.value !== (n.value = t ?? void 0) && (e.value !== t || t === 0 && e.nodeName === Zi) && (e.value = t ?? "");
}
function ea(e, t) {
	var n = ra(e);
	n.checked !== (n.checked = t ?? void 0) && (e.checked = t);
}
function Z(e, t, n, r) {
	var i = ra(e);
	O && (i[t] = e.getAttribute(t), t === "src" || t === "srcset" || t === "href" && e.nodeName === qi) || i[t] !== (i[t] = n) && (t === "loading" && (e[le] = n), n == null ? e.removeAttribute(t) : typeof n != "string" && aa(e).has(t) ? e[t] = n : e.setAttribute(t, n));
}
function ta(e, t, n, r, i = !1, a = !1) {
	O && i && e.nodeName === Ji && ("defaultValue" in n || "defaultChecked" in n || Qi(e));
	var o = ra(e), s = o[Gi], c = !o[Ki];
	let l = O && s;
	l && we(!1);
	var u = t || {}, d = e.nodeName === Yi, f = e.nodeName === Xi;
	try {
		for (var p in t) !(p in n) && p[0] + p[1] !== "$$" && (n[p] = null);
		n.class ? n.class = Ei(n.class) : (r || n[Ui]) && (n.class = null), n[Wi] && (n.style ??= null);
		var m = aa(e);
		if (e.nodeName === Ji && "type" in n && ("value" in n || "__value" in n)) {
			var h = n.type;
			(h !== u.type || h === void 0 && e.hasAttribute("type")) && (u.type = h, Z(e, "type", h, a));
		}
		for (let i in n) {
			let l = n[i];
			if (d && i === "value" && l == null) e.value = e.__value = "", u[i] = l;
			else if (i === "class") Mi(e, e.namespaceURI === "http://www.w3.org/1999/xhtml", l, r, t?.[Ui], n[Ui]), u[i] = l, u[Ui] = n[Ui];
			else if (i === "style") Pi(e, l, t?.[Wi], n[Wi]), u[i] = l, u[Wi] = n[Wi];
			else {
				var g = u[i];
				if (l !== g || l === void 0 && e.hasAttribute(i)) {
					u[i] = l;
					var _ = i[0] + i[1];
					if (_ !== "$$") {
						if (_ === "on") {
							let t = {}, n = "$$" + i, r = i.slice(2);
							var v = kr(r);
							if (Dr(r) && (r = r.slice(0, -7), t.capture = !0), !v && g) {
								if (l != null) continue;
								e.removeEventListener(r, u[n], t), u[n] = null;
							}
							if (v) K(r, e, l), Vr([r]);
							else if (l != null) {
								function a(e) {
									u[i].call(this, e);
								}
								u[n] = Rr(r, e, a, t);
							}
						} else if (i === "style") Z(e, i, l);
						else if (i === "autofocus") ft(e, !!l);
						else if (!s && (i === "__value" || i === "value" && l != null)) e.__value = l, (g == null || e.value !== l || l === 0 && e.nodeName === Zi) && (e.value = l);
						else if (i === "selected" && d) Fi(e, l);
						else {
							var y = i;
							c || (y = Mr(y));
							var b = y === "defaultValue" || y === "defaultChecked";
							if (f && y === "defaultValue") continue;
							if (l == null && !s && !b) {
								if (o[i] = null, y === "value" || y === "checked") {
									let n = e, r = t === void 0;
									if (y === "value") {
										let e = n.defaultValue;
										n.removeAttribute(y), n.defaultValue = e, n.value = n.__value = r ? e : null;
									} else {
										let e = n.defaultChecked;
										n.removeAttribute(y), n.defaultChecked = e, n.checked = r ? e : !1;
									}
								} else e.removeAttribute(i);
							} else b || (s || typeof l != "string") && m.has(y) ? (e[y] = l, y in o && (o[y] = ve)) : typeof l != "function" && Z(e, y, l, a);
						}
					}
				}
			}
		}
	} finally {
		l && we(!0);
	}
	return u;
}
function na(e, t, n = [], r = [], i = [], a, o = !1, s = !1) {
	vt(i, n, r, (n) => {
		var r = void 0, i = {}, c = e.nodeName === Xi, l = !1;
		if (Rn(() => {
			var u = t(...n.map(G)), d = ta(e, r, u, a, o, s);
			if (l && c) {
				var f = e;
				"defaultValue" in u && Ii(f, u.defaultValue), "value" in u && Ri(f, u.value);
			}
			for (let e of Object.getOwnPropertySymbols(i)) u[e] || Un(i[e]);
			for (let t of Object.getOwnPropertySymbols(u)) {
				var p = u[t];
				t.description !== "@attach" || r && p === r[t] || (i[t] && Un(i[t]), i[t] = zn(() => Ci(e, () => p))), d[t] = p;
			}
			r = d;
		}), c) {
			var u = e;
			Pn(() => {
				var e = r;
				"defaultValue" in e && Ii(u, e.defaultValue), Ri(u, e.value, !0), zi(u);
			});
		}
		l = !0;
	});
}
function ra(e) {
	return e[ue] ??= {
		[Gi]: e.nodeName.includes("-"),
		[Ki]: e.namespaceURI === ye
	};
}
var ia = /* @__PURE__ */ new Map();
function aa(e) {
	var t = e.getAttribute("is") || e.nodeName, n = ia.get(t);
	if (n) return n;
	ia.set(t, n = /* @__PURE__ */ new Set());
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var s in r = o(i), r) r[s].set && s !== "innerHTML" && s !== "textContent" && s !== "innerText" && n.add(s);
		i = l(i);
	}
	return n;
}
// node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function oa(e, t, n = t) {
	var r = /* @__PURE__ */ new WeakSet();
	_t(e, "input", async (i) => {
		var a = i ? e.defaultValue : e.value;
		if (a = sa(e) ? ca(a) : a, n(a), F !== null && r.add(F), await xr(), a !== (a = t())) {
			var o = e.selectionStart, s = e.selectionEnd, c = e.value.length;
			if (e.value = a ?? "", s !== null) {
				var l = e.value.length;
				o === s && s === c && l > c ? (e.selectionStart = l, e.selectionEnd = l) : (e.selectionStart = o, e.selectionEnd = Math.min(s, l));
			}
		}
	}), (O && e.defaultValue !== e.value || wr(t) == null && e.value) && (n(sa(e) ? ca(e.value) : e.value), F !== null && r.add(F)), In(() => {
		var n = t();
		if (e === document.activeElement) {
			var i = F;
			if (r.has(i)) return;
		}
		sa(e) && n === ca(e.value) || (e.type !== "date" || n || e.value) && n !== e.value && (e.value = n ?? "");
	});
}
function sa(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function ca(e) {
	return e === "" ? null : +e;
}
var la = /* @__PURE__ */ new class e {
	#e = /* @__PURE__ */ new WeakMap();
	#t;
	#n;
	static entries = /* @__PURE__ */ new WeakMap();
	constructor(e) {
		this.#n = e;
	}
	observe(e, t) {
		var n = this.#e.get(e) || /* @__PURE__ */ new Set();
		return n.add(t), this.#e.set(e, n), this.#r().observe(e, this.#n), () => {
			var n = this.#e.get(e);
			n.delete(t), n.size === 0 && (this.#e.delete(e), this.#t.unobserve(e));
		};
	}
	#r() {
		return this.#t ??= new ResizeObserver((t) => {
			for (var n of t) {
				e.entries.set(n.target, n);
				for (var r of this.#e.get(n.target) || []) r(n);
			}
		});
	}
}({ box: "border-box" });
function ua(e, t, n) {
	var r = la.observe(e, () => n(e[t]));
	Pn(() => (wr(() => n(e[t])), r));
}
// node_modules/svelte/src/internal/client/dom/elements/bindings/this.js
function da(e, t) {
	return e === t || e?.[oe] === t;
}
function fa(e = nt(), t, n, r) {
	var i = j.r, a = W;
	return Pn(() => {
		var o, s;
		return In(() => {
			o = s, s = r?.() || [], wr(() => {
				da(n(...s), e) || (t(e, ...s), o && da(n(...o), e) && t(null, ...o));
			});
		}), () => {
			let r = a;
			for (; r !== i && r.parent !== null && r.parent.f & 33554432;) r = r.parent;
			let o = () => {
				s && da(n(...s), e) && t(null, ...s);
			}, c = r.teardown;
			r.teardown = () => {
				o(), c?.();
			};
		};
	}), e;
}
// node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function pa(e = !1) {
	let t = j, n = t.l.u;
	if (!n) return;
	let r = () => Tr(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ St(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => G(i);
	}
	n.b.length && jn(() => {
		ma(t, r), m(n.b);
	}), kn(() => {
		let e = wr(() => n.m.map(p));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && kn(() => {
		ma(t, r), m(n.a);
	});
}
function ma(e, t) {
	if (e.l.s) for (let t of e.l.s) G(t);
	t();
}
// node_modules/svelte/src/internal/client/reactivity/store.js
var ha = !1;
function ga(e) {
	var t = ha;
	try {
		return ha = !1, [e(), ha];
	} finally {
		ha = t;
	}
}
// node_modules/svelte/src/internal/client/reactivity/props.js
var _a = {
	get(e, t) {
		if (!e.exclude.has(t)) return e.props[t];
	},
	set(e, t) {
		return !1;
	},
	getOwnPropertyDescriptor(e, t) {
		if (!e.exclude.has(t) && t in e.props) return {
			enumerable: !0,
			configurable: !0,
			value: e.props[t]
		};
	},
	has(e, t) {
		return !e.exclude.has(t) && t in e.props;
	},
	ownKeys(e) {
		return Reflect.ownKeys(e.props).filter((t) => !e.exclude.has(t));
	}
};
/*#__NO_SIDE_EFFECTS__*/
function va(e, t, n) {
	return new Proxy({
		props: e,
		exclude: t
	}, _a);
}
var ya = {
	get(e, t) {
		let n = e.props.length;
		for (; n--;) {
			let r = e.props[n];
			if (d(r) && (r = r()), typeof r == "object" && r && t in r) return r[t];
		}
	},
	set(e, t, n) {
		let r = e.props.length;
		for (; r--;) {
			let i = e.props[r];
			d(i) && (i = i());
			let o = a(i, t);
			if (o && o.set) return o.set(n), !0;
		}
		return !1;
	},
	getOwnPropertyDescriptor(e, t) {
		let n = e.props.length;
		for (; n--;) {
			let r = e.props[n];
			if (d(r) && (r = r()), typeof r == "object" && r && t in r) {
				let e = a(r, t);
				return e && !e.configurable && (e.configurable = !0), e;
			}
		}
	},
	has(e, t) {
		if (t === oe || t === ce) return !1;
		for (let n of e.props) if (d(n) && (n = n()), n != null && t in n) return !0;
		return !1;
	},
	ownKeys(e) {
		let t = [];
		for (let n of e.props) if (d(n) && (n = n()), n) {
			for (let e in n) t.includes(e) || t.push(e);
			for (let e of Object.getOwnPropertySymbols(n)) t.includes(e) || t.push(e);
		}
		return t;
	}
};
function ba(...e) {
	return new Proxy({ props: e }, ya);
}
function Q(e, t, n, r) {
	var i = !Ge || !!(n & 2), o = !!(n & 8), s = !!(n & 16), c = r, l = !0, u = void 0, d = () => s && i ? (u ??= /* @__PURE__ */ St(r), G(u)) : (l && (l = !1, c = s ? wr(r) : r), c);
	let f;
	if (o) {
		var p = oe in e || ce in e;
		f = a(e, t)?.set ?? (p && t in e ? (n) => e[t] = n : void 0);
	}
	var m, h = !1;
	o ? [m, h] = ga(() => e[t]) : m = e[t], m === void 0 && r !== void 0 && (m = d(), f && (i && Be(t), f(m)));
	var g = i ? () => {
		var n = e[t];
		return n === void 0 ? d() : (l = !0, n);
	} : () => {
		var n = e[t];
		return n !== void 0 && (c = void 0), n === void 0 ? c : n;
	};
	if (i && !(n & 4)) return g;
	if (f) {
		var _ = e.$$legacy;
		return (function(e, t) {
			return arguments.length > 0 ? ((!i || !t || _ || h) && f(t ? g() : e), e) : g();
		});
	}
	var v = !1, y = (n & 1 ? St : Tt)(() => (v = !1, g()));
	o && G(y);
	var b = W;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? G(y) : i && o ? sn(e) : e;
			return L(y, n), v = !0, c !== void 0 && (c = n), e;
		}
		return Qn && v || b.f & 16384 ? y.v : G(y);
	});
}
function xa(e) {
	j === null && Ne("onMount"), Ge && j.l !== null ? Ca(j).m.push(e) : kn(() => {
		let t = wr(e);
		if (typeof t == "function") return t;
	});
}
function Sa(e) {
	j === null && Ne("onDestroy"), xa(() => () => wr(e));
}
function Ca(e) {
	var t = e.l;
	return t.u ??= {
		a: [],
		b: [],
		m: []
	};
}
// node_modules/svelte/src/internal/disclose-version.js
typeof window < "u" && ((window.__svelte ??= {}).v ??= /* @__PURE__ */ new Set()).add("5");
// node_modules/d3-dispatch/src/dispatch.js
var wa = { value: () => {} };
function Ta() {
	for (var e = 0, t = arguments.length, n = {}, r; e < t; ++e) {
		if (!(r = arguments[e] + "") || r in n || /[\s.]/.test(r)) throw Error("illegal type: " + r);
		n[r] = [];
	}
	return new Ea(n);
}
function Ea(e) {
	this._ = e;
}
function Da(e, t) {
	return e.trim().split(/^|\s+/).map(function(e) {
		var n = "", r = e.indexOf(".");
		if (r >= 0 && (n = e.slice(r + 1), e = e.slice(0, r)), e && !t.hasOwnProperty(e)) throw Error("unknown type: " + e);
		return {
			type: e,
			name: n
		};
	});
}
Ea.prototype = Ta.prototype = {
	constructor: Ea,
	on: function(e, t) {
		var n = this._, r = Da(e + "", n), i, a = -1, o = r.length;
		if (arguments.length < 2) {
			for (; ++a < o;) if ((i = (e = r[a]).type) && (i = Oa(n[i], e.name))) return i;
		} else {
			if (t != null && typeof t != "function") throw Error("invalid callback: " + t);
			for (; ++a < o;) if (i = (e = r[a]).type) n[i] = ka(n[i], e.name, t);
			else if (t == null) for (i in n) n[i] = ka(n[i], e.name, null);
			return this;
		}
	},
	copy: function() {
		var e = {}, t = this._;
		for (var n in t) e[n] = t[n].slice();
		return new Ea(e);
	},
	call: function(e, t) {
		if ((i = arguments.length - 2) > 0) for (var n = Array(i), r = 0, i, a; r < i; ++r) n[r] = arguments[r + 2];
		if (!this._.hasOwnProperty(e)) throw Error("unknown type: " + e);
		for (a = this._[e], r = 0, i = a.length; r < i; ++r) a[r].value.apply(t, n);
	},
	apply: function(e, t, n) {
		if (!this._.hasOwnProperty(e)) throw Error("unknown type: " + e);
		for (var r = this._[e], i = 0, a = r.length; i < a; ++i) r[i].value.apply(t, n);
	}
};
function Oa(e, t) {
	for (var n = 0, r = e.length, i; n < r; ++n) if ((i = e[n]).name === t) return i.value;
}
function ka(e, t, n) {
	for (var r = 0, i = e.length; r < i; ++r) if (e[r].name === t) {
		e[r] = wa, e = e.slice(0, r).concat(e.slice(r + 1));
		break;
	}
	return n != null && e.push({
		name: t,
		value: n
	}), e;
}
var Aa = {
	svg: "http://www.w3.org/2000/svg",
	xhtml: "http://www.w3.org/1999/xhtml",
	xlink: "http://www.w3.org/1999/xlink",
	xml: "http://www.w3.org/XML/1998/namespace",
	xmlns: "http://www.w3.org/2000/xmlns/"
};
// node_modules/d3-selection/src/namespace.js
function ja(e) {
	var t = e += "", n = t.indexOf(":");
	return n >= 0 && (t = e.slice(0, n)) !== "xmlns" && (e = e.slice(n + 1)), Aa.hasOwnProperty(t) ? {
		space: Aa[t],
		local: e
	} : e;
}
// node_modules/d3-selection/src/creator.js
function Ma(e) {
	return function() {
		var t = this.ownerDocument, n = this.namespaceURI;
		return n === "http://www.w3.org/1999/xhtml" && t.documentElement.namespaceURI === "http://www.w3.org/1999/xhtml" ? t.createElement(e) : t.createElementNS(n, e);
	};
}
function Na(e) {
	return function() {
		return this.ownerDocument.createElementNS(e.space, e.local);
	};
}
function Pa(e) {
	var t = ja(e);
	return (t.local ? Na : Ma)(t);
}
// node_modules/d3-selection/src/selector.js
function Fa() {}
function Ia(e) {
	return e == null ? Fa : function() {
		return this.querySelector(e);
	};
}
// node_modules/d3-selection/src/selection/select.js
function La(e) {
	typeof e != "function" && (e = Ia(e));
	for (var t = this._groups, n = t.length, r = Array(n), i = 0; i < n; ++i) for (var a = t[i], o = a.length, s = r[i] = Array(o), c, l, u = 0; u < o; ++u) (c = a[u]) && (l = e.call(c, c.__data__, u, a)) && ("__data__" in c && (l.__data__ = c.__data__), s[u] = l);
	return new Es(r, this._parents);
}
// node_modules/d3-selection/src/array.js
function Ra(e) {
	return e == null ? [] : Array.isArray(e) ? e : Array.from(e);
}
// node_modules/d3-selection/src/selectorAll.js
function za() {
	return [];
}
function Ba(e) {
	return e == null ? za : function() {
		return this.querySelectorAll(e);
	};
}
// node_modules/d3-selection/src/selection/selectAll.js
function Va(e) {
	return function() {
		return Ra(e.apply(this, arguments));
	};
}
function Ha(e) {
	e = typeof e == "function" ? Va(e) : Ba(e);
	for (var t = this._groups, n = t.length, r = [], i = [], a = 0; a < n; ++a) for (var o = t[a], s = o.length, c, l = 0; l < s; ++l) (c = o[l]) && (r.push(e.call(c, c.__data__, l, o)), i.push(c));
	return new Es(r, i);
}
// node_modules/d3-selection/src/matcher.js
function Ua(e) {
	return function() {
		return this.matches(e);
	};
}
function Wa(e) {
	return function(t) {
		return t.matches(e);
	};
}
// node_modules/d3-selection/src/selection/selectChild.js
var Ga = Array.prototype.find;
function Ka(e) {
	return function() {
		return Ga.call(this.children, e);
	};
}
function qa() {
	return this.firstElementChild;
}
function Ja(e) {
	return this.select(e == null ? qa : Ka(typeof e == "function" ? e : Wa(e)));
}
// node_modules/d3-selection/src/selection/selectChildren.js
var Ya = Array.prototype.filter;
function Xa() {
	return Array.from(this.children);
}
function Za(e) {
	return function() {
		return Ya.call(this.children, e);
	};
}
function Qa(e) {
	return this.selectAll(e == null ? Xa : Za(typeof e == "function" ? e : Wa(e)));
}
// node_modules/d3-selection/src/selection/filter.js
function $a(e) {
	typeof e != "function" && (e = Ua(e));
	for (var t = this._groups, n = t.length, r = Array(n), i = 0; i < n; ++i) for (var a = t[i], o = a.length, s = r[i] = [], c, l = 0; l < o; ++l) (c = a[l]) && e.call(c, c.__data__, l, a) && s.push(c);
	return new Es(r, this._parents);
}
// node_modules/d3-selection/src/selection/sparse.js
function eo(e) {
	return Array(e.length);
}
// node_modules/d3-selection/src/selection/enter.js
function to() {
	return new Es(this._enter || this._groups.map(eo), this._parents);
}
function no(e, t) {
	this.ownerDocument = e.ownerDocument, this.namespaceURI = e.namespaceURI, this._next = null, this._parent = e, this.__data__ = t;
}
no.prototype = {
	constructor: no,
	appendChild: function(e) {
		return this._parent.insertBefore(e, this._next);
	},
	insertBefore: function(e, t) {
		return this._parent.insertBefore(e, t);
	},
	querySelector: function(e) {
		return this._parent.querySelector(e);
	},
	querySelectorAll: function(e) {
		return this._parent.querySelectorAll(e);
	}
};
// node_modules/d3-selection/src/constant.js
function ro(e) {
	return function() {
		return e;
	};
}
// node_modules/d3-selection/src/selection/data.js
function io(e, t, n, r, i, a) {
	for (var o = 0, s, c = t.length, l = a.length; o < l; ++o) (s = t[o]) ? (s.__data__ = a[o], r[o] = s) : n[o] = new no(e, a[o]);
	for (; o < c; ++o) (s = t[o]) && (i[o] = s);
}
function ao(e, t, n, r, i, a, o) {
	var s, c, l = /* @__PURE__ */ new Map(), u = t.length, d = a.length, f = Array(u), p;
	for (s = 0; s < u; ++s) (c = t[s]) && (f[s] = p = o.call(c, c.__data__, s, t) + "", l.has(p) ? i[s] = c : l.set(p, c));
	for (s = 0; s < d; ++s) p = o.call(e, a[s], s, a) + "", (c = l.get(p)) ? (r[s] = c, c.__data__ = a[s], l.delete(p)) : n[s] = new no(e, a[s]);
	for (s = 0; s < u; ++s) (c = t[s]) && l.get(f[s]) === c && (i[s] = c);
}
function oo(e) {
	return e.__data__;
}
function so(e, t) {
	if (!arguments.length) return Array.from(this, oo);
	var n = t ? ao : io, r = this._parents, i = this._groups;
	typeof e != "function" && (e = ro(e));
	for (var a = i.length, o = Array(a), s = Array(a), c = Array(a), l = 0; l < a; ++l) {
		var u = r[l], d = i[l], f = d.length, p = co(e.call(u, u && u.__data__, l, r)), m = p.length, h = s[l] = Array(m), g = o[l] = Array(m);
		n(u, d, h, g, c[l] = Array(f), p, t);
		for (var _ = 0, v = 0, y, b; _ < m; ++_) if (y = h[_]) {
			for (_ >= v && (v = _ + 1); !(b = g[v]) && ++v < m;);
			y._next = b || null;
		}
	}
	return o = new Es(o, r), o._enter = s, o._exit = c, o;
}
function co(e) {
	return typeof e == "object" && "length" in e ? e : Array.from(e);
}
// node_modules/d3-selection/src/selection/exit.js
function lo() {
	return new Es(this._exit || this._groups.map(eo), this._parents);
}
// node_modules/d3-selection/src/selection/join.js
function uo(e, t, n) {
	var r = this.enter(), i = this, a = this.exit();
	return typeof e == "function" ? (r = e(r), r &&= r.selection()) : r = r.append(e + ""), t != null && (i = t(i), i &&= i.selection()), n == null ? a.remove() : n(a), r && i ? r.merge(i).order() : i;
}
// node_modules/d3-selection/src/selection/merge.js
function fo(e) {
	for (var t = e.selection ? e.selection() : e, n = this._groups, r = t._groups, i = n.length, a = r.length, o = Math.min(i, a), s = Array(i), c = 0; c < o; ++c) for (var l = n[c], u = r[c], d = l.length, f = s[c] = Array(d), p, m = 0; m < d; ++m) (p = l[m] || u[m]) && (f[m] = p);
	for (; c < i; ++c) s[c] = n[c];
	return new Es(s, this._parents);
}
// node_modules/d3-selection/src/selection/order.js
function po() {
	for (var e = this._groups, t = -1, n = e.length; ++t < n;) for (var r = e[t], i = r.length - 1, a = r[i], o; --i >= 0;) (o = r[i]) && (a && o.compareDocumentPosition(a) ^ 4 && a.parentNode.insertBefore(o, a), a = o);
	return this;
}
// node_modules/d3-selection/src/selection/sort.js
function mo(e) {
	e ||= ho;
	function t(t, n) {
		return t && n ? e(t.__data__, n.__data__) : !t - !n;
	}
	for (var n = this._groups, r = n.length, i = Array(r), a = 0; a < r; ++a) {
		for (var o = n[a], s = o.length, c = i[a] = Array(s), l, u = 0; u < s; ++u) (l = o[u]) && (c[u] = l);
		c.sort(t);
	}
	return new Es(i, this._parents).order();
}
function ho(e, t) {
	return e < t ? -1 : e > t ? 1 : e >= t ? 0 : NaN;
}
// node_modules/d3-selection/src/selection/call.js
function go() {
	var e = arguments[0];
	return arguments[0] = this, e.apply(null, arguments), this;
}
// node_modules/d3-selection/src/selection/nodes.js
function _o() {
	return Array.from(this);
}
// node_modules/d3-selection/src/selection/node.js
function vo() {
	for (var e = this._groups, t = 0, n = e.length; t < n; ++t) for (var r = e[t], i = 0, a = r.length; i < a; ++i) {
		var o = r[i];
		if (o) return o;
	}
	return null;
}
// node_modules/d3-selection/src/selection/size.js
function yo() {
	let e = 0;
	for (let t of this) ++e;
	return e;
}
// node_modules/d3-selection/src/selection/empty.js
function bo() {
	return !this.node();
}
// node_modules/d3-selection/src/selection/each.js
function xo(e) {
	for (var t = this._groups, n = 0, r = t.length; n < r; ++n) for (var i = t[n], a = 0, o = i.length, s; a < o; ++a) (s = i[a]) && e.call(s, s.__data__, a, i);
	return this;
}
// node_modules/d3-selection/src/selection/attr.js
function So(e) {
	return function() {
		this.removeAttribute(e);
	};
}
function Co(e) {
	return function() {
		this.removeAttributeNS(e.space, e.local);
	};
}
function wo(e, t) {
	return function() {
		this.setAttribute(e, t);
	};
}
function To(e, t) {
	return function() {
		this.setAttributeNS(e.space, e.local, t);
	};
}
function Eo(e, t) {
	return function() {
		var n = t.apply(this, arguments);
		n == null ? this.removeAttribute(e) : this.setAttribute(e, n);
	};
}
function Do(e, t) {
	return function() {
		var n = t.apply(this, arguments);
		n == null ? this.removeAttributeNS(e.space, e.local) : this.setAttributeNS(e.space, e.local, n);
	};
}
function Oo(e, t) {
	var n = ja(e);
	if (arguments.length < 2) {
		var r = this.node();
		return n.local ? r.getAttributeNS(n.space, n.local) : r.getAttribute(n);
	}
	return this.each((t == null ? n.local ? Co : So : typeof t == "function" ? n.local ? Do : Eo : n.local ? To : wo)(n, t));
}
// node_modules/d3-selection/src/window.js
function ko(e) {
	return e.ownerDocument && e.ownerDocument.defaultView || e.document && e || e.defaultView;
}
// node_modules/d3-selection/src/selection/style.js
function Ao(e) {
	return function() {
		this.style.removeProperty(e);
	};
}
function jo(e, t, n) {
	return function() {
		this.style.setProperty(e, t, n);
	};
}
function Mo(e, t, n) {
	return function() {
		var r = t.apply(this, arguments);
		r == null ? this.style.removeProperty(e) : this.style.setProperty(e, r, n);
	};
}
function No(e, t, n) {
	return arguments.length > 1 ? this.each((t == null ? Ao : typeof t == "function" ? Mo : jo)(e, t, n ?? "")) : Po(this.node(), e);
}
function Po(e, t) {
	return e.style.getPropertyValue(t) || ko(e).getComputedStyle(e, null).getPropertyValue(t);
}
// node_modules/d3-selection/src/selection/property.js
function Fo(e) {
	return function() {
		delete this[e];
	};
}
function Io(e, t) {
	return function() {
		this[e] = t;
	};
}
function Lo(e, t) {
	return function() {
		var n = t.apply(this, arguments);
		n == null ? delete this[e] : this[e] = n;
	};
}
function Ro(e, t) {
	return arguments.length > 1 ? this.each((t == null ? Fo : typeof t == "function" ? Lo : Io)(e, t)) : this.node()[e];
}
// node_modules/d3-selection/src/selection/classed.js
function zo(e) {
	return e.trim().split(/^|\s+/);
}
function Bo(e) {
	return e.classList || new Vo(e);
}
function Vo(e) {
	this._node = e, this._names = zo(e.getAttribute("class") || "");
}
Vo.prototype = {
	add: function(e) {
		this._names.indexOf(e) < 0 && (this._names.push(e), this._node.setAttribute("class", this._names.join(" ")));
	},
	remove: function(e) {
		var t = this._names.indexOf(e);
		t >= 0 && (this._names.splice(t, 1), this._node.setAttribute("class", this._names.join(" ")));
	},
	contains: function(e) {
		return this._names.indexOf(e) >= 0;
	}
};
function Ho(e, t) {
	for (var n = Bo(e), r = -1, i = t.length; ++r < i;) n.add(t[r]);
}
function Uo(e, t) {
	for (var n = Bo(e), r = -1, i = t.length; ++r < i;) n.remove(t[r]);
}
function Wo(e) {
	return function() {
		Ho(this, e);
	};
}
function Go(e) {
	return function() {
		Uo(this, e);
	};
}
function Ko(e, t) {
	return function() {
		(t.apply(this, arguments) ? Ho : Uo)(this, e);
	};
}
function qo(e, t) {
	var n = zo(e + "");
	if (arguments.length < 2) {
		for (var r = Bo(this.node()), i = -1, a = n.length; ++i < a;) if (!r.contains(n[i])) return !1;
		return !0;
	}
	return this.each((typeof t == "function" ? Ko : t ? Wo : Go)(n, t));
}
// node_modules/d3-selection/src/selection/text.js
function Jo() {
	this.textContent = "";
}
function Yo(e) {
	return function() {
		this.textContent = e;
	};
}
function Xo(e) {
	return function() {
		var t = e.apply(this, arguments);
		this.textContent = t ?? "";
	};
}
function Zo(e) {
	return arguments.length ? this.each(e == null ? Jo : (typeof e == "function" ? Xo : Yo)(e)) : this.node().textContent;
}
// node_modules/d3-selection/src/selection/html.js
function Qo() {
	this.innerHTML = "";
}
function $o(e) {
	return function() {
		this.innerHTML = e;
	};
}
function es(e) {
	return function() {
		var t = e.apply(this, arguments);
		this.innerHTML = t ?? "";
	};
}
function ts(e) {
	return arguments.length ? this.each(e == null ? Qo : (typeof e == "function" ? es : $o)(e)) : this.node().innerHTML;
}
// node_modules/d3-selection/src/selection/raise.js
function ns() {
	this.nextSibling && this.parentNode.appendChild(this);
}
function rs() {
	return this.each(ns);
}
// node_modules/d3-selection/src/selection/lower.js
function is() {
	this.previousSibling && this.parentNode.insertBefore(this, this.parentNode.firstChild);
}
function as() {
	return this.each(is);
}
// node_modules/d3-selection/src/selection/append.js
function os(e) {
	var t = typeof e == "function" ? e : Pa(e);
	return this.select(function() {
		return this.appendChild(t.apply(this, arguments));
	});
}
// node_modules/d3-selection/src/selection/insert.js
function ss() {
	return null;
}
function cs(e, t) {
	var n = typeof e == "function" ? e : Pa(e), r = t == null ? ss : typeof t == "function" ? t : Ia(t);
	return this.select(function() {
		return this.insertBefore(n.apply(this, arguments), r.apply(this, arguments) || null);
	});
}
// node_modules/d3-selection/src/selection/remove.js
function ls() {
	var e = this.parentNode;
	e && e.removeChild(this);
}
function us() {
	return this.each(ls);
}
// node_modules/d3-selection/src/selection/clone.js
function ds() {
	var e = this.cloneNode(!1), t = this.parentNode;
	return t ? t.insertBefore(e, this.nextSibling) : e;
}
function fs() {
	var e = this.cloneNode(!0), t = this.parentNode;
	return t ? t.insertBefore(e, this.nextSibling) : e;
}
function ps(e) {
	return this.select(e ? fs : ds);
}
// node_modules/d3-selection/src/selection/datum.js
function ms(e) {
	return arguments.length ? this.property("__data__", e) : this.node().__data__;
}
// node_modules/d3-selection/src/selection/on.js
function hs(e) {
	return function(t) {
		e.call(this, t, this.__data__);
	};
}
function gs(e) {
	return e.trim().split(/^|\s+/).map(function(e) {
		var t = "", n = e.indexOf(".");
		return n >= 0 && (t = e.slice(n + 1), e = e.slice(0, n)), {
			type: e,
			name: t
		};
	});
}
function _s(e) {
	return function() {
		var t = this.__on;
		if (t) {
			for (var n = 0, r = -1, i = t.length, a; n < i; ++n) a = t[n], (!e.type || a.type === e.type) && a.name === e.name ? this.removeEventListener(a.type, a.listener, a.options) : t[++r] = a;
			++r ? t.length = r : delete this.__on;
		}
	};
}
function vs(e, t, n) {
	return function() {
		var r = this.__on, i, a = hs(t);
		if (r) {
			for (var o = 0, s = r.length; o < s; ++o) if ((i = r[o]).type === e.type && i.name === e.name) {
				this.removeEventListener(i.type, i.listener, i.options), this.addEventListener(i.type, i.listener = a, i.options = n), i.value = t;
				return;
			}
		}
		this.addEventListener(e.type, a, n), i = {
			type: e.type,
			name: e.name,
			value: t,
			listener: a,
			options: n
		}, r ? r.push(i) : this.__on = [i];
	};
}
function ys(e, t, n) {
	var r = gs(e + ""), i, a = r.length, o;
	if (arguments.length < 2) {
		var s = this.node().__on;
		if (s) {
			for (var c = 0, l = s.length, u; c < l; ++c) for (i = 0, u = s[c]; i < a; ++i) if ((o = r[i]).type === u.type && o.name === u.name) return u.value;
		}
	} else {
		for (s = t ? vs : _s, i = 0; i < a; ++i) this.each(s(r[i], t, n));
		return this;
	}
}
// node_modules/d3-selection/src/selection/dispatch.js
function bs(e, t, n) {
	var r = ko(e), i = r.CustomEvent;
	typeof i == "function" ? i = new i(t, n) : (i = r.document.createEvent("Event"), n ? (i.initEvent(t, n.bubbles, n.cancelable), i.detail = n.detail) : i.initEvent(t, !1, !1)), e.dispatchEvent(i);
}
function xs(e, t) {
	return function() {
		return bs(this, e, t);
	};
}
function Ss(e, t) {
	return function() {
		return bs(this, e, t.apply(this, arguments));
	};
}
function Cs(e, t) {
	return this.each((typeof t == "function" ? Ss : xs)(e, t));
}
// node_modules/d3-selection/src/selection/iterator.js
function* ws() {
	for (var e = this._groups, t = 0, n = e.length; t < n; ++t) for (var r = e[t], i = 0, a = r.length, o; i < a; ++i) (o = r[i]) && (yield o);
}
// node_modules/d3-selection/src/selection/index.js
var Ts = [null];
function Es(e, t) {
	this._groups = e, this._parents = t;
}
function Ds() {
	return new Es([[document.documentElement]], Ts);
}
function Os() {
	return this;
}
Es.prototype = Ds.prototype = {
	constructor: Es,
	select: La,
	selectAll: Ha,
	selectChild: Ja,
	selectChildren: Qa,
	filter: $a,
	data: so,
	enter: to,
	exit: lo,
	join: uo,
	merge: fo,
	selection: Os,
	order: po,
	sort: mo,
	call: go,
	nodes: _o,
	node: vo,
	size: yo,
	empty: bo,
	each: xo,
	attr: Oo,
	style: No,
	property: Ro,
	classed: qo,
	text: Zo,
	html: ts,
	raise: rs,
	lower: as,
	append: os,
	insert: cs,
	remove: us,
	clone: ps,
	datum: ms,
	on: ys,
	dispatch: Cs,
	[Symbol.iterator]: ws
};
// node_modules/d3-selection/src/select.js
function ks(e) {
	return typeof e == "string" ? new Es([[document.querySelector(e)]], [document.documentElement]) : new Es([[e]], Ts);
}
// node_modules/d3-selection/src/sourceEvent.js
function As(e) {
	let t;
	for (; t = e.sourceEvent;) e = t;
	return e;
}
// node_modules/d3-selection/src/pointer.js
function js(e, t) {
	if (e = As(e), t === void 0 && (t = e.currentTarget), t) {
		var n = t.ownerSVGElement || t;
		if (n.createSVGPoint) {
			var r = n.createSVGPoint();
			return r.x = e.clientX, r.y = e.clientY, r = r.matrixTransform(t.getScreenCTM().inverse()), [r.x, r.y];
		}
		if (t.getBoundingClientRect) {
			var i = t.getBoundingClientRect();
			return [e.clientX - i.left - t.clientLeft, e.clientY - i.top - t.clientTop];
		}
	}
	return [e.pageX, e.pageY];
}
// node_modules/d3-drag/src/noevent.js
var Ms = { passive: !1 }, Ns = {
	capture: !0,
	passive: !1
};
function Ps(e) {
	e.stopImmediatePropagation();
}
function Fs(e) {
	e.preventDefault(), e.stopImmediatePropagation();
}
// node_modules/d3-drag/src/nodrag.js
function Is(e) {
	var t = e.document.documentElement, n = ks(e).on("dragstart.drag", Fs, Ns);
	"onselectstart" in t ? n.on("selectstart.drag", Fs, Ns) : (t.__noselect = t.style.MozUserSelect, t.style.MozUserSelect = "none");
}
function Ls(e, t) {
	var n = e.document.documentElement, r = ks(e).on("dragstart.drag", null);
	t && (r.on("click.drag", Fs, Ns), setTimeout(function() {
		r.on("click.drag", null);
	}, 0)), "onselectstart" in n ? r.on("selectstart.drag", null) : (n.style.MozUserSelect = n.__noselect, delete n.__noselect);
}
// node_modules/d3-drag/src/constant.js
var Rs = (e) => () => e;
// node_modules/d3-drag/src/event.js
function zs(e, { sourceEvent: t, subject: n, target: r, identifier: i, active: a, x: o, y: s, dx: c, dy: l, dispatch: u }) {
	Object.defineProperties(this, {
		type: {
			value: e,
			enumerable: !0,
			configurable: !0
		},
		sourceEvent: {
			value: t,
			enumerable: !0,
			configurable: !0
		},
		subject: {
			value: n,
			enumerable: !0,
			configurable: !0
		},
		target: {
			value: r,
			enumerable: !0,
			configurable: !0
		},
		identifier: {
			value: i,
			enumerable: !0,
			configurable: !0
		},
		active: {
			value: a,
			enumerable: !0,
			configurable: !0
		},
		x: {
			value: o,
			enumerable: !0,
			configurable: !0
		},
		y: {
			value: s,
			enumerable: !0,
			configurable: !0
		},
		dx: {
			value: c,
			enumerable: !0,
			configurable: !0
		},
		dy: {
			value: l,
			enumerable: !0,
			configurable: !0
		},
		_: { value: u }
	});
}
zs.prototype.on = function() {
	var e = this._.on.apply(this._, arguments);
	return e === this._ ? this : e;
};
// node_modules/d3-drag/src/drag.js
function Bs(e) {
	return !e.ctrlKey && !e.button;
}
function Vs() {
	return this.parentNode;
}
function Hs(e, t) {
	return t ?? {
		x: e.x,
		y: e.y
	};
}
function Us() {
	return navigator.maxTouchPoints || "ontouchstart" in this;
}
function Ws() {
	var e = Bs, t = Vs, n = Hs, r = Us, i = {}, a = Ta("start", "drag", "end"), o = 0, s, c, l, u, d = 0;
	function f(e) {
		e.on("mousedown.drag", p).filter(r).on("touchstart.drag", g).on("touchmove.drag", _, Ms).on("touchend.drag touchcancel.drag", v).style("touch-action", "none").style("-webkit-tap-highlight-color", "rgba(0,0,0,0)");
	}
	function p(n, r) {
		if (!u && e.call(this, n, r)) {
			var i = y(this, t.call(this, n, r), n, r, "mouse");
			i && (ks(n.view).on("mousemove.drag", m, Ns).on("mouseup.drag", h, Ns), Is(n.view), Ps(n), l = !1, s = n.clientX, c = n.clientY, i("start", n));
		}
	}
	function m(e) {
		if (Fs(e), !l) {
			var t = e.clientX - s, n = e.clientY - c;
			l = t * t + n * n > d;
		}
		i.mouse("drag", e);
	}
	function h(e) {
		ks(e.view).on("mousemove.drag mouseup.drag", null), Ls(e.view, l), Fs(e), i.mouse("end", e);
	}
	function g(n, r) {
		if (e.call(this, n, r)) for (var i = n.changedTouches, a = t.call(this, n, r), o = i.length, s = 0, c; s < o; ++s) (c = y(this, a, n, r, i[s].identifier, i[s])) && (Ps(n), c("start", n, i[s]));
	}
	function _(e) {
		for (var t = e.changedTouches, n = t.length, r = 0, a; r < n; ++r) (a = i[t[r].identifier]) && (Fs(e), a("drag", e, t[r]));
	}
	function v(e) {
		var t = e.changedTouches, n = t.length, r, a;
		for (u && clearTimeout(u), u = setTimeout(function() {
			u = null;
		}, 500), r = 0; r < n; ++r) (a = i[t[r].identifier]) && (Ps(e), a("end", e, t[r]));
	}
	function y(e, t, r, s, c, l) {
		var u = a.copy(), d = js(l || r, t), p, m, h;
		if ((h = n.call(e, new zs("beforestart", {
			sourceEvent: r,
			target: f,
			identifier: c,
			active: o,
			x: d[0],
			y: d[1],
			dx: 0,
			dy: 0,
			dispatch: u
		}), s)) != null) return p = h.x - d[0] || 0, m = h.y - d[1] || 0, function n(r, a, l) {
			var g = d, _;
			switch (r) {
				case "start":
					i[c] = n, _ = o++;
					break;
				case "end": delete i[c], --o;
				case "drag": d = js(l || a, t), _ = o;
			}
			u.call(r, e, new zs(r, {
				sourceEvent: a,
				subject: h,
				target: f,
				identifier: c,
				active: _,
				x: d[0] + p,
				y: d[1] + m,
				dx: d[0] - g[0],
				dy: d[1] - g[1],
				dispatch: u
			}), s);
		};
	}
	return f.filter = function(t) {
		return arguments.length ? (e = typeof t == "function" ? t : Rs(!!t), f) : e;
	}, f.container = function(e) {
		return arguments.length ? (t = typeof e == "function" ? e : Rs(e), f) : t;
	}, f.subject = function(e) {
		return arguments.length ? (n = typeof e == "function" ? e : Rs(e), f) : n;
	}, f.touchable = function(e) {
		return arguments.length ? (r = typeof e == "function" ? e : Rs(!!e), f) : r;
	}, f.on = function() {
		var e = a.on.apply(a, arguments);
		return e === a ? f : e;
	}, f.clickDistance = function(e) {
		return arguments.length ? (d = (e = +e) * e, f) : Math.sqrt(d);
	}, f;
}
// node_modules/d3-color/src/define.js
function Gs(e, t, n) {
	e.prototype = t.prototype = n, n.constructor = e;
}
function Ks(e, t) {
	var n = Object.create(e.prototype);
	for (var r in t) n[r] = t[r];
	return n;
}
// node_modules/d3-color/src/color.js
function qs() {}
var Js = .7, Ys = 1 / Js, Xs = "\\s*([+-]?\\d+)\\s*", Zs = "\\s*([+-]?(?:\\d*\\.)?\\d+(?:[eE][+-]?\\d+)?)\\s*", Qs = "\\s*([+-]?(?:\\d*\\.)?\\d+(?:[eE][+-]?\\d+)?)%\\s*", $s = /^#([0-9a-f]{3,8})$/, ec = RegExp(`^rgb\\(${Xs},${Xs},${Xs}\\)$`), tc = RegExp(`^rgb\\(${Qs},${Qs},${Qs}\\)$`), nc = RegExp(`^rgba\\(${Xs},${Xs},${Xs},${Zs}\\)$`), rc = RegExp(`^rgba\\(${Qs},${Qs},${Qs},${Zs}\\)$`), ic = RegExp(`^hsl\\(${Zs},${Qs},${Qs}\\)$`), ac = RegExp(`^hsla\\(${Zs},${Qs},${Qs},${Zs}\\)$`), oc = {
	aliceblue: 15792383,
	antiquewhite: 16444375,
	aqua: 65535,
	aquamarine: 8388564,
	azure: 15794175,
	beige: 16119260,
	bisque: 16770244,
	black: 0,
	blanchedalmond: 16772045,
	blue: 255,
	blueviolet: 9055202,
	brown: 10824234,
	burlywood: 14596231,
	cadetblue: 6266528,
	chartreuse: 8388352,
	chocolate: 13789470,
	coral: 16744272,
	cornflowerblue: 6591981,
	cornsilk: 16775388,
	crimson: 14423100,
	cyan: 65535,
	darkblue: 139,
	darkcyan: 35723,
	darkgoldenrod: 12092939,
	darkgray: 11119017,
	darkgreen: 25600,
	darkgrey: 11119017,
	darkkhaki: 12433259,
	darkmagenta: 9109643,
	darkolivegreen: 5597999,
	darkorange: 16747520,
	darkorchid: 10040012,
	darkred: 9109504,
	darksalmon: 15308410,
	darkseagreen: 9419919,
	darkslateblue: 4734347,
	darkslategray: 3100495,
	darkslategrey: 3100495,
	darkturquoise: 52945,
	darkviolet: 9699539,
	deeppink: 16716947,
	deepskyblue: 49151,
	dimgray: 6908265,
	dimgrey: 6908265,
	dodgerblue: 2003199,
	firebrick: 11674146,
	floralwhite: 16775920,
	forestgreen: 2263842,
	fuchsia: 16711935,
	gainsboro: 14474460,
	ghostwhite: 16316671,
	gold: 16766720,
	goldenrod: 14329120,
	gray: 8421504,
	green: 32768,
	greenyellow: 11403055,
	grey: 8421504,
	honeydew: 15794160,
	hotpink: 16738740,
	indianred: 13458524,
	indigo: 4915330,
	ivory: 16777200,
	khaki: 15787660,
	lavender: 15132410,
	lavenderblush: 16773365,
	lawngreen: 8190976,
	lemonchiffon: 16775885,
	lightblue: 11393254,
	lightcoral: 15761536,
	lightcyan: 14745599,
	lightgoldenrodyellow: 16448210,
	lightgray: 13882323,
	lightgreen: 9498256,
	lightgrey: 13882323,
	lightpink: 16758465,
	lightsalmon: 16752762,
	lightseagreen: 2142890,
	lightskyblue: 8900346,
	lightslategray: 7833753,
	lightslategrey: 7833753,
	lightsteelblue: 11584734,
	lightyellow: 16777184,
	lime: 65280,
	limegreen: 3329330,
	linen: 16445670,
	magenta: 16711935,
	maroon: 8388608,
	mediumaquamarine: 6737322,
	mediumblue: 205,
	mediumorchid: 12211667,
	mediumpurple: 9662683,
	mediumseagreen: 3978097,
	mediumslateblue: 8087790,
	mediumspringgreen: 64154,
	mediumturquoise: 4772300,
	mediumvioletred: 13047173,
	midnightblue: 1644912,
	mintcream: 16121850,
	mistyrose: 16770273,
	moccasin: 16770229,
	navajowhite: 16768685,
	navy: 128,
	oldlace: 16643558,
	olive: 8421376,
	olivedrab: 7048739,
	orange: 16753920,
	orangered: 16729344,
	orchid: 14315734,
	palegoldenrod: 15657130,
	palegreen: 10025880,
	paleturquoise: 11529966,
	palevioletred: 14381203,
	papayawhip: 16773077,
	peachpuff: 16767673,
	peru: 13468991,
	pink: 16761035,
	plum: 14524637,
	powderblue: 11591910,
	purple: 8388736,
	rebeccapurple: 6697881,
	red: 16711680,
	rosybrown: 12357519,
	royalblue: 4286945,
	saddlebrown: 9127187,
	salmon: 16416882,
	sandybrown: 16032864,
	seagreen: 3050327,
	seashell: 16774638,
	sienna: 10506797,
	silver: 12632256,
	skyblue: 8900331,
	slateblue: 6970061,
	slategray: 7372944,
	slategrey: 7372944,
	snow: 16775930,
	springgreen: 65407,
	steelblue: 4620980,
	tan: 13808780,
	teal: 32896,
	thistle: 14204888,
	tomato: 16737095,
	turquoise: 4251856,
	violet: 15631086,
	wheat: 16113331,
	white: 16777215,
	whitesmoke: 16119285,
	yellow: 16776960,
	yellowgreen: 10145074
};
Gs(qs, dc, {
	copy(e) {
		return Object.assign(new this.constructor(), this, e);
	},
	displayable() {
		return this.rgb().displayable();
	},
	hex: sc,
	formatHex: sc,
	formatHex8: cc,
	formatHsl: lc,
	formatRgb: uc,
	toString: uc
});
function sc() {
	return this.rgb().formatHex();
}
function cc() {
	return this.rgb().formatHex8();
}
function lc() {
	return wc(this).formatHsl();
}
function uc() {
	return this.rgb().formatRgb();
}
function dc(e) {
	var t, n;
	return e = (e + "").trim().toLowerCase(), (t = $s.exec(e)) ? (n = t[1].length, t = parseInt(t[1], 16), n === 6 ? fc(t) : n === 3 ? new gc(t >> 8 & 15 | t >> 4 & 240, t >> 4 & 15 | t & 240, (t & 15) << 4 | t & 15, 1) : n === 8 ? pc(t >> 24 & 255, t >> 16 & 255, t >> 8 & 255, (t & 255) / 255) : n === 4 ? pc(t >> 12 & 15 | t >> 8 & 240, t >> 8 & 15 | t >> 4 & 240, t >> 4 & 15 | t & 240, ((t & 15) << 4 | t & 15) / 255) : null) : (t = ec.exec(e)) ? new gc(t[1], t[2], t[3], 1) : (t = tc.exec(e)) ? new gc(t[1] * 255 / 100, t[2] * 255 / 100, t[3] * 255 / 100, 1) : (t = nc.exec(e)) ? pc(t[1], t[2], t[3], t[4]) : (t = rc.exec(e)) ? pc(t[1] * 255 / 100, t[2] * 255 / 100, t[3] * 255 / 100, t[4]) : (t = ic.exec(e)) ? Cc(t[1], t[2] / 100, t[3] / 100, 1) : (t = ac.exec(e)) ? Cc(t[1], t[2] / 100, t[3] / 100, t[4]) : oc.hasOwnProperty(e) ? fc(oc[e]) : e === "transparent" ? new gc(NaN, NaN, NaN, 0) : null;
}
function fc(e) {
	return new gc(e >> 16 & 255, e >> 8 & 255, e & 255, 1);
}
function pc(e, t, n, r) {
	return r <= 0 && (e = t = n = NaN), new gc(e, t, n, r);
}
function mc(e) {
	return e instanceof qs || (e = dc(e)), e ? (e = e.rgb(), new gc(e.r, e.g, e.b, e.opacity)) : new gc();
}
function hc(e, t, n, r) {
	return arguments.length === 1 ? mc(e) : new gc(e, t, n, r ?? 1);
}
function gc(e, t, n, r) {
	this.r = +e, this.g = +t, this.b = +n, this.opacity = +r;
}
Gs(gc, hc, Ks(qs, {
	brighter(e) {
		return e = e == null ? Ys : Ys ** +e, new gc(this.r * e, this.g * e, this.b * e, this.opacity);
	},
	darker(e) {
		return e = e == null ? Js : Js ** +e, new gc(this.r * e, this.g * e, this.b * e, this.opacity);
	},
	rgb() {
		return this;
	},
	clamp() {
		return new gc(xc(this.r), xc(this.g), xc(this.b), bc(this.opacity));
	},
	displayable() {
		return -.5 <= this.r && this.r < 255.5 && -.5 <= this.g && this.g < 255.5 && -.5 <= this.b && this.b < 255.5 && 0 <= this.opacity && this.opacity <= 1;
	},
	hex: _c,
	formatHex: _c,
	formatHex8: vc,
	formatRgb: yc,
	toString: yc
}));
function _c() {
	return `#${Sc(this.r)}${Sc(this.g)}${Sc(this.b)}`;
}
function vc() {
	return `#${Sc(this.r)}${Sc(this.g)}${Sc(this.b)}${Sc((isNaN(this.opacity) ? 1 : this.opacity) * 255)}`;
}
function yc() {
	let e = bc(this.opacity);
	return `${e === 1 ? "rgb(" : "rgba("}${xc(this.r)}, ${xc(this.g)}, ${xc(this.b)}${e === 1 ? ")" : `, ${e})`}`;
}
function bc(e) {
	return isNaN(e) ? 1 : Math.max(0, Math.min(1, e));
}
function xc(e) {
	return Math.max(0, Math.min(255, Math.round(e) || 0));
}
function Sc(e) {
	return e = xc(e), (e < 16 ? "0" : "") + e.toString(16);
}
function Cc(e, t, n, r) {
	return r <= 0 ? e = t = n = NaN : n <= 0 || n >= 1 ? e = t = NaN : t <= 0 && (e = NaN), new Ec(e, t, n, r);
}
function wc(e) {
	if (e instanceof Ec) return new Ec(e.h, e.s, e.l, e.opacity);
	if (e instanceof qs || (e = dc(e)), !e) return new Ec();
	if (e instanceof Ec) return e;
	e = e.rgb();
	var t = e.r / 255, n = e.g / 255, r = e.b / 255, i = Math.min(t, n, r), a = Math.max(t, n, r), o = NaN, s = a - i, c = (a + i) / 2;
	return s ? (o = t === a ? (n - r) / s + (n < r) * 6 : n === a ? (r - t) / s + 2 : (t - n) / s + 4, s /= c < .5 ? a + i : 2 - a - i, o *= 60) : s = c > 0 && c < 1 ? 0 : o, new Ec(o, s, c, e.opacity);
}
function Tc(e, t, n, r) {
	return arguments.length === 1 ? wc(e) : new Ec(e, t, n, r ?? 1);
}
function Ec(e, t, n, r) {
	this.h = +e, this.s = +t, this.l = +n, this.opacity = +r;
}
Gs(Ec, Tc, Ks(qs, {
	brighter(e) {
		return e = e == null ? Ys : Ys ** +e, new Ec(this.h, this.s, this.l * e, this.opacity);
	},
	darker(e) {
		return e = e == null ? Js : Js ** +e, new Ec(this.h, this.s, this.l * e, this.opacity);
	},
	rgb() {
		var e = this.h % 360 + (this.h < 0) * 360, t = isNaN(e) || isNaN(this.s) ? 0 : this.s, n = this.l, r = n + (n < .5 ? n : 1 - n) * t, i = 2 * n - r;
		return new gc(kc(e >= 240 ? e - 240 : e + 120, i, r), kc(e, i, r), kc(e < 120 ? e + 240 : e - 120, i, r), this.opacity);
	},
	clamp() {
		return new Ec(Dc(this.h), Oc(this.s), Oc(this.l), bc(this.opacity));
	},
	displayable() {
		return (0 <= this.s && this.s <= 1 || isNaN(this.s)) && 0 <= this.l && this.l <= 1 && 0 <= this.opacity && this.opacity <= 1;
	},
	formatHsl() {
		let e = bc(this.opacity);
		return `${e === 1 ? "hsl(" : "hsla("}${Dc(this.h)}, ${Oc(this.s) * 100}%, ${Oc(this.l) * 100}%${e === 1 ? ")" : `, ${e})`}`;
	}
}));
function Dc(e) {
	return e = (e || 0) % 360, e < 0 ? e + 360 : e;
}
function Oc(e) {
	return Math.max(0, Math.min(1, e || 0));
}
function kc(e, t, n) {
	return (e < 60 ? t + (n - t) * e / 60 : e < 180 ? n : e < 240 ? t + (n - t) * (240 - e) / 60 : t) * 255;
}
// node_modules/d3-interpolate/src/constant.js
var Ac = (e) => () => e;
// node_modules/d3-interpolate/src/color.js
function jc(e, t) {
	return function(n) {
		return e + n * t;
	};
}
function Mc(e, t, n) {
	return e **= +n, t = t ** +n - e, n = 1 / n, function(r) {
		return (e + r * t) ** +n;
	};
}
function Nc(e) {
	return (e = +e) == 1 ? Pc : function(t, n) {
		return n - t ? Mc(t, n, e) : Ac(isNaN(t) ? n : t);
	};
}
function Pc(e, t) {
	var n = t - e;
	return n ? jc(e, n) : Ac(isNaN(e) ? t : e);
}
// node_modules/d3-interpolate/src/rgb.js
var Fc = (function e(t) {
	var n = Nc(t);
	function r(e, t) {
		var r = n((e = hc(e)).r, (t = hc(t)).r), i = n(e.g, t.g), a = n(e.b, t.b), o = Pc(e.opacity, t.opacity);
		return function(t) {
			return e.r = r(t), e.g = i(t), e.b = a(t), e.opacity = o(t), e + "";
		};
	}
	return r.gamma = e, r;
})(1);
// node_modules/d3-interpolate/src/numberArray.js
function Ic(e, t) {
	t ||= [];
	var n = e ? Math.min(t.length, e.length) : 0, r = t.slice(), i;
	return function(a) {
		for (i = 0; i < n; ++i) r[i] = e[i] * (1 - a) + t[i] * a;
		return r;
	};
}
function Lc(e) {
	return ArrayBuffer.isView(e) && !(e instanceof DataView);
}
// node_modules/d3-interpolate/src/array.js
function Rc(e, t) {
	for (var n = t ? t.length : 0, r = e ? Math.min(n, e.length) : 0, i = Array(r), a = Array(n), o = 0; o < r; ++o) i[o] = qc(e[o], t[o]);
	for (; o < n; ++o) a[o] = t[o];
	return function(e) {
		for (o = 0; o < r; ++o) a[o] = i[o](e);
		return a;
	};
}
// node_modules/d3-interpolate/src/date.js
function zc(e, t) {
	var n = /* @__PURE__ */ new Date();
	return e = +e, t = +t, function(r) {
		return n.setTime(e * (1 - r) + t * r), n;
	};
}
// node_modules/d3-interpolate/src/number.js
function Bc(e, t) {
	return e = +e, t = +t, function(n) {
		return e * (1 - n) + t * n;
	};
}
// node_modules/d3-interpolate/src/object.js
function Vc(e, t) {
	var n = {}, r = {}, i;
	for (i in typeof e == "object" && e || (e = {}), typeof t == "object" && t || (t = {}), t) i in e ? n[i] = qc(e[i], t[i]) : r[i] = t[i];
	return function(e) {
		for (i in n) r[i] = n[i](e);
		return r;
	};
}
// node_modules/d3-interpolate/src/string.js
var Hc = /[-+]?(?:\d+\.?\d*|\.?\d+)(?:[eE][-+]?\d+)?/g, Uc = new RegExp(Hc.source, "g");
function Wc(e) {
	return function() {
		return e;
	};
}
function Gc(e) {
	return function(t) {
		return e(t) + "";
	};
}
function Kc(e, t) {
	var n = Hc.lastIndex = Uc.lastIndex = 0, r, i, a, o = -1, s = [], c = [];
	for (e += "", t += ""; (r = Hc.exec(e)) && (i = Uc.exec(t));) (a = i.index) > n && (a = t.slice(n, a), s[o] ? s[o] += a : s[++o] = a), (r = r[0]) === (i = i[0]) ? s[o] ? s[o] += i : s[++o] = i : (s[++o] = null, c.push({
		i: o,
		x: Bc(r, i)
	})), n = Uc.lastIndex;
	return n < t.length && (a = t.slice(n), s[o] ? s[o] += a : s[++o] = a), s.length < 2 ? c[0] ? Gc(c[0].x) : Wc(t) : (t = c.length, function(e) {
		for (var n = 0, r; n < t; ++n) s[(r = c[n]).i] = r.x(e);
		return s.join("");
	});
}
// node_modules/d3-interpolate/src/value.js
function qc(e, t) {
	var n = typeof t, r;
	return t == null || n === "boolean" ? Ac(t) : (n === "number" ? Bc : n === "string" ? (r = dc(t)) ? (t = r, Fc) : Kc : t instanceof dc ? Fc : t instanceof Date ? zc : Lc(t) ? Ic : Array.isArray(t) ? Rc : typeof t.valueOf != "function" && typeof t.toString != "function" || isNaN(t) ? Vc : Bc)(e, t);
}
// node_modules/d3-interpolate/src/transform/decompose.js
var Jc = 180 / Math.PI, Yc = {
	translateX: 0,
	translateY: 0,
	rotate: 0,
	skewX: 0,
	scaleX: 1,
	scaleY: 1
};
function Xc(e, t, n, r, i, a) {
	var o, s, c;
	return (o = Math.sqrt(e * e + t * t)) && (e /= o, t /= o), (c = e * n + t * r) && (n -= e * c, r -= t * c), (s = Math.sqrt(n * n + r * r)) && (n /= s, r /= s, c /= s), e * r < t * n && (e = -e, t = -t, c = -c, o = -o), {
		translateX: i,
		translateY: a,
		rotate: Math.atan2(t, e) * Jc,
		skewX: Math.atan(c) * Jc,
		scaleX: o,
		scaleY: s
	};
}
// node_modules/d3-interpolate/src/transform/parse.js
var Zc;
function Qc(e) {
	let t = new (typeof DOMMatrix == "function" ? DOMMatrix : WebKitCSSMatrix)(e + "");
	return t.isIdentity ? Yc : Xc(t.a, t.b, t.c, t.d, t.e, t.f);
}
function $c(e) {
	return e == null || (Zc ||= document.createElementNS("http://www.w3.org/2000/svg", "g"), Zc.setAttribute("transform", e), !(e = Zc.transform.baseVal.consolidate())) ? Yc : (e = e.matrix, Xc(e.a, e.b, e.c, e.d, e.e, e.f));
}
// node_modules/d3-interpolate/src/transform/index.js
function el(e, t, n, r) {
	function i(e) {
		return e.length ? e.pop() + " " : "";
	}
	function a(e, r, i, a, o, s) {
		if (e !== i || r !== a) {
			var c = o.push("translate(", null, t, null, n);
			s.push({
				i: c - 4,
				x: Bc(e, i)
			}, {
				i: c - 2,
				x: Bc(r, a)
			});
		} else (i || a) && o.push("translate(" + i + t + a + n);
	}
	function o(e, t, n, a) {
		e === t ? t && n.push(i(n) + "rotate(" + t + r) : (e - t > 180 ? t += 360 : t - e > 180 && (e += 360), a.push({
			i: n.push(i(n) + "rotate(", null, r) - 2,
			x: Bc(e, t)
		}));
	}
	function s(e, t, n, a) {
		e === t ? t && n.push(i(n) + "skewX(" + t + r) : a.push({
			i: n.push(i(n) + "skewX(", null, r) - 2,
			x: Bc(e, t)
		});
	}
	function c(e, t, n, r, a, o) {
		if (e !== n || t !== r) {
			var s = a.push(i(a) + "scale(", null, ",", null, ")");
			o.push({
				i: s - 4,
				x: Bc(e, n)
			}, {
				i: s - 2,
				x: Bc(t, r)
			});
		} else (n !== 1 || r !== 1) && a.push(i(a) + "scale(" + n + "," + r + ")");
	}
	return function(t, n) {
		var r = [], i = [];
		return t = e(t), n = e(n), a(t.translateX, t.translateY, n.translateX, n.translateY, r, i), o(t.rotate, n.rotate, r, i), s(t.skewX, n.skewX, r, i), c(t.scaleX, t.scaleY, n.scaleX, n.scaleY, r, i), t = n = null, function(e) {
			for (var t = -1, n = i.length, a; ++t < n;) r[(a = i[t]).i] = a.x(e);
			return r.join("");
		};
	};
}
var tl = el(Qc, "px, ", "px)", "deg)"), nl = el($c, ", ", ")", ")"), rl = 1e-12;
function il(e) {
	return ((e = Math.exp(e)) + 1 / e) / 2;
}
function al(e) {
	return ((e = Math.exp(e)) - 1 / e) / 2;
}
function ol(e) {
	return ((e = Math.exp(2 * e)) - 1) / (e + 1);
}
var sl = (function e(t, n, r) {
	function i(e, i) {
		var a = e[0], o = e[1], s = e[2], c = i[0], l = i[1], u = i[2], d = c - a, f = l - o, p = d * d + f * f, m, h;
		if (p < rl) h = Math.log(u / s) / t, m = function(e) {
			return [
				a + e * d,
				o + e * f,
				s * Math.exp(t * e * h)
			];
		};
		else {
			var g = Math.sqrt(p), _ = (u * u - s * s + r * p) / (2 * s * n * g), v = (u * u - s * s - r * p) / (2 * u * n * g), y = Math.log(Math.sqrt(_ * _ + 1) - _);
			h = (Math.log(Math.sqrt(v * v + 1) - v) - y) / t, m = function(e) {
				var r = e * h, i = il(y), c = s / (n * g) * (i * ol(t * r + y) - al(y));
				return [
					a + c * d,
					o + c * f,
					s * i / il(t * r + y)
				];
			};
		}
		return m.duration = h * 1e3 * t / Math.SQRT2, m;
	}
	return i.rho = function(t) {
		var n = Math.max(.001, +t), r = n * n;
		return e(n, r, r * r);
	}, i;
})(Math.SQRT2, 2, 4), cl = 0, ll = 0, ul = 0, dl = 1e3, fl, pl, ml = 0, hl = 0, gl = 0, _l = typeof performance == "object" && performance.now ? performance : Date, vl = typeof window == "object" && window.requestAnimationFrame ? window.requestAnimationFrame.bind(window) : function(e) {
	setTimeout(e, 17);
};
function yl() {
	return hl ||= (vl(bl), _l.now() + gl);
}
function bl() {
	hl = 0;
}
function xl() {
	this._call = this._time = this._next = null;
}
xl.prototype = Sl.prototype = {
	constructor: xl,
	restart: function(e, t, n) {
		if (typeof e != "function") throw TypeError("callback is not a function");
		n = (n == null ? yl() : +n) + (t == null ? 0 : +t), !this._next && pl !== this && (pl ? pl._next = this : fl = this, pl = this), this._call = e, this._time = n, Dl();
	},
	stop: function() {
		this._call && (this._call = null, this._time = Infinity, Dl());
	}
};
function Sl(e, t, n) {
	var r = new xl();
	return r.restart(e, t, n), r;
}
function Cl() {
	yl(), ++cl;
	for (var e = fl, t; e;) (t = hl - e._time) >= 0 && e._call.call(void 0, t), e = e._next;
	--cl;
}
function wl() {
	hl = (ml = _l.now()) + gl, cl = ll = 0;
	try {
		Cl();
	} finally {
		cl = 0, El(), hl = 0;
	}
}
function Tl() {
	var e = _l.now(), t = e - ml;
	t > dl && (gl -= t, ml = e);
}
function El() {
	for (var e, t = fl, n, r = Infinity; t;) t._call ? (r > t._time && (r = t._time), e = t, t = t._next) : (n = t._next, t._next = null, t = e ? e._next = n : fl = n);
	pl = e, Dl(r);
}
function Dl(e) {
	cl || (ll &&= clearTimeout(ll), e - hl > 24 ? (e < Infinity && (ll = setTimeout(wl, e - _l.now() - gl)), ul &&= clearInterval(ul)) : (ul ||= (ml = _l.now(), setInterval(Tl, dl)), cl = 1, vl(wl)));
}
// node_modules/d3-timer/src/timeout.js
function Ol(e, t, n) {
	var r = new xl();
	return t = t == null ? 0 : +t, r.restart((n) => {
		r.stop(), e(n + t);
	}, t, n), r;
}
// node_modules/d3-transition/src/transition/schedule.js
var kl = Ta("start", "end", "cancel", "interrupt"), Al = [];
function jl(e, t, n, r, i, a) {
	var o = e.__transition;
	if (!o) e.__transition = {};
	else if (n in o) return;
	Fl(e, n, {
		name: t,
		index: r,
		group: i,
		on: kl,
		tween: Al,
		time: a.time,
		delay: a.delay,
		duration: a.duration,
		ease: a.ease,
		timer: null,
		state: 0
	});
}
function Ml(e, t) {
	var n = Pl(e, t);
	if (n.state > 0) throw Error("too late; already scheduled");
	return n;
}
function Nl(e, t) {
	var n = Pl(e, t);
	if (n.state > 3) throw Error("too late; already running");
	return n;
}
function Pl(e, t) {
	var n = e.__transition;
	if (!n || !(n = n[t])) throw Error("transition not found");
	return n;
}
function Fl(e, t, n) {
	var r = e.__transition, i;
	r[t] = n, n.timer = Sl(a, 0, n.time);
	function a(e) {
		n.state = 1, n.timer.restart(o, n.delay, n.time), n.delay <= e && o(e - n.delay);
	}
	function o(a) {
		var l, u, d, f;
		if (n.state !== 1) return c();
		for (l in r) if (f = r[l], f.name === n.name) {
			if (f.state === 3) return Ol(o);
			f.state === 4 ? (f.state = 6, f.timer.stop(), f.on.call("interrupt", e, e.__data__, f.index, f.group), delete r[l]) : +l < t && (f.state = 6, f.timer.stop(), f.on.call("cancel", e, e.__data__, f.index, f.group), delete r[l]);
		}
		if (Ol(function() {
			n.state === 3 && (n.state = 4, n.timer.restart(s, n.delay, n.time), s(a));
		}), n.state = 2, n.on.call("start", e, e.__data__, n.index, n.group), n.state === 2) {
			for (n.state = 3, i = Array(d = n.tween.length), l = 0, u = -1; l < d; ++l) (f = n.tween[l].value.call(e, e.__data__, n.index, n.group)) && (i[++u] = f);
			i.length = u + 1;
		}
	}
	function s(t) {
		for (var r = t < n.duration ? n.ease.call(null, t / n.duration) : (n.timer.restart(c), n.state = 5, 1), a = -1, o = i.length; ++a < o;) i[a].call(e, r);
		n.state === 5 && (n.on.call("end", e, e.__data__, n.index, n.group), c());
	}
	function c() {
		for (var i in n.state = 6, n.timer.stop(), delete r[t], r) return;
		delete e.__transition;
	}
}
// node_modules/d3-transition/src/interrupt.js
function Il(e, t) {
	var n = e.__transition, r, i, a = !0, o;
	if (n) {
		for (o in t = t == null ? null : t + "", n) (r = n[o]).name === t ? (i = r.state > 2 && r.state < 5, r.state = 6, r.timer.stop(), r.on.call(i ? "interrupt" : "cancel", e, e.__data__, r.index, r.group), delete n[o]) : a = !1;
		a && delete e.__transition;
	}
}
// node_modules/d3-transition/src/selection/interrupt.js
function Ll(e) {
	return this.each(function() {
		Il(this, e);
	});
}
// node_modules/d3-transition/src/transition/tween.js
function Rl(e, t) {
	var n, r;
	return function() {
		var i = Nl(this, e), a = i.tween;
		if (a !== n) {
			r = n = a;
			for (var o = 0, s = r.length; o < s; ++o) if (r[o].name === t) {
				r = r.slice(), r.splice(o, 1);
				break;
			}
		}
		i.tween = r;
	};
}
function zl(e, t, n) {
	var r, i;
	if (typeof n != "function") throw Error();
	return function() {
		var a = Nl(this, e), o = a.tween;
		if (o !== r) {
			i = (r = o).slice();
			for (var s = {
				name: t,
				value: n
			}, c = 0, l = i.length; c < l; ++c) if (i[c].name === t) {
				i[c] = s;
				break;
			}
			c === l && i.push(s);
		}
		a.tween = i;
	};
}
function Bl(e, t) {
	var n = this._id;
	if (e += "", arguments.length < 2) {
		for (var r = Pl(this.node(), n).tween, i = 0, a = r.length, o; i < a; ++i) if ((o = r[i]).name === e) return o.value;
		return null;
	}
	return this.each((t == null ? Rl : zl)(n, e, t));
}
function Vl(e, t, n) {
	var r = e._id;
	return e.each(function() {
		var e = Nl(this, r);
		(e.value ||= {})[t] = n.apply(this, arguments);
	}), function(e) {
		return Pl(e, r).value[t];
	};
}
// node_modules/d3-transition/src/transition/interpolate.js
function Hl(e, t) {
	var n;
	return (typeof t == "number" ? Bc : t instanceof dc ? Fc : (n = dc(t)) ? (t = n, Fc) : Kc)(e, t);
}
// node_modules/d3-transition/src/transition/attr.js
function Ul(e) {
	return function() {
		this.removeAttribute(e);
	};
}
function Wl(e) {
	return function() {
		this.removeAttributeNS(e.space, e.local);
	};
}
function Gl(e, t, n) {
	var r, i = n + "", a;
	return function() {
		var o = this.getAttribute(e);
		return o === i ? null : o === r ? a : a = t(r = o, n);
	};
}
function Kl(e, t, n) {
	var r, i = n + "", a;
	return function() {
		var o = this.getAttributeNS(e.space, e.local);
		return o === i ? null : o === r ? a : a = t(r = o, n);
	};
}
function ql(e, t, n) {
	var r, i, a;
	return function() {
		var o, s = n(this), c;
		return s == null ? void this.removeAttribute(e) : (o = this.getAttribute(e), c = s + "", o === c ? null : o === r && c === i ? a : (i = c, a = t(r = o, s)));
	};
}
function Jl(e, t, n) {
	var r, i, a;
	return function() {
		var o, s = n(this), c;
		return s == null ? void this.removeAttributeNS(e.space, e.local) : (o = this.getAttributeNS(e.space, e.local), c = s + "", o === c ? null : o === r && c === i ? a : (i = c, a = t(r = o, s)));
	};
}
function Yl(e, t) {
	var n = ja(e), r = n === "transform" ? nl : Hl;
	return this.attrTween(e, typeof t == "function" ? (n.local ? Jl : ql)(n, r, Vl(this, "attr." + e, t)) : t == null ? (n.local ? Wl : Ul)(n) : (n.local ? Kl : Gl)(n, r, t));
}
// node_modules/d3-transition/src/transition/attrTween.js
function Xl(e, t) {
	return function(n) {
		this.setAttribute(e, t.call(this, n));
	};
}
function Zl(e, t) {
	return function(n) {
		this.setAttributeNS(e.space, e.local, t.call(this, n));
	};
}
function Ql(e, t) {
	var n, r;
	function i() {
		var i = t.apply(this, arguments);
		return i !== r && (n = (r = i) && Zl(e, i)), n;
	}
	return i._value = t, i;
}
function $l(e, t) {
	var n, r;
	function i() {
		var i = t.apply(this, arguments);
		return i !== r && (n = (r = i) && Xl(e, i)), n;
	}
	return i._value = t, i;
}
function eu(e, t) {
	var n = "attr." + e;
	if (arguments.length < 2) return (n = this.tween(n)) && n._value;
	if (t == null) return this.tween(n, null);
	if (typeof t != "function") throw Error();
	var r = ja(e);
	return this.tween(n, (r.local ? Ql : $l)(r, t));
}
// node_modules/d3-transition/src/transition/delay.js
function tu(e, t) {
	return function() {
		Ml(this, e).delay = +t.apply(this, arguments);
	};
}
function nu(e, t) {
	return t = +t, function() {
		Ml(this, e).delay = t;
	};
}
function ru(e) {
	var t = this._id;
	return arguments.length ? this.each((typeof e == "function" ? tu : nu)(t, e)) : Pl(this.node(), t).delay;
}
// node_modules/d3-transition/src/transition/duration.js
function iu(e, t) {
	return function() {
		Nl(this, e).duration = +t.apply(this, arguments);
	};
}
function au(e, t) {
	return t = +t, function() {
		Nl(this, e).duration = t;
	};
}
function ou(e) {
	var t = this._id;
	return arguments.length ? this.each((typeof e == "function" ? iu : au)(t, e)) : Pl(this.node(), t).duration;
}
// node_modules/d3-transition/src/transition/ease.js
function su(e, t) {
	if (typeof t != "function") throw Error();
	return function() {
		Nl(this, e).ease = t;
	};
}
function cu(e) {
	var t = this._id;
	return arguments.length ? this.each(su(t, e)) : Pl(this.node(), t).ease;
}
// node_modules/d3-transition/src/transition/easeVarying.js
function lu(e, t) {
	return function() {
		var n = t.apply(this, arguments);
		if (typeof n != "function") throw Error();
		Nl(this, e).ease = n;
	};
}
function uu(e) {
	if (typeof e != "function") throw Error();
	return this.each(lu(this._id, e));
}
// node_modules/d3-transition/src/transition/filter.js
function du(e) {
	typeof e != "function" && (e = Ua(e));
	for (var t = this._groups, n = t.length, r = Array(n), i = 0; i < n; ++i) for (var a = t[i], o = a.length, s = r[i] = [], c, l = 0; l < o; ++l) (c = a[l]) && e.call(c, c.__data__, l, a) && s.push(c);
	return new Bu(r, this._parents, this._name, this._id);
}
// node_modules/d3-transition/src/transition/merge.js
function fu(e) {
	if (e._id !== this._id) throw Error();
	for (var t = this._groups, n = e._groups, r = t.length, i = n.length, a = Math.min(r, i), o = Array(r), s = 0; s < a; ++s) for (var c = t[s], l = n[s], u = c.length, d = o[s] = Array(u), f, p = 0; p < u; ++p) (f = c[p] || l[p]) && (d[p] = f);
	for (; s < r; ++s) o[s] = t[s];
	return new Bu(o, this._parents, this._name, this._id);
}
// node_modules/d3-transition/src/transition/on.js
function pu(e) {
	return (e + "").trim().split(/^|\s+/).every(function(e) {
		var t = e.indexOf(".");
		return t >= 0 && (e = e.slice(0, t)), !e || e === "start";
	});
}
function mu(e, t, n) {
	var r, i, a = pu(t) ? Ml : Nl;
	return function() {
		var o = a(this, e), s = o.on;
		s !== r && (i = (r = s).copy()).on(t, n), o.on = i;
	};
}
function hu(e, t) {
	var n = this._id;
	return arguments.length < 2 ? Pl(this.node(), n).on.on(e) : this.each(mu(n, e, t));
}
// node_modules/d3-transition/src/transition/remove.js
function gu(e) {
	return function() {
		var t = this.parentNode;
		for (var n in this.__transition) if (+n !== e) return;
		t && t.removeChild(this);
	};
}
function _u() {
	return this.on("end.remove", gu(this._id));
}
// node_modules/d3-transition/src/transition/select.js
function vu(e) {
	var t = this._name, n = this._id;
	typeof e != "function" && (e = Ia(e));
	for (var r = this._groups, i = r.length, a = Array(i), o = 0; o < i; ++o) for (var s = r[o], c = s.length, l = a[o] = Array(c), u, d, f = 0; f < c; ++f) (u = s[f]) && (d = e.call(u, u.__data__, f, s)) && ("__data__" in u && (d.__data__ = u.__data__), l[f] = d, jl(l[f], t, n, f, l, Pl(u, n)));
	return new Bu(a, this._parents, t, n);
}
// node_modules/d3-transition/src/transition/selectAll.js
function yu(e) {
	var t = this._name, n = this._id;
	typeof e != "function" && (e = Ba(e));
	for (var r = this._groups, i = r.length, a = [], o = [], s = 0; s < i; ++s) for (var c = r[s], l = c.length, u, d = 0; d < l; ++d) if (u = c[d]) {
		for (var f = e.call(u, u.__data__, d, c), p, m = Pl(u, n), h = 0, g = f.length; h < g; ++h) (p = f[h]) && jl(p, t, n, h, f, m);
		a.push(f), o.push(u);
	}
	return new Bu(a, o, t, n);
}
// node_modules/d3-transition/src/transition/selection.js
var bu = Ds.prototype.constructor;
function xu() {
	return new bu(this._groups, this._parents);
}
// node_modules/d3-transition/src/transition/style.js
function Su(e, t) {
	var n, r, i;
	return function() {
		var a = Po(this, e), o = (this.style.removeProperty(e), Po(this, e));
		return a === o ? null : a === n && o === r ? i : i = t(n = a, r = o);
	};
}
function Cu(e) {
	return function() {
		this.style.removeProperty(e);
	};
}
function wu(e, t, n) {
	var r, i = n + "", a;
	return function() {
		var o = Po(this, e);
		return o === i ? null : o === r ? a : a = t(r = o, n);
	};
}
function Tu(e, t, n) {
	var r, i, a;
	return function() {
		var o = Po(this, e), s = n(this), c = s + "";
		return s ?? (c = s = (this.style.removeProperty(e), Po(this, e))), o === c ? null : o === r && c === i ? a : (i = c, a = t(r = o, s));
	};
}
function Eu(e, t) {
	var n, r, i, a = "style." + t, o = "end." + a, s;
	return function() {
		var c = Nl(this, e), l = c.on, u = c.value[a] == null ? s ||= Cu(t) : void 0;
		(l !== n || i !== u) && (r = (n = l).copy()).on(o, i = u), c.on = r;
	};
}
function Du(e, t, n) {
	var r = (e += "") == "transform" ? tl : Hl;
	return t == null ? this.styleTween(e, Su(e, r)).on("end.style." + e, Cu(e)) : typeof t == "function" ? this.styleTween(e, Tu(e, r, Vl(this, "style." + e, t))).each(Eu(this._id, e)) : this.styleTween(e, wu(e, r, t), n).on("end.style." + e, null);
}
// node_modules/d3-transition/src/transition/styleTween.js
function Ou(e, t, n) {
	return function(r) {
		this.style.setProperty(e, t.call(this, r), n);
	};
}
function ku(e, t, n) {
	var r, i;
	function a() {
		var a = t.apply(this, arguments);
		return a !== i && (r = (i = a) && Ou(e, a, n)), r;
	}
	return a._value = t, a;
}
function Au(e, t, n) {
	var r = "style." + (e += "");
	if (arguments.length < 2) return (r = this.tween(r)) && r._value;
	if (t == null) return this.tween(r, null);
	if (typeof t != "function") throw Error();
	return this.tween(r, ku(e, t, n ?? ""));
}
// node_modules/d3-transition/src/transition/text.js
function ju(e) {
	return function() {
		this.textContent = e;
	};
}
function Mu(e) {
	return function() {
		var t = e(this);
		this.textContent = t ?? "";
	};
}
function Nu(e) {
	return this.tween("text", typeof e == "function" ? Mu(Vl(this, "text", e)) : ju(e == null ? "" : e + ""));
}
// node_modules/d3-transition/src/transition/textTween.js
function Pu(e) {
	return function(t) {
		this.textContent = e.call(this, t);
	};
}
function Fu(e) {
	var t, n;
	function r() {
		var r = e.apply(this, arguments);
		return r !== n && (t = (n = r) && Pu(r)), t;
	}
	return r._value = e, r;
}
function Iu(e) {
	var t = "text";
	if (arguments.length < 1) return (t = this.tween(t)) && t._value;
	if (e == null) return this.tween(t, null);
	if (typeof e != "function") throw Error();
	return this.tween(t, Fu(e));
}
// node_modules/d3-transition/src/transition/transition.js
function Lu() {
	for (var e = this._name, t = this._id, n = Vu(), r = this._groups, i = r.length, a = 0; a < i; ++a) for (var o = r[a], s = o.length, c, l = 0; l < s; ++l) if (c = o[l]) {
		var u = Pl(c, t);
		jl(c, e, n, l, o, {
			time: u.time + u.delay + u.duration,
			delay: 0,
			duration: u.duration,
			ease: u.ease
		});
	}
	return new Bu(r, this._parents, e, n);
}
// node_modules/d3-transition/src/transition/end.js
function Ru() {
	var e, t, n = this, r = n._id, i = n.size();
	return new Promise(function(a, o) {
		var s = { value: o }, c = { value: function() {
			--i === 0 && a();
		} };
		n.each(function() {
			var n = Nl(this, r), i = n.on;
			i !== e && (t = (e = i).copy(), t._.cancel.push(s), t._.interrupt.push(s), t._.end.push(c)), n.on = t;
		}), i === 0 && a();
	});
}
// node_modules/d3-transition/src/transition/index.js
var zu = 0;
function Bu(e, t, n, r) {
	this._groups = e, this._parents = t, this._name = n, this._id = r;
}
function Vu() {
	return ++zu;
}
var Hu = Ds.prototype;
Bu.prototype = {
	constructor: Bu,
	select: vu,
	selectAll: yu,
	selectChild: Hu.selectChild,
	selectChildren: Hu.selectChildren,
	filter: du,
	merge: fu,
	selection: xu,
	transition: Lu,
	call: Hu.call,
	nodes: Hu.nodes,
	node: Hu.node,
	size: Hu.size,
	empty: Hu.empty,
	each: Hu.each,
	on: hu,
	attr: Yl,
	attrTween: eu,
	style: Du,
	styleTween: Au,
	text: Nu,
	textTween: Iu,
	remove: _u,
	tween: Bl,
	delay: ru,
	duration: ou,
	ease: cu,
	easeVarying: uu,
	end: Ru,
	[Symbol.iterator]: Hu[Symbol.iterator]
};
// node_modules/d3-ease/src/cubic.js
function Uu(e) {
	return ((e *= 2) <= 1 ? e * e * e : (e -= 2) * e * e + 2) / 2;
}
// node_modules/d3-transition/src/selection/transition.js
var Wu = {
	time: null,
	delay: 0,
	duration: 250,
	ease: Uu
};
function Gu(e, t) {
	for (var n; !(n = e.__transition) || !(n = n[t]);) if (!(e = e.parentNode)) throw Error(`transition ${t} not found`);
	return n;
}
function Ku(e) {
	var t, n;
	e instanceof Bu ? (t = e._id, e = e._name) : (t = Vu(), (n = Wu).time = yl(), e = e == null ? null : e + "");
	for (var r = this._groups, i = r.length, a = 0; a < i; ++a) for (var o = r[a], s = o.length, c, l = 0; l < s; ++l) (c = o[l]) && jl(c, e, t, l, o, n || Gu(c, t));
	return new Bu(r, this._parents, e, t);
}
Ds.prototype.interrupt = Ll, Ds.prototype.transition = Ku;
// node_modules/d3-zoom/src/constant.js
var qu = (e) => () => e;
// node_modules/d3-zoom/src/event.js
function Ju(e, { sourceEvent: t, target: n, transform: r, dispatch: i }) {
	Object.defineProperties(this, {
		type: {
			value: e,
			enumerable: !0,
			configurable: !0
		},
		sourceEvent: {
			value: t,
			enumerable: !0,
			configurable: !0
		},
		target: {
			value: n,
			enumerable: !0,
			configurable: !0
		},
		transform: {
			value: r,
			enumerable: !0,
			configurable: !0
		},
		_: { value: i }
	});
}
// node_modules/d3-zoom/src/transform.js
function Yu(e, t, n) {
	this.k = e, this.x = t, this.y = n;
}
Yu.prototype = {
	constructor: Yu,
	scale: function(e) {
		return e === 1 ? this : new Yu(this.k * e, this.x, this.y);
	},
	translate: function(e, t) {
		return e === 0 & t === 0 ? this : new Yu(this.k, this.x + this.k * e, this.y + this.k * t);
	},
	apply: function(e) {
		return [e[0] * this.k + this.x, e[1] * this.k + this.y];
	},
	applyX: function(e) {
		return e * this.k + this.x;
	},
	applyY: function(e) {
		return e * this.k + this.y;
	},
	invert: function(e) {
		return [(e[0] - this.x) / this.k, (e[1] - this.y) / this.k];
	},
	invertX: function(e) {
		return (e - this.x) / this.k;
	},
	invertY: function(e) {
		return (e - this.y) / this.k;
	},
	rescaleX: function(e) {
		return e.copy().domain(e.range().map(this.invertX, this).map(e.invert, e));
	},
	rescaleY: function(e) {
		return e.copy().domain(e.range().map(this.invertY, this).map(e.invert, e));
	},
	toString: function() {
		return "translate(" + this.x + "," + this.y + ") scale(" + this.k + ")";
	}
};
var Xu = new Yu(1, 0, 0);
Zu.prototype = Yu.prototype;
function Zu(e) {
	for (; !e.__zoom;) if (!(e = e.parentNode)) return Xu;
	return e.__zoom;
}
// node_modules/d3-zoom/src/noevent.js
function Qu(e) {
	e.stopImmediatePropagation();
}
function $u(e) {
	e.preventDefault(), e.stopImmediatePropagation();
}
// node_modules/d3-zoom/src/zoom.js
function ed(e) {
	return (!e.ctrlKey || e.type === "wheel") && !e.button;
}
function td() {
	var e = this;
	return e instanceof SVGElement ? (e = e.ownerSVGElement || e, e.hasAttribute("viewBox") ? (e = e.viewBox.baseVal, [[e.x, e.y], [e.x + e.width, e.y + e.height]]) : [[0, 0], [e.width.baseVal.value, e.height.baseVal.value]]) : [[0, 0], [e.clientWidth, e.clientHeight]];
}
function nd() {
	return this.__zoom || Xu;
}
function rd(e) {
	return -e.deltaY * (e.deltaMode === 1 ? .05 : e.deltaMode ? 1 : .002) * (e.ctrlKey ? 10 : 1);
}
function id() {
	return navigator.maxTouchPoints || "ontouchstart" in this;
}
function ad(e, t, n) {
	var r = e.invertX(t[0][0]) - n[0][0], i = e.invertX(t[1][0]) - n[1][0], a = e.invertY(t[0][1]) - n[0][1], o = e.invertY(t[1][1]) - n[1][1];
	return e.translate(i > r ? (r + i) / 2 : Math.min(0, r) || Math.max(0, i), o > a ? (a + o) / 2 : Math.min(0, a) || Math.max(0, o));
}
function od() {
	var e = ed, t = td, n = ad, r = rd, i = id, a = [0, Infinity], o = [[-Infinity, -Infinity], [Infinity, Infinity]], s = 250, c = sl, l = Ta("start", "zoom", "end"), u, d, f, p = 500, m = 150, h = 0, g = 10;
	function _(e) {
		e.property("__zoom", nd).on("wheel.zoom", w, { passive: !1 }).on("mousedown.zoom", T).on("dblclick.zoom", ee).filter(i).on("touchstart.zoom", E).on("touchmove.zoom", D).on("touchend.zoom touchcancel.zoom", te).style("-webkit-tap-highlight-color", "rgba(0,0,0,0)");
	}
	_.transform = function(e, t, n, r) {
		var i = e.selection ? e.selection() : e;
		i.property("__zoom", nd), e === i ? i.interrupt().each(function() {
			S(this, arguments).event(r).start().zoom(null, typeof t == "function" ? t.apply(this, arguments) : t).end();
		}) : x(e, t, n, r);
	}, _.scaleBy = function(e, t, n, r) {
		_.scaleTo(e, function() {
			return this.__zoom.k * (typeof t == "function" ? t.apply(this, arguments) : t);
		}, n, r);
	}, _.scaleTo = function(e, r, i, a) {
		_.transform(e, function() {
			var e = t.apply(this, arguments), a = this.__zoom, s = i == null ? b(e) : typeof i == "function" ? i.apply(this, arguments) : i, c = a.invert(s), l = typeof r == "function" ? r.apply(this, arguments) : r;
			return n(y(v(a, l), s, c), e, o);
		}, i, a);
	}, _.translateBy = function(e, r, i, a) {
		_.transform(e, function() {
			return n(this.__zoom.translate(typeof r == "function" ? r.apply(this, arguments) : r, typeof i == "function" ? i.apply(this, arguments) : i), t.apply(this, arguments), o);
		}, null, a);
	}, _.translateTo = function(e, r, i, a, s) {
		_.transform(e, function() {
			var e = t.apply(this, arguments), s = this.__zoom, c = a == null ? b(e) : typeof a == "function" ? a.apply(this, arguments) : a;
			return n(Xu.translate(c[0], c[1]).scale(s.k).translate(typeof r == "function" ? -r.apply(this, arguments) : -r, typeof i == "function" ? -i.apply(this, arguments) : -i), e, o);
		}, a, s);
	};
	function v(e, t) {
		return t = Math.max(a[0], Math.min(a[1], t)), t === e.k ? e : new Yu(t, e.x, e.y);
	}
	function y(e, t, n) {
		var r = t[0] - n[0] * e.k, i = t[1] - n[1] * e.k;
		return r === e.x && i === e.y ? e : new Yu(e.k, r, i);
	}
	function b(e) {
		return [(+e[0][0] + +e[1][0]) / 2, (+e[0][1] + +e[1][1]) / 2];
	}
	function x(e, n, r, i) {
		e.on("start.zoom", function() {
			S(this, arguments).event(i).start();
		}).on("interrupt.zoom end.zoom", function() {
			S(this, arguments).event(i).end();
		}).tween("zoom", function() {
			var e = this, a = arguments, o = S(e, a).event(i), s = t.apply(e, a), l = r == null ? b(s) : typeof r == "function" ? r.apply(e, a) : r, u = Math.max(s[1][0] - s[0][0], s[1][1] - s[0][1]), d = e.__zoom, f = typeof n == "function" ? n.apply(e, a) : n, p = c(d.invert(l).concat(u / d.k), f.invert(l).concat(u / f.k));
			return function(e) {
				if (e === 1) e = f;
				else {
					var t = p(e), n = u / t[2];
					e = new Yu(n, l[0] - t[0] * n, l[1] - t[1] * n);
				}
				o.zoom(null, e);
			};
		});
	}
	function S(e, t, n) {
		return !n && e.__zooming || new C(e, t);
	}
	function C(e, n) {
		this.that = e, this.args = n, this.active = 0, this.sourceEvent = null, this.extent = t.apply(e, n), this.taps = 0;
	}
	C.prototype = {
		event: function(e) {
			return e && (this.sourceEvent = e), this;
		},
		start: function() {
			return ++this.active === 1 && (this.that.__zooming = this, this.emit("start")), this;
		},
		zoom: function(e, t) {
			return this.mouse && e !== "mouse" && (this.mouse[1] = t.invert(this.mouse[0])), this.touch0 && e !== "touch" && (this.touch0[1] = t.invert(this.touch0[0])), this.touch1 && e !== "touch" && (this.touch1[1] = t.invert(this.touch1[0])), this.that.__zoom = t, this.emit("zoom"), this;
		},
		end: function() {
			return --this.active === 0 && (delete this.that.__zooming, this.emit("end")), this;
		},
		emit: function(e) {
			var t = ks(this.that).datum();
			l.call(e, this.that, new Ju(e, {
				sourceEvent: this.sourceEvent,
				target: _,
				type: e,
				transform: this.that.__zoom,
				dispatch: l
			}), t);
		}
	};
	function w(t, ...i) {
		if (!e.apply(this, arguments)) return;
		var s = S(this, i).event(t), c = this.__zoom, l = Math.max(a[0], Math.min(a[1], c.k * 2 ** r.apply(this, arguments))), u = js(t);
		if (s.wheel) (s.mouse[0][0] !== u[0] || s.mouse[0][1] !== u[1]) && (s.mouse[1] = c.invert(s.mouse[0] = u)), clearTimeout(s.wheel);
		else if (c.k === l) return;
		else s.mouse = [u, c.invert(u)], Il(this), s.start();
		$u(t), s.wheel = setTimeout(d, m), s.zoom("mouse", n(y(v(c, l), s.mouse[0], s.mouse[1]), s.extent, o));
		function d() {
			s.wheel = null, s.end();
		}
	}
	function T(t, ...r) {
		if (f || !e.apply(this, arguments)) return;
		var i = t.currentTarget, a = S(this, r, !0).event(t), s = ks(t.view).on("mousemove.zoom", d, !0).on("mouseup.zoom", p, !0), c = js(t, i), l = t.clientX, u = t.clientY;
		Is(t.view), Qu(t), a.mouse = [c, this.__zoom.invert(c)], Il(this), a.start();
		function d(e) {
			if ($u(e), !a.moved) {
				var t = e.clientX - l, r = e.clientY - u;
				a.moved = t * t + r * r > h;
			}
			a.event(e).zoom("mouse", n(y(a.that.__zoom, a.mouse[0] = js(e, i), a.mouse[1]), a.extent, o));
		}
		function p(e) {
			s.on("mousemove.zoom mouseup.zoom", null), Ls(e.view, a.moved), $u(e), a.event(e).end();
		}
	}
	function ee(r, ...i) {
		if (e.apply(this, arguments)) {
			var a = this.__zoom, c = js(r.changedTouches ? r.changedTouches[0] : r, this), l = a.invert(c), u = a.k * (r.shiftKey ? .5 : 2), d = n(y(v(a, u), c, l), t.apply(this, i), o);
			$u(r), s > 0 ? ks(this).transition().duration(s).call(x, d, c, r) : ks(this).call(_.transform, d, c, r);
		}
	}
	function E(t, ...n) {
		if (e.apply(this, arguments)) {
			var r = t.touches, i = r.length, a = S(this, n, t.changedTouches.length === i).event(t), o, s, c, l;
			for (Qu(t), s = 0; s < i; ++s) c = r[s], l = js(c, this), l = [
				l,
				this.__zoom.invert(l),
				c.identifier
			], a.touch0 ? !a.touch1 && a.touch0[2] !== l[2] && (a.touch1 = l, a.taps = 0) : (a.touch0 = l, o = !0, a.taps = 1 + !!u);
			u &&= clearTimeout(u), o && (a.taps < 2 && (d = l[0], u = setTimeout(function() {
				u = null;
			}, p)), Il(this), a.start());
		}
	}
	function D(e, ...t) {
		if (this.__zooming) {
			var r = S(this, t).event(e), i = e.changedTouches, a = i.length, s, c, l, u;
			for ($u(e), s = 0; s < a; ++s) c = i[s], l = js(c, this), r.touch0 && r.touch0[2] === c.identifier ? r.touch0[0] = l : r.touch1 && r.touch1[2] === c.identifier && (r.touch1[0] = l);
			if (c = r.that.__zoom, r.touch1) {
				var d = r.touch0[0], f = r.touch0[1], p = r.touch1[0], m = r.touch1[1], h = (h = p[0] - d[0]) * h + (h = p[1] - d[1]) * h, g = (g = m[0] - f[0]) * g + (g = m[1] - f[1]) * g;
				c = v(c, Math.sqrt(h / g)), l = [(d[0] + p[0]) / 2, (d[1] + p[1]) / 2], u = [(f[0] + m[0]) / 2, (f[1] + m[1]) / 2];
			} else if (r.touch0) l = r.touch0[0], u = r.touch0[1];
			else return;
			r.zoom("touch", n(y(c, l, u), r.extent, o));
		}
	}
	function te(e, ...t) {
		if (this.__zooming) {
			var n = S(this, t).event(e), r = e.changedTouches, i = r.length, a, o;
			for (Qu(e), f && clearTimeout(f), f = setTimeout(function() {
				f = null;
			}, p), a = 0; a < i; ++a) o = r[a], n.touch0 && n.touch0[2] === o.identifier ? delete n.touch0 : n.touch1 && n.touch1[2] === o.identifier && delete n.touch1;
			if (n.touch1 && !n.touch0 && (n.touch0 = n.touch1, delete n.touch1), n.touch0) n.touch0[1] = this.__zoom.invert(n.touch0[0]);
			else if (n.end(), n.taps === 2 && (o = js(o, this), Math.hypot(d[0] - o[0], d[1] - o[1]) < g)) {
				var s = ks(this).on("dblclick.zoom");
				s && s.apply(this, arguments);
			}
		}
	}
	return _.wheelDelta = function(e) {
		return arguments.length ? (r = typeof e == "function" ? e : qu(+e), _) : r;
	}, _.filter = function(t) {
		return arguments.length ? (e = typeof t == "function" ? t : qu(!!t), _) : e;
	}, _.touchable = function(e) {
		return arguments.length ? (i = typeof e == "function" ? e : qu(!!e), _) : i;
	}, _.extent = function(e) {
		return arguments.length ? (t = typeof e == "function" ? e : qu([[+e[0][0], +e[0][1]], [+e[1][0], +e[1][1]]]), _) : t;
	}, _.scaleExtent = function(e) {
		return arguments.length ? (a[0] = +e[0], a[1] = +e[1], _) : [a[0], a[1]];
	}, _.translateExtent = function(e) {
		return arguments.length ? (o[0][0] = +e[0][0], o[1][0] = +e[1][0], o[0][1] = +e[0][1], o[1][1] = +e[1][1], _) : [[o[0][0], o[0][1]], [o[1][0], o[1][1]]];
	}, _.constrain = function(e) {
		return arguments.length ? (n = e, _) : n;
	}, _.duration = function(e) {
		return arguments.length ? (s = +e, _) : s;
	}, _.interpolate = function(e) {
		return arguments.length ? (c = e, _) : c;
	}, _.on = function() {
		var e = l.on.apply(l, arguments);
		return e === l ? _ : e;
	}, _.clickDistance = function(e) {
		return arguments.length ? (h = (e = +e) * e, _) : Math.sqrt(h);
	}, _.tapDistance = function(e) {
		return arguments.length ? (g = +e, _) : g;
	}, _;
}
// node_modules/@xyflow/system/dist/esm/index.js
var sd = {
	error001: (e = "react") => `Seems like you have not used ${e === "svelte" ? "SvelteFlowProvider" : "ReactFlowProvider"} as an ancestor. Help: https://${e}flow.dev/error#001`,
	error002: () => "It looks like you've created a new nodeTypes or edgeTypes object. If this wasn't on purpose please define the nodeTypes/edgeTypes outside of the component or memoize them.",
	error003: (e) => `Node type "${e}" not found. Using fallback type "default".`,
	error004: () => "The parent container needs a width and a height to render the graph.",
	error005: () => "Only child nodes can use a parent extent.",
	error006: () => "Can't create edge. An edge needs a source and a target.",
	error007: (e) => `The old edge with id=${e} does not exist.`,
	error009: (e) => `Marker type "${e}" doesn't exist.`,
	error008: (e, { id: t, sourceHandle: n, targetHandle: r }) => `Couldn't create edge for ${e} handle id: "${e === "source" ? n : r}", edge id: ${t}.`,
	error010: () => "Handle: No node id found. Make sure to only use a Handle inside a custom Node.",
	error011: (e) => `Edge type "${e}" not found. Using fallback type "default".`,
	error012: (e) => `Node with id "${e}" does not exist, it may have been removed. This can happen when a node is deleted before the "onNodeClick" handler is called.`,
	error013: (e = "react") => `It seems that you haven't loaded the styles. Please import '@xyflow/${e}/dist/style.css' or base.css to make sure everything is working properly.`,
	error014: () => "useNodeConnections: No node ID found. Call useNodeConnections inside a custom Node or provide a node ID.",
	error015: () => "It seems that you are trying to drag a node that is not initialized. Please use onNodesChange as explained in the docs.",
	error016: (e) => `Edge with id "${e}" does not exist, it may have been removed. This can happen when an edge is deleted before the "onEdgeClick" handler is called.`
}, cd = [[-Infinity, -Infinity], [Infinity, Infinity]], ld = [
	"Enter",
	" ",
	"Escape"
], ud = {
	"node.a11yDescription.default": "Press enter or space to select a node. Press delete to remove it and escape to cancel.",
	"node.a11yDescription.keyboardDisabled": "Press enter or space to select a node. You can then use the arrow keys to move the node around. Press delete to remove it and escape to cancel.",
	"node.a11yDescription.ariaLiveMessage": ({ direction: e, x: t, y: n }) => `Moved selected node ${e}. New position, x: ${t}, y: ${n}`,
	"edge.a11yDescription.default": "Press enter or space to select an edge. You can then press delete to remove it or escape to cancel.",
	"controls.ariaLabel": "Control Panel",
	"controls.zoomIn.ariaLabel": "Zoom In",
	"controls.zoomOut.ariaLabel": "Zoom Out",
	"controls.fitView.ariaLabel": "Fit View",
	"controls.interactive.ariaLabel": "Toggle Interactivity",
	"minimap.ariaLabel": "Mini Map",
	"handle.ariaLabel": "Handle"
}, dd;
(function(e) {
	e.Strict = "strict", e.Loose = "loose";
})(dd ||= {});
var fd;
(function(e) {
	e.Free = "free", e.Vertical = "vertical", e.Horizontal = "horizontal";
})(fd ||= {});
var pd;
(function(e) {
	e.Partial = "partial", e.Full = "full";
})(pd ||= {});
var md = {
	inProgress: !1,
	isValid: null,
	from: null,
	fromHandle: null,
	fromPosition: null,
	fromNode: null,
	to: null,
	toHandle: null,
	toPosition: null,
	toNode: null,
	pointer: null
}, hd;
(function(e) {
	e.Bezier = "default", e.Straight = "straight", e.Step = "step", e.SmoothStep = "smoothstep", e.SimpleBezier = "simplebezier";
})(hd ||= {});
var gd;
(function(e) {
	e.Arrow = "arrow", e.ArrowClosed = "arrowclosed";
})(gd ||= {});
var $;
(function(e) {
	e.Left = "left", e.Top = "top", e.Right = "right", e.Bottom = "bottom";
})($ ||= {});
var _d = {
	[$.Left]: $.Right,
	[$.Right]: $.Left,
	[$.Top]: $.Bottom,
	[$.Bottom]: $.Top
}, vd = (e) => !!e && typeof e == "object" && "id" in e && "source" in e && "target" in e, yd = (e) => !!e && typeof e == "object" && "id" in e && "position" in e && !("source" in e) && !("target" in e), bd = (e) => !!e && typeof e == "object" && "id" in e && "internals" in e && !("source" in e) && !("target" in e), xd = (e, t = [0, 0]) => {
	let { width: n, height: r } = tf(e), i = e.origin ?? t, a = n * i[0], o = r * i[1];
	return {
		x: e.position.x - a,
		y: e.position.y - o
	};
}, Sd = (e, t = { nodeOrigin: [0, 0] }) => {
	if (e.length === 0) return {
		x: 0,
		y: 0,
		width: 0,
		height: 0
	};
	let n = !1, r = e.reduce((e, r) => {
		let i = typeof r == "string", a = !t.nodeLookup && !i ? r : void 0;
		return t.nodeLookup && (a = i ? t.nodeLookup.get(r) : bd(r) ? r : t.nodeLookup.get(r.id)), a ? (n = !0, Fd(e, zd(a, t.nodeOrigin))) : e;
	}, {
		x: Infinity,
		y: Infinity,
		x2: -Infinity,
		y2: -Infinity
	});
	return n ? Ld(r) : {
		x: 0,
		y: 0,
		width: 0,
		height: 0
	};
}, Cd = (e, t = {}) => {
	let n = {
		x: Infinity,
		y: Infinity,
		x2: -Infinity,
		y2: -Infinity
	}, r = !1;
	return e.forEach((e) => {
		(t.filter === void 0 || t.filter(e)) && (n = Fd(n, zd(e)), r = !0);
	}), r ? Ld(n) : {
		x: 0,
		y: 0,
		width: 0,
		height: 0
	};
}, wd = (e, t, [n, r, i] = [
	0,
	0,
	1
], a = !1, o = !1) => {
	let s = (t.x - n) / i, c = (t.y - r) / i, l = t.width / i, u = t.height / i, d = [];
	for (let t of e.values()) {
		let { measured: e, selectable: n = !0, hidden: r = !1 } = t;
		if (o && !n || r) continue;
		let i = e.width ?? t.width ?? t.initialWidth ?? 0, f = e.height ?? t.height ?? t.initialHeight ?? 0, { x: p, y: m } = t.internals.positionAbsolute, h = Vd(s, c, l, u, p, m, i, f), g = i * f, _ = a && h > 0;
		(!t.internals.handleBounds || _ || h >= g || t.dragging) && d.push(t);
	}
	return d;
}, Td = (e, t) => {
	let n = /* @__PURE__ */ new Set();
	return e.forEach((e) => {
		n.add(e.id);
	}), t.filter((e) => n.has(e.source) || n.has(e.target));
};
function Ed(e, t) {
	let n = /* @__PURE__ */ new Map(), r = t?.nodes ? new Set(t.nodes.map((e) => e.id)) : null;
	return e.forEach((e) => {
		let i;
		if (t?.includeHiddenNodes) {
			let { width: t, height: n } = tf(e);
			i = t > 0 && n > 0;
		} else i = !!(e.measured.width && e.measured.height && !e.hidden);
		i && (!r || r.has(e.id)) && n.set(e.id, e);
	}), n;
}
async function Dd({ nodes: e, width: t, height: n, panZoom: r, minZoom: i, maxZoom: a }, o) {
	if (e.size === 0) return !0;
	let s = Qd(Cd(Ed(e, o)), t, n, o?.minZoom ?? i, o?.maxZoom ?? a, o?.padding ?? .1);
	return await r.setViewport(s, {
		duration: o?.duration,
		ease: o?.ease,
		interpolate: o?.interpolate
	}), !0;
}
function Od({ nodeId: e, nextPosition: t, nodeLookup: n, nodeOrigin: r = [0, 0], nodeExtent: i, onError: a }) {
	let o = n.get(e), s = o.parentId ? n.get(o.parentId) : void 0, { x: c, y: l } = s ? s.internals.positionAbsolute : {
		x: 0,
		y: 0
	}, u = o.origin ?? r, d = o.extent || i;
	if (o.extent === "parent" && !o.expandParent) {
		if (!s) a?.("005", sd.error005());
		else {
			let { width: e, height: t } = tf(s);
			e && t && (d = [[c, l], [c + e, l + t]]);
		}
	} else s && ef(o.extent) && (d = [[o.extent[0][0] + c, o.extent[0][1] + l], [o.extent[1][0] + c, o.extent[1][1] + l]]);
	let f = ef(d) ? jd(t, d, o.measured) : t;
	return (o.measured.width === void 0 || o.measured.height === void 0) && a?.("015", sd.error015()), {
		position: {
			x: f.x - c + (o.measured.width ?? 0) * u[0],
			y: f.y - l + (o.measured.height ?? 0) * u[1]
		},
		positionAbsolute: f
	};
}
async function kd({ nodesToRemove: e = [], edgesToRemove: t = [], nodes: n, edges: r, onBeforeDelete: i }) {
	let a = new Set(e.map((e) => e.id)), o = [];
	for (let e of n) {
		if (e.deletable === !1) continue;
		let t = a.has(e.id), n = !t && e.parentId && o.find((t) => t.id === e.parentId);
		(t || n) && o.push(e);
	}
	let s = new Set(t.map((e) => e.id)), c = r.filter((e) => e.deletable !== !1), l = Td(o, c);
	for (let e of c) s.has(e.id) && !l.find((t) => t.id === e.id) && l.push(e);
	if (!i) return {
		edges: l,
		nodes: o
	};
	let u = await i({
		nodes: o,
		edges: l
	});
	return typeof u == "boolean" ? u ? {
		edges: l,
		nodes: o
	} : {
		edges: [],
		nodes: []
	} : u;
}
var Ad = (e, t = 0, n = 1) => Math.min(Math.max(e, t), n), jd = (e = {
	x: 0,
	y: 0
}, t, n) => ({
	x: Ad(e.x, t[0][0], t[1][0] - (n?.width ?? 0)),
	y: Ad(e.y, t[0][1], t[1][1] - (n?.height ?? 0))
});
function Md(e, t, n) {
	let { width: r, height: i } = tf(n), { x: a, y: o } = n.internals.positionAbsolute;
	return jd(e, [[a, o], [a + r, o + i]], t);
}
var Nd = (e, t, n) => e < t ? Ad(Math.abs(e - t), 1, t) / t : e > n ? -Ad(Math.abs(e - n), 1, t) / t : 0, Pd = (e, t, n = 15, r = 40) => [Nd(e.x, r, t.width - r) * n, Nd(e.y, r, t.height - r) * n], Fd = (e, t) => ({
	x: Math.min(e.x, t.x),
	y: Math.min(e.y, t.y),
	x2: Math.max(e.x2, t.x2),
	y2: Math.max(e.y2, t.y2)
}), Id = ({ x: e, y: t, width: n, height: r }) => ({
	x: e,
	y: t,
	x2: e + n,
	y2: t + r
}), Ld = ({ x: e, y: t, x2: n, y2: r }) => ({
	x: e,
	y: t,
	width: n - e,
	height: r - t
}), Rd = (e, t = [0, 0]) => {
	let { x: n, y: r } = bd(e) ? e.internals.positionAbsolute : xd(e, t);
	return {
		x: n,
		y: r,
		width: e.measured?.width ?? e.width ?? e.initialWidth ?? 0,
		height: e.measured?.height ?? e.height ?? e.initialHeight ?? 0
	};
}, zd = (e, t = [0, 0]) => {
	let { x: n, y: r } = bd(e) ? e.internals.positionAbsolute : xd(e, t);
	return {
		x: n,
		y: r,
		x2: n + (e.measured?.width ?? e.width ?? e.initialWidth ?? 0),
		y2: r + (e.measured?.height ?? e.height ?? e.initialHeight ?? 0)
	};
}, Bd = (e, t) => Ld(Fd(Id(e), Id(t))), Vd = (e, t, n, r, i, a, o, s) => {
	let c = Math.max(0, Math.min(e + n, i + o) - Math.max(e, i)), l = Math.max(0, Math.min(t + r, a + s) - Math.max(t, a));
	return Math.ceil(c * l);
}, Hd = (e, t) => Vd(e.x, e.y, e.width, e.height, t.x, t.y, t.width, t.height), Ud = (e) => Wd(e.width) && Wd(e.height) && Wd(e.x) && Wd(e.y), Wd = (e) => !isNaN(e) && isFinite(e), Gd = (e, t) => (e, t) => {}, Kd = (e, t = [1, 1]) => ({
	x: t[0] * Math.round(e.x / t[0]),
	y: t[1] * Math.round(e.y / t[1])
}), qd = ({ x: e, y: t }, [n, r, i], a = !1, o = [1, 1]) => {
	let s = {
		x: (e - n) / i,
		y: (t - r) / i
	};
	return a ? Kd(s, o) : s;
}, Jd = ({ x: e, y: t }, [n, r, i]) => ({
	x: e * i + n,
	y: t * i + r
});
function Yd(e, t) {
	if (typeof e == "number") return Math.floor((t - t / (1 + e)) * .5);
	if (typeof e == "string" && e.endsWith("px")) {
		let t = parseFloat(e);
		if (!Number.isNaN(t)) return Math.floor(t);
	}
	if (typeof e == "string" && e.endsWith("%")) {
		let n = parseFloat(e);
		if (!Number.isNaN(n)) return Math.floor(t * n * .01);
	}
	return console.error(`The padding value "${e}" is invalid. Please provide a number or a string with a valid unit (px or %).`), 0;
}
function Xd(e, t, n) {
	if (typeof e == "string" || typeof e == "number") {
		let r = Yd(e, n), i = Yd(e, t);
		return {
			top: r,
			right: i,
			bottom: r,
			left: i,
			x: i * 2,
			y: r * 2
		};
	}
	if (typeof e == "object") {
		let r = Yd(e.top ?? e.y ?? 0, n), i = Yd(e.bottom ?? e.y ?? 0, n), a = Yd(e.left ?? e.x ?? 0, t), o = Yd(e.right ?? e.x ?? 0, t);
		return {
			top: r,
			right: o,
			bottom: i,
			left: a,
			x: a + o,
			y: r + i
		};
	}
	return {
		top: 0,
		right: 0,
		bottom: 0,
		left: 0,
		x: 0,
		y: 0
	};
}
function Zd(e, t, n, r, i, a) {
	let { x: o, y: s } = Jd(e, [
		t,
		n,
		r
	]), { x: c, y: l } = Jd({
		x: e.x + e.width,
		y: e.y + e.height
	}, [
		t,
		n,
		r
	]), u = i - c, d = a - l;
	return {
		left: Math.floor(o),
		top: Math.floor(s),
		right: Math.floor(u),
		bottom: Math.floor(d)
	};
}
var Qd = (e, t, n, r, i, a) => {
	let o = Xd(a, t, n), s = (t - o.x) / e.width, c = (n - o.y) / e.height, l = Ad(Math.min(s, c), r, i), u = e.x + e.width / 2, d = e.y + e.height / 2, f = t / 2 - u * l, p = n / 2 - d * l, m = Zd(e, f, p, l, t, n), h = {
		left: Math.min(m.left - o.left, 0),
		top: Math.min(m.top - o.top, 0),
		right: Math.min(m.right - o.right, 0),
		bottom: Math.min(m.bottom - o.bottom, 0)
	};
	return {
		x: f - h.left + h.right,
		y: p - h.top + h.bottom,
		zoom: l
	};
}, $d = () => typeof navigator < "u" && navigator?.userAgent?.indexOf("Mac") >= 0;
function ef(e) {
	return e != null && e !== "parent";
}
function tf(e) {
	return {
		width: e.measured?.width ?? e.width ?? e.initialWidth ?? 0,
		height: e.measured?.height ?? e.height ?? e.initialHeight ?? 0
	};
}
function nf(e) {
	return (e.measured?.width ?? e.width ?? e.initialWidth) !== void 0 && (e.measured?.height ?? e.height ?? e.initialHeight) !== void 0;
}
function rf(e, t = {
	width: 0,
	height: 0
}, n, r, i) {
	let a = { ...e }, o = r.get(n);
	if (o) {
		let e = o.origin || i;
		a.x += o.internals.positionAbsolute.x - (t.width ?? 0) * e[0], a.y += o.internals.positionAbsolute.y - (t.height ?? 0) * e[1];
	}
	return a;
}
function af(e) {
	return {
		...ud,
		...e || {}
	};
}
function of(e, t) {
	if (!e && !t) return !0;
	if (!e || !t || e.size !== t.size) return !1;
	if (!e.size && !t.size) return !0;
	for (let n of e.keys()) if (!t.has(n)) return !1;
	return !0;
}
function sf(e, t, n) {
	if (!n) return;
	let r = [];
	e.forEach((e, n) => {
		t?.has(n) || r.push(e);
	}), r.length && n(r);
}
function cf(e) {
	return e === null ? null : e ? "valid" : "invalid";
}
function lf(e, { snapGrid: t = [0, 0], snapToGrid: n = !1, transform: r, containerBounds: i }) {
	let { x: a, y: o } = hf(e), s = qd({
		x: a - (i?.left ?? 0),
		y: o - (i?.top ?? 0)
	}, r), { x: c, y: l } = n ? Kd(s, t) : s;
	return {
		xSnapped: c,
		ySnapped: l,
		...s
	};
}
var uf = (e) => ({
	width: e.offsetWidth,
	height: e.offsetHeight
}), df = (e) => e?.getRootNode?.() || window?.document, ff = [
	"INPUT",
	"SELECT",
	"TEXTAREA"
];
function pf(e) {
	let t = e.composedPath?.()?.[0] || e.target;
	return t?.nodeType === 1 ? ff.includes(t.nodeName) || t.hasAttribute("contenteditable") || !!t.closest(".nokey") : !1;
}
var mf = (e) => "clientX" in e, hf = (e, t) => {
	let n = mf(e), r = n ? e.clientX : e.touches?.[0].clientX, i = n ? e.clientY : e.touches?.[0].clientY;
	return {
		x: r - (t?.left ?? 0),
		y: i - (t?.top ?? 0)
	};
}, gf = (e, t, n, r, i) => {
	let a = t.querySelectorAll(`.${e}`);
	return !a || !a.length ? null : Array.from(a).map((t) => {
		let a = t.getBoundingClientRect();
		return {
			id: t.getAttribute("data-handleid"),
			type: e,
			nodeId: i,
			position: t.getAttribute("data-handlepos"),
			x: (a.left - n.left) / r,
			y: (a.top - n.top) / r,
			...uf(t)
		};
	});
};
function _f({ sourceX: e, sourceY: t, targetX: n, targetY: r, sourceControlX: i, sourceControlY: a, targetControlX: o, targetControlY: s }) {
	let c = e * .125 + i * .375 + o * .375 + n * .125, l = t * .125 + a * .375 + s * .375 + r * .125;
	return [
		c,
		l,
		Math.abs(c - e),
		Math.abs(l - t)
	];
}
function vf(e, t) {
	return e >= 0 ? .5 * e : t * 25 * Math.sqrt(-e);
}
function yf({ pos: e, x1: t, y1: n, x2: r, y2: i, c: a }) {
	switch (e) {
		case $.Left: return [t - vf(t - r, a), n];
		case $.Right: return [t + vf(r - t, a), n];
		case $.Top: return [t, n - vf(n - i, a)];
		case $.Bottom: return [t, n + vf(i - n, a)];
	}
}
function bf({ sourceX: e, sourceY: t, sourcePosition: n = $.Bottom, targetX: r, targetY: i, targetPosition: a = $.Top, curvature: o = .25 }) {
	let [s, c] = yf({
		pos: n,
		x1: e,
		y1: t,
		x2: r,
		y2: i,
		c: o
	}), [l, u] = yf({
		pos: a,
		x1: r,
		y1: i,
		x2: e,
		y2: t,
		c: o
	}), [d, f, p, m] = _f({
		sourceX: e,
		sourceY: t,
		targetX: r,
		targetY: i,
		sourceControlX: s,
		sourceControlY: c,
		targetControlX: l,
		targetControlY: u
	});
	return [
		`M${e},${t} C${s},${c} ${l},${u} ${r},${i}`,
		d,
		f,
		p,
		m
	];
}
function xf({ sourceX: e, sourceY: t, targetX: n, targetY: r }) {
	let i = Math.abs(n - e) / 2, a = n < e ? n + i : n - i, o = Math.abs(r - t) / 2;
	return [
		a,
		r < t ? r + o : r - o,
		i,
		o
	];
}
function Sf({ sourceNode: e, targetNode: t, selected: n = !1, zIndex: r = 0, elevateOnSelect: i = !1, zIndexMode: a = "basic" }) {
	return a === "manual" ? r : (i && n ? r + 1e3 : r) + Math.max(e.parentId || i && e.selected ? e.internals.z : 0, t.parentId || i && t.selected ? t.internals.z : 0);
}
function Cf({ sourceNode: e, targetNode: t, width: n, height: r, transform: i }) {
	let a = Fd(zd(e), zd(t));
	return a.x === a.x2 && (a.x2 += 1), a.y === a.y2 && (a.y2 += 1), Hd({
		x: -i[0] / i[2],
		y: -i[1] / i[2],
		width: n / i[2],
		height: r / i[2]
	}, Ld(a)) > 0;
}
var wf = ({ source: e, sourceHandle: t, target: n, targetHandle: r }) => `xy-edge__${e}${t || ""}-${n}${r || ""}`, Tf = (e, t) => t.some((t) => t.source === e.source && t.target === e.target && (t.sourceHandle === e.sourceHandle || !t.sourceHandle && !e.sourceHandle) && (t.targetHandle === e.targetHandle || !t.targetHandle && !e.targetHandle)), Ef = (e, t, n = {}) => {
	if (!e.source || !e.target) return n.onError?.("006", sd.error006()), t;
	let r = n.getEdgeId || wf, i;
	return i = vd(e) ? { ...e } : {
		...e,
		id: r(e)
	}, Tf(i, t) ? t : (i.sourceHandle === null && delete i.sourceHandle, i.targetHandle === null && delete i.targetHandle, t.concat(i));
};
function Df({ sourceX: e, sourceY: t, targetX: n, targetY: r }) {
	let [i, a, o, s] = xf({
		sourceX: e,
		sourceY: t,
		targetX: n,
		targetY: r
	});
	return [
		`M ${e},${t}L ${n},${r}`,
		i,
		a,
		o,
		s
	];
}
var Of = {
	[$.Left]: {
		x: -1,
		y: 0
	},
	[$.Right]: {
		x: 1,
		y: 0
	},
	[$.Top]: {
		x: 0,
		y: -1
	},
	[$.Bottom]: {
		x: 0,
		y: 1
	}
}, kf = ({ source: e, sourcePosition: t = $.Bottom, target: n }) => t === $.Left || t === $.Right ? e.x < n.x ? {
	x: 1,
	y: 0
} : {
	x: -1,
	y: 0
} : e.y < n.y ? {
	x: 0,
	y: 1
} : {
	x: 0,
	y: -1
}, Af = (e, t) => Math.sqrt((t.x - e.x) ** 2 + (t.y - e.y) ** 2);
function jf({ source: e, sourcePosition: t = $.Bottom, target: n, targetPosition: r = $.Top, center: i, offset: a, stepPosition: o }) {
	let s = Of[t], c = Of[r], l = {
		x: e.x + s.x * a,
		y: e.y + s.y * a
	}, u = {
		x: n.x + c.x * a,
		y: n.y + c.y * a
	}, d = kf({
		source: l,
		sourcePosition: t,
		target: u
	}), f = d.x === 0 ? "y" : "x", p = d[f], m = [], h, g, _ = {
		x: 0,
		y: 0
	}, v = {
		x: 0,
		y: 0
	}, [, , y, b] = xf({
		sourceX: e.x,
		sourceY: e.y,
		targetX: n.x,
		targetY: n.y
	});
	if (s[f] * c[f] === -1) {
		f === "x" ? (h = i.x ?? l.x + (u.x - l.x) * o, g = i.y ?? (l.y + u.y) / 2) : (h = i.x ?? (l.x + u.x) / 2, g = i.y ?? l.y + (u.y - l.y) * o);
		let e = [{
			x: h,
			y: l.y
		}, {
			x: h,
			y: u.y
		}], t = [{
			x: l.x,
			y: g
		}, {
			x: u.x,
			y: g
		}];
		m = s[f] === p ? f === "x" ? e : t : f === "x" ? t : e;
	} else {
		let i = [{
			x: l.x,
			y: u.y
		}], o = [{
			x: u.x,
			y: l.y
		}];
		if (m = f === "x" ? s.x === p ? o : i : s.y === p ? i : o, t === r) {
			let t = Math.abs(e[f] - n[f]);
			if (t <= a) {
				let r = Math.min(a - 1, a - t);
				s[f] === p ? _[f] = (l[f] > e[f] ? -1 : 1) * r : v[f] = (u[f] > n[f] ? -1 : 1) * r;
			}
		}
		if (t !== r) {
			let e = f === "x" ? "y" : "x", t = s[f] === c[e], n = l[e] > u[e], r = l[e] < u[e];
			(s[f] === 1 && (!t && n || t && r) || s[f] !== 1 && (!t && r || t && n)) && (m = f === "x" ? i : o);
		}
		let d = {
			x: l.x + _.x,
			y: l.y + _.y
		}, y = {
			x: u.x + v.x,
			y: u.y + v.y
		};
		Math.max(Math.abs(d.x - m[0].x), Math.abs(y.x - m[0].x)) >= Math.max(Math.abs(d.y - m[0].y), Math.abs(y.y - m[0].y)) ? (h = (d.x + y.x) / 2, g = m[0].y) : (h = m[0].x, g = (d.y + y.y) / 2);
	}
	let x = {
		x: l.x + _.x,
		y: l.y + _.y
	}, S = {
		x: u.x + v.x,
		y: u.y + v.y
	};
	return [
		[
			e,
			...x.x !== m[0].x || x.y !== m[0].y ? [x] : [],
			...m,
			...S.x !== m[m.length - 1].x || S.y !== m[m.length - 1].y ? [S] : [],
			n
		],
		h,
		g,
		y,
		b
	];
}
function Mf(e, t, n, r) {
	let i = Math.min(Af(e, t) / 2, Af(t, n) / 2, r), { x: a, y: o } = t;
	if (e.x === a && a === n.x || e.y === o && o === n.y) return `L${a} ${o}`;
	if (e.y === o) {
		let t = e.x < n.x ? -1 : 1, r = e.y < n.y ? 1 : -1;
		return `L ${a + i * t},${o}Q ${a},${o} ${a},${o + i * r}`;
	}
	let s = e.x < n.x ? 1 : -1;
	return `L ${a},${o + i * (e.y < n.y ? -1 : 1)}Q ${a},${o} ${a + i * s},${o}`;
}
function Nf({ sourceX: e, sourceY: t, sourcePosition: n = $.Bottom, targetX: r, targetY: i, targetPosition: a = $.Top, borderRadius: o = 5, centerX: s, centerY: c, offset: l = 20, stepPosition: u = .5 }) {
	let [d, f, p, m, h] = jf({
		source: {
			x: e,
			y: t
		},
		sourcePosition: n,
		target: {
			x: r,
			y: i
		},
		targetPosition: a,
		center: {
			x: s,
			y: c
		},
		offset: l,
		stepPosition: u
	}), g = `M${d[0].x} ${d[0].y}`;
	for (let e = 1; e < d.length - 1; e++) g += Mf(d[e - 1], d[e], d[e + 1], o);
	return g += `L${d[d.length - 1].x} ${d[d.length - 1].y}`, [
		g,
		f,
		p,
		m,
		h
	];
}
function Pf(e) {
	return e && !!(e.internals.handleBounds || e.handles?.length) && !!(e.measured.width || e.width || e.initialWidth);
}
function Ff(e) {
	let { sourceNode: t, targetNode: n } = e;
	if (!Pf(t) || !Pf(n)) return null;
	let r = t.internals.handleBounds || If(t.handles), i = n.internals.handleBounds || If(n.handles), a = Rf(r?.source ?? [], e.sourceHandle), o = Rf(e.connectionMode === dd.Strict ? i?.target ?? [] : (i?.target ?? []).concat(i?.source ?? []), e.targetHandle);
	if (!a || !o) return e.onError?.("008", sd.error008(a ? "target" : "source", {
		id: e.id,
		sourceHandle: e.sourceHandle,
		targetHandle: e.targetHandle
	})), null;
	let s = a?.position || $.Bottom, c = o?.position || $.Top, l = Lf(t, a, s), u = Lf(n, o, c);
	return {
		sourceX: l.x,
		sourceY: l.y,
		targetX: u.x,
		targetY: u.y,
		sourcePosition: s,
		targetPosition: c
	};
}
function If(e) {
	if (!e) return null;
	let t = [], n = [];
	for (let r of e) r.width = r.width ?? 1, r.height = r.height ?? 1, r.type === "source" ? t.push(r) : r.type === "target" && n.push(r);
	return {
		source: t,
		target: n
	};
}
function Lf(e, t, n = $.Left, r = !1) {
	let i = (t?.x ?? 0) + e.internals.positionAbsolute.x, a = (t?.y ?? 0) + e.internals.positionAbsolute.y, { width: o, height: s } = t ?? tf(e);
	if (r) return {
		x: i + o / 2,
		y: a + s / 2
	};
	switch (t?.position ?? n) {
		case $.Top: return {
			x: i + o / 2,
			y: a
		};
		case $.Right: return {
			x: i + o,
			y: a + s / 2
		};
		case $.Bottom: return {
			x: i + o / 2,
			y: a + s
		};
		case $.Left: return {
			x: i,
			y: a + s / 2
		};
	}
}
function Rf(e, t) {
	return e && (t ? e.find((e) => e.id === t) : e[0]) || null;
}
function zf(e, t) {
	return e ? typeof e == "string" ? e : `${t ? `${t}__` : ""}${Object.keys(e).sort().map((t) => `${t}=${e[t]}`).join("&")}` : "";
}
function Bf(e, { id: t, defaultColor: n, defaultMarkerStart: r, defaultMarkerEnd: i }) {
	let a = /* @__PURE__ */ new Set();
	return e.reduce((e, o) => ([o.markerStart || r, o.markerEnd || i].forEach((r) => {
		if (r && typeof r == "object") {
			let i = zf(r, t);
			a.has(i) || (e.push({
				id: i,
				color: r.color || n,
				...r
			}), a.add(i));
		}
	}), e), []).sort((e, t) => e.id.localeCompare(t.id));
}
var Vf = 1e3, Hf = 10, Uf = {
	nodeOrigin: [0, 0],
	nodeExtent: cd,
	elevateNodesOnSelect: !0,
	zIndexMode: "basic",
	defaults: {}
}, Wf = {
	...Uf,
	checkEquality: !0
};
function Gf(e, t) {
	let n = { ...e };
	for (let e in t) t[e] !== void 0 && (n[e] = t[e]);
	return n;
}
function Kf(e, t, n) {
	let r = Gf(Uf, n);
	for (let n of e.values()) if (n.parentId) Zf(n, e, t, r);
	else {
		let e = jd(xd(n, r.nodeOrigin), ef(n.extent) ? n.extent : r.nodeExtent, tf(n));
		n.internals.positionAbsolute = e;
	}
}
function qf(e, t) {
	if (!e.handles) return e.measured ? t?.internals.handleBounds : void 0;
	let n = [], r = [];
	for (let t of e.handles) {
		let i = {
			id: t.id,
			width: t.width ?? 1,
			height: t.height ?? 1,
			nodeId: e.id,
			x: t.x,
			y: t.y,
			position: t.position,
			type: t.type
		};
		t.type === "source" ? n.push(i) : t.type === "target" && r.push(i);
	}
	return {
		source: n,
		target: r
	};
}
function Jf(e) {
	return e === "manual";
}
function Yf(e, t, n, r = {}) {
	let i = Gf(Wf, r), a = { i: 0 }, o = new Map(t), s = i?.elevateNodesOnSelect && !Jf(i.zIndexMode) ? Vf : 0, c = e.length > 0, l = !1;
	t.clear(), n.clear();
	for (let u of e) {
		let e = o.get(u.id);
		if (i.checkEquality && u === e?.internals.userNode) t.set(u.id, e);
		else {
			let n = jd(xd(u, i.nodeOrigin), ef(u.extent) ? u.extent : i.nodeExtent, tf(u));
			e = {
				...i.defaults,
				...u,
				measured: {
					width: u.measured?.width,
					height: u.measured?.height
				},
				internals: {
					positionAbsolute: n,
					handleBounds: qf(u, e),
					z: Qf(u, s, i.zIndexMode),
					userNode: u
				}
			}, t.set(u.id, e);
		}
		e.measured !== void 0 && e.measured.width !== void 0 && e.measured.height !== void 0 || e.hidden || (c = !1), u.parentId && Zf(e, t, n, r, a), l ||= u.selected ?? !1;
	}
	return {
		nodesInitialized: c,
		hasSelectedNodes: l
	};
}
function Xf(e, t) {
	if (!e.parentId) return;
	let n = t.get(e.parentId);
	n ? n.set(e.id, e) : t.set(e.parentId, /* @__PURE__ */ new Map([[e.id, e]]));
}
function Zf(e, t, n, r, i) {
	let { elevateNodesOnSelect: a, nodeOrigin: o, nodeExtent: s, zIndexMode: c } = Gf(Uf, r), l = e.parentId, u = t.get(l);
	if (!u) {
		console.warn(`Parent node ${l} not found. Please make sure that parent nodes are in front of their child nodes in the nodes array.`);
		return;
	}
	Xf(e, n), i && !u.parentId && u.internals.rootParentIndex === void 0 && c === "auto" && (u.internals.rootParentIndex = ++i.i, u.internals.z = u.internals.z + i.i * Hf), i && u.internals.rootParentIndex !== void 0 && (i.i = u.internals.rootParentIndex);
	let { x: d, y: f, z: p } = $f(e, u, o, s, a && !Jf(c) ? Vf : 0, c), { positionAbsolute: m } = e.internals, h = d !== m.x || f !== m.y;
	(h || p !== e.internals.z) && t.set(e.id, {
		...e,
		internals: {
			...e.internals,
			positionAbsolute: h ? {
				x: d,
				y: f
			} : m,
			z: p
		}
	});
}
function Qf(e, t, n) {
	let r = Wd(e.zIndex) ? e.zIndex : 0;
	return Jf(n) ? r : r + (e.selected ? t : 0);
}
function $f(e, t, n, r, i, a) {
	let { x: o, y: s } = t.internals.positionAbsolute, c = tf(e), l = xd(e, n), u = ef(e.extent) ? jd(l, e.extent, c) : l, d = jd({
		x: o + u.x,
		y: s + u.y
	}, r, c);
	e.extent === "parent" && (d = Md(d, c, t));
	let f = Qf(e, i, a), p = t.internals.z ?? 0;
	return {
		x: d.x,
		y: d.y,
		z: p >= f ? p + 1 : f
	};
}
function ep(e, t, n, r = [0, 0]) {
	let i = [], a = /* @__PURE__ */ new Map();
	for (let n of e) {
		let e = t.get(n.parentId);
		if (!e) continue;
		let r = Bd(a.get(n.parentId)?.expandedRect ?? Rd(e), n.rect);
		a.set(n.parentId, {
			expandedRect: r,
			parent: e
		});
	}
	return a.size > 0 && a.forEach(({ expandedRect: t, parent: a }, o) => {
		let s = a.internals.positionAbsolute, c = tf(a), l = a.origin ?? r, u = t.x < s.x ? Math.round(Math.abs(s.x - t.x)) : 0, d = t.y < s.y ? Math.round(Math.abs(s.y - t.y)) : 0, f = Math.max(c.width, Math.round(t.width)), p = Math.max(c.height, Math.round(t.height)), m = (f - c.width) * l[0], h = (p - c.height) * l[1];
		(u > 0 || d > 0 || m || h) && (i.push({
			id: o,
			type: "position",
			position: {
				x: a.position.x - u + m,
				y: a.position.y - d + h
			}
		}), n.get(o)?.forEach((t) => {
			e.some((e) => e.id === t.id) || i.push({
				id: t.id,
				type: "position",
				position: {
					x: t.position.x + u,
					y: t.position.y + d
				}
			});
		})), (c.width < t.width || c.height < t.height || u || d) && i.push({
			id: o,
			type: "dimensions",
			setAttributes: !0,
			dimensions: {
				width: f + (u ? l[0] * u - m : 0),
				height: p + (d ? l[1] * d - h : 0)
			}
		});
	}), i;
}
function tp(e, t, n, r, i, a, o) {
	let s = r?.querySelector(".xyflow__viewport"), c = !1;
	if (!s) return {
		changes: [],
		updatedInternals: c
	};
	let l = [], u = window.getComputedStyle(s), { m22: d } = new window.DOMMatrixReadOnly(u.transform), f = [];
	for (let r of e.values()) {
		let e = t.get(r.id);
		if (!e) continue;
		if (e.hidden) {
			t.set(e.id, {
				...e,
				internals: {
					...e.internals,
					handleBounds: void 0
				}
			}), c = !0;
			continue;
		}
		let s = uf(r.nodeElement), u = e.measured.width !== s.width || e.measured.height !== s.height;
		if (s.width && s.height && (u || !e.internals.handleBounds || r.force)) {
			let p = r.nodeElement.getBoundingClientRect(), m = ef(e.extent) ? e.extent : a, { positionAbsolute: h } = e.internals;
			if (e.parentId && e.extent === "parent") {
				let n = t.get(e.parentId);
				n && (h = Md(h, s, n));
			} else m && (h = jd(h, m, s));
			let g = {
				...e,
				measured: s,
				internals: {
					...e.internals,
					positionAbsolute: h,
					handleBounds: {
						source: gf("source", r.nodeElement, p, d, e.id),
						target: gf("target", r.nodeElement, p, d, e.id)
					}
				}
			};
			t.set(e.id, g), e.parentId && Zf(g, t, n, {
				nodeOrigin: i,
				zIndexMode: o
			}), c = !0, u && (l.push({
				id: e.id,
				type: "dimensions",
				dimensions: s
			}), e.expandParent && e.parentId && f.push({
				id: e.id,
				parentId: e.parentId,
				rect: Rd(g, i)
			}));
		}
	}
	if (f.length > 0) {
		let e = ep(f, t, n, i);
		l.push(...e);
	}
	return {
		changes: l,
		updatedInternals: c
	};
}
async function np({ delta: e, panZoom: t, transform: n, translateExtent: r, width: i, height: a }) {
	if (!t || !e.x && !e.y) return !1;
	let o = await t.setViewportConstrained({
		x: n[0] + e.x,
		y: n[1] + e.y,
		zoom: n[2]
	}, [[0, 0], [i, a]], r);
	return !!o && (o.x !== n[0] || o.y !== n[1] || o.k !== n[2]);
}
function rp(e, t, n, r, i, a) {
	let o = i, s = r.get(o) || /* @__PURE__ */ new Map();
	r.set(o, s.set(n, t)), o = `${i}-${e}`;
	let c = r.get(o) || /* @__PURE__ */ new Map();
	if (r.set(o, c.set(n, t)), a) {
		o = `${i}-${e}-${a}`;
		let s = r.get(o) || /* @__PURE__ */ new Map();
		r.set(o, s.set(n, t));
	}
}
function ip(e, t, n) {
	e.clear(), t.clear();
	for (let r of n) {
		let { source: n, target: i, sourceHandle: a = null, targetHandle: o = null } = r, s = {
			edgeId: r.id,
			source: n,
			target: i,
			sourceHandle: a,
			targetHandle: o
		}, c = `${n}-${a}--${i}-${o}`;
		rp("source", s, `${i}-${o}--${n}-${a}`, e, n, a), rp("target", s, c, e, i, o), t.set(r.id, r);
	}
}
function ap(e, t) {
	if (!e.parentId) return !1;
	let n = t.get(e.parentId);
	return n ? n.selected ? !0 : ap(n, t) : !1;
}
function op(e, t, n) {
	let r = e;
	do {
		if (r?.matches?.(t)) return !0;
		if (r === n) return !1;
		r = r?.parentElement;
	} while (r);
	return !1;
}
function sp(e, t, n, r) {
	let i = /* @__PURE__ */ new Map();
	for (let [a, o] of e) if ((o.selected || o.id === r) && (!o.parentId || !ap(o, e)) && (o.draggable || t && o.draggable === void 0)) {
		let t = e.get(a);
		t && i.set(a, {
			id: a,
			position: t.position || {
				x: 0,
				y: 0
			},
			distance: {
				x: n.x - t.internals.positionAbsolute.x,
				y: n.y - t.internals.positionAbsolute.y
			},
			extent: t.extent,
			parentId: t.parentId,
			origin: t.origin,
			expandParent: t.expandParent,
			internals: { positionAbsolute: t.internals.positionAbsolute || {
				x: 0,
				y: 0
			} },
			measured: {
				width: t.measured.width ?? 0,
				height: t.measured.height ?? 0
			}
		});
	}
	return i;
}
function cp({ nodeId: e, dragItems: t, nodeLookup: n, dragging: r = !0 }) {
	let i = [];
	for (let [e, a] of t) {
		let t = n.get(e)?.internals.userNode;
		t && i.push({
			...t,
			position: a.position,
			dragging: r
		});
	}
	if (!e) return [i[0], i];
	let a = n.get(e)?.internals.userNode;
	return [a ? {
		...a,
		position: t.get(e)?.position || a.position,
		dragging: r
	} : i[0], i];
}
function lp({ dragItems: e, snapGrid: t, x: n, y: r }) {
	let i = e.values().next().value;
	if (!i) return null;
	let a = {
		x: n - i.distance.x,
		y: r - i.distance.y
	}, o = Kd(a, t);
	return {
		x: o.x - a.x,
		y: o.y - a.y
	};
}
function up({ onNodeMouseDown: e, getStoreItems: t, onDragStart: n, onDrag: r, onDragStop: i }) {
	let a = {
		x: null,
		y: null
	}, o = 0, s = /* @__PURE__ */ new Map(), c = !1, l = {
		x: 0,
		y: 0
	}, u = null, d = !1, f = null, p = !1, m = !1, h = null;
	function g({ noDragClassName: g, handleSelector: _, domNode: v, isSelectable: y, nodeId: b, nodeClickDistance: x = 0 }) {
		f = ks(v);
		function S({ x: e, y: n }) {
			let { nodeLookup: i, nodeExtent: o, snapGrid: c, snapToGrid: l, nodeOrigin: u, onNodeDrag: d, onSelectionDrag: f, onError: p, updateNodePositions: g } = t();
			a = {
				x: e,
				y: n
			};
			let _ = !1, v = s.size > 1, y = v && o ? Id(Cd(s)) : null, x = v && l ? lp({
				dragItems: s,
				snapGrid: c,
				x: e,
				y: n
			}) : null;
			for (let [t, r] of s) {
				if (!i.has(t)) continue;
				let a = {
					x: e - r.distance.x,
					y: n - r.distance.y
				};
				l && (a = x ? {
					x: Math.round(a.x + x.x),
					y: Math.round(a.y + x.y)
				} : Kd(a, c));
				let s = null;
				if (v && o && !r.extent && y) {
					let { positionAbsolute: e } = r.internals, t = e.x - y.x + o[0][0], n = e.x + r.measured.width - y.x2 + o[1][0], i = e.y - y.y + o[0][1], a = e.y + r.measured.height - y.y2 + o[1][1];
					s = [[t, i], [n, a]];
				}
				let { position: d, positionAbsolute: f } = Od({
					nodeId: t,
					nextPosition: a,
					nodeLookup: i,
					nodeExtent: s || o,
					nodeOrigin: u,
					onError: p
				});
				_ = _ || r.position.x !== d.x || r.position.y !== d.y, r.position = d, r.internals.positionAbsolute = f;
			}
			if (m ||= _, _ && (g(s, !0), h && (r || d || !b && f))) {
				let [e, t] = cp({
					nodeId: b,
					dragItems: s,
					nodeLookup: i
				});
				r?.(h, s, e, t), d?.(h, e, t), b || f?.(h, t);
			}
		}
		async function C() {
			if (!u) return;
			let { transform: e, panBy: n, autoPanSpeed: r, autoPanOnNodeDrag: i } = t();
			if (!i) {
				c = !1, cancelAnimationFrame(o);
				return;
			}
			let [s, d] = Pd(l, u, r);
			(s !== 0 || d !== 0) && (a.x = (a.x ?? 0) - s / e[2], a.y = (a.y ?? 0) - d / e[2], await n({
				x: s,
				y: d
			}) && S(a)), o = requestAnimationFrame(C);
		}
		function w(r) {
			let { nodeLookup: i, multiSelectionActive: o, nodesDraggable: c, transform: l, snapGrid: f, snapToGrid: p, selectNodesOnDrag: m, onNodeDragStart: h, onSelectionDragStart: g, unselectNodesAndEdges: _ } = t();
			d = !0, m && y || o || !b || i.get(b)?.selected || _(), y && m && b && e?.(b);
			let v = lf(r.sourceEvent, {
				transform: l,
				snapGrid: f,
				snapToGrid: p,
				containerBounds: u
			});
			if (a = v, s = sp(i, c, v, b), s.size > 0 && (n || h || !b && g)) {
				let [e, t] = cp({
					nodeId: b,
					dragItems: s,
					nodeLookup: i
				});
				n?.(r.sourceEvent, s, e, t), h?.(r.sourceEvent, e, t), b || g?.(r.sourceEvent, t);
			}
		}
		let T = Ws().clickDistance(x).on("start", (e) => {
			let { domNode: n, nodeDragThreshold: r, transform: i, snapGrid: o, snapToGrid: s } = t();
			u = n?.getBoundingClientRect() || null, p = !1, m = !1, h = e.sourceEvent, r === 0 && w(e), a = lf(e.sourceEvent, {
				transform: i,
				snapGrid: o,
				snapToGrid: s,
				containerBounds: u
			}), l = hf(e.sourceEvent, u);
		}).on("drag", (e) => {
			let { autoPanOnNodeDrag: n, transform: r, snapGrid: i, snapToGrid: o, nodeDragThreshold: f, nodeLookup: m } = t(), g = lf(e.sourceEvent, {
				transform: r,
				snapGrid: i,
				snapToGrid: o,
				containerBounds: u
			});
			if (h = e.sourceEvent, (e.sourceEvent.type === "touchmove" && e.sourceEvent.touches.length > 1 || b && !m.has(b)) && (p = !0), !p) {
				if (!c && n && d && (c = !0, C()), !d) {
					let t = hf(e.sourceEvent, u), n = t.x - l.x, r = t.y - l.y;
					Math.sqrt(n * n + r * r) > f && w(e);
				}
				(a.x !== g.xSnapped || a.y !== g.ySnapped) && s && d && (l = hf(e.sourceEvent, u), S(g));
			}
		}).on("end", (e) => {
			if (!d || p) p && s.size > 0 && t().updateNodePositions(s, !1);
			else if (c = !1, d = !1, cancelAnimationFrame(o), s.size > 0) {
				let { nodeLookup: n, updateNodePositions: r, onNodeDragStop: a, onSelectionDragStop: o } = t();
				if (m &&= (r(s, !1), !1), i || a || !b && o) {
					let [t, r] = cp({
						nodeId: b,
						dragItems: s,
						nodeLookup: n,
						dragging: !1
					});
					i?.(e.sourceEvent, s, t, r), a?.(e.sourceEvent, t, r), b || o?.(e.sourceEvent, r);
				}
			}
		}).filter((e) => {
			let t = e.target;
			return !e.button && (!g || !op(t, `.${g}`, v)) && (!_ || op(t, _, v));
		});
		f.call(T);
	}
	function _() {
		f?.on(".drag", null);
	}
	return {
		update: g,
		destroy: _
	};
}
function dp(e, t, n) {
	let r = [], i = {
		x: e.x - n,
		y: e.y - n,
		width: n * 2,
		height: n * 2
	};
	for (let e of t.values()) Hd(i, Rd(e)) > 0 && r.push(e);
	return r;
}
var fp = 250;
function pp(e, t, n, r) {
	let i = [], a = Infinity, o = dp(e, n, t + fp);
	for (let n of o) {
		let o = [...n.internals.handleBounds?.source ?? [], ...n.internals.handleBounds?.target ?? []];
		for (let s of o) {
			if (r.nodeId === s.nodeId && r.type === s.type && r.id === s.id) continue;
			let { x: o, y: c } = Lf(n, s, s.position, !0), l = Math.sqrt((o - e.x) ** 2 + (c - e.y) ** 2);
			l > t || (l < a ? (i = [{
				...s,
				x: o,
				y: c
			}], a = l) : l === a && i.push({
				...s,
				x: o,
				y: c
			}));
		}
	}
	if (!i.length) return null;
	if (i.length > 1) {
		let e = r.type === "source" ? "target" : "source";
		return i.find((t) => t.type === e) ?? i[0];
	}
	return i[0];
}
function mp(e, t, n, r, i, a = !1) {
	let o = r.get(e);
	if (!o) return null;
	let s = i === "strict" ? o.internals.handleBounds?.[t] : [...o.internals.handleBounds?.source ?? [], ...o.internals.handleBounds?.target ?? []], c = (n ? s?.find((e) => e.id === n) : s?.[0]) ?? null;
	return c && a ? {
		...c,
		...Lf(o, c, c.position, !0)
	} : c;
}
function hp(e, t) {
	return e || (t?.classList.contains("target") ? "target" : t?.classList.contains("source") ? "source" : null);
}
function gp(e, t) {
	let n = null;
	return t ? n = !0 : e && !t && (n = !1), n;
}
var _p = () => !0;
function vp(e, { connectionMode: t, connectionRadius: n, handleId: r, nodeId: i, edgeUpdaterType: a, isTarget: o, domNode: s, nodeLookup: c, lib: l, autoPanOnConnect: u, flowId: d, panBy: f, cancelConnection: p, onConnectStart: m, onConnect: h, onConnectEnd: g, isValidConnection: _ = _p, onReconnectEnd: v, updateConnection: y, getTransform: b, getFromHandle: x, autoPanSpeed: S, dragThreshold: C = 1, handleDomNode: w }) {
	let T = df(e.target), ee = 0, E, { x: D, y: te } = hf(e), ne = hp(a, w), re = s?.getBoundingClientRect(), ie = !1;
	if (!re || !ne) return;
	let ae = mp(i, ne, r, c, t);
	if (!ae) return;
	let oe = hf(e, re), se = !1, ce = null, le = !1, ue = null;
	function de() {
		if (!u || !re) return;
		let [e, t] = Pd(oe, re, S);
		f({
			x: e,
			y: t
		}), ee = requestAnimationFrame(de);
	}
	let fe = {
		...ae,
		nodeId: i,
		type: ne,
		position: ae.position
	}, pe = c.get(i), me = {
		inProgress: !0,
		isValid: null,
		from: Lf(pe, fe, $.Left, !0),
		fromHandle: fe,
		fromPosition: fe.position,
		fromNode: pe,
		to: oe,
		toHandle: null,
		toPosition: _d[fe.position],
		toNode: null,
		pointer: oe
	};
	function he() {
		ie = !0, y(me), m?.(e, {
			nodeId: i,
			handleId: r,
			handleType: ne
		});
	}
	C === 0 && he();
	function ge(e) {
		if (!ie) {
			let { x: t, y: n } = hf(e), r = t - D, i = n - te;
			if (!(r * r + i * i > C * C)) return;
			he();
		}
		if (!x() || !fe) {
			_e(e);
			return;
		}
		let a = b();
		oe = hf(e, re), E = pp(qd(oe, a, !1, [1, 1]), n, c, fe), se ||= (de(), !0);
		let s = yp(e, {
			handle: E,
			connectionMode: t,
			fromNodeId: i,
			fromHandleId: r,
			fromType: o ? "target" : "source",
			isValidConnection: _,
			doc: T,
			lib: l,
			flowId: d,
			nodeLookup: c
		});
		ue = s.handleDomNode, ce = s.connection, le = gp(!!E, s.isValid);
		let u = c.get(i), f = u ? Lf(u, fe, $.Left, !0) : me.from, p = {
			...me,
			from: f,
			isValid: le,
			to: s.toHandle && le ? Jd({
				x: s.toHandle.x,
				y: s.toHandle.y
			}, a) : oe,
			toHandle: s.toHandle,
			toPosition: le && s.toHandle ? s.toHandle.position : _d[fe.position],
			toNode: s.toHandle ? c.get(s.toHandle.nodeId) : null,
			pointer: oe
		};
		y(p), me = p;
	}
	function _e(e) {
		if (!("touches" in e && e.touches.length > 0)) {
			if (ie) {
				(E || ue) && ce && le && h?.(ce);
				let { inProgress: t, ...n } = me, r = {
					...n,
					toPosition: me.toHandle ? me.toPosition : null
				};
				g?.(e, r), a && v?.(e, r);
			}
			p(), cancelAnimationFrame(ee), se = !1, le = !1, ce = null, ue = null, T.removeEventListener("mousemove", ge), T.removeEventListener("mouseup", _e), T.removeEventListener("touchmove", ge), T.removeEventListener("touchend", _e);
		}
	}
	T.addEventListener("mousemove", ge), T.addEventListener("mouseup", _e), T.addEventListener("touchmove", ge), T.addEventListener("touchend", _e);
}
function yp(e, { handle: t, connectionMode: n, fromNodeId: r, fromHandleId: i, fromType: a, doc: o, lib: s, flowId: c, isValidConnection: l = _p, nodeLookup: u }) {
	let d = a === "target", f = t ? o.querySelector(`.${s}-flow__handle[data-id="${c}-${t?.nodeId}-${t?.id}-${t?.type}"]`) : null, { x: p, y: m } = hf(e), h = o.elementFromPoint(p, m), g = h?.classList.contains(`${s}-flow__handle`) ? h : f, _ = {
		handleDomNode: g,
		isValid: !1,
		connection: null,
		toHandle: null
	};
	if (g) {
		let e = hp(void 0, g), t = g.getAttribute("data-nodeid"), a = g.getAttribute("data-handleid"), o = g.classList.contains("connectable"), s = g.classList.contains("connectableend");
		if (!t || !e) return _;
		let c = {
			source: d ? t : r,
			sourceHandle: d ? a : i,
			target: d ? r : t,
			targetHandle: d ? i : a
		};
		_.connection = c, _.isValid = o && s && (n === dd.Strict ? d && e === "source" || !d && e === "target" : t !== r || a !== i) && l(c), _.toHandle = mp(t, e, a, u, n, !0);
	}
	return _;
}
var bp = {
	onPointerDown: vp,
	isValid: yp
};
function xp({ domNode: e, panZoom: t, getTransform: n, getViewScale: r }) {
	let i = ks(e);
	function a({ translateExtent: e, width: a, height: o, zoomStep: s = 1, pannable: c = !0, zoomable: l = !0, inversePan: u = !1 }) {
		let d = (e) => {
			if (e.sourceEvent.type !== "wheel" || !t) return;
			let r = n(), i = e.sourceEvent.ctrlKey && $d() ? 10 : 1, a = -e.sourceEvent.deltaY * (e.sourceEvent.deltaMode === 1 ? .05 : e.sourceEvent.deltaMode ? 1 : .002) * s, o = r[2] * 2 ** (a * i);
			t.scaleTo(o);
		}, f = [0, 0], p = od().on("start", (e) => {
			(e.sourceEvent.type === "mousedown" || e.sourceEvent.type === "touchstart") && (f = [e.sourceEvent.clientX ?? e.sourceEvent.touches[0].clientX, e.sourceEvent.clientY ?? e.sourceEvent.touches[0].clientY]);
		}).on("zoom", c ? (i) => {
			let s = n();
			if (i.sourceEvent.type !== "mousemove" && i.sourceEvent.type !== "touchmove" || !t) return;
			let c = [i.sourceEvent.clientX ?? i.sourceEvent.touches[0].clientX, i.sourceEvent.clientY ?? i.sourceEvent.touches[0].clientY], l = [c[0] - f[0], c[1] - f[1]];
			f = c;
			let d = r() * Math.max(s[2], Math.log(s[2])) * (u ? -1 : 1), p = {
				x: s[0] - l[0] * d,
				y: s[1] - l[1] * d
			}, m = [[0, 0], [a, o]];
			t.setViewportConstrained({
				x: p.x,
				y: p.y,
				zoom: s[2]
			}, m, e);
		} : null).on("zoom.wheel", l ? d : null);
		i.call(p, {});
	}
	function o() {
		i.on("zoom", null);
	}
	return {
		update: a,
		destroy: o,
		pointer: js
	};
}
var Sp = (e) => ({
	x: e.x,
	y: e.y,
	zoom: e.k
}), Cp = ({ x: e, y: t, zoom: n }) => Xu.translate(e, t).scale(n), wp = (e, t) => e.target.closest(`.${t}`), Tp = (e, t) => t === 2 && Array.isArray(e) && e.includes(2), Ep = (e) => ((e *= 2) <= 1 ? e * e * e : (e -= 2) * e * e + 2) / 2, Dp = (e, t = 0, n = Ep, r = () => {}) => {
	let i = typeof t == "number" && t > 0;
	return i || r(), i ? e.transition().duration(t).ease(n).on("end", r) : e;
}, Op = (e) => {
	let t = e.ctrlKey && $d() ? 10 : 1;
	return -e.deltaY * (e.deltaMode === 1 ? .05 : e.deltaMode ? 1 : .002) * t;
};
function kp({ zoomPanValues: e, noWheelClassName: t, d3Selection: n, d3Zoom: r, panOnScrollMode: i, panOnScrollSpeed: a, zoomOnPinch: o, onPanZoomStart: s, onPanZoom: c, onPanZoomEnd: l }) {
	return (u) => {
		if (wp(u, t)) return u.ctrlKey && u.preventDefault(), !1;
		u.preventDefault(), u.stopImmediatePropagation();
		let d = n.property("__zoom").k || 1;
		if (u.ctrlKey && o) {
			let e = js(u), t = d * 2 ** Op(u);
			r.scaleTo(n, t, e, u);
			return;
		}
		let f = u.deltaMode === 1 ? 20 : 1, p = i === fd.Vertical ? 0 : u.deltaX * f, m = i === fd.Horizontal ? 0 : u.deltaY * f;
		!$d() && u.shiftKey && i !== fd.Vertical && (p = u.deltaY * f, m = 0), r.translateBy(n, -(p / d) * a, -(m / d) * a, { internal: !0 });
		let h = Sp(n.property("__zoom"));
		clearTimeout(e.panScrollTimeout), e.isPanScrolling ? c?.(u, h) : (e.isPanScrolling = !0, s?.(u, h)), e.panScrollTimeout = setTimeout(() => {
			l?.(u, h), e.isPanScrolling = !1;
		}, 150);
	};
}
function Ap({ noWheelClassName: e, preventScrolling: t, d3ZoomHandler: n }) {
	return function(r, i) {
		let a = r.type === "wheel", o = !t && a && !r.ctrlKey, s = wp(r, e);
		if (r.ctrlKey && a && s && r.preventDefault(), o || s) return null;
		r.preventDefault(), n.call(this, r, i);
	};
}
function jp({ zoomPanValues: e, onDraggingChange: t, onPanZoomStart: n }) {
	return (r) => {
		if (r.sourceEvent?.internal) return;
		let i = Sp(r.transform);
		e.mouseButton = r.sourceEvent?.button || 0, e.isZoomingOrPanning = !0, e.prevViewport = i, r.sourceEvent?.type === "mousedown" && t(!0), n && n?.(r.sourceEvent, i);
	};
}
function Mp({ zoomPanValues: e, panOnDrag: t, onPaneContextMenu: n, onTransformChange: r, onPanZoom: i }) {
	return (a) => {
		e.usedRightMouseButton = !!(n && Tp(t, e.mouseButton ?? 0)), a.sourceEvent?.sync || r([
			a.transform.x,
			a.transform.y,
			a.transform.k
		]), i && !a.sourceEvent?.internal && i?.(a.sourceEvent, Sp(a.transform));
	};
}
function Np({ zoomPanValues: e, panOnDrag: t, panOnScroll: n, onDraggingChange: r, onPanZoomEnd: i, onPaneContextMenu: a }) {
	return (o) => {
		if (!o.sourceEvent?.internal && (e.isZoomingOrPanning = !1, a && Tp(t, e.mouseButton ?? 0) && !e.usedRightMouseButton && o.sourceEvent && a(o.sourceEvent), e.usedRightMouseButton = !1, r(!1), i)) {
			let t = Sp(o.transform);
			e.prevViewport = t, clearTimeout(e.timerId), e.timerId = setTimeout(() => {
				i?.(o.sourceEvent, t);
			}, n ? 150 : 0);
		}
	};
}
function Pp({ panActivationKeyPressed: e, zoomActivationKeyPressed: t, zoomOnScroll: n, zoomOnPinch: r, panOnDrag: i, panOnScroll: a, zoomOnDoubleClick: o, userSelectionActive: s, noWheelClassName: c, noPanClassName: l, lib: u, connectionInProgress: d }) {
	return (f) => {
		let p = t || n, m = r && f.ctrlKey, h = f.type === "wheel";
		if (f.button === 1 && f.type === "mousedown" && (wp(f, `${u}-flow__node`) || wp(f, `${u}-flow__edge`) || wp(f, `${u}-flow__selection`) || wp(f, `${u}-flow__nodesselection`))) return !0;
		if (!i && !p && !a && !o && !r || s || d && !h || wp(f, c) && h || wp(f, l) && (!h || a && h && !t) || !r && f.ctrlKey && h) return !1;
		if (!r && f.type === "touchstart" && f.touches?.length > 1) return f.preventDefault(), !1;
		if (!p && !a && !m && h || !i && (f.type === "mousedown" || f.type === "touchstart") || Array.isArray(i) && !i.includes(f.button) && f.type === "mousedown") return !1;
		let g = Array.isArray(i) && i.includes(f.button) || !f.button || f.button <= 1;
		return (!f.ctrlKey || h || e) && g;
	};
}
function Fp({ domNode: e, minZoom: t, maxZoom: n, translateExtent: r, viewport: i, onPanZoom: a, onPanZoomStart: o, onPanZoomEnd: s, onDraggingChange: c }) {
	let l = {
		isZoomingOrPanning: !1,
		usedRightMouseButton: !1,
		prevViewport: {},
		mouseButton: 0,
		timerId: void 0,
		panScrollTimeout: void 0,
		isPanScrolling: !1
	}, u = e.getBoundingClientRect(), d = [[0, 0], [u.width, u.height]];
	(typeof ResizeObserver < "u" ? new ResizeObserver((e) => {
		let t = e[0];
		t && (d = [[0, 0], [t.contentRect.width, t.contentRect.height]]);
	}) : null)?.observe(e);
	let f = od().extent(() => d).scaleExtent([t, n]).translateExtent(r), p = ks(e).call(f);
	y({
		x: i.x,
		y: i.y,
		zoom: Ad(i.zoom, t, n)
	}, [[0, 0], [u.width, u.height]], r);
	let m = p.on("wheel.zoom"), h = p.on("dblclick.zoom");
	f.wheelDelta(Op);
	async function g(e, t) {
		return p ? new Promise((n) => {
			f?.interpolate(t?.interpolate === "linear" ? qc : sl).transform(Dp(p, t?.duration, t?.ease, () => n(!0)), e);
		}) : !1;
	}
	function _({ noWheelClassName: e, noPanClassName: t, onPaneContextMenu: n, userSelectionActive: r, panOnScroll: i, panOnDrag: u, panOnScrollMode: d, panOnScrollSpeed: g, preventScrolling: _, zoomOnPinch: y, zoomOnScroll: b, zoomOnDoubleClick: x, panActivationKeyPressed: S = !1, zoomActivationKeyPressed: C, lib: w, onTransformChange: T, connectionInProgress: ee, paneClickDistance: E, selectionOnDrag: D }) {
		r && !l.isZoomingOrPanning && v();
		let te = i && !C && !r;
		f.clickDistance(D ? Infinity : !Wd(E) || E < 0 ? 0 : E);
		let ne = te ? kp({
			zoomPanValues: l,
			noWheelClassName: e,
			d3Selection: p,
			d3Zoom: f,
			panOnScrollMode: d,
			panOnScrollSpeed: g,
			zoomOnPinch: y,
			onPanZoomStart: o,
			onPanZoom: a,
			onPanZoomEnd: s
		}) : Ap({
			noWheelClassName: e,
			preventScrolling: _,
			d3ZoomHandler: m
		});
		p.on("wheel.zoom", ne, { passive: !1 });
		let re = jp({
			zoomPanValues: l,
			onDraggingChange: c,
			onPanZoomStart: o
		});
		f.on("start", re);
		let ie = Mp({
			zoomPanValues: l,
			panOnDrag: u,
			onPaneContextMenu: !!n,
			onPanZoom: a,
			onTransformChange: T
		});
		f.on("zoom", ie);
		let ae = Np({
			zoomPanValues: l,
			panOnDrag: u,
			panOnScroll: i,
			onPaneContextMenu: n,
			onPanZoomEnd: s,
			onDraggingChange: c
		});
		f.on("end", ae);
		let oe = Pp({
			panActivationKeyPressed: S,
			zoomActivationKeyPressed: C,
			panOnDrag: u,
			zoomOnScroll: b,
			panOnScroll: i,
			zoomOnDoubleClick: x,
			zoomOnPinch: y,
			userSelectionActive: r,
			noPanClassName: t,
			noWheelClassName: e,
			lib: w,
			connectionInProgress: ee
		});
		f.filter(oe), x ? p.on("dblclick.zoom", h) : p.on("dblclick.zoom", null);
	}
	function v() {
		f.on("zoom", null);
	}
	async function y(e, t, n) {
		let r = Cp(e), i = f?.constrain()(r, t, n);
		return i && await g(i), i;
	}
	async function b(e, t) {
		let n = Cp(e);
		return await g(n, t), n;
	}
	function x(e) {
		if (p) {
			let t = Cp(e), n = p.property("__zoom");
			(n.k !== e.zoom || n.x !== e.x || n.y !== e.y) && f?.transform(p, t, null, { sync: !0 });
		}
	}
	function S() {
		let e = p ? Zu(p.node()) : {
			x: 0,
			y: 0,
			k: 1
		};
		return {
			x: e.x,
			y: e.y,
			zoom: e.k
		};
	}
	async function C(e, t) {
		return p ? new Promise((n) => {
			f?.interpolate(t?.interpolate === "linear" ? qc : sl).scaleTo(Dp(p, t?.duration, t?.ease, () => n(!0)), e);
		}) : !1;
	}
	async function w(e, t) {
		return p ? new Promise((n) => {
			f?.interpolate(t?.interpolate === "linear" ? qc : sl).scaleBy(Dp(p, t?.duration, t?.ease, () => n(!0)), e);
		}) : !1;
	}
	function T(e) {
		f?.scaleExtent(e);
	}
	function ee(e) {
		f?.translateExtent(e);
	}
	function E(e) {
		let t = !Wd(e) || e < 0 ? 0 : e;
		f?.clickDistance(t);
	}
	return {
		update: _,
		destroy: v,
		setViewport: b,
		setViewportConstrained: y,
		getViewport: S,
		scaleTo: C,
		scaleBy: w,
		setScaleExtent: T,
		setTranslateExtent: ee,
		syncViewport: x,
		setClickDistance: E
	};
}
var Ip;
(function(e) {
	e.Line = "line", e.Handle = "handle";
})(Ip ||= {});
// node_modules/@xyflow/svelte/dist/lib/utils/edges.js
var Lp = Gd("Svelte Flow", "https://svelteflow.dev/");
function Rp(e, t, n = {}) {
	return Ef(e, t, {
		...n,
		onError: n.onError ?? Lp
	});
}
// node_modules/@xyflow/svelte/dist/lib/store/context.js
function zp() {
	let e = {};
	return [(t) => {
		if (t && !tt(e)) throw Error(t);
		return $e(e);
	}, (t) => et(e, t)];
}
var [Bp, Vp] = zp(), [Hp, Up] = zp(), [Wp, Gp] = zp(), Kp = /* @__PURE__ */ new Set([
	"$$slots",
	"$$events",
	"$$legacy",
	"id",
	"type",
	"position",
	"style",
	"class",
	"isConnectable",
	"isConnectableStart",
	"isConnectableEnd",
	"isValidConnection",
	"onconnect",
	"ondisconnect",
	"children"
]), qp = /* @__PURE__ */ q("<div><!></div>");
function Jp(e, t) {
	M(t, !0);
	let n = Q(t, "id", 3, null), r = Q(t, "type", 3, "source"), i = Q(t, "position", 19, () => $.Top), a = Q(t, "isConnectableStart", 3, !0), o = Q(t, "isConnectableEnd", 3, !0), s = /* @__PURE__ */ va(t, Kp), c = Bp("Handle must be used within a Custom Node component"), l = Hp("Handle must be used within a Custom Node component"), u = /* @__PURE__ */ P(() => r() === "target"), d = /* @__PURE__ */ P(() => t.isConnectable === void 0 ? l.value : t.isConnectable), p = Mm(), m = /* @__PURE__ */ P(() => p.ariaLabelConfig), h = null;
	jn(() => {
		if (t.onconnect || t.ondisconnect) {
			p.edges;
			let e = p.connectionLookup.get(`${c}-${r()}${n() ? `-${n()}` : ""}`);
			if (h && !of(e, h)) {
				let n = e ?? /* @__PURE__ */ new Map();
				sf(h, n, t.ondisconnect), sf(n, h, t.onconnect);
			}
			h = new Map(e);
		}
	});
	let g = /* @__PURE__ */ P(() => {
		if (!p.connection.inProgress) return [
			!1,
			!1,
			!1,
			!1,
			null
		];
		let { fromHandle: e, toHandle: t, isValid: i } = p.connection, a = e && e.nodeId === c && e.type === r() && e.id === n(), o = t && t.nodeId === c && t.type === r() && t.id === n();
		return [
			!0,
			a,
			o,
			p.connectionMode === dd.Strict ? e?.type !== r() : c !== e?.nodeId || n() !== e?.id,
			o && i
		];
	}), v = /* @__PURE__ */ P(() => _(G(g), 5)), y = /* @__PURE__ */ P(() => G(v)[0]), b = /* @__PURE__ */ P(() => G(v)[1]), x = /* @__PURE__ */ P(() => G(v)[2]), S = /* @__PURE__ */ P(() => G(v)[3]), C = /* @__PURE__ */ P(() => G(v)[4]);
	function w(e) {
		let t = p.onbeforeconnect ? p.onbeforeconnect(e) : e;
		t && (p.addEdge(t), p.onconnect?.(e));
	}
	function T(e) {
		let r = mf(e);
		e.currentTarget && (r && e.button === 0 || !r) && bp.onPointerDown(e, {
			handleId: n(),
			nodeId: c,
			isTarget: G(u),
			connectionRadius: p.connectionRadius,
			domNode: p.domNode,
			nodeLookup: p.nodeLookup,
			connectionMode: p.connectionMode,
			lib: "svelte",
			autoPanOnConnect: p.autoPanOnConnect,
			autoPanSpeed: p.autoPanSpeed,
			flowId: p.flowId,
			isValidConnection: t.isValidConnection || ((...e) => p.isValidConnection?.(...e) ?? !0),
			updateConnection: p.updateConnection,
			cancelConnection: p.cancelConnection,
			panBy: p.panBy,
			onConnect: w,
			onConnectStart: p.onconnectstart,
			onConnectEnd: (...e) => p.onconnectend?.(...e),
			getTransform: () => [
				p.viewport.x,
				p.viewport.y,
				p.viewport.zoom
			],
			getFromHandle: () => p.connection.fromHandle,
			dragThreshold: p.connectionDragThreshold,
			handleDomNode: e.currentTarget
		});
	}
	function ee(e) {
		if (!c || !p.clickConnectStartHandle && !a()) return;
		if (!p.clickConnectStartHandle) {
			p.onclickconnectstart?.(e, {
				nodeId: c,
				handleId: n(),
				handleType: r()
			}), p.clickConnectStartHandle = {
				nodeId: c,
				type: r(),
				id: n()
			};
			return;
		}
		let i = df(e.target), o = t.isValidConnection ?? p.isValidConnection, { connectionMode: s, clickConnectStartHandle: l, flowId: u, nodeLookup: d } = p, { connection: f, isValid: m } = bp.isValid(e, {
			handle: {
				nodeId: c,
				id: n(),
				type: r()
			},
			connectionMode: s,
			fromNodeId: l.nodeId,
			fromHandleId: l.id ?? null,
			fromType: l.type,
			isValidConnection: o,
			flowId: u,
			doc: i,
			lib: "svelte",
			nodeLookup: d
		});
		m && f && w(f);
		let h = structuredClone(Je(p.connection));
		delete h.inProgress, h.toPosition = h.toHandle ? h.toHandle.position : null, p.onclickconnectend?.(e, h), p.clickConnectStartHandle = null;
	}
	var E = qp(), D = () => {};
	na(E, () => ({
		"data-handleid": n(),
		"data-nodeid": c,
		"data-handlepos": i(),
		"data-id": `${p.flowId ?? ""}-${c ?? ""}-${n() ?? "null" ?? ""}-${r() ?? ""}`,
		class: [
			"svelte-flow__handle",
			`svelte-flow__handle-${i()}`,
			p.noDragClass,
			p.noPanClass,
			i(),
			t.class
		],
		onmousedown: T,
		ontouchstart: T,
		onclick: p.clickConnect ? ee : void 0,
		onkeypress: D,
		style: t.style,
		role: "button",
		"aria-label": G(m)["handle.ariaLabel"],
		tabindex: "-1",
		...s,
		[Ui]: {
			valid: G(C),
			connectingto: G(x),
			connectingfrom: G(b),
			source: !G(u),
			target: G(u),
			connectablestart: a(),
			connectableend: o(),
			connectable: G(d),
			connectionindicator: G(d) && (!G(y) || G(S)) && (G(y) || p.clickConnectStartHandle ? o() : a())
		}
	})), bi(R(E), () => t.children ?? f), A(E), J(e, E), N();
}
// node_modules/@xyflow/svelte/dist/lib/components/nodes/DefaultNode.svelte
var Yp = /* @__PURE__ */ q("<!> <!>", 1);
function Xp(e, t) {
	M(t, !0);
	let n = Q(t, "targetPosition", 19, () => $.Top), r = Q(t, "sourcePosition", 19, () => $.Bottom);
	var i = Yp(), a = z(i);
	Jp(a, {
		type: "target",
		get position() {
			return n();
		}
	});
	var o = V(a);
	Jp(V(o), {
		type: "source",
		get position() {
			return r();
		}
	}), H(() => Y(o, ` ${t.data?.label ?? ""} `)), J(e, i), N();
}
// node_modules/@xyflow/svelte/dist/lib/components/nodes/InputNode.svelte
var Zp = /* @__PURE__ */ q(" <!>", 1);
function Qp(e, t) {
	M(t, !0);
	let n = Q(t, "data", 19, () => ({ label: "Node" })), r = Q(t, "sourcePosition", 19, () => $.Bottom);
	De();
	var i = Zp(), a = z(i);
	Jp(V(a), {
		type: "source",
		get position() {
			return r();
		}
	}), H(() => Y(a, `${n()?.label ?? ""} `)), J(e, i), N();
}
// node_modules/@xyflow/svelte/dist/lib/components/nodes/OutputNode.svelte
var $p = /* @__PURE__ */ q(" <!>", 1);
function em(e, t) {
	M(t, !0);
	let n = Q(t, "data", 19, () => ({ label: "Node" })), r = Q(t, "targetPosition", 19, () => $.Top);
	De();
	var i = $p(), a = z(i);
	Jp(V(a), {
		type: "target",
		get position() {
			return r();
		}
	}), H(() => Y(a, `${n()?.label ?? ""} `)), J(e, i), N();
}
// node_modules/@xyflow/svelte/dist/lib/components/nodes/GroupNode.svelte
function tm(e, t) {}
// node_modules/@xyflow/svelte/dist/lib/actions/portal/portal.svelte.js
function nm(e, t, n) {
	if (!n || !t) return;
	let r = n === "root" ? t : t.querySelector(`.svelte-flow__${n}`);
	r && r.appendChild(e);
}
function rm(e, t) {
	let n = /* @__PURE__ */ P(Mm), r = /* @__PURE__ */ P(() => G(n).domNode), i;
	return G(r) ? nm(e, G(r), t) : i = Mn(() => {
		kn(() => {
			nm(e, G(r), t), i?.();
		});
	}), {
		async update(t) {
			nm(e, G(r), t);
		},
		destroy() {
			e.parentNode && e.parentNode.removeChild(e), i?.();
		}
	};
}
// node_modules/@xyflow/svelte/dist/lib/actions/portal/utils.svelte.js
function im() {
	let e = /* @__PURE__ */ I(typeof window > "u");
	if (G(e)) {
		let t = Mn(() => {
			kn(() => {
				L(e, !1), t?.();
			});
		});
	}
	return { get value() {
		return G(e);
	} };
}
// node_modules/@xyflow/svelte/dist/lib/utils/index.js
var am = (e) => yd(e), om = (e) => vd(e);
function sm(e) {
	return e === void 0 ? void 0 : `${e}px`;
}
var cm = {
	ArrowUp: {
		x: 0,
		y: -1
	},
	ArrowDown: {
		x: 0,
		y: 1
	},
	ArrowLeft: {
		x: -1,
		y: 0
	},
	ArrowRight: {
		x: 1,
		y: 0
	}
}, lm = /* @__PURE__ */ new Set([
	"$$slots",
	"$$events",
	"$$legacy",
	"x",
	"y",
	"width",
	"height",
	"selectEdgeOnClick",
	"transparent",
	"class",
	"children"
]), um = /* @__PURE__ */ q("<div><!></div>");
function dm(e, t) {
	M(t, !0);
	let n = Q(t, "x", 3, 0), r = Q(t, "y", 3, 0), i = Q(t, "selectEdgeOnClick", 3, !1), a = Q(t, "transparent", 3, !1), o = /* @__PURE__ */ va(t, lm), s = Mm(), c = Wp("EdgeLabel must be used within a Custom Edge component"), l = /* @__PURE__ */ P(() => s.visible.edges.get(c)?.zIndex);
	var u = um(), d = () => {
		i() && c && s.handleEdgeSelection(c);
	};
	na(u, (e, s, c) => ({
		class: [
			"svelte-flow__edge-label",
			{ transparent: a() },
			t.class
		],
		tabindex: "-1",
		onclick: d,
		...o,
		[Wi]: {
			display: e,
			cursor: i() ? "pointer" : void 0,
			transform: `translate(-50%, -50%) translate(${n() ?? ""}px,${r() ?? ""}px)`,
			"pointer-events": "all",
			width: s,
			height: c,
			"z-index": G(l)
		}
	}), [
		() => im().value ? "none" : void 0,
		() => sm(t.width),
		() => sm(t.height)
	], void 0, void 0, "svelte-1wg91mu"), bi(R(u), () => t.children ?? f), A(u), Si(u, (e, t) => rm?.(e, t), () => "edge-labels"), J(e, u), N();
}
// node_modules/@xyflow/svelte/dist/lib/components/edges/BaseEdge.svelte
var fm = /* @__PURE__ */ new Set([
	"$$slots",
	"$$events",
	"$$legacy",
	"id",
	"path",
	"label",
	"labelX",
	"labelY",
	"labelStyle",
	"markerStart",
	"markerEnd",
	"style",
	"interactionWidth",
	"class"
]), pm = /* @__PURE__ */ Xr("<path></path>"), mm = /* @__PURE__ */ Xr("<path fill=\"none\"></path><!><!>", 1);
function hm(e, t) {
	let n = Q(t, "interactionWidth", 3, 20), r = /* @__PURE__ */ va(t, fm);
	var i = mm(), a = z(i), o = V(a), s = (e) => {
		var i = pm();
		na(i, () => ({
			d: t.path,
			"stroke-opacity": 0,
			"stroke-width": n(),
			fill: "none",
			class: "svelte-flow__edge-interaction",
			...r
		})), J(e, i);
	};
	X(o, (e) => {
		n() > 0 && e(s);
	});
	var c = V(o), l = (e) => {
		dm(e, {
			get x() {
				return t.labelX;
			},
			get y() {
				return t.labelY;
			},
			get style() {
				return t.labelStyle;
			},
			selectEdgeOnClick: !0,
			children: (e, n) => {
				De();
				var r = Zr();
				H(() => Y(r, t.label)), J(e, r);
			},
			$$slots: { default: !0 }
		});
	};
	X(c, (e) => {
		t.label && e(l);
	}), H(() => {
		Z(a, "id", t.id), Z(a, "d", t.path), Mi(a, 0, Ei(["svelte-flow__edge-path", t.class])), Z(a, "marker-start", t.markerStart), Z(a, "marker-end", t.markerEnd), Pi(a, t.style);
	}), J(e, i);
}
// node_modules/@xyflow/svelte/dist/lib/components/edges/BezierEdge.svelte
function gm(e, t) {
	M(t, !0);
	let n = /* @__PURE__ */ P(() => bf({
		sourceX: t.sourceX,
		sourceY: t.sourceY,
		targetX: t.targetX,
		targetY: t.targetY,
		sourcePosition: t.sourcePosition,
		targetPosition: t.targetPosition,
		curvature: t.pathOptions?.curvature
	})), r = /* @__PURE__ */ P(() => _(G(n), 3)), i = /* @__PURE__ */ P(() => G(r)[0]), a = /* @__PURE__ */ P(() => G(r)[1]), o = /* @__PURE__ */ P(() => G(r)[2]);
	hm(e, {
		get id() {
			return t.id;
		},
		get path() {
			return G(i);
		},
		get labelX() {
			return G(a);
		},
		get labelY() {
			return G(o);
		},
		get label() {
			return t.label;
		},
		get labelStyle() {
			return t.labelStyle;
		},
		get markerStart() {
			return t.markerStart;
		},
		get markerEnd() {
			return t.markerEnd;
		},
		get interactionWidth() {
			return t.interactionWidth;
		},
		get style() {
			return t.style;
		}
	}), N();
}
// node_modules/@xyflow/svelte/dist/lib/components/edges/SmoothStepEdgeInternal.svelte
function _m(e, t) {
	M(t, !0);
	let n = /* @__PURE__ */ P(() => Nf({
		sourceX: t.sourceX,
		sourceY: t.sourceY,
		targetX: t.targetX,
		targetY: t.targetY,
		sourcePosition: t.sourcePosition,
		targetPosition: t.targetPosition
	})), r = /* @__PURE__ */ P(() => _(G(n), 3)), i = /* @__PURE__ */ P(() => G(r)[0]), a = /* @__PURE__ */ P(() => G(r)[1]), o = /* @__PURE__ */ P(() => G(r)[2]);
	hm(e, {
		get path() {
			return G(i);
		},
		get labelX() {
			return G(a);
		},
		get labelY() {
			return G(o);
		},
		get label() {
			return t.label;
		},
		get labelStyle() {
			return t.labelStyle;
		},
		get markerStart() {
			return t.markerStart;
		},
		get markerEnd() {
			return t.markerEnd;
		},
		get interactionWidth() {
			return t.interactionWidth;
		},
		get style() {
			return t.style;
		}
	}), N();
}
// node_modules/@xyflow/svelte/dist/lib/components/edges/StraightEdgeInternal.svelte
function vm(e, t) {
	M(t, !0);
	let n = /* @__PURE__ */ P(() => Df({
		sourceX: t.sourceX,
		sourceY: t.sourceY,
		targetX: t.targetX,
		targetY: t.targetY
	})), r = /* @__PURE__ */ P(() => _(G(n), 3)), i = /* @__PURE__ */ P(() => G(r)[0]), a = /* @__PURE__ */ P(() => G(r)[1]), o = /* @__PURE__ */ P(() => G(r)[2]);
	hm(e, {
		get path() {
			return G(i);
		},
		get labelX() {
			return G(a);
		},
		get labelY() {
			return G(o);
		},
		get label() {
			return t.label;
		},
		get labelStyle() {
			return t.labelStyle;
		},
		get markerStart() {
			return t.markerStart;
		},
		get markerEnd() {
			return t.markerEnd;
		},
		get interactionWidth() {
			return t.interactionWidth;
		},
		get style() {
			return t.style;
		}
	}), N();
}
// node_modules/@xyflow/svelte/dist/lib/components/edges/StepEdgeInternal.svelte
function ym(e, t) {
	M(t, !0);
	let n = /* @__PURE__ */ P(() => Nf({
		sourceX: t.sourceX,
		sourceY: t.sourceY,
		targetX: t.targetX,
		targetY: t.targetY,
		sourcePosition: t.sourcePosition,
		targetPosition: t.targetPosition,
		borderRadius: 0
	})), r = /* @__PURE__ */ P(() => _(G(n), 3)), i = /* @__PURE__ */ P(() => G(r)[0]), a = /* @__PURE__ */ P(() => G(r)[1]), o = /* @__PURE__ */ P(() => G(r)[2]);
	hm(e, {
		get path() {
			return G(i);
		},
		get labelX() {
			return G(a);
		},
		get labelY() {
			return G(o);
		},
		get label() {
			return t.label;
		},
		get labelStyle() {
			return t.labelStyle;
		},
		get markerStart() {
			return t.markerStart;
		},
		get markerEnd() {
			return t.markerEnd;
		},
		get interactionWidth() {
			return t.interactionWidth;
		},
		get style() {
			return t.style;
		}
	}), N();
}
// node_modules/svelte/src/reactivity/reactive-value.js
var bm = class {
	#e;
	#t;
	constructor(e, t) {
		this.#e = e, this.#t = $r(t);
	}
	get current() {
		return this.#t(), this.#e();
	}
}, xm = /\(.+\)/, Sm = /* @__PURE__ */ new Set([
	"all",
	"print",
	"screen",
	"and",
	"or",
	"not",
	"only"
]), Cm = class extends bm {
	constructor(e, t) {
		let n = xm.test(e) || e.split(/[\s,]+/).some((e) => Sm.has(e.trim())) ? e : `(${e})`, r = window.matchMedia(n);
		super(() => r.matches, (e) => zr(r, "change", e));
	}
};
// node_modules/@xyflow/svelte/dist/lib/store/visibleElements.js
function wm(e, t, n, r) {
	let i = /* @__PURE__ */ new Map();
	return wd(e, {
		x: 0,
		y: 0,
		width: n,
		height: r
	}, t, !0).forEach((e) => {
		i.set(e.id, e);
	}), i;
}
function Tm(e) {
	let { edges: t, defaultEdgeOptions: n, nodeLookup: r, previousEdges: i, connectionMode: a, onerror: o, onlyRenderVisible: s, elevateEdgesOnSelect: c, zIndexMode: l } = e, u = /* @__PURE__ */ new Map();
	for (let d of t) {
		let t = r.get(d.source), f = r.get(d.target);
		if (!t || !f || t.hidden || f.hidden) continue;
		if (s) {
			let { visibleNodes: n, transform: r, width: i, height: a } = e;
			if (Cf({
				sourceNode: t,
				targetNode: f,
				width: i,
				height: a,
				transform: r
			})) n.set(t.id, t), n.set(f.id, f);
			else continue;
		}
		let p = i.get(d.id);
		if (p && d === p.edge && t == p.sourceNode && f == p.targetNode) {
			u.set(d.id, p);
			continue;
		}
		let m = Ff({
			id: d.id,
			sourceNode: t,
			targetNode: f,
			sourceHandle: d.sourceHandle || null,
			targetHandle: d.targetHandle || null,
			connectionMode: a,
			onError: o
		});
		m && u.set(d.id, {
			...n,
			...d,
			...m,
			zIndex: Sf({
				selected: d.selected,
				zIndex: d.zIndex ?? n.zIndex,
				sourceNode: t,
				targetNode: f,
				elevateOnSelect: c,
				zIndexMode: l
			}),
			sourceNode: t,
			targetNode: f,
			edge: d
		});
	}
	return u;
}
// node_modules/@xyflow/svelte/dist/lib/store/initial-store.svelte.js
var Em = Gd("Svelte Flow", "https://svelteflow.dev/"), Dm = {
	input: Qp,
	output: em,
	default: Xp,
	group: tm
}, Om = {
	straight: vm,
	smoothstep: _m,
	default: gm,
	step: ym
};
function km(e, t, n, r, i, a) {
	return t && !n && r && i ? Qd(Cd(a, { filter: (e) => !(!e.width && !e.initialWidth || !e.height && !e.initialHeight) }), r, i, .5, 2, .1) : n ?? {
		x: 0,
		y: 0,
		zoom: 1
	};
}
function Am(e) {
	class t {
		#e = /* @__PURE__ */ P(() => e.props.id ?? "1");
		get flowId() {
			return G(this.#e);
		}
		set flowId(e) {
			L(this.#e, e);
		}
		#t = /* @__PURE__ */ I(null);
		get domNode() {
			return G(this.#t);
		}
		set domNode(e) {
			L(this.#t, e);
		}
		#n = /* @__PURE__ */ I(null);
		get panZoom() {
			return G(this.#n);
		}
		set panZoom(e) {
			L(this.#n, e);
		}
		#r = /* @__PURE__ */ I(e.width ?? 0);
		get width() {
			return G(this.#r);
		}
		set width(e) {
			L(this.#r, e);
		}
		#i = /* @__PURE__ */ I(e.height ?? 0);
		get height() {
			return G(this.#i);
		}
		set height(e) {
			L(this.#i, e);
		}
		#a = /* @__PURE__ */ I(e.props.zIndexMode ?? "basic");
		get zIndexMode() {
			return G(this.#a);
		}
		set zIndexMode(e) {
			L(this.#a, e);
		}
		#o = /* @__PURE__ */ P(() => {
			let { nodesInitialized: t } = Yf(e.nodes, this.nodeLookup, this.parentLookup, {
				nodeExtent: this.nodeExtent,
				nodeOrigin: this.nodeOrigin,
				elevateNodesOnSelect: e.props.elevateNodesOnSelect ?? !0,
				checkEquality: !0,
				zIndexMode: this.zIndexMode
			});
			return this.fitViewQueued && t && (this.fitViewOptions?.duration ? this.resolveFitView() : queueMicrotask(() => {
				this.resolveFitView();
			})), t;
		});
		get nodesInitialized() {
			return G(this.#o);
		}
		set nodesInitialized(e) {
			L(this.#o, e);
		}
		#s = /* @__PURE__ */ P(() => this.panZoom !== null);
		get viewportInitialized() {
			return G(this.#s);
		}
		set viewportInitialized(e) {
			L(this.#s, e);
		}
		#c = /* @__PURE__ */ P(() => (ip(this.connectionLookup, this.edgeLookup, e.edges), e.edges));
		get _edges() {
			return G(this.#c);
		}
		set _edges(e) {
			L(this.#c, e);
		}
		get nodes() {
			return this.nodesInitialized, e.nodes;
		}
		set nodes(t) {
			e.nodes = t;
		}
		get edges() {
			return this._edges;
		}
		set edges(t) {
			e.edges = t;
		}
		_prevSelectedNodes = [];
		_prevSelectedNodeIds = /* @__PURE__ */ new Set();
		#l = /* @__PURE__ */ P(() => {
			let e = this._prevSelectedNodeIds.size, t = /* @__PURE__ */ new Set(), n = this.nodes.filter((e) => (e.selected && (t.add(e.id), this._prevSelectedNodeIds.delete(e.id)), e.selected));
			return (e !== t.size || this._prevSelectedNodeIds.size > 0) && (this._prevSelectedNodes = n), this._prevSelectedNodeIds = t, this._prevSelectedNodes;
		});
		get selectedNodes() {
			return G(this.#l);
		}
		set selectedNodes(e) {
			L(this.#l, e);
		}
		_prevSelectedEdges = [];
		_prevSelectedEdgeIds = /* @__PURE__ */ new Set();
		#u = /* @__PURE__ */ P(() => {
			let e = this._prevSelectedEdgeIds.size, t = /* @__PURE__ */ new Set(), n = this.edges.filter((e) => (e.selected && (t.add(e.id), this._prevSelectedEdgeIds.delete(e.id)), e.selected));
			return (e !== t.size || this._prevSelectedEdgeIds.size > 0) && (this._prevSelectedEdges = n), this._prevSelectedEdgeIds = t, this._prevSelectedEdges;
		});
		get selectedEdges() {
			return G(this.#u);
		}
		set selectedEdges(e) {
			L(this.#u, e);
		}
		selectionChangeHandlers = /* @__PURE__ */ new Map();
		nodeLookup = /* @__PURE__ */ new Map();
		parentLookup = /* @__PURE__ */ new Map();
		connectionLookup = /* @__PURE__ */ new Map();
		edgeLookup = /* @__PURE__ */ new Map();
		_prevVisibleEdges = /* @__PURE__ */ new Map();
		#d = /* @__PURE__ */ P(() => {
			let { nodes: t, _edges: n, _prevVisibleEdges: r, nodeLookup: i, connectionMode: a, onerror: o, onlyRenderVisibleElements: s, defaultEdgeOptions: c, zIndexMode: l } = this, u, d, f = {
				edges: n,
				defaultEdgeOptions: c,
				previousEdges: r,
				nodeLookup: i,
				connectionMode: a,
				elevateEdgesOnSelect: e.props.elevateEdgesOnSelect ?? !0,
				zIndexMode: l,
				onerror: o
			};
			if (s) {
				let { viewport: e, width: t, height: n } = this, r = [
					e.x,
					e.y,
					e.zoom
				];
				u = wm(i, r, t, n), d = Tm({
					...f,
					onlyRenderVisible: !0,
					visibleNodes: u,
					transform: r,
					width: t,
					height: n
				});
			} else u = this.nodeLookup, d = Tm(f);
			return this._prevVisibleEdges = d, {
				nodes: u,
				edges: d
			};
		});
		get visible() {
			return G(this.#d);
		}
		set visible(e) {
			L(this.#d, e);
		}
		#f = /* @__PURE__ */ P(() => e.props.nodesDraggable ?? !0);
		get nodesDraggable() {
			return G(this.#f);
		}
		set nodesDraggable(e) {
			L(this.#f, e);
		}
		#p = /* @__PURE__ */ P(() => e.props.nodesConnectable ?? !0);
		get nodesConnectable() {
			return G(this.#p);
		}
		set nodesConnectable(e) {
			L(this.#p, e);
		}
		#m = /* @__PURE__ */ P(() => e.props.elementsSelectable ?? !0);
		get elementsSelectable() {
			return G(this.#m);
		}
		set elementsSelectable(e) {
			L(this.#m, e);
		}
		#h = /* @__PURE__ */ P(() => e.props.nodesFocusable ?? !0);
		get nodesFocusable() {
			return G(this.#h);
		}
		set nodesFocusable(e) {
			L(this.#h, e);
		}
		#g = /* @__PURE__ */ P(() => e.props.edgesFocusable ?? !0);
		get edgesFocusable() {
			return G(this.#g);
		}
		set edgesFocusable(e) {
			L(this.#g, e);
		}
		#_ = /* @__PURE__ */ P(() => e.props.disableKeyboardA11y ?? !1);
		get disableKeyboardA11y() {
			return G(this.#_);
		}
		set disableKeyboardA11y(e) {
			L(this.#_, e);
		}
		#v = /* @__PURE__ */ P(() => e.props.minZoom ?? .5);
		get minZoom() {
			return G(this.#v);
		}
		set minZoom(e) {
			L(this.#v, e);
		}
		#y = /* @__PURE__ */ P(() => e.props.maxZoom ?? 2);
		get maxZoom() {
			return G(this.#y);
		}
		set maxZoom(e) {
			L(this.#y, e);
		}
		#b = /* @__PURE__ */ P(() => e.props.nodeOrigin ?? [0, 0]);
		get nodeOrigin() {
			return G(this.#b);
		}
		set nodeOrigin(e) {
			L(this.#b, e);
		}
		#x = /* @__PURE__ */ P(() => e.props.nodeExtent ?? cd);
		get nodeExtent() {
			return G(this.#x);
		}
		set nodeExtent(e) {
			L(this.#x, e);
		}
		#S = /* @__PURE__ */ P(() => e.props.translateExtent ?? cd);
		get translateExtent() {
			return G(this.#S);
		}
		set translateExtent(e) {
			L(this.#S, e);
		}
		#C = /* @__PURE__ */ P(() => e.props.defaultEdgeOptions ?? {});
		get defaultEdgeOptions() {
			return G(this.#C);
		}
		set defaultEdgeOptions(e) {
			L(this.#C, e);
		}
		#w = /* @__PURE__ */ P(() => e.props.nodeDragThreshold ?? 1);
		get nodeDragThreshold() {
			return G(this.#w);
		}
		set nodeDragThreshold(e) {
			L(this.#w, e);
		}
		#T = /* @__PURE__ */ P(() => e.props.autoPanOnNodeDrag ?? !0);
		get autoPanOnNodeDrag() {
			return G(this.#T);
		}
		set autoPanOnNodeDrag(e) {
			L(this.#T, e);
		}
		#E = /* @__PURE__ */ P(() => e.props.autoPanOnConnect ?? !0);
		get autoPanOnConnect() {
			return G(this.#E);
		}
		set autoPanOnConnect(e) {
			L(this.#E, e);
		}
		#D = /* @__PURE__ */ P(() => e.props.autoPanOnNodeFocus ?? !0);
		get autoPanOnNodeFocus() {
			return G(this.#D);
		}
		set autoPanOnNodeFocus(e) {
			L(this.#D, e);
		}
		#O = /* @__PURE__ */ P(() => e.props.autoPanSpeed ?? 15);
		get autoPanSpeed() {
			return G(this.#O);
		}
		set autoPanSpeed(e) {
			L(this.#O, e);
		}
		#k = /* @__PURE__ */ P(() => e.props.connectionDragThreshold ?? 1);
		get connectionDragThreshold() {
			return G(this.#k);
		}
		set connectionDragThreshold(e) {
			L(this.#k, e);
		}
		fitViewQueued = e.props.fitView ?? !1;
		fitViewOptions = e.props.fitViewOptions;
		fitViewResolver = null;
		#A = /* @__PURE__ */ P(() => e.props.snapGrid ?? null);
		get snapGrid() {
			return G(this.#A);
		}
		set snapGrid(e) {
			L(this.#A, e);
		}
		#j = /* @__PURE__ */ I(!1);
		get dragging() {
			return G(this.#j);
		}
		set dragging(e) {
			L(this.#j, e);
		}
		#M = /* @__PURE__ */ I(null);
		get selectionRect() {
			return G(this.#M);
		}
		set selectionRect(e) {
			L(this.#M, e);
		}
		#N = /* @__PURE__ */ I(!1);
		get selectionKeyPressed() {
			return G(this.#N);
		}
		set selectionKeyPressed(e) {
			L(this.#N, e);
		}
		#P = /* @__PURE__ */ I(!1);
		get multiselectionKeyPressed() {
			return G(this.#P);
		}
		set multiselectionKeyPressed(e) {
			L(this.#P, e);
		}
		#F = /* @__PURE__ */ I(!1);
		get deleteKeyPressed() {
			return G(this.#F);
		}
		set deleteKeyPressed(e) {
			L(this.#F, e);
		}
		#I = /* @__PURE__ */ I(!1);
		get panActivationKeyPressed() {
			return G(this.#I);
		}
		set panActivationKeyPressed(e) {
			L(this.#I, e);
		}
		#L = /* @__PURE__ */ I(!1);
		get zoomActivationKeyPressed() {
			return G(this.#L);
		}
		set zoomActivationKeyPressed(e) {
			L(this.#L, e);
		}
		#R = /* @__PURE__ */ I(null);
		get selectionRectMode() {
			return G(this.#R);
		}
		set selectionRectMode(e) {
			L(this.#R, e);
		}
		#z = /* @__PURE__ */ I("");
		get ariaLiveMessage() {
			return G(this.#z);
		}
		set ariaLiveMessage(e) {
			L(this.#z, e);
		}
		#B = /* @__PURE__ */ P(() => e.props.selectionMode ?? pd.Partial);
		get selectionMode() {
			return G(this.#B);
		}
		set selectionMode(e) {
			L(this.#B, e);
		}
		#V = /* @__PURE__ */ P(() => ({
			...Dm,
			...e.props.nodeTypes
		}));
		get nodeTypes() {
			return G(this.#V);
		}
		set nodeTypes(e) {
			L(this.#V, e);
		}
		#H = /* @__PURE__ */ P(() => ({
			...Om,
			...e.props.edgeTypes
		}));
		get edgeTypes() {
			return G(this.#H);
		}
		set edgeTypes(e) {
			L(this.#H, e);
		}
		#U = /* @__PURE__ */ P(() => e.props.noPanClass ?? "nopan");
		get noPanClass() {
			return G(this.#U);
		}
		set noPanClass(e) {
			L(this.#U, e);
		}
		#W = /* @__PURE__ */ P(() => e.props.noDragClass ?? "nodrag");
		get noDragClass() {
			return G(this.#W);
		}
		set noDragClass(e) {
			L(this.#W, e);
		}
		#G = /* @__PURE__ */ P(() => e.props.noWheelClass ?? "nowheel");
		get noWheelClass() {
			return G(this.#G);
		}
		set noWheelClass(e) {
			L(this.#G, e);
		}
		#K = /* @__PURE__ */ P(() => af(e.props.ariaLabelConfig));
		get ariaLabelConfig() {
			return G(this.#K);
		}
		set ariaLabelConfig(e) {
			L(this.#K, e);
		}
		#q = /* @__PURE__ */ I(km(this.nodesInitialized, e.props.fitView, e.props.initialViewport, this.width, this.height, this.nodeLookup));
		get _viewport() {
			return G(this.#q);
		}
		set _viewport(e) {
			L(this.#q, e);
		}
		get viewport() {
			return e.viewport ?? this._viewport;
		}
		set viewport(t) {
			e.viewport &&= t, this._viewport = t;
		}
		#J = /* @__PURE__ */ I(md);
		get _connection() {
			return G(this.#J);
		}
		set _connection(e) {
			L(this.#J, e);
		}
		#Y = /* @__PURE__ */ P(() => this._connection.inProgress ? {
			...this._connection,
			to: qd(this._connection.to, [
				this.viewport.x,
				this.viewport.y,
				this.viewport.zoom
			])
		} : this._connection);
		get connection() {
			return G(this.#Y);
		}
		set connection(e) {
			L(this.#Y, e);
		}
		#X = /* @__PURE__ */ P(() => e.props.connectionMode ?? dd.Strict);
		get connectionMode() {
			return G(this.#X);
		}
		set connectionMode(e) {
			L(this.#X, e);
		}
		#Z = /* @__PURE__ */ P(() => e.props.connectionRadius ?? 20);
		get connectionRadius() {
			return G(this.#Z);
		}
		set connectionRadius(e) {
			L(this.#Z, e);
		}
		#Q = /* @__PURE__ */ P(() => e.props.isValidConnection ?? (() => !0));
		get isValidConnection() {
			return G(this.#Q);
		}
		set isValidConnection(e) {
			L(this.#Q, e);
		}
		#$ = /* @__PURE__ */ P(() => e.props.selectNodesOnDrag ?? !0);
		get selectNodesOnDrag() {
			return G(this.#$);
		}
		set selectNodesOnDrag(e) {
			L(this.#$, e);
		}
		#ee = /* @__PURE__ */ P(() => e.props.defaultMarkerColor === void 0 ? "#b1b1b7" : e.props.defaultMarkerColor);
		get defaultMarkerColor() {
			return G(this.#ee);
		}
		set defaultMarkerColor(e) {
			L(this.#ee, e);
		}
		#te = /* @__PURE__ */ P(() => Bf(e.edges, {
			defaultColor: this.defaultMarkerColor,
			id: this.flowId,
			defaultMarkerStart: this.defaultEdgeOptions.markerStart,
			defaultMarkerEnd: this.defaultEdgeOptions.markerEnd
		}));
		get markers() {
			return G(this.#te);
		}
		set markers(e) {
			L(this.#te, e);
		}
		#ne = /* @__PURE__ */ P(() => e.props.onlyRenderVisibleElements ?? !1);
		get onlyRenderVisibleElements() {
			return G(this.#ne);
		}
		set onlyRenderVisibleElements(e) {
			L(this.#ne, e);
		}
		#re = /* @__PURE__ */ P(() => e.props.onflowerror ?? Em);
		get onerror() {
			return G(this.#re);
		}
		set onerror(e) {
			L(this.#re, e);
		}
		#ie = /* @__PURE__ */ P(() => e.props.ondelete);
		get ondelete() {
			return G(this.#ie);
		}
		set ondelete(e) {
			L(this.#ie, e);
		}
		#ae = /* @__PURE__ */ P(() => e.props.onbeforedelete);
		get onbeforedelete() {
			return G(this.#ae);
		}
		set onbeforedelete(e) {
			L(this.#ae, e);
		}
		#oe = /* @__PURE__ */ P(() => e.props.onbeforeconnect);
		get onbeforeconnect() {
			return G(this.#oe);
		}
		set onbeforeconnect(e) {
			L(this.#oe, e);
		}
		#se = /* @__PURE__ */ P(() => e.props.onconnect);
		get onconnect() {
			return G(this.#se);
		}
		set onconnect(e) {
			L(this.#se, e);
		}
		#ce = /* @__PURE__ */ P(() => e.props.onconnectstart);
		get onconnectstart() {
			return G(this.#ce);
		}
		set onconnectstart(e) {
			L(this.#ce, e);
		}
		#le = /* @__PURE__ */ P(() => e.props.onconnectend);
		get onconnectend() {
			return G(this.#le);
		}
		set onconnectend(e) {
			L(this.#le, e);
		}
		#ue = /* @__PURE__ */ P(() => e.props.onbeforereconnect);
		get onbeforereconnect() {
			return G(this.#ue);
		}
		set onbeforereconnect(e) {
			L(this.#ue, e);
		}
		#de = /* @__PURE__ */ P(() => e.props.onreconnect);
		get onreconnect() {
			return G(this.#de);
		}
		set onreconnect(e) {
			L(this.#de, e);
		}
		#fe = /* @__PURE__ */ P(() => e.props.onreconnectstart);
		get onreconnectstart() {
			return G(this.#fe);
		}
		set onreconnectstart(e) {
			L(this.#fe, e);
		}
		#pe = /* @__PURE__ */ P(() => e.props.onreconnectend);
		get onreconnectend() {
			return G(this.#pe);
		}
		set onreconnectend(e) {
			L(this.#pe, e);
		}
		#me = /* @__PURE__ */ P(() => e.props.clickConnect ?? !0);
		get clickConnect() {
			return G(this.#me);
		}
		set clickConnect(e) {
			L(this.#me, e);
		}
		#he = /* @__PURE__ */ P(() => e.props.onclickconnectstart);
		get onclickconnectstart() {
			return G(this.#he);
		}
		set onclickconnectstart(e) {
			L(this.#he, e);
		}
		#ge = /* @__PURE__ */ P(() => e.props.onclickconnectend);
		get onclickconnectend() {
			return G(this.#ge);
		}
		set onclickconnectend(e) {
			L(this.#ge, e);
		}
		#_e = /* @__PURE__ */ I(null);
		get clickConnectStartHandle() {
			return G(this.#_e);
		}
		set clickConnectStartHandle(e) {
			L(this.#_e, e);
		}
		#ve = /* @__PURE__ */ P(() => e.props.onselectiondrag);
		get onselectiondrag() {
			return G(this.#ve);
		}
		set onselectiondrag(e) {
			L(this.#ve, e);
		}
		#ye = /* @__PURE__ */ P(() => e.props.onselectiondragstart);
		get onselectiondragstart() {
			return G(this.#ye);
		}
		set onselectiondragstart(e) {
			L(this.#ye, e);
		}
		#be = /* @__PURE__ */ P(() => e.props.onselectiondragstop);
		get onselectiondragstop() {
			return G(this.#be);
		}
		set onselectiondragstop(e) {
			L(this.#be, e);
		}
		resolveFitView = async () => {
			this.panZoom && (await Dd({
				nodes: this.nodeLookup,
				width: this.width,
				height: this.height,
				panZoom: this.panZoom,
				minZoom: this.minZoom,
				maxZoom: this.maxZoom
			}, this.fitViewOptions), this.fitViewResolver?.resolve(!0), this.fitViewQueued = !1, this.fitViewOptions = void 0, this.fitViewResolver = null);
		};
		_prefersDark = new Cm("(prefers-color-scheme: dark)", e.props.colorModeSSR === "dark");
		#xe = /* @__PURE__ */ P(() => e.props.colorMode === "system" ? this._prefersDark.current ? "dark" : "light" : e.props.colorMode ?? "light");
		get colorMode() {
			return G(this.#xe);
		}
		set colorMode(e) {
			L(this.#xe, e);
		}
		constructor() {}
		resetStoreValues() {
			this.dragging = !1, this.selectionRect = null, this.selectionRectMode = null, this.selectionKeyPressed = !1, this.multiselectionKeyPressed = !1, this.deleteKeyPressed = !1, this.panActivationKeyPressed = !1, this.zoomActivationKeyPressed = !1, this._connection = md, this.clickConnectStartHandle = null, this.viewport = e.props.initialViewport ?? {
				x: 0,
				y: 0,
				zoom: 1
			}, this.ariaLiveMessage = "";
		}
	}
	return new t();
}
// node_modules/@xyflow/svelte/dist/lib/hooks/useStore.js
var jm = sd.error001("svelte");
function Mm() {
	let e = $e(Nm);
	if (!e) throw Error(jm);
	return e.getStore();
}
// node_modules/@xyflow/svelte/dist/lib/store/index.js
var Nm = Symbol();
function Pm(e) {
	let t = Am(e);
	function n(e) {
		t.nodeTypes = {
			...Dm,
			...e
		};
	}
	function r(e) {
		t.edgeTypes = {
			...Om,
			...e
		};
	}
	function i(e) {
		t.edges = Rp(e, t.edges, { onError: t.onerror });
	}
	let a = (e, n = !1) => {
		t.nodes = t.nodes.map((r) => {
			if (t.connection.inProgress && t.connection.fromNode.id === r.id) {
				let e = t.nodeLookup.get(r.id);
				e && (t.connection = {
					...t.connection,
					from: Lf(e, t.connection.fromHandle, $.Left, !0)
				});
			}
			let i = e.get(r.id);
			return i ? {
				...r,
				position: i.position,
				dragging: n
			} : r;
		});
	};
	function o(e) {
		let { changes: n, updatedInternals: r } = tp(e, t.nodeLookup, t.parentLookup, t.domNode, t.nodeOrigin, t.nodeExtent, t.zIndexMode);
		if (!r) return;
		Kf(t.nodeLookup, t.parentLookup, {
			nodeOrigin: t.nodeOrigin,
			nodeExtent: t.nodeExtent,
			zIndexMode: t.zIndexMode
		}), t.fitViewQueued && t.resolveFitView();
		let i = /* @__PURE__ */ new Map();
		for (let e of n) {
			let n = t.nodeLookup.get(e.id)?.internals.userNode;
			if (!n) continue;
			let r = { ...n };
			switch (e.type) {
				case "dimensions": {
					let t = {
						...r.measured,
						...e.dimensions
					};
					e.setAttributes && (r.width = e.dimensions?.width ?? r.width, r.height = e.dimensions?.height ?? r.height), r.measured = t;
					break;
				}
				case "position": r.position = e.position ?? r.position;
			}
			i.set(e.id, r);
		}
		t.nodes = t.nodes.map((e) => i.get(e.id) ?? e);
	}
	function s(e) {
		let n = t.fitViewResolver ?? Promise.withResolvers();
		return t.fitViewQueued = !0, t.fitViewOptions = e, t.fitViewResolver = n, t.nodes = [...t.nodes], n.promise;
	}
	async function c(e, n, r) {
		let i = r?.zoom === void 0 ? t.maxZoom : r.zoom, a = t.panZoom;
		return a ? (await a.setViewport({
			x: t.width / 2 - e * i,
			y: t.height / 2 - n * i,
			zoom: i
		}, {
			duration: r?.duration,
			ease: r?.ease,
			interpolate: r?.interpolate
		}), !0) : !1;
	}
	async function l(e, n) {
		let r = t.panZoom;
		return r ? r.scaleBy(e, n) : !1;
	}
	async function u(e) {
		return l(1.2, e);
	}
	function d(e) {
		return l(1 / 1.2, e);
	}
	function f(e) {
		let n = t.panZoom;
		n && (n.setScaleExtent([e, t.maxZoom]), t.minZoom = e);
	}
	function p(e) {
		let n = t.panZoom;
		n && (n.setScaleExtent([t.minZoom, e]), t.maxZoom = e);
	}
	function m(e) {
		let n = t.panZoom;
		n && (n.setTranslateExtent(e), t.translateExtent = e);
	}
	function h(e, t = null) {
		let n = !1, r = e.map((e) => (!t || t.has(e.id)) && e.selected ? (n = !0, {
			...e,
			selected: !1
		}) : e);
		return [n, r];
	}
	function g(e) {
		let n = e?.nodes ? new Set(e.nodes.map((e) => e.id)) : null, [r, i] = h(t.nodes, n);
		r && (t.nodes = i);
		let a = e?.edges ? new Set(e.edges.map((e) => e.id)) : null, [o, s] = h(t.edges, a);
		o && (t.edges = s);
	}
	function _(e) {
		let n = t.multiselectionKeyPressed;
		t.nodes = t.nodes.map((t) => {
			let r = e.includes(t.id), i = n && t.selected || r;
			return !!t.selected === i ? t : {
				...t,
				selected: i
			};
		}), n || g({ nodes: [] });
	}
	function v(e) {
		let n = t.multiselectionKeyPressed;
		t.edges = t.edges.map((t) => {
			let r = e.includes(t.id), i = n && t.selected || r;
			return !!t.selected === i ? t : {
				...t,
				selected: i
			};
		}), n || g({ edges: [] });
	}
	function y(e, n, r) {
		let i = t.nodeLookup.get(e);
		i ? (t.selectionRect = null, t.selectionRectMode = null, i.selected ? (n || i.selected && t.multiselectionKeyPressed) && (g({
			nodes: [i.internals.userNode],
			edges: []
		}), requestAnimationFrame(() => r?.blur())) : _([e])) : t.onerror("012", sd.error012(e));
	}
	function b(e) {
		let n = t.edgeLookup.get(e);
		n ? (n.selectable || t.elementsSelectable && n.selectable === void 0) && (t.selectionRect = null, t.selectionRectMode = null, n.selected ? n.selected && t.multiselectionKeyPressed && g({
			nodes: [],
			edges: [n]
		}) : v([e])) : t.onerror("016", sd.error016(e));
	}
	function x(e, n) {
		let { nodeExtent: r, snapGrid: i, nodeOrigin: o, nodeLookup: s, nodesDraggable: c, onerror: l } = t, u = /* @__PURE__ */ new Map(), d = i?.[0] ?? 5, f = i?.[1] ?? 5, p = e.x * d * n, m = e.y * f * n;
		for (let e of s.values()) {
			if (!(e.selected && (e.draggable || c && e.draggable === void 0))) continue;
			let t = {
				x: e.internals.positionAbsolute.x + p,
				y: e.internals.positionAbsolute.y + m
			};
			i && (t = Kd(t, i));
			let { position: n, positionAbsolute: a } = Od({
				nodeId: e.id,
				nextPosition: t,
				nodeLookup: s,
				nodeExtent: r,
				nodeOrigin: o,
				onError: l
			});
			e.position = n, e.internals.positionAbsolute = a, u.set(e.id, e);
		}
		a(u);
	}
	function S(e) {
		return np({
			delta: e,
			panZoom: t.panZoom,
			transform: [
				t.viewport.x,
				t.viewport.y,
				t.viewport.zoom
			],
			translateExtent: t.translateExtent,
			width: t.width,
			height: t.height
		});
	}
	let C = (e) => {
		t._connection = { ...e };
	};
	function w() {
		t._connection = md;
	}
	function T() {
		t.resetStoreValues(), g();
	}
	return Object.assign(t, {
		setNodeTypes: n,
		setEdgeTypes: r,
		addEdge: i,
		updateNodePositions: a,
		updateNodeInternals: o,
		zoomIn: u,
		zoomOut: d,
		fitView: s,
		setCenter: c,
		setMinZoom: f,
		setMaxZoom: p,
		setTranslateExtent: m,
		unselectNodesAndEdges: g,
		addSelectedNodes: _,
		addSelectedEdges: v,
		handleNodeSelection: y,
		handleEdgeSelection: b,
		moveSelectedNodes: x,
		panBy: S,
		updateConnection: C,
		cancelConnection: w,
		reset: T
	});
}
// node_modules/@xyflow/svelte/dist/lib/actions/zoom/index.js
function Fm(e, t) {
	let { minZoom: n, maxZoom: r, initialViewport: i, onPanZoomStart: a, onPanZoom: o, onPanZoomEnd: s, translateExtent: c, setPanZoomInstance: l, onDraggingChange: u, onTransformChange: d } = t, f = Fp({
		domNode: e,
		minZoom: n,
		maxZoom: r,
		translateExtent: c,
		viewport: i,
		onPanZoom: o,
		onPanZoomStart: a,
		onPanZoomEnd: s,
		onDraggingChange: u
	}), p = f.getViewport();
	return (i.x !== p.x || i.y !== p.y || i.zoom !== p.zoom) && d([
		p.x,
		p.y,
		p.zoom
	]), l(f), f.update(t), { update(e) {
		f.update(e);
	} };
}
// node_modules/@xyflow/svelte/dist/lib/container/Zoom/Zoom.svelte
var Im = /* @__PURE__ */ q("<div class=\"svelte-flow__zoom svelte-flow__container\"><!></div>");
function Lm(e, t) {
	M(t, !0);
	let n = Q(t, "store", 15), r = /* @__PURE__ */ P(() => n().panActivationKeyPressed || t.panOnDrag), i = /* @__PURE__ */ P(() => n().panActivationKeyPressed || t.panOnScroll), { viewport: a } = n(), o = !1;
	kn(() => {
		!o && n().viewportInitialized && (t.oninit?.(), o = !0);
	});
	var s = Im();
	bi(R(s), () => t.children), A(s), Si(s, (e, t) => Fm?.(e, t), () => ({
		viewport: n().viewport,
		minZoom: n().minZoom,
		maxZoom: n().maxZoom,
		initialViewport: a,
		onDraggingChange: (e) => {
			n(n().dragging = e, !0);
		},
		setPanZoomInstance: (e) => {
			n(n().panZoom = e, !0);
		},
		onPanZoomStart: t.onmovestart,
		onPanZoom: t.onmove,
		onPanZoomEnd: t.onmoveend,
		zoomOnScroll: t.zoomOnScroll,
		zoomOnDoubleClick: t.zoomOnDoubleClick,
		zoomOnPinch: t.zoomOnPinch,
		panOnScroll: G(i),
		panOnDrag: G(r),
		panOnScrollSpeed: t.panOnScrollSpeed,
		panOnScrollMode: t.panOnScrollMode,
		panActivationKeyPressed: n().panActivationKeyPressed,
		zoomActivationKeyPressed: n().zoomActivationKeyPressed,
		preventScrolling: typeof t.preventScrolling != "boolean" || t.preventScrolling,
		noPanClassName: n().noPanClass,
		noWheelClassName: n().noWheelClass,
		userSelectionActive: !!n().selectionRect,
		translateExtent: n().translateExtent,
		lib: "svelte",
		paneClickDistance: t.paneClickDistance,
		selectionOnDrag: t.selectionOnDrag,
		onTransformChange: (e) => {
			n(n().viewport = {
				x: e[0],
				y: e[1],
				zoom: e[2]
			}, !0);
		},
		connectionInProgress: n().connection.inProgress
	})), J(e, s), N();
}
// node_modules/@xyflow/svelte/dist/lib/container/Pane/Pane.svelte
function Rm(e, t) {
	return (n) => {
		n.target === t && e?.(n);
	};
}
function zm(e) {
	return (t) => {
		let n = e.has(t.id);
		return !!t.selected === n ? t : {
			...t,
			selected: n
		};
	};
}
function Bm(e, t) {
	if (e.size !== t.size) return !1;
	for (let n of e) if (!t.has(n)) return !1;
	return !0;
}
var Vm = /* @__PURE__ */ q("<div><!></div>");
function Hm(e, t) {
	M(t, !0);
	let n = Q(t, "store", 15), r = Q(t, "panOnDrag", 3, !0), i = Q(t, "paneClickDistance", 3, 1), a = Q(t, "autoPanOnSelection", 3, !0), o, s = null, c = !1, l = /* @__PURE__ */ new Set(), u = /* @__PURE__ */ new Set(), d = /* @__PURE__ */ P(() => n().panActivationKeyPressed || r()), f = /* @__PURE__ */ P(() => n().selectionKeyPressed || !!n().selectionRect || t.selectionOnDrag && G(d) !== !0), p = /* @__PURE__ */ P(() => n().elementsSelectable && (G(f) || n().selectionRectMode === "user")), m = !1, h = 0, g = {
		x: 0,
		y: 0
	}, _ = !1;
	function v(e) {
		if (e.pointerType === "touch" && G(d) !== !1 && !n().selectionKeyPressed || (s = o?.getBoundingClientRect(), !s)) return;
		let r = e.target === o, i = !r && !!e.target.closest(".nokey"), a = t.selectionOnDrag && r || n().selectionKeyPressed;
		if (i || !G(f) || !a || e.button !== 0 || !e.isPrimary) return;
		e.target?.setPointerCapture?.(e.pointerId), m = !1, _ = !1;
		let { x: c, y: l } = hf(e, s), u = qd({
			x: c,
			y: l
		}, [
			n().viewport.x,
			n().viewport.y,
			n().viewport.zoom
		]);
		n(n().selectionRect = {
			width: 0,
			height: 0,
			startX: u.x,
			startY: u.y,
			x: c,
			y: l
		}, !0), r || (e.stopPropagation(), e.preventDefault());
	}
	function y(e, t) {
		if (n().selectionRect?.startX === void 0 || n().selectionRect.startY === void 0) return;
		let r = {
			x: n().selectionRect?.startX,
			y: n().selectionRect?.startY
		}, i = Jd(r, [
			n().viewport.x,
			n().viewport.y,
			n().viewport.zoom
		]), a = {
			startX: r.x,
			startY: r.y,
			x: e < i.x ? e : i.x,
			y: t < i.y ? t : i.y,
			width: Math.abs(e - i.x),
			height: Math.abs(t - i.y)
		}, o = l, s = u;
		l = new Set(wd(n().nodeLookup, a, [
			n().viewport.x,
			n().viewport.y,
			n().viewport.zoom
		], n().selectionMode === pd.Partial, !0).map((e) => e.id));
		let c = n().defaultEdgeOptions.selectable ?? !0;
		u = /* @__PURE__ */ new Set();
		for (let e of l) {
			let t = n().connectionLookup.get(e);
			if (t) for (let { edgeId: e } of t.values()) {
				let t = n().edgeLookup.get(e);
				t && (t.selectable ?? c) && u.add(e);
			}
		}
		Bm(o, l) || n(n().nodes = n().nodes.map(zm(l)), !0), Bm(s, u) || n(n().edges = n().edges.map(zm(u)), !0), n(n().selectionRectMode = "user", !0), n(n().selectionRect = a, !0);
	}
	function b() {
		if (!a() || !s) return;
		let [e, t] = Pd(g, s, n().autoPanSpeed);
		n().panBy({
			x: e,
			y: t
		}).then((e) => {
			!m || !e || y(g.x, g.y), h = requestAnimationFrame(b);
		});
	}
	function x() {
		cancelAnimationFrame(h), h = 0, _ = !1;
	}
	Sa(() => {
		typeof window < "u" && x();
	});
	function S(e) {
		if (!G(f) || !s || !n().selectionRect) return;
		let r = hf(e, s);
		g = {
			x: r.x,
			y: r.y
		};
		let a = Jd({
			x: n().selectionRect.startX,
			y: n().selectionRect.startY
		}, [
			n().viewport.x,
			n().viewport.y,
			n().viewport.zoom
		]);
		if (!m) {
			let o = n().selectionKeyPressed ? 0 : i();
			if (Math.hypot(r.x - a.x, r.y - a.y) <= o) return;
			n().unselectNodesAndEdges(), t.onselectionstart?.(e);
		}
		m = !0, _ ||= (b(), !0), y(r.x, r.y);
	}
	function C(e) {
		G(p) ? e.button === 0 && (e.target?.releasePointerCapture?.(e.pointerId), !m && e.target === o && E?.(e), n(n().selectionRect = null, !0), m && n(n().selectionRectMode = l.size > 0 ? "nodes" : null, !0), m && t.onselectionend?.(e), x()) : e.target === o && n().connection.inProgress && (c = !0);
	}
	function w(e) {
		e.target?.releasePointerCapture?.(e.pointerId), x();
	}
	let T = (e) => {
		Array.isArray(G(d)) && G(d).includes(2) ? e.preventDefault() : t.onpanecontextmenu?.({ event: e });
	}, ee = (e) => {
		m &&= (e.stopPropagation(), !1);
	};
	function E(e) {
		m || n().connection.inProgress || c ? (m = !1, c = !1) : (t.onpaneclick?.({ event: e }), n().unselectNodesAndEdges(), n(n().selectionRectMode = null, !0), n(n().selectionRect = null, !0));
	}
	var D = Vm();
	let te;
	var ne = /* @__PURE__ */ P(() => G(p) ? void 0 : Rm(E, o)), re = /* @__PURE__ */ P(() => Rm(T, o));
	bi(R(D), () => t.children), A(D), fa(D, (e) => o = e, () => o), H((e) => te = Mi(D, 1, "svelte-flow__pane svelte-flow__container", null, te, {
		draggable: e,
		dragging: n().dragging,
		selection: G(f)
	}), [() => r() === !0 || Array.isArray(r()) && r().includes(0)]), K("click", D, function(...e) {
		G(ne)?.apply(this, e);
	}), Br("pointerdown", D, function(...e) {
		(G(p) ? v : void 0)?.apply(this, e);
	}, !0), K("pointermove", D, function(...e) {
		(G(p) ? S : void 0)?.apply(this, e);
	}), K("pointerup", D, C), Br("pointercancel", D, function(...e) {
		(G(p) ? w : void 0)?.apply(this, e);
	}), K("contextmenu", D, function(...e) {
		G(re)?.apply(this, e);
	}), Br("click", D, function(...e) {
		(G(p) ? ee : void 0)?.apply(this, e);
	}, !0), J(e, D), N();
}
Vr([
	"click",
	"pointermove",
	"pointerup",
	"contextmenu"
]);
// node_modules/@xyflow/svelte/dist/lib/container/Viewport/Viewport.svelte
var Um = /* @__PURE__ */ q("<div class=\"svelte-flow__viewport xyflow__viewport svelte-flow__container\"><!></div>");
function Wm(e, t) {
	M(t, !0);
	var n = Um();
	let r;
	bi(R(n), () => t.children), A(n), H(() => r = Pi(n, "", r, { transform: `translate(${t.store.viewport.x ?? ""}px, ${t.store.viewport.y ?? ""}px) scale(${t.store.viewport.zoom ?? ""})` })), J(e, n), N();
}
// node_modules/@xyflow/svelte/dist/lib/actions/drag/index.js
function Gm(e, t) {
	let { store: n, onDrag: r, onDragStart: i, onDragStop: a, onNodeMouseDown: o } = t, s = up({
		onDrag: r,
		onDragStart: i,
		onDragStop: a,
		onNodeMouseDown: o,
		getStoreItems: () => {
			let { snapGrid: e, viewport: t } = n;
			return {
				nodes: n.nodes,
				nodeLookup: n.nodeLookup,
				edges: n.edges,
				nodeExtent: n.nodeExtent,
				snapGrid: e || [0, 0],
				snapToGrid: !!e,
				nodeOrigin: n.nodeOrigin,
				multiSelectionActive: n.multiselectionKeyPressed,
				domNode: n.domNode,
				transform: [
					t.x,
					t.y,
					t.zoom
				],
				autoPanOnNodeDrag: n.autoPanOnNodeDrag,
				nodesDraggable: n.nodesDraggable,
				selectNodesOnDrag: n.selectNodesOnDrag,
				nodeDragThreshold: n.nodeDragThreshold,
				unselectNodesAndEdges: n.unselectNodesAndEdges,
				updateNodePositions: n.updateNodePositions,
				onSelectionDrag: n.onselectiondrag,
				onSelectionDragStart: n.onselectiondragstart,
				onSelectionDragStop: n.onselectiondragstop,
				panBy: n.panBy
			};
		}
	});
	function c(e, t) {
		t.disabled ? s.destroy() : s.update({
			domNode: e,
			noDragClassName: t.noDragClass,
			handleSelector: t.handleSelector,
			nodeId: t.nodeId,
			isSelectable: t.isSelectable,
			nodeClickDistance: t.nodeClickDistance
		});
	}
	return c(e, t), {
		update(t) {
			c(e, t);
		},
		destroy() {
			s.destroy();
		}
	};
}
// node_modules/@xyflow/svelte/dist/lib/components/A11yDescriptions/A11yDescriptions.svelte
var Km = /* @__PURE__ */ q("<div aria-live=\"assertive\" aria-atomic=\"true\" class=\"a11y-live-msg svelte-13pq11u\"> </div>"), qm = /* @__PURE__ */ q("<div class=\"a11y-hidden svelte-13pq11u\"> </div> <div class=\"a11y-hidden svelte-13pq11u\"> </div> <!>", 1);
function Jm(e, t) {
	M(t, !0);
	var n = qm(), r = z(n), i = B(r, !0), a = V(r, 2), o = B(a, !0), s = V(a, 2), c = (e) => {
		var n = Km(), r = B(n, !0);
		H(() => {
			Z(n, "id", `${Zm}-${t.store.flowId}`), Y(r, t.store.ariaLiveMessage);
		}), J(e, n);
	};
	X(s, (e) => {
		t.store.disableKeyboardA11y || e(c);
	}), H(() => {
		Z(r, "id", `${Ym}-${t.store.flowId}`), Y(i, t.store.disableKeyboardA11y ? t.store.ariaLabelConfig["node.a11yDescription.default"] : t.store.ariaLabelConfig["node.a11yDescription.keyboardDisabled"]), Z(a, "id", `${Xm}-${t.store.flowId}`), Y(o, t.store.ariaLabelConfig["edge.a11yDescription.default"]);
	}), J(e, n), N();
}
// node_modules/@xyflow/svelte/dist/lib/components/A11yDescriptions/index.js
var Ym = "svelte-flow__node-desc", Xm = "svelte-flow__edge-desc", Zm = "svelte-flow__aria-live", Qm = /* @__PURE__ */ q("<div><!></div>");
function $m(e, t) {
	M(t, !0);
	let n = Q(t, "store", 15), r = /* @__PURE__ */ P(() => g(t.node.data, () => ({}), !0)), i = /* @__PURE__ */ P(() => g(t.node.selected, !1)), a = /* @__PURE__ */ P(() => t.node.draggable), o = /* @__PURE__ */ P(() => t.node.selectable), s = /* @__PURE__ */ P(() => g(t.node.deletable, !0)), c = /* @__PURE__ */ P(() => t.node.connectable), l = /* @__PURE__ */ P(() => t.node.focusable), u = /* @__PURE__ */ P(() => g(t.node.hidden, !1)), d = /* @__PURE__ */ P(() => g(t.node.dragging, !1)), f = /* @__PURE__ */ P(() => g(t.node.style, "")), p = /* @__PURE__ */ P(() => t.node.class), m = /* @__PURE__ */ P(() => g(t.node.type, "default")), h = /* @__PURE__ */ P(() => t.node.parentId), _ = /* @__PURE__ */ P(() => t.node.sourcePosition), v = /* @__PURE__ */ P(() => t.node.targetPosition), y = /* @__PURE__ */ P(() => g(t.node.measured, () => ({
		width: 0,
		height: 0
	}), !0).width), b = /* @__PURE__ */ P(() => g(t.node.measured, () => ({
		width: 0,
		height: 0
	}), !0).height), x = /* @__PURE__ */ P(() => t.node.initialWidth), S = /* @__PURE__ */ P(() => t.node.initialHeight), C = /* @__PURE__ */ P(() => t.node.width), w = /* @__PURE__ */ P(() => t.node.height), T = /* @__PURE__ */ P(() => t.node.dragHandle), ee = /* @__PURE__ */ P(() => g(t.node.internals.z, 0)), E = /* @__PURE__ */ P(() => t.node.internals.positionAbsolute.x), D = /* @__PURE__ */ P(() => t.node.internals.positionAbsolute.y), te = /* @__PURE__ */ P(() => t.node.internals.userNode), { id: ne } = t.node, re = /* @__PURE__ */ P(() => G(a) ?? n().nodesDraggable), ie = /* @__PURE__ */ P(() => G(o) ?? n().elementsSelectable), ae = /* @__PURE__ */ P(() => G(c) ?? n().nodesConnectable), oe = /* @__PURE__ */ P(() => nf(t.node)), se = /* @__PURE__ */ P(() => !!t.node.internals.handleBounds), ce = /* @__PURE__ */ P(() => G(oe) && G(se)), le = /* @__PURE__ */ P(() => G(l) ?? n().nodesFocusable);
	function ue(e) {
		return n().parentLookup.has(e);
	}
	let de = /* @__PURE__ */ P(() => ue(ne)), fe = /* @__PURE__ */ I(null), pe = null, me = G(m), he = G(_), ge = G(v), _e = /* @__PURE__ */ P(() => n().nodeTypes[G(m)] ?? Xp), ve = /* @__PURE__ */ P(() => n().ariaLabelConfig);
	Vp(ne), Up({ get value() {
		return G(ae);
	} });
	let ye = /* @__PURE__ */ P(() => {
		let e = G(y) === void 0 ? G(C) ?? G(x) : G(C), t = G(b) === void 0 ? G(w) ?? G(S) : G(w);
		if (e !== void 0 || t !== void 0 || G(f) !== void 0) return `${G(f)};${e ? `width:${sm(e)};` : ""}${t ? `height:${sm(t)};` : ""}`;
	});
	kn(() => {
		(G(m) !== me || G(_) !== he || G(v) !== ge) && G(fe) !== null && requestAnimationFrame(() => {
			G(fe) !== null && n().updateNodeInternals(/* @__PURE__ */ new Map([[ne, {
				id: ne,
				nodeElement: G(fe),
				force: !0
			}]]));
		}), me = G(m), he = G(_), ge = G(v);
	}), kn(() => {
		t.resizeObserver && (!G(ce) || G(fe) !== pe) && (pe && t.resizeObserver.unobserve(pe), G(fe) && t.resizeObserver.observe(G(fe)), pe = G(fe));
	}), Sa(() => {
		pe && t.resizeObserver?.unobserve(pe);
	});
	function be(e) {
		G(ie) && (!n().selectNodesOnDrag || !G(re) || n().nodeDragThreshold > 0) && n().handleNodeSelection(ne), t.onnodeclick?.({
			node: G(te),
			event: e
		});
	}
	function xe(e) {
		if (!(pf(e) || n().disableKeyboardA11y)) {
			if (ld.includes(e.key) && G(ie)) {
				let t = e.key === "Escape";
				n().handleNodeSelection(ne, t, G(fe));
			} else G(re) && t.node.selected && Object.prototype.hasOwnProperty.call(cm, e.key) && (e.preventDefault(), n(n().ariaLiveMessage = G(ve)["node.a11yDescription.ariaLiveMessage"]({
				direction: e.key.replace("Arrow", "").toLowerCase(),
				x: ~~t.node.internals.positionAbsolute.x,
				y: ~~t.node.internals.positionAbsolute.y
			}), !0), n().moveSelectedNodes(cm[e.key], e.shiftKey ? 4 : 1));
		}
	}
	let Se = () => {
		if (n().disableKeyboardA11y || !n().autoPanOnNodeFocus || !G(fe)?.matches(":focus-visible")) return;
		let { width: e, height: r, viewport: i } = n();
		wd(/* @__PURE__ */ new Map([[ne, t.node]]), {
			x: 0,
			y: 0,
			width: e,
			height: r
		}, [
			i.x,
			i.y,
			i.zoom
		], !0).length > 0 || n().setCenter(t.node.position.x + (t.node.measured.width ?? 0) / 2, t.node.position.y + (t.node.measured.height ?? 0) / 2, { zoom: i.zoom });
	};
	var Ce = Qr(), O = z(Ce), we = (e) => {
		var a = Qm();
		na(a, () => ({
			"data-id": ne,
			class: [
				"svelte-flow__node",
				`svelte-flow__node-${G(m)}`,
				G(p)
			],
			style: G(ye),
			onclick: be,
			onpointerenter: t.onnodepointerenter ? (e) => t.onnodepointerenter({
				node: G(te),
				event: e
			}) : void 0,
			onpointerleave: t.onnodepointerleave ? (e) => t.onnodepointerleave({
				node: G(te),
				event: e
			}) : void 0,
			onpointermove: t.onnodepointermove ? (e) => t.onnodepointermove({
				node: G(te),
				event: e
			}) : void 0,
			oncontextmenu: t.onnodecontextmenu ? (e) => t.onnodecontextmenu({
				node: G(te),
				event: e
			}) : void 0,
			onkeydown: G(le) ? xe : void 0,
			onfocus: G(le) ? Se : void 0,
			tabIndex: G(le) ? 0 : void 0,
			role: t.node.ariaRole ?? (G(le) ? "group" : void 0),
			"aria-label": t.node.ariaLabel,
			"aria-roledescription": "node",
			"aria-describedby": n().disableKeyboardA11y ? void 0 : `${Ym}-${n().flowId}`,
			...t.node.domAttributes,
			[Ui]: {
				dragging: G(d),
				selected: G(i),
				draggable: G(re),
				connectable: G(ae),
				selectable: G(ie),
				nopan: G(re),
				parent: G(de)
			},
			[Wi]: {
				"z-index": G(ee),
				transform: `translate(${G(E) ?? ""}px, ${G(D) ?? ""}px)`,
				visibility: G(oe) ? "visible" : "hidden"
			}
		})), xi(R(a), () => G(_e), (e, t) => {
			t(e, {
				get data() {
					return G(r);
				},
				get id() {
					return ne;
				},
				get selected() {
					return G(i);
				},
				get selectable() {
					return G(ie);
				},
				get deletable() {
					return G(s);
				},
				get sourcePosition() {
					return G(_);
				},
				get targetPosition() {
					return G(v);
				},
				get zIndex() {
					return G(ee);
				},
				get dragging() {
					return G(d);
				},
				get draggable() {
					return G(re);
				},
				get dragHandle() {
					return G(T);
				},
				get parentId() {
					return G(h);
				},
				get type() {
					return G(m);
				},
				get isConnectable() {
					return G(ae);
				},
				get positionAbsoluteX() {
					return G(E);
				},
				get positionAbsoluteY() {
					return G(D);
				},
				get width() {
					return G(C);
				},
				get height() {
					return G(w);
				}
			});
		}), A(a), Si(a, (e, t) => Gm?.(e, t), () => ({
			nodeId: ne,
			isSelectable: G(ie),
			disabled: !G(re),
			handleSelector: G(T),
			noDragClass: n().noDragClass,
			nodeClickDistance: t.nodeClickDistance,
			onNodeMouseDown: n().handleNodeSelection,
			onDrag: (e, n, r, i) => {
				t.onnodedrag?.({
					event: e,
					targetNode: r,
					nodes: i
				});
			},
			onDragStart: (e, n, r, i) => {
				t.onnodedragstart?.({
					event: e,
					targetNode: r,
					nodes: i
				});
			},
			onDragStop: (e, n, r, i) => {
				t.onnodedragstop?.({
					event: e,
					targetNode: r,
					nodes: i
				});
			},
			store: n()
		})), fa(a, (e) => L(fe, e), () => G(fe)), J(e, a);
	};
	X(O, (e) => {
		G(u) || e(we);
	}), J(e, Ce), N();
}
// node_modules/@xyflow/svelte/dist/lib/container/NodeRenderer/NodeRenderer.svelte
var eh = /* @__PURE__ */ q("<div class=\"svelte-flow__nodes\"></div>");
function th(e, t) {
	M(t, !0);
	let n = Q(t, "store", 15), r = typeof ResizeObserver > "u" ? null : new ResizeObserver((e) => {
		let t = /* @__PURE__ */ new Map();
		e.forEach((e) => {
			let n = e.target.getAttribute("data-id");
			t.set(n, {
				id: n,
				nodeElement: e.target,
				force: !0
			});
		}), n().updateNodeInternals(t);
	});
	Sa(() => {
		r?.disconnect();
	});
	var i = eh();
	mi(i, 21, () => n().visible.nodes.values(), (e) => e.id, (e, i) => {
		$m(e, {
			get node() {
				return G(i);
			},
			get resizeObserver() {
				return r;
			},
			get nodeClickDistance() {
				return t.nodeClickDistance;
			},
			get onnodeclick() {
				return t.onnodeclick;
			},
			get onnodepointerenter() {
				return t.onnodepointerenter;
			},
			get onnodepointermove() {
				return t.onnodepointermove;
			},
			get onnodepointerleave() {
				return t.onnodepointerleave;
			},
			get onnodedrag() {
				return t.onnodedrag;
			},
			get onnodedragstart() {
				return t.onnodedragstart;
			},
			get onnodedragstop() {
				return t.onnodedragstop;
			},
			get onnodecontextmenu() {
				return t.onnodecontextmenu;
			},
			get store() {
				return n();
			},
			set store(e) {
				n(e);
			}
		});
	}), A(i), J(e, i), N();
}
// node_modules/@xyflow/svelte/dist/lib/components/EdgeWrapper/EdgeWrapper.svelte
var nh = /* @__PURE__ */ Xr("<svg class=\"svelte-flow__edge-wrapper\"><g><!></g></svg>");
function rh(e, t) {
	M(t, !0);
	let n = /* @__PURE__ */ P(() => t.edge.id), r = /* @__PURE__ */ P(() => t.edge.source), i = /* @__PURE__ */ P(() => t.edge.target), a = /* @__PURE__ */ P(() => t.edge.sourceX), o = /* @__PURE__ */ P(() => t.edge.sourceY), s = /* @__PURE__ */ P(() => t.edge.targetX), c = /* @__PURE__ */ P(() => t.edge.targetY), l = /* @__PURE__ */ P(() => t.edge.sourcePosition), u = /* @__PURE__ */ P(() => t.edge.targetPosition), d = /* @__PURE__ */ P(() => g(t.edge.animated, !1)), f = /* @__PURE__ */ P(() => g(t.edge.selected, !1)), p = /* @__PURE__ */ P(() => t.edge.label), m = /* @__PURE__ */ P(() => t.edge.labelStyle), h = /* @__PURE__ */ P(() => g(t.edge.data, () => ({}), !0)), _ = /* @__PURE__ */ P(() => t.edge.style), v = /* @__PURE__ */ P(() => t.edge.interactionWidth), y = /* @__PURE__ */ P(() => g(t.edge.type, "default")), b = /* @__PURE__ */ P(() => t.edge.sourceHandle), x = /* @__PURE__ */ P(() => t.edge.targetHandle), S = /* @__PURE__ */ P(() => t.edge.markerStart), C = /* @__PURE__ */ P(() => t.edge.markerEnd), w = /* @__PURE__ */ P(() => t.edge.selectable), T = /* @__PURE__ */ P(() => t.edge.focusable), ee = /* @__PURE__ */ P(() => g(t.edge.deletable, !0)), E = /* @__PURE__ */ P(() => t.edge.hidden), D = /* @__PURE__ */ P(() => t.edge.zIndex), te = /* @__PURE__ */ P(() => t.edge.class), ne = /* @__PURE__ */ P(() => t.edge.ariaLabel);
	Gp(G(n));
	let re = null, ie = /* @__PURE__ */ P(() => G(w) ?? t.store.elementsSelectable), ae = /* @__PURE__ */ P(() => G(T) ?? t.store.edgesFocusable), oe = /* @__PURE__ */ P(() => t.store.edgeTypes[G(y)] ?? gm), se = /* @__PURE__ */ P(() => G(S) ? `url('#${zf(G(S), t.store.flowId)}')` : void 0), ce = /* @__PURE__ */ P(() => G(C) ? `url('#${zf(G(C), t.store.flowId)}')` : void 0);
	function le(e) {
		let r = t.store.edgeLookup.get(G(n));
		r && (G(ie) && t.store.handleEdgeSelection(G(n)), t.onedgeclick?.({
			event: e,
			edge: r
		}));
	}
	function ue(e, r) {
		let i = t.store.edgeLookup.get(G(n));
		i && r({
			event: e,
			edge: i
		});
	}
	function de(e) {
		if (!t.store.disableKeyboardA11y && ld.includes(e.key) && G(ie)) {
			let { unselectNodesAndEdges: r, addSelectedEdges: i } = t.store;
			e.key === "Escape" ? (re?.blur(), r({ edges: [t.edge] })) : i([G(n)]);
		}
	}
	var fe = Qr(), pe = z(fe), me = (e) => {
		var g = nh();
		let S;
		var C = R(g);
		na(C, () => ({
			class: ["svelte-flow__edge", G(te)],
			"data-id": G(n),
			onclick: le,
			oncontextmenu: t.onedgecontextmenu ? (e) => {
				ue(e, t.onedgecontextmenu);
			} : void 0,
			onpointerenter: t.onedgepointerenter ? (e) => {
				ue(e, t.onedgepointerenter);
			} : void 0,
			onpointerleave: t.onedgepointerleave ? (e) => {
				ue(e, t.onedgepointerleave);
			} : void 0,
			"aria-label": G(ne) === null ? void 0 : G(ne) ? G(ne) : `Edge from ${G(r)} to ${G(i)}`,
			"aria-describedby": G(ae) ? `${Xm}-${t.store.flowId}` : void 0,
			role: t.edge.ariaRole ?? (G(ae) ? "group" : "img"),
			"aria-roledescription": "edge",
			onkeydown: G(ae) ? de : void 0,
			tabindex: G(ae) ? 0 : void 0,
			...t.edge.domAttributes,
			[Ui]: {
				animated: G(d),
				selected: G(f),
				selectable: G(ie)
			}
		})), xi(R(C), () => G(oe), (e, t) => {
			t(e, {
				get id() {
					return G(n);
				},
				get source() {
					return G(r);
				},
				get target() {
					return G(i);
				},
				get sourceX() {
					return G(a);
				},
				get sourceY() {
					return G(o);
				},
				get targetX() {
					return G(s);
				},
				get targetY() {
					return G(c);
				},
				get sourcePosition() {
					return G(l);
				},
				get targetPosition() {
					return G(u);
				},
				get animated() {
					return G(d);
				},
				get selected() {
					return G(f);
				},
				get label() {
					return G(p);
				},
				get labelStyle() {
					return G(m);
				},
				get data() {
					return G(h);
				},
				get style() {
					return G(_);
				},
				get interactionWidth() {
					return G(v);
				},
				get selectable() {
					return G(ie);
				},
				get deletable() {
					return G(ee);
				},
				get type() {
					return G(y);
				},
				get sourceHandleId() {
					return G(b);
				},
				get targetHandleId() {
					return G(x);
				},
				get markerStart() {
					return G(se);
				},
				get markerEnd() {
					return G(ce);
				}
			});
		}), A(C), fa(C, (e) => re = e, () => re), A(g), H(() => S = Pi(g, "", S, { "z-index": G(D) })), J(e, g);
	};
	X(pe, (e) => {
		G(E) || e(me);
	}), J(e, fe), N();
}
// node_modules/svelte/src/internal/flags/legacy.js
Ke();
// node_modules/@xyflow/svelte/dist/lib/container/EdgeRenderer/MarkerDefinition/MarkerDefinition.svelte
var ih = /* @__PURE__ */ Xr("<defs></defs>");
function ah(e, t) {
	M(t, !1);
	let n = Mm();
	pa();
	var r = ih();
	mi(r, 5, () => n.markers, (e) => e.id, (e, t) => {
		lh(e, ba(() => G(t)));
	}), A(r), J(e, r), N();
}
// node_modules/@xyflow/svelte/dist/lib/container/EdgeRenderer/MarkerDefinition/Marker.svelte
var oh = /* @__PURE__ */ Xr("<polyline class=\"arrow\" fill=\"none\" stroke-linecap=\"round\" stroke-linejoin=\"round\" points=\"-5,-4 0,0 -5,4\"></polyline>"), sh = /* @__PURE__ */ Xr("<polyline class=\"arrowclosed\" stroke-linecap=\"round\" stroke-linejoin=\"round\" points=\"-5,-4 0,0 -5,4 -5,-4\"></polyline>"), ch = /* @__PURE__ */ Xr("<marker class=\"svelte-flow__arrowhead\" viewBox=\"-10 -10 20 20\" refX=\"0\" refY=\"0\"><!></marker>");
function lh(e, t) {
	M(t, !0);
	let n = Q(t, "width", 3, 12.5), r = Q(t, "height", 3, 12.5), i = Q(t, "markerUnits", 3, "strokeWidth"), a = Q(t, "orient", 3, "auto-start-reverse"), o = Q(t, "color", 3, "none");
	var s = ch(), c = R(s), l = (e) => {
		var n = oh();
		let r;
		H(() => {
			Z(n, "stroke-width", t.strokeWidth), r = Pi(n, "", r, { stroke: o() });
		}), J(e, n);
	}, u = (e) => {
		var n = sh();
		let r;
		H(() => {
			Z(n, "stroke-width", t.strokeWidth), r = Pi(n, "", r, {
				stroke: o(),
				fill: o()
			});
		}), J(e, n);
	};
	X(c, (e) => {
		t.type === gd.Arrow ? e(l) : t.type === gd.ArrowClosed && e(u, 1);
	}), A(s), H(() => {
		Z(s, "id", t.id), Z(s, "markerWidth", `${n()}`), Z(s, "markerHeight", `${r()}`), Z(s, "markerUnits", i()), Z(s, "orient", a());
	}), J(e, s), N();
}
// node_modules/@xyflow/svelte/dist/lib/container/EdgeRenderer/EdgeRenderer.svelte
var uh = /* @__PURE__ */ q("<div class=\"svelte-flow__edges\"><svg class=\"svelte-flow__marker\"><!></svg> <!></div>");
function dh(e, t) {
	M(t, !0);
	let n = Q(t, "store", 15);
	var r = uh(), i = R(r);
	ah(R(i), {}), A(i), mi(V(i, 2), 17, () => n().visible.edges.values(), (e) => e.id, (e, r) => {
		rh(e, {
			get edge() {
				return G(r);
			},
			get onedgeclick() {
				return t.onedgeclick;
			},
			get onedgecontextmenu() {
				return t.onedgecontextmenu;
			},
			get onedgepointerenter() {
				return t.onedgepointerenter;
			},
			get onedgepointerleave() {
				return t.onedgepointerleave;
			},
			get store() {
				return n();
			},
			set store(e) {
				n(e);
			}
		});
	}), A(r), J(e, r), N();
}
// node_modules/@xyflow/svelte/dist/lib/components/Selection/Selection.svelte
var fh = /* @__PURE__ */ q("<div class=\"svelte-flow__selection svelte-1vr3gfi\"></div>");
function ph(e, t) {
	M(t, !0);
	let n = Q(t, "x", 3, 0), r = Q(t, "y", 3, 0), i = Q(t, "width", 3, 0), a = Q(t, "height", 3, 0), o = Q(t, "isVisible", 3, !0);
	var s = Qr(), c = z(s), l = (e) => {
		var t = fh();
		let o;
		H((e, i) => o = Pi(t, "", o, {
			width: e,
			height: i,
			transform: `translate(${n()}px, ${r()}px)`
		}), [() => typeof i() == "string" ? i() : sm(i()), () => typeof a() == "string" ? a() : sm(a())]), J(e, t);
	};
	X(c, (e) => {
		o() && e(l);
	}), J(e, s), N();
}
// node_modules/@xyflow/svelte/dist/lib/components/NodeSelection/NodeSelection.svelte
var mh = /* @__PURE__ */ q("<div><!></div>");
function hh(e, t) {
	M(t, !0);
	let n = /* @__PURE__ */ I(void 0);
	kn(() => {
		t.store.disableKeyboardA11y || G(n)?.focus({ preventScroll: !0 });
	});
	let r = /* @__PURE__ */ P(() => {
		if (t.store.selectionRectMode === "nodes") {
			t.store.nodes;
			let e = Cd(t.store.nodeLookup, { filter: (e) => !!e.selected });
			if (e.width > 0 && e.height > 0) return e;
		}
		return null;
	});
	function i(e) {
		let n = t.store.nodes.filter((e) => e.selected);
		t.onselectioncontextmenu?.({
			nodes: n,
			event: e
		});
	}
	function a(e) {
		let n = t.store.nodes.filter((e) => e.selected);
		t.onselectionclick?.({
			nodes: n,
			event: e
		});
	}
	function o(e) {
		Object.prototype.hasOwnProperty.call(cm, e.key) && (e.preventDefault(), t.store.moveSelectedNodes(cm[e.key], e.shiftKey ? 4 : 1));
	}
	var s = Qr(), c = z(s), l = (e) => {
		var s = mh();
		let c;
		ph(R(s), {
			width: "100%",
			height: "100%",
			x: 0,
			y: 0
		}), A(s), Si(s, (e, t) => Gm?.(e, t), () => ({
			disabled: !1,
			store: t.store,
			onDrag: (e, n, r, i) => {
				t.onnodedrag?.({
					event: e,
					targetNode: null,
					nodes: i
				});
			},
			onDragStart: (e, n, r, i) => {
				t.onnodedragstart?.({
					event: e,
					targetNode: null,
					nodes: i
				});
			},
			onDragStop: (e, n, r, i) => {
				t.onnodedragstop?.({
					event: e,
					targetNode: null,
					nodes: i
				});
			}
		})), fa(s, (e) => L(n, e), () => G(n)), H((e, n) => {
			Mi(s, 1, Ei(["svelte-flow__selection-wrapper", t.store.noPanClass]), "svelte-sf2y5e"), Z(s, "role", t.store.disableKeyboardA11y ? void 0 : "button"), Z(s, "tabindex", t.store.disableKeyboardA11y ? void 0 : -1), c = Pi(s, "", c, {
				width: e,
				height: n,
				transform: `translate(${G(r).x ?? ""}px, ${G(r).y ?? ""}px)`
			});
		}, [() => sm(G(r).width), () => sm(G(r).height)]), K("contextmenu", s, i), K("click", s, a), K("keydown", s, function(...e) {
			(t.store.disableKeyboardA11y ? void 0 : o)?.apply(this, e);
		}), J(e, s);
	}, u = /* @__PURE__ */ P(() => t.store.selectionRectMode === "nodes" && G(r) && Wd(G(r).x) && Wd(G(r).y));
	X(c, (e) => {
		G(u) && e(l);
	}), J(e, s), N();
}
Vr([
	"contextmenu",
	"click",
	"keydown"
]);
// node_modules/@svelte-put/shortcut/src/shortcut.js
function gh(e) {
	switch (e) {
		case "none": return 0;
		case "ctrl": return 8;
		case "shift": return 4;
		case "alt": return 2;
		case "meta": return 1;
	}
}
function _h(e, t) {
	let { enabled: n = !0, trigger: r, type: i = "keydown" } = t;
	function a(t) {
		let n = Array.isArray(r) ? r : [r], i = [
			t.metaKey,
			t.altKey,
			t.shiftKey,
			t.ctrlKey
		].reduce((e, t, n) => t ? e | 1 << n : e, 0);
		for (let r of n) {
			let n = {
				preventDefault: !1,
				enabled: !0,
				...r
			}, { modifier: a, key: o, code: s, callback: c, preventDefault: l, enabled: u } = n;
			if (!o && !s && console.warn("[svelte-put/shortcut] Trigger should have either `key` or `code`, a trigger missing both was detected! Check your configuration"), u && (o || s)) {
				if (s && t.code !== s || o && t.key !== o) continue;
				if (a === null || a === !1) {
					if (i !== 0) continue;
				} else if (a !== void 0 && a?.[0]?.length > 0) {
					let e = Array.isArray(a) ? a : [a], t = !1;
					for (let n of e) if ((Array.isArray(n) ? n : [n]).reduce((e, t) => e | gh(t), 0) === i) {
						t = !0;
						break;
					}
					if (!t) continue;
				}
				l && t.preventDefault();
				let r = {
					node: e,
					trigger: n,
					originalEvent: t
				};
				e.dispatchEvent(new CustomEvent("shortcut", { detail: r })), c?.(r);
			}
		}
	}
	let o;
	return n && (o = zr(e, i, a)), {
		update: (t) => {
			let { enabled: s = !0, type: c = "keydown" } = t;
			n && (!s || i !== c) ? o?.() : !n && s && (o = zr(e, c, a)), n = s, i = c, r = t.trigger;
		},
		destroy: () => {
			o?.();
		}
	};
}
// node_modules/@xyflow/svelte/dist/lib/hooks/useSvelteFlow.svelte.js
function vh() {
	let e = /* @__PURE__ */ P(Mm), t = (t) => {
		let n = am(t) ? t : G(e).nodeLookup.get(t.id), r = n.parentId ? rf(n.position, n.measured, n.parentId, G(e).nodeLookup, G(e).nodeOrigin) : n.position;
		return Rd({
			...n,
			position: r,
			width: n.measured?.width ?? n.width,
			height: n.measured?.height ?? n.height
		});
	};
	function n(t, n, r = { replace: !1 }) {
		G(e).nodes = wr(() => G(e).nodes).map((e) => {
			if (e.id === t) {
				let t = typeof n == "function" ? n(e) : n;
				return r?.replace && am(t) ? t : {
					...e,
					...t
				};
			}
			return e;
		});
	}
	function r(t, n, r = { replace: !1 }) {
		G(e).edges = wr(() => G(e).edges).map((e) => {
			if (e.id === t) {
				let t = typeof n == "function" ? n(e) : n;
				return r.replace && om(t) ? t : {
					...e,
					...t
				};
			}
			return e;
		});
	}
	let i = (t) => G(e).nodeLookup.get(t);
	return {
		zoomIn: G(e).zoomIn,
		zoomOut: G(e).zoomOut,
		getInternalNode: i,
		getNode: (e) => i(e)?.internals.userNode,
		getNodes: (t) => t === void 0 ? G(e).nodes : yh(G(e).nodeLookup, t),
		getEdge: (t) => G(e).edgeLookup.get(t),
		getEdges: (t) => t === void 0 ? G(e).edges : yh(G(e).edgeLookup, t),
		setZoom: async (t, n) => {
			let r = G(e).panZoom;
			return r ? r.scaleTo(t, n) : !1;
		},
		getZoom: () => G(e).viewport.zoom,
		setViewport: async (t, n) => {
			let r = G(e).viewport;
			return G(e).panZoom ? (await G(e).panZoom.setViewport({
				x: t.x ?? r.x,
				y: t.y ?? r.y,
				zoom: t.zoom ?? r.zoom
			}, n), !0) : !1;
		},
		getViewport: () => Je(G(e).viewport),
		setCenter: async (t, n, r) => G(e).setCenter(t, n, r),
		fitView: (t) => G(e).fitView(t),
		fitBounds: async (t, n) => {
			if (!G(e).panZoom) return !1;
			let r = Qd(t, G(e).width, G(e).height, G(e).minZoom, G(e).maxZoom, n?.padding ?? .1);
			return await G(e).panZoom.setViewport(r, {
				duration: n?.duration,
				ease: n?.ease,
				interpolate: n?.interpolate
			}), !0;
		},
		getIntersectingNodes: (n, r = !0, i) => {
			let a = Ud(n), o = a ? n : t(n);
			return o ? (i || G(e).nodes).filter((t) => {
				let i = G(e).nodeLookup.get(t.id);
				if (!i || !a && t.id === n.id) return !1;
				let s = Rd(i), c = Hd(s, o);
				return r && c > 0 || c >= s.width * s.height || c >= o.width * o.height;
			}) : [];
		},
		isNodeIntersecting: (e, n, r = !0) => {
			let i = Ud(e) ? e : t(e);
			if (!i) return !1;
			let a = Hd(i, n);
			return r && a > 0 || a >= n.width * n.height || a >= i.width * i.height;
		},
		deleteElements: async ({ nodes: t = [], edges: n = [] }) => {
			let { nodes: r, edges: i } = await kd({
				nodesToRemove: t,
				edgesToRemove: n,
				nodes: G(e).nodes,
				edges: G(e).edges,
				onBeforeDelete: G(e).onbeforedelete
			});
			return r && (G(e).nodes = wr(() => G(e).nodes).filter((e) => !r.some(({ id: t }) => t === e.id))), i && (G(e).edges = wr(() => G(e).edges).filter((e) => !i.some(({ id: t }) => t === e.id))), (r.length > 0 || i.length > 0) && G(e).ondelete?.({
				nodes: r,
				edges: i
			}), {
				deletedNodes: r,
				deletedEdges: i
			};
		},
		screenToFlowPosition: (t, n = { snapToGrid: !0 }) => {
			if (!G(e).domNode) return t;
			let r = n.snapToGrid ? G(e).snapGrid : !1, { x: i, y: a, zoom: o } = G(e).viewport, { x: s, y: c } = G(e).domNode.getBoundingClientRect();
			return qd({
				x: t.x - s,
				y: t.y - c
			}, [
				i,
				a,
				o
			], r !== null, r || [1, 1]);
		},
		flowToScreenPosition: (t) => {
			if (!G(e).domNode) return t;
			let { x: n, y: r, zoom: i } = G(e).viewport, { x: a, y: o } = G(e).domNode.getBoundingClientRect(), s = Jd(t, [
				n,
				r,
				i
			]);
			return {
				x: s.x + a,
				y: s.y + o
			};
		},
		toObject: () => structuredClone({
			nodes: [...G(e).nodes],
			edges: [...G(e).edges],
			viewport: { ...G(e).viewport }
		}),
		updateNode: n,
		updateNodeData: (t, r, i) => {
			let a = G(e).nodeLookup.get(t)?.internals.userNode;
			if (!a) return;
			let o = typeof r == "function" ? r(a) : r;
			n(t, (e) => ({
				...e,
				data: i?.replace ? o : {
					...e.data,
					...o
				}
			}));
		},
		updateEdge: r,
		getNodesBounds: (t) => Sd(t, {
			nodeLookup: G(e).nodeLookup,
			nodeOrigin: G(e).nodeOrigin
		}),
		getHandleConnections: ({ type: t, id: n, nodeId: r }) => Array.from(G(e).connectionLookup.get(`${r}-${t}-${n ?? null}`)?.values() ?? [])
	};
}
function yh(e, t) {
	let n = [];
	for (let r of t) {
		let t = e.get(r);
		if (t) {
			let e = "internals" in t ? t.internals?.userNode : t;
			n.push(e);
		}
	}
	return n;
}
// node_modules/@xyflow/svelte/dist/lib/components/KeyHandler/KeyHandler.svelte
function bh(e, t) {
	M(t, !0);
	let n = Q(t, "store", 15), r = Q(t, "selectionKey", 3, "Shift"), i = Q(t, "multiSelectionKey", 19, () => $d() ? "Meta" : "Control"), a = Q(t, "deleteKey", 3, "Backspace"), o = Q(t, "panActivationKey", 3, " "), s = Q(t, "zoomActivationKey", 19, () => $d() ? "Meta" : "Control"), { deleteElements: c } = vh();
	function l(e) {
		return typeof e == "object" && !!e;
	}
	function u(e) {
		return l(e) && e.modifier || [];
	}
	function d(e) {
		return e == null ? "" : l(e) ? e.key : e;
	}
	function f(e, t) {
		return (Array.isArray(e) ? e : [e]).map((e) => {
			let n = d(e);
			return {
				key: n,
				modifier: u(e),
				enabled: n !== null,
				callback: t
			};
		});
	}
	function p() {
		n(n().selectionRect = null, !0), n(n().selectionKeyPressed = !1, !0), n(n().multiselectionKeyPressed = !1, !0), n(n().deleteKeyPressed = !1, !0), n(n().panActivationKeyPressed = !1, !0), n(n().zoomActivationKeyPressed = !1, !0);
	}
	function m() {
		let e = n().nodes.filter((e) => e.selected), t = n().edges.filter((e) => e.selected);
		c({
			nodes: e,
			edges: t
		});
	}
	Br("blur", un, p), Br("contextmenu", un, p), Si(un, (e, t) => _h?.(e, t), () => ({
		trigger: f(r(), () => n(n().selectionKeyPressed = !0, !0)),
		type: "keydown"
	})), Si(un, (e, t) => _h?.(e, t), () => ({
		trigger: f(r(), () => n(n().selectionKeyPressed = !1, !0)),
		type: "keyup"
	})), Si(un, (e, t) => _h?.(e, t), () => ({
		trigger: f(i(), () => {
			n(n().multiselectionKeyPressed = !0, !0);
		}),
		type: "keydown"
	})), Si(un, (e, t) => _h?.(e, t), () => ({
		trigger: f(i(), () => n(n().multiselectionKeyPressed = !1, !0)),
		type: "keyup"
	})), Si(un, (e, t) => _h?.(e, t), () => ({
		trigger: f(a(), (e) => {
			!(e.originalEvent.ctrlKey || e.originalEvent.metaKey || e.originalEvent.shiftKey) && !pf(e.originalEvent) && (n(n().deleteKeyPressed = !0, !0), m());
		}),
		type: "keydown"
	})), Si(un, (e, t) => _h?.(e, t), () => ({
		trigger: f(a(), () => n(n().deleteKeyPressed = !1, !0)),
		type: "keyup"
	})), Si(un, (e, t) => _h?.(e, t), () => ({
		trigger: f(o(), () => n(n().panActivationKeyPressed = !0, !0)),
		type: "keydown"
	})), Si(un, (e, t) => _h?.(e, t), () => ({
		trigger: f(o(), () => n(n().panActivationKeyPressed = !1, !0)),
		type: "keyup"
	})), Si(un, (e, t) => _h?.(e, t), () => ({
		trigger: f(s(), () => n(n().zoomActivationKeyPressed = !0, !0)),
		type: "keydown"
	})), Si(un, (e, t) => _h?.(e, t), () => ({
		trigger: f(s(), () => n(n().zoomActivationKeyPressed = !1, !0)),
		type: "keyup"
	})), N();
}
// node_modules/@xyflow/svelte/dist/lib/components/ConnectionLine/ConnectionLine.svelte
var xh = /* @__PURE__ */ Xr("<path fill=\"none\" class=\"svelte-flow__connection-path\"></path>"), Sh = /* @__PURE__ */ Xr("<svg class=\"svelte-flow__connectionline\"><g><!></g></svg>");
function Ch(e, t) {
	M(t, !0);
	let n = /* @__PURE__ */ P(() => {
		if (!t.store.connection.inProgress) return "";
		let e = {
			sourceX: t.store.connection.from.x,
			sourceY: t.store.connection.from.y,
			sourcePosition: t.store.connection.fromPosition,
			targetX: t.store.connection.to.x,
			targetY: t.store.connection.to.y,
			targetPosition: t.store.connection.toPosition
		};
		switch (t.type) {
			case hd.Bezier: {
				let [t] = bf(e);
				return t;
			}
			case hd.Straight: {
				let [t] = Df(e);
				return t;
			}
			case hd.Step:
			case hd.SmoothStep: {
				let [n] = Nf({
					...e,
					borderRadius: t.type === hd.Step ? 0 : void 0
				});
				return n;
			}
		}
	});
	var r = Qr(), i = z(r), a = (e) => {
		var r = Sh(), i = R(r), a = R(i), o = (e) => {
			var n = Qr();
			xi(z(n), () => t.LineComponent, (e, t) => {
				t(e, {});
			}), J(e, n);
		}, s = (e) => {
			var r = xh();
			H(() => {
				Z(r, "d", G(n)), Pi(r, t.style);
			}), J(e, r);
		};
		X(a, (e) => {
			t.LineComponent ? e(o) : e(s, -1);
		}), A(i), A(r), H((e) => {
			Z(r, "width", t.store.width), Z(r, "height", t.store.height), Pi(r, t.containerStyle), Mi(i, 0, e);
		}, [() => Ei(["svelte-flow__connection", cf(t.store.connection.isValid)])]), J(e, r);
	};
	X(i, (e) => {
		t.store.connection.inProgress && e(a);
	}), J(e, r), N();
}
// node_modules/@xyflow/svelte/dist/lib/container/Panel/Panel.svelte
var wh = /* @__PURE__ */ new Set([
	"$$slots",
	"$$events",
	"$$legacy",
	"position",
	"style",
	"class",
	"children"
]), Th = /* @__PURE__ */ q("<div><!></div>");
function Eh(e, t) {
	M(t, !0);
	let n = Q(t, "position", 3, "top-right"), r = /* @__PURE__ */ va(t, wh), i = /* @__PURE__ */ P(() => `${n()}`.split("-"));
	var a = Th();
	na(a, (e) => ({
		class: e,
		style: t.style,
		...r
	}), [() => [
		"svelte-flow__panel",
		t.class,
		...G(i)
	]]), bi(R(a), () => t.children ?? f), A(a), J(e, a), N();
}
// node_modules/@xyflow/svelte/dist/lib/components/Attribution/Attribution.svelte
var Dh = /* @__PURE__ */ q("<a target=\"_blank\" rel=\"noopener noreferrer\" aria-label=\"Svelte Flow attribution\">Svelte Flow</a>");
function Oh(e, t) {
	M(t, !0);
	let n = Q(t, "position", 3, "bottom-right"), r = "https://svelteflow.dev?utm_source=attribution";
	var i = Qr(), a = z(i), o = (e) => {
		{
			let t = /* @__PURE__ */ P(() => `Please only hide this attribution when you are subscribed to Svelte Flow Pro: ${r}`);
			Eh(e, {
				get position() {
					return n();
				},
				class: "svelte-flow__attribution",
				get "data-message"() {
					return G(t);
				},
				children: (e, t) => {
					var n = Dh();
					H(() => Z(n, "href", r)), J(e, n);
				},
				$$slots: { default: !0 }
			});
		}
	};
	X(a, (e) => {
		t.proOptions?.hideAttribution || e(o);
	}), J(e, i), N();
}
// node_modules/@xyflow/svelte/dist/lib/container/SvelteFlow/Wrapper.svelte
var kh = /* @__PURE__ */ q("<div><!></div>");
function Ah(e, t) {
	M(t, !0);
	let n = Q(t, "domNode", 15), r = Q(t, "clientWidth", 15), i = Q(t, "clientHeight", 15), a = /* @__PURE__ */ P(() => t.rest.class), o = /* @__PURE__ */ P(() => v(t.rest, /* @__PURE__ */ "id.class.nodeTypes.edgeTypes.colorMode.isValidConnection.onmove.onmovestart.onmoveend.onflowerror.ondelete.onbeforedelete.onbeforeconnect.onconnect.onconnectstart.onconnectend.onbeforereconnect.onreconnect.onreconnectstart.onreconnectend.onclickconnectstart.onclickconnectend.oninit.onselectionchange.onselectiondragstart.onselectiondrag.onselectiondragstop.onselectionstart.onselectionend.clickConnect.fitView.fitViewOptions.nodeOrigin.nodeDragThreshold.connectionDragThreshold.minZoom.maxZoom.initialViewport.connectionRadius.connectionMode.selectionMode.selectNodesOnDrag.snapGrid.defaultMarkerColor.translateExtent.nodeExtent.onlyRenderVisibleElements.autoPanOnConnect.autoPanOnNodeDrag.colorModeSSR.defaultEdgeOptions.elevateNodesOnSelect.elevateEdgesOnSelect.nodesDraggable.autoPanOnNodeFocus.nodesConnectable.elementsSelectable.nodesFocusable.edgesFocusable.disableKeyboardA11y.noDragClass.noPanClass.noWheelClass.ariaLabelConfig.autoPanSpeed.panOnScrollSpeed.zIndexMode.autoPanOnSelection".split(".")));
	function s(e) {
		e.currentTarget.scrollTo({
			top: 0,
			left: 0,
			behavior: "auto"
		}), t.rest.onscroll && t.rest.onscroll(e);
	}
	var c = kh();
	na(c, (e, n) => ({
		class: [
			"svelte-flow",
			"svelte-flow__container",
			t.colorMode,
			G(a)
		],
		"data-testid": "svelte-flow__wrapper",
		role: "application",
		onscroll: s,
		...G(o),
		[Wi]: {
			width: e,
			height: n
		}
	}), [() => sm(t.width), () => sm(t.height)], void 0, void 0, "svelte-mkap6j"), bi(R(c), () => t.children ?? f), A(c), fa(c, (e) => n(e), () => n()), ua(c, "clientHeight", i), ua(c, "clientWidth", r), J(e, c), N();
}
// node_modules/@xyflow/svelte/dist/lib/container/SvelteFlow/SvelteFlow.svelte
var jh = /* @__PURE__ */ new Set(/* @__PURE__ */ "$$slots.$$events.$$legacy.width.height.proOptions.selectionKey.deleteKey.panActivationKey.multiSelectionKey.zoomActivationKey.paneClickDistance.nodeClickDistance.onmovestart.onmoveend.onmove.oninit.onnodeclick.onnodecontextmenu.onnodedrag.onnodedragstart.onnodedragstop.onnodepointerenter.onnodepointermove.onnodepointerleave.onselectionclick.onselectioncontextmenu.onselectionstart.onselectionend.onedgeclick.onedgecontextmenu.onedgepointerenter.onedgepointerleave.onpaneclick.onpanecontextmenu.panOnScrollMode.preventScrolling.zoomOnScroll.zoomOnDoubleClick.zoomOnPinch.panOnScroll.panOnScrollSpeed.panOnDrag.selectionOnDrag.autoPanOnSelection.connectionLineComponent.connectionLineStyle.connectionLineContainerStyle.connectionLineType.attributionPosition.children.nodes.edges.viewport".split(".")), Mh = /* @__PURE__ */ q("<div class=\"svelte-flow__viewport-back svelte-flow__container\"></div> <!> <div class=\"svelte-flow__edge-labels svelte-flow__container\"></div> <!> <!> <!> <div class=\"svelte-flow__viewport-front svelte-flow__container\"></div>", 1), Nh = /* @__PURE__ */ q("<!> <!>", 1), Ph = /* @__PURE__ */ q("<!> <!> <!> <!> <!>", 1);
function Fh(e, t) {
	M(t, !0);
	let n = Q(t, "paneClickDistance", 3, 1), r = Q(t, "nodeClickDistance", 3, 1), i = Q(t, "panOnScrollMode", 19, () => fd.Free), a = Q(t, "preventScrolling", 3, !0), o = Q(t, "zoomOnScroll", 3, !0), s = Q(t, "zoomOnDoubleClick", 3, !0), c = Q(t, "zoomOnPinch", 3, !0), l = Q(t, "panOnScroll", 3, !1), u = Q(t, "panOnScrollSpeed", 3, .5), d = Q(t, "panOnDrag", 3, !0), p = Q(t, "selectionOnDrag", 3, !1), m = Q(t, "autoPanOnSelection", 3, !0), h = Q(t, "connectionLineType", 19, () => hd.Bezier), g = Q(t, "nodes", 31, () => sn([])), _ = Q(t, "edges", 31, () => sn([])), v = Q(t, "viewport", 15, void 0), y = /* @__PURE__ */ va(t, jh), b = Pm({
		props: y,
		width: t.width,
		height: t.height,
		get nodes() {
			return g();
		},
		set nodes(e) {
			g(e);
		},
		get edges() {
			return _();
		},
		set edges(e) {
			_(e);
		},
		get viewport() {
			return v();
		},
		set viewport(e) {
			v(e);
		}
	}), x = $e(Nm);
	x && x.setStore && x.setStore(b), et(Nm, {
		provider: !1,
		getStore() {
			return b;
		}
	}), kn(() => {
		let e = {
			nodes: b.selectedNodes,
			edges: b.selectedEdges
		};
		wr(() => t.onselectionchange)?.(e);
		for (let t of b.selectionChangeHandlers.values()) t(e);
	}), Sa(() => {
		x?.setStore(Pm({
			width: 0,
			height: 0,
			nodes: [],
			edges: [],
			props: {}
		}));
	}), Ah(e, {
		get colorMode() {
			return b.colorMode;
		},
		get width() {
			return t.width;
		},
		get height() {
			return t.height;
		},
		get rest() {
			return y;
		},
		get domNode() {
			return b.domNode;
		},
		set domNode(e) {
			b.domNode = e;
		},
		get clientWidth() {
			return b.width;
		},
		set clientWidth(e) {
			b.width = e;
		},
		get clientHeight() {
			return b.height;
		},
		set clientHeight(e) {
			b.height = e;
		},
		children: (e, g) => {
			var _ = Ph(), v = z(_);
			bh(v, {
				get selectionKey() {
					return t.selectionKey;
				},
				get deleteKey() {
					return t.deleteKey;
				},
				get panActivationKey() {
					return t.panActivationKey;
				},
				get multiSelectionKey() {
					return t.multiSelectionKey;
				},
				get zoomActivationKey() {
					return t.zoomActivationKey;
				},
				get store() {
					return b;
				},
				set store(e) {
					b = e;
				}
			});
			var y = V(v, 2);
			Lm(y, {
				get panOnScrollMode() {
					return i();
				},
				get preventScrolling() {
					return a();
				},
				get zoomOnScroll() {
					return o();
				},
				get zoomOnDoubleClick() {
					return s();
				},
				get zoomOnPinch() {
					return c();
				},
				get panOnScroll() {
					return l();
				},
				get panOnScrollSpeed() {
					return u();
				},
				get panOnDrag() {
					return d();
				},
				get paneClickDistance() {
					return n();
				},
				get selectionOnDrag() {
					return p();
				},
				get onmovestart() {
					return t.onmovestart;
				},
				get onmove() {
					return t.onmove;
				},
				get onmoveend() {
					return t.onmoveend;
				},
				get oninit() {
					return t.oninit;
				},
				get store() {
					return b;
				},
				set store(e) {
					b = e;
				},
				children: (e, i) => {
					Hm(e, {
						get onpaneclick() {
							return t.onpaneclick;
						},
						get onpanecontextmenu() {
							return t.onpanecontextmenu;
						},
						get onselectionstart() {
							return t.onselectionstart;
						},
						get onselectionend() {
							return t.onselectionend;
						},
						get panOnDrag() {
							return d();
						},
						get paneClickDistance() {
							return n();
						},
						get selectionOnDrag() {
							return p();
						},
						get autoPanOnSelection() {
							return m();
						},
						get store() {
							return b;
						},
						set store(e) {
							b = e;
						},
						children: (e, n) => {
							var i = Nh(), a = z(i);
							Wm(a, {
								get store() {
									return b;
								},
								set store(e) {
									b = e;
								},
								children: (e, n) => {
									var i = Mh(), a = V(z(i), 2);
									dh(a, {
										get onedgeclick() {
											return t.onedgeclick;
										},
										get onedgecontextmenu() {
											return t.onedgecontextmenu;
										},
										get onedgepointerenter() {
											return t.onedgepointerenter;
										},
										get onedgepointerleave() {
											return t.onedgepointerleave;
										},
										get store() {
											return b;
										},
										set store(e) {
											b = e;
										}
									});
									var o = V(a, 4);
									Ch(o, {
										get type() {
											return h();
										},
										get LineComponent() {
											return t.connectionLineComponent;
										},
										get containerStyle() {
											return t.connectionLineContainerStyle;
										},
										get style() {
											return t.connectionLineStyle;
										},
										get store() {
											return b;
										},
										set store(e) {
											b = e;
										}
									});
									var s = V(o, 2);
									th(s, {
										get nodeClickDistance() {
											return r();
										},
										get onnodeclick() {
											return t.onnodeclick;
										},
										get onnodecontextmenu() {
											return t.onnodecontextmenu;
										},
										get onnodepointerenter() {
											return t.onnodepointerenter;
										},
										get onnodepointermove() {
											return t.onnodepointermove;
										},
										get onnodepointerleave() {
											return t.onnodepointerleave;
										},
										get onnodedrag() {
											return t.onnodedrag;
										},
										get onnodedragstart() {
											return t.onnodedragstart;
										},
										get onnodedragstop() {
											return t.onnodedragstop;
										},
										get store() {
											return b;
										},
										set store(e) {
											b = e;
										}
									}), hh(V(s, 2), {
										get onselectionclick() {
											return t.onselectionclick;
										},
										get onselectioncontextmenu() {
											return t.onselectioncontextmenu;
										},
										get onnodedrag() {
											return t.onnodedrag;
										},
										get onnodedragstart() {
											return t.onnodedragstart;
										},
										get onnodedragstop() {
											return t.onnodedragstop;
										},
										get store() {
											return b;
										},
										set store(e) {
											b = e;
										}
									}), De(2), J(e, i);
								},
								$$slots: { default: !0 }
							});
							var o = V(a, 2);
							{
								let e = /* @__PURE__ */ P(() => !!(b.selectionRect && b.selectionRectMode === "user")), t = /* @__PURE__ */ P(() => b.selectionRect?.width), n = /* @__PURE__ */ P(() => b.selectionRect?.height), r = /* @__PURE__ */ P(() => b.selectionRect?.x), i = /* @__PURE__ */ P(() => b.selectionRect?.y);
								ph(o, {
									get isVisible() {
										return G(e);
									},
									get width() {
										return G(t);
									},
									get height() {
										return G(n);
									},
									get x() {
										return G(r);
									},
									get y() {
										return G(i);
									}
								});
							}
							J(e, i);
						},
						$$slots: { default: !0 }
					});
				},
				$$slots: { default: !0 }
			});
			var x = V(y, 2);
			Oh(x, {
				get proOptions() {
					return t.proOptions;
				},
				get position() {
					return t.attributionPosition;
				}
			});
			var S = V(x, 2);
			Jm(S, { get store() {
				return b;
			} }), bi(V(S, 2), () => t.children ?? f), J(e, _);
		},
		$$slots: { default: !0 }
	}), N();
}
// node_modules/@xyflow/svelte/dist/lib/components/SvelteFlowProvider/SvelteFlowProvider.svelte
function Ih(e, t) {
	M(t, !0);
	let n = /* @__PURE__ */ I(Pm({
		props: {},
		nodes: [],
		edges: []
	}));
	et(Nm, {
		provider: !0,
		getStore() {
			return G(n);
		},
		setStore: (e) => {
			L(n, e);
		}
	}), Sa(() => {
		G(n).reset();
	});
	var r = Qr();
	bi(z(r), () => t.children ?? f), J(e, r), N();
}
// node_modules/@xyflow/svelte/dist/lib/plugins/Controls/ControlButton.svelte
var Lh = /* @__PURE__ */ new Set([
	"$$slots",
	"$$events",
	"$$legacy",
	"class",
	"bgColor",
	"bgColorHover",
	"color",
	"colorHover",
	"borderColor",
	"onclick",
	"children"
]), Rh = /* @__PURE__ */ q("<button><!></button>");
function zh(e, t) {
	let n = /* @__PURE__ */ va(t, Lh);
	var r = Rh();
	na(r, () => ({
		type: "button",
		onclick: t.onclick,
		class: ["svelte-flow__controls-button", t.class],
		...n,
		[Wi]: {
			"--xy-controls-button-background-color-props": t.bgColor,
			"--xy-controls-button-background-color-hover-props": t.bgColorHover,
			"--xy-controls-button-color-props": t.color,
			"--xy-controls-button-color-hover-props": t.colorHover,
			"--xy-controls-button-border-color-props": t.borderColor
		}
	})), bi(R(r), () => t.children ?? f), A(r), J(e, r);
}
// node_modules/@xyflow/svelte/dist/lib/plugins/Controls/Icons/Plus.svelte
var Bh = /* @__PURE__ */ Xr("<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 32 32\"><path d=\"M32 18.133H18.133V32h-4.266V18.133H0v-4.266h13.867V0h4.266v13.867H32z\"></path></svg>");
function Vh(e) {
	J(e, Bh());
}
// node_modules/@xyflow/svelte/dist/lib/plugins/Controls/Icons/Minus.svelte
var Hh = /* @__PURE__ */ Xr("<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 32 5\"><path d=\"M0 0h32v4.2H0z\"></path></svg>");
function Uh(e) {
	J(e, Hh());
}
// node_modules/@xyflow/svelte/dist/lib/plugins/Controls/Icons/Fit.svelte
var Wh = /* @__PURE__ */ Xr("<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 32 30\"><path d=\"M3.692 4.63c0-.53.4-.938.939-.938h5.215V0H4.708C2.13 0 0 2.054 0 4.63v5.216h3.692V4.631zM27.354 0h-5.2v3.692h5.17c.53 0 .984.4.984.939v5.215H32V4.631A4.624 4.624 0 0027.354 0zm.954 24.83c0 .532-.4.94-.939.94h-5.215v3.768h5.215c2.577 0 4.631-2.13 4.631-4.707v-5.139h-3.692v5.139zm-23.677.94c-.531 0-.939-.4-.939-.94v-5.138H0v5.139c0 2.577 2.13 4.707 4.708 4.707h5.138V25.77H4.631z\"></path></svg>");
function Gh(e) {
	J(e, Wh());
}
// node_modules/@xyflow/svelte/dist/lib/plugins/Controls/Icons/Lock.svelte
var Kh = /* @__PURE__ */ Xr("<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 25 32\"><path d=\"M21.333 10.667H19.81V7.619C19.81 3.429 16.38 0 12.19 0 8 0 4.571 3.429 4.571 7.619v3.048H3.048A3.056 3.056 0 000 13.714v15.238A3.056 3.056 0 003.048 32h18.285a3.056 3.056 0 003.048-3.048V13.714a3.056 3.056 0 00-3.048-3.047zM12.19 24.533a3.056 3.056 0 01-3.047-3.047 3.056 3.056 0 013.047-3.048 3.056 3.056 0 013.048 3.048 3.056 3.056 0 01-3.048 3.047zm4.724-13.866H7.467V7.619c0-2.59 2.133-4.724 4.723-4.724 2.591 0 4.724 2.133 4.724 4.724v3.048z\"></path></svg>");
function qh(e) {
	J(e, Kh());
}
// node_modules/@xyflow/svelte/dist/lib/plugins/Controls/Icons/Unlock.svelte
var Jh = /* @__PURE__ */ Xr("<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 25 32\"><path d=\"M21.333 10.667H19.81V7.619C19.81 3.429 16.38 0 12.19 0c-4.114 1.828-1.37 2.133.305 2.438 1.676.305 4.42 2.59 4.42 5.181v3.048H3.047A3.056 3.056 0 000 13.714v15.238A3.056 3.056 0 003.048 32h18.285a3.056 3.056 0 003.048-3.048V13.714a3.056 3.056 0 00-3.048-3.047zM12.19 24.533a3.056 3.056 0 01-3.047-3.047 3.056 3.056 0 013.047-3.048 3.056 3.056 0 013.048 3.048 3.056 3.056 0 01-3.048 3.047z\"></path></svg>");
function Yh(e) {
	J(e, Jh());
}
// node_modules/@xyflow/svelte/dist/lib/plugins/Controls/Controls.svelte
var Xh = /* @__PURE__ */ new Set([
	"$$slots",
	"$$events",
	"$$legacy",
	"position",
	"orientation",
	"showZoom",
	"showFitView",
	"showLock",
	"style",
	"class",
	"buttonBgColor",
	"buttonBgColorHover",
	"buttonColor",
	"buttonColorHover",
	"buttonBorderColor",
	"fitViewOptions",
	"children",
	"before",
	"after"
]), Zh = /* @__PURE__ */ q("<!> <!>", 1), Qh = /* @__PURE__ */ q("<!> <!> <!> <!> <!> <!>", 1);
function $h(e, t) {
	M(t, !0);
	let n = Q(t, "position", 3, "bottom-left"), r = Q(t, "orientation", 3, "vertical"), i = Q(t, "showZoom", 3, !0), a = Q(t, "showFitView", 3, !0), o = Q(t, "showLock", 3, !0), s = /* @__PURE__ */ va(t, Xh), c = /* @__PURE__ */ P(Mm), l = /* @__PURE__ */ P(() => ({
		bgColor: t.buttonBgColor,
		bgColorHover: t.buttonBgColorHover,
		color: t.buttonColor,
		colorHover: t.buttonColorHover,
		borderColor: t.buttonBorderColor
	})), u = /* @__PURE__ */ P(() => G(c).nodesDraggable || G(c).nodesConnectable || G(c).elementsSelectable), d = /* @__PURE__ */ P(() => G(c).viewport.zoom <= G(c).minZoom), f = /* @__PURE__ */ P(() => G(c).viewport.zoom >= G(c).maxZoom), p = /* @__PURE__ */ P(() => G(c).ariaLabelConfig), m = /* @__PURE__ */ P(() => r() === "horizontal" ? "horizontal" : "vertical"), h = () => {
		G(c).zoomIn();
	}, g = () => {
		G(c).zoomOut();
	}, _ = () => {
		G(c).fitView(t.fitViewOptions);
	}, v = () => {
		let e = !G(u);
		G(c).nodesDraggable = e, G(c).nodesConnectable = e, G(c).elementsSelectable = e;
	};
	{
		let r = /* @__PURE__ */ P(() => [
			"svelte-flow__controls",
			G(m),
			t.class
		]);
		Eh(e, ba({
			get class() {
				return G(r);
			},
			get position() {
				return n();
			},
			"data-testid": "svelte-flow__controls",
			get "aria-label"() {
				return G(p)["controls.ariaLabel"];
			},
			get style() {
				return t.style;
			}
		}, () => s, {
			children: (e, n) => {
				var r = Qh(), s = z(r), c = (e) => {
					var n = Qr();
					bi(z(n), () => t.before), J(e, n);
				};
				X(s, (e) => {
					t.before && e(c);
				});
				var m = V(s, 2), y = (e) => {
					var t = Zh(), n = z(t);
					zh(n, ba({
						onclick: h,
						class: "svelte-flow__controls-zoomin",
						get title() {
							return G(p)["controls.zoomIn.ariaLabel"];
						},
						get "aria-label"() {
							return G(p)["controls.zoomIn.ariaLabel"];
						},
						get disabled() {
							return G(f);
						}
					}, () => G(l), {
						children: (e, t) => {
							Vh(e, {});
						},
						$$slots: { default: !0 }
					})), zh(V(n, 2), ba({
						onclick: g,
						class: "svelte-flow__controls-zoomout",
						get title() {
							return G(p)["controls.zoomOut.ariaLabel"];
						},
						get "aria-label"() {
							return G(p)["controls.zoomOut.ariaLabel"];
						},
						get disabled() {
							return G(d);
						}
					}, () => G(l), {
						children: (e, t) => {
							Uh(e, {});
						},
						$$slots: { default: !0 }
					})), J(e, t);
				};
				X(m, (e) => {
					i() && e(y);
				});
				var b = V(m, 2), x = (e) => {
					zh(e, ba({
						class: "svelte-flow__controls-fitview",
						onclick: _,
						get title() {
							return G(p)["controls.fitView.ariaLabel"];
						},
						get "aria-label"() {
							return G(p)["controls.fitView.ariaLabel"];
						}
					}, () => G(l), {
						children: (e, t) => {
							Gh(e, {});
						},
						$$slots: { default: !0 }
					}));
				};
				X(b, (e) => {
					a() && e(x);
				});
				var S = V(b, 2), C = (e) => {
					zh(e, ba({
						class: "svelte-flow__controls-interactive",
						onclick: v,
						get title() {
							return G(p)["controls.interactive.ariaLabel"];
						},
						get "aria-label"() {
							return G(p)["controls.interactive.ariaLabel"];
						}
					}, () => G(l), {
						children: (e, t) => {
							var n = Qr(), r = z(n), i = (e) => {
								Yh(e, {});
							}, a = (e) => {
								qh(e, {});
							};
							X(r, (e) => {
								G(u) ? e(i) : e(a, -1);
							}), J(e, n);
						},
						$$slots: { default: !0 }
					}));
				};
				X(S, (e) => {
					o() && e(C);
				});
				var w = V(S, 2), T = (e) => {
					var n = Qr();
					bi(z(n), () => t.children), J(e, n);
				};
				X(w, (e) => {
					t.children && e(T);
				});
				var ee = V(w, 2), E = (e) => {
					var n = Qr();
					bi(z(n), () => t.after), J(e, n);
				};
				X(ee, (e) => {
					t.after && e(E);
				}), J(e, r);
			},
			$$slots: { default: !0 }
		}));
	}
	N();
}
// node_modules/@xyflow/svelte/dist/lib/plugins/Background/types.js
var eg;
(function(e) {
	e.Lines = "lines", e.Dots = "dots", e.Cross = "cross";
})(eg ||= {});
// node_modules/@xyflow/svelte/dist/lib/plugins/Background/DotPattern.svelte
var tg = /* @__PURE__ */ Xr("<circle></circle>");
function ng(e, t) {
	var n = tg();
	H(() => {
		Z(n, "cx", t.radius), Z(n, "cy", t.radius), Z(n, "r", t.radius), Mi(n, 0, Ei([
			"svelte-flow__background-pattern",
			"dots",
			t.class
		]));
	}), J(e, n);
}
// node_modules/@xyflow/svelte/dist/lib/plugins/Background/LinePattern.svelte
var rg = /* @__PURE__ */ Xr("<path></path>");
function ig(e, t) {
	M(t, !0);
	var n = rg();
	H(() => {
		Z(n, "stroke-width", t.lineWidth), Z(n, "d", `M${t.dimensions[0] / 2} 0 V${t.dimensions[1]} M0 ${t.dimensions[1] / 2} H${t.dimensions[0]}`), Mi(n, 0, Ei([
			"svelte-flow__background-pattern",
			t.variant,
			t.class
		]));
	}), J(e, n), N();
}
// node_modules/@xyflow/svelte/dist/lib/plugins/Background/Background.svelte
var ag = {
	[eg.Dots]: 1,
	[eg.Lines]: 1,
	[eg.Cross]: 6
}, og = /* @__PURE__ */ Xr("<svg data-testid=\"svelte-flow__background\"><pattern patternUnits=\"userSpaceOnUse\"><!></pattern><rect x=\"0\" y=\"0\" width=\"100%\" height=\"100%\"></rect></svg>");
function sg(e, t) {
	M(t, !0);
	let n = Q(t, "variant", 19, () => eg.Dots), r = Q(t, "gap", 3, 20), i = Q(t, "lineWidth", 3, 1), a = /* @__PURE__ */ P(Mm), o = /* @__PURE__ */ P(() => n() === eg.Dots), s = /* @__PURE__ */ P(() => n() === eg.Cross), c = /* @__PURE__ */ P(() => Array.isArray(r()) ? r() : [r(), r()]), l = /* @__PURE__ */ P(() => `background-pattern-${G(a).flowId}-${t.id ?? ""}`), u = /* @__PURE__ */ P(() => [G(c)[0] * G(a).viewport.zoom || 1, G(c)[1] * G(a).viewport.zoom || 1]), d = /* @__PURE__ */ P(() => (t.size ?? ag[n()]) * G(a).viewport.zoom), f = /* @__PURE__ */ P(() => G(s) ? [G(d), G(d)] : G(u)), p = /* @__PURE__ */ P(() => G(o) ? [G(d) / 2, G(d) / 2] : [G(f)[0] / 2, G(f)[1] / 2]);
	var m = og();
	let h;
	var g = R(m), _ = R(g), v = (e) => {
		{
			let n = /* @__PURE__ */ P(() => G(d) / 2);
			ng(e, {
				get radius() {
					return G(n);
				},
				get class() {
					return t.patternClass;
				}
			});
		}
	}, y = (e) => {
		ig(e, {
			get dimensions() {
				return G(f);
			},
			get variant() {
				return n();
			},
			get lineWidth() {
				return i();
			},
			get class() {
				return t.patternClass;
			}
		});
	};
	X(_, (e) => {
		G(o) ? e(v) : e(y, -1);
	}), A(g);
	var b = V(g);
	A(m), H(() => {
		Mi(m, 0, Ei([
			"svelte-flow__background",
			"svelte-flow__container",
			t.class
		])), h = Pi(m, "", h, {
			"--xy-background-color-props": t.bgColor,
			"--xy-background-pattern-color-props": t.patternColor
		}), Z(g, "id", G(l)), Z(g, "x", G(a).viewport.x % G(u)[0]), Z(g, "y", G(a).viewport.y % G(u)[1]), Z(g, "width", G(u)[0]), Z(g, "height", G(u)[1]), Z(g, "patternTransform", `translate(-${G(p)[0]},-${G(p)[1]})`), Z(b, "fill", `url(#${G(l)})`);
	}), J(e, m), N();
}
// node_modules/@xyflow/svelte/dist/lib/hooks/useInternalNode.svelte.js
function cg(e) {
	let t = /* @__PURE__ */ P(Mm), n = /* @__PURE__ */ P(() => G(t).nodeLookup), r = /* @__PURE__ */ P(() => G(t).nodes), i = /* @__PURE__ */ P(() => (G(r), G(n).get(e)));
	return { get current() {
		return G(i);
	} };
}
// node_modules/@xyflow/svelte/dist/lib/plugins/Minimap/MinimapNode.svelte
var lg = /* @__PURE__ */ Xr("<rect></rect>");
function ug(e, t) {
	M(t, !0);
	let n = Q(t, "borderRadius", 3, 5), r = Q(t, "strokeWidth", 3, 2), i = /* @__PURE__ */ P(() => cg(t.id)), a = /* @__PURE__ */ P(() => {
		if (!G(i).current) return {
			width: 0,
			height: 0,
			x: 0,
			y: 0
		};
		let { width: e, height: n } = tf(G(i).current);
		return {
			width: t.width ?? e,
			height: t.height ?? n,
			x: t.x ?? G(i).current.internals.positionAbsolute.x,
			y: t.y ?? G(i).current.internals.positionAbsolute.y
		};
	}), o = /* @__PURE__ */ P(() => G(a).width), s = /* @__PURE__ */ P(() => G(a).height), c = /* @__PURE__ */ P(() => G(a).x), l = /* @__PURE__ */ P(() => G(a).y);
	var u = Qr(), d = z(u), f = (e) => {
		let i = /* @__PURE__ */ P(() => t.nodeComponent);
		var a = Qr();
		xi(z(a), () => G(i), (e, i) => {
			i(e, {
				get id() {
					return t.id;
				},
				get x() {
					return G(c);
				},
				get y() {
					return G(l);
				},
				get width() {
					return G(o);
				},
				get height() {
					return G(s);
				},
				get borderRadius() {
					return n();
				},
				get class() {
					return t.class;
				},
				get color() {
					return t.color;
				},
				get shapeRendering() {
					return t.shapeRendering;
				},
				get strokeColor() {
					return t.strokeColor;
				},
				get strokeWidth() {
					return r();
				},
				get selected() {
					return t.selected;
				}
			});
		}), J(e, a);
	}, p = (e) => {
		var i = lg();
		let a, u;
		H(() => {
			a = Mi(i, 0, Ei(["svelte-flow__minimap-node", t.class]), null, a, { selected: t.selected }), Z(i, "x", G(c)), Z(i, "y", G(l)), Z(i, "rx", n()), Z(i, "ry", n()), Z(i, "width", G(o)), Z(i, "height", G(s)), Z(i, "shape-rendering", t.shapeRendering), u = Pi(i, "", u, {
				fill: t.color,
				stroke: t.strokeColor,
				"stroke-width": r()
			});
		}), J(e, i);
	};
	X(d, (e) => {
		t.nodeComponent ? e(f) : e(p, -1);
	}), J(e, u), N();
}
// node_modules/@xyflow/svelte/dist/lib/plugins/Minimap/interactive.js
function dg(e, t) {
	let n = xp({
		domNode: e,
		panZoom: t.panZoom,
		getTransform: () => {
			let { viewport: e } = t.store;
			return [
				e.x,
				e.y,
				e.zoom
			];
		},
		getViewScale: t.getViewScale
	});
	n.update({
		translateExtent: t.translateExtent,
		width: t.width,
		height: t.height,
		inversePan: t.inversePan,
		zoomStep: t.zoomStep,
		pannable: t.pannable,
		zoomable: t.zoomable
	});
	function r(e) {
		n.update({
			translateExtent: e.translateExtent,
			width: e.width,
			height: e.height,
			inversePan: e.inversePan,
			zoomStep: e.zoomStep,
			pannable: e.pannable,
			zoomable: e.zoomable
		});
	}
	return {
		update: r,
		destroy() {
			n.destroy();
		}
	};
}
// node_modules/@xyflow/svelte/dist/lib/plugins/Minimap/Minimap.svelte
var fg = (e) => e instanceof Function ? e : () => e, pg = /* @__PURE__ */ new Set([
	"$$slots",
	"$$events",
	"$$legacy",
	"position",
	"ariaLabel",
	"nodeStrokeColor",
	"nodeColor",
	"nodeClass",
	"nodeBorderRadius",
	"nodeStrokeWidth",
	"nodeComponent",
	"bgColor",
	"maskColor",
	"maskStrokeColor",
	"maskStrokeWidth",
	"width",
	"height",
	"pannable",
	"zoomable",
	"inversePan",
	"zoomStep",
	"class"
]), mg = /* @__PURE__ */ Xr("<title> </title>"), hg = /* @__PURE__ */ Xr("<svg class=\"svelte-flow__minimap-svg\" role=\"img\"><!><!><path class=\"svelte-flow__minimap-mask\" fill-rule=\"evenodd\" pointer-events=\"none\"></path></svg>"), gg = /* @__PURE__ */ q("<svelte-css-wrapper style=\"display: contents\"><!></svelte-css-wrapper>", 1);
function _g(e, t) {
	M(t, !0);
	let n = Q(t, "position", 3, "bottom-right"), r = Q(t, "nodeStrokeColor", 3, "transparent"), i = Q(t, "nodeClass", 3, ""), a = Q(t, "nodeBorderRadius", 3, 5), o = Q(t, "nodeStrokeWidth", 3, 2), s = Q(t, "width", 3, 200), c = Q(t, "height", 3, 150), l = Q(t, "pannable", 3, !0), u = Q(t, "zoomable", 3, !0), d = /* @__PURE__ */ va(t, pg), f = /* @__PURE__ */ P(Mm), p = /* @__PURE__ */ P(() => G(f).ariaLabelConfig), m = typeof window > "u" || window.chrome ? "crispEdges" : "geometricPrecision", h = /* @__PURE__ */ P(() => `svelte-flow__minimap-desc-${G(f).flowId}`), g = /* @__PURE__ */ P(() => ({
		x: -G(f).viewport.x / G(f).viewport.zoom,
		y: -G(f).viewport.y / G(f).viewport.zoom,
		width: G(f).width / G(f).viewport.zoom,
		height: G(f).height / G(f).viewport.zoom
	})), _ = /* @__PURE__ */ P(() => G(f).nodes.some((e) => !e.hidden)), v = /* @__PURE__ */ P(() => G(_) ? Bd(Cd(G(f).nodeLookup, { filter: (e) => !e.hidden }), G(g)) : G(g)), y = /* @__PURE__ */ P(() => G(v).width / s()), b = /* @__PURE__ */ P(() => G(v).height / c()), x = /* @__PURE__ */ P(() => Math.max(G(y), G(b))), S = /* @__PURE__ */ P(() => G(x) * s()), C = /* @__PURE__ */ P(() => G(x) * c()), w = /* @__PURE__ */ P(() => 5 * G(x)), T = /* @__PURE__ */ P(() => G(v).x - (G(S) - G(v).width) / 2 - G(w)), ee = /* @__PURE__ */ P(() => G(v).y - (G(C) - G(v).height) / 2 - G(w)), E = /* @__PURE__ */ P(() => G(S) + G(w) * 2), D = /* @__PURE__ */ P(() => G(C) + G(w) * 2), te = () => G(x);
	var ne = gg(), re = z(ne);
	{
		let e = /* @__PURE__ */ P(() => ["svelte-flow__minimap", t.class]);
		li(re, () => ({ "--xy-minimap-background-color-props": t.bgColor })), Eh(re.lastChild, ba({
			get position() {
				return n();
			},
			get class() {
				return G(e);
			},
			"data-testid": "svelte-flow__minimap"
		}, () => d, {
			children: (e, n) => {
				var d = Qr(), _ = z(d), v = (e) => {
					var n = hg();
					let d;
					var _ = R(n), v = (e) => {
						var n = mg(), r = B(n, !0);
						H(() => {
							Z(n, "id", G(h)), Y(r, t.ariaLabel ?? G(p)["minimap.ariaLabel"]);
						}), J(e, n);
					};
					X(_, (e) => {
						(t.ariaLabel ?? G(p)["minimap.ariaLabel"]) && e(v);
					});
					var y = V(_);
					mi(y, 17, () => G(f).nodes, (e) => e.id, (e, n) => {
						let s = /* @__PURE__ */ P(() => G(f).nodeLookup.get(G(n).id));
						var c = Qr(), l = z(c), u = (e) => {
							{
								let c = /* @__PURE__ */ P(() => t.nodeColor === void 0 ? void 0 : fg(t.nodeColor)(G(n))), l = /* @__PURE__ */ P(() => fg(r())(G(n))), u = /* @__PURE__ */ P(() => fg(i())(G(n)));
								ug(e, {
									get id() {
										return G(s).id;
									},
									get selected() {
										return G(s).selected;
									},
									get nodeComponent() {
										return t.nodeComponent;
									},
									get color() {
										return G(c);
									},
									get borderRadius() {
										return a();
									},
									get strokeColor() {
										return G(l);
									},
									get strokeWidth() {
										return o();
									},
									get shapeRendering() {
										return m;
									},
									get class() {
										return G(u);
									}
								});
							}
						}, d = /* @__PURE__ */ P(() => G(s) && nf(G(s)) && !G(s).hidden);
						X(l, (e) => {
							G(d) && e(u);
						}), J(e, c);
					});
					var b = V(y);
					A(n), Si(n, (e, t) => dg?.(e, t), () => ({
						store: G(f),
						panZoom: G(f).panZoom,
						getViewScale: te,
						translateExtent: G(f).translateExtent,
						width: G(f).width,
						height: G(f).height,
						inversePan: t.inversePan,
						zoomStep: t.zoomStep,
						pannable: l(),
						zoomable: u()
					})), H(() => {
						Z(n, "width", s()), Z(n, "height", c()), Z(n, "viewBox", `${G(T) ?? ""} ${G(ee) ?? ""} ${G(E) ?? ""} ${G(D) ?? ""}`), Z(n, "aria-labelledby", G(h)), d = Pi(n, "", d, {
							"--xy-minimap-mask-background-color-props": t.maskColor,
							"--xy-minimap-mask-stroke-color-props": t.maskStrokeColor,
							"--xy-minimap-mask-stroke-width-props": t.maskStrokeWidth ? t.maskStrokeWidth * G(x) : void 0
						}), Z(b, "d", `M${G(T) - G(w)},${G(ee) - G(w)}h${G(E) + G(w) * 2}v${G(D) + G(w) * 2}h${-G(E) - G(w) * 2}z
      M${G(g).x ?? ""},${G(g).y ?? ""}h${G(g).width ?? ""}v${G(g).height ?? ""}h${-G(g).width}z`);
					}), J(e, n);
				};
				X(_, (e) => {
					G(f).panZoom && e(v);
				}), J(e, d);
			},
			$$slots: { default: !0 }
		})), A(re);
	}
	J(e, ne), N();
}
// src/StrategyNode.svelte
var vg = /* @__PURE__ */ q("<span aria-label=\"protected\">⌁</span>"), yg = /* @__PURE__ */ q("<span class=\"node-status\"> </span>"), bg = /* @__PURE__ */ q("<div><!> <div class=\"node-top\"><span class=\"node-dot\"></span><span class=\"node-kind\"> </span><!></div> <strong> </strong> <div class=\"node-component\"> </div> <small> </small> <!> <!></div>");
function xg(e, t) {
	M(t, !0);
	var n = bg();
	let r, i;
	var a = R(n), o = (e) => {
		Jp(e, {
			type: "target",
			get position() {
				return $.Left;
			},
			get title() {
				return t.data.inputType;
			},
			get "aria-label"() {
				return t.data.inputType;
			}
		});
	};
	X(a, (e) => {
		(t.data.kind !== "context" || t.data.component === "execution") && e(o);
	});
	var s = V(a, 2), c = V(R(s)), l = B(c, !0), u = V(c), d = (e) => {
		J(e, vg());
	};
	X(u, (e) => {
		t.data.protected && e(d);
	}), A(s);
	var f = V(s, 2), p = B(f, !0), m = V(f, 2), h = B(m, !0), g = V(m, 2), _ = B(g, !0), v = V(g, 2), y = (e) => {
		var n = yg(), r = B(n, !0);
		H(() => Y(r, t.data.status)), J(e, n);
	};
	X(v, (e) => {
		t.data.status && e(y);
	});
	var b = V(v, 2), x = (e) => {
		Jp(e, {
			type: "source",
			get position() {
				return $.Right;
			},
			get title() {
				return t.data.outputType;
			},
			get "aria-label"() {
				return t.data.outputType;
			}
		});
	};
	X(b, (e) => {
		t.data.component !== "execution" && e(x);
	}), A(n), H(() => {
		r = Mi(n, 1, "strategy-node", null, r, { selected: t.selected }), Z(n, "title", t.data.summary), i = Pi(n, "", i, { "--node-accent": t.data.color }), Y(l, t.data.kindLabel), Y(p, t.data.label), Y(h, t.data.component), Y(_, t.data.summary);
	}), J(e, n), N();
}
// src/documents.ts
var Sg = (e) => JSON.parse(JSON.stringify(e)), Cg = (e) => ["main", ...e].join("/");
function wg(e, t) {
	return t.reduce((e, t) => {
		let n = e.sleeves?.find((e) => e.id === t);
		if (!n) throw Error("Unknown graph scope");
		return n.definition;
	}, e);
}
function Tg(e, t, n) {
	if (n === "@portfolio") return {
		...e.schema.defaults.portfolio,
		...t.portfolio?.params
	};
	if (n === "@risk") return {
		...e.schema.defaults.risk,
		...t.risk
	};
	if (n === "@execution") return {
		...e.schema.defaults.execution,
		...t.execution
	};
	let r = t.nodes?.find((e) => e.id === n);
	return r ? {
		...e.schema.components[r.component]?.defaults,
		...r.params
	} : {};
}
function Eg(e, t) {
	let n = wg(e.document, t), r = e.config, i = Cg(t), a = e.layout[i]?.positions || {}, o = { universe: 0 }, s = n.nodes || [], c = [...s];
	for (let e = 0; e <= s.length && c.length; e++) for (let e of [...c]) (e.inputs || ["universe"]).every((e) => e in o) && (o[e.id] = 1 + Math.max(...(e.inputs || ["universe"]).map((e) => o[e])), c.splice(c.indexOf(e), 1));
	let l = [], u = [], d = {}, f = (t, n, o) => {
		let s = d[o] || 0;
		d[o] = s + 1;
		let c = e.compiled_digest && e.compiled_digest === e.evidence.definition_digest ? e.evidence.nodes?.[i + "/" + t] : void 0, l = c?.stages.at(-1), f = c?.events.findLast((e) => e.kind === "stage")?.data, p = String(f?.status || l?.status || ""), m = r.status_labels?.[p] || p;
		l?.passed !== void 0 && (n.summary = `${r.ui.passed} ${l.passed} / ${l.input_count} · ${l.duration_ms} ${r.ui.milliseconds}`), u.push({
			id: t,
			type: "strategy",
			position: a[t] || {
				x: o * Number(r.limits.layout_gap_x),
				y: s * Number(r.limits.layout_gap_y)
			},
			data: {
				...n,
				status: m,
				selected: !1
			},
			deletable: !n.protected
		});
	}, p = (e, t, n, i, a = !1) => ({
		label: e,
		component: t,
		kind: n,
		kindLabel: r.groups[n]?.label || n,
		inputType: r.ports[n]?.input || "",
		outputType: r.ports[n]?.output || "",
		summary: i,
		color: r.groups[n]?.color || r.groups.context.color,
		protected: a,
		status: "",
		selected: !1
	}), m = (e, t, n = "", r = !1, i = !1) => l.push({
		id: e + ">" + t + (i ? ":context" : ""),
		source: e,
		target: t,
		label: n,
		selectable: !r,
		deletable: !r,
		style: i ? "stroke-dasharray:4 5;opacity:.45" : void 0,
		data: {
			protected: r,
			context: i
		},
		markerEnd: { type: "arrowclosed" }
	});
	f("universe", p(r.ui.universe, "context", "context", String(n.universe?.symbols?.length || 0), !0), 0);
	for (let t of s) {
		let n = e.schema.components[t.component];
		f(t.id, p(t.id, n?.label || t.component, n?.kind || "context", (t.inputs || ["universe"]).join(", ")), o[t.id] ?? 1);
		for (let e of t.inputs || ["universe"]) m(e, t.id);
		[
			"lightgbm",
			"xgboost",
			"mlp"
		].includes(t.component) && !(t.inputs || []).includes("universe") && m("universe", t.id, r.ui.context, !0, !0);
	}
	for (let e of n.sleeves || []) f("s:" + e.id, p(e.id, e.definition.name, "portfolio", r.ui.budget + " " + (e.budget * 100).toFixed(1) + "%", !0), 1), m("universe", "s:" + e.id, "", !0);
	let h = 1 + Math.max(0, ...Object.values(o), +!!n.sleeves?.length);
	if (f("@portfolio", p(r.ui.portfolio, e.schema.portfolios[n.portfolio?.component || "equal"], "portfolio", r.ui.protected, !0), h), n.sleeves?.length) for (let e of n.sleeves) m("s:" + e.id, "@portfolio", (e.budget * 100).toFixed(1) + "%", !0);
	else m(n.output || "universe", "@portfolio", "", !0);
	return f("@risk", p(r.ui.risk, "risk", "risk", r.ui.protected, !0), h + 1), f("@execution", p(r.ui.execution, "execution", "context", r.ui.protected, !0), h + 2), m("@portfolio", "@risk", "", !0), m("@risk", "@execution", "", !0), {
		nodes: u,
		edges: l
	};
}
function Dg(e, t, n) {
	let { source: r, target: i } = n;
	if (!r || !i || r === i || r.startsWith("@") || i.startsWith("@") || r.startsWith("s:") || i.startsWith("s:")) return !1;
	let a = e.nodes?.find((e) => e.id === i), o = e.nodes?.find((e) => e.id === r);
	if (!a || r !== "universe" && !o || o?.component === "agent" || (a.inputs || []).includes(r)) return !1;
	let s = t.schema.components[a.component]?.kind, c = o ? t.schema.components[o.component]?.kind : "filter";
	if ([
		"factor_preprocess",
		"factor_select",
		"factor_score"
	].includes(a.component) !== (c === "factor") || a.component === "factor_preprocess" && o?.component === "factor_select" || a.component === "factor_score" && a.params?.weighting === "icir" && o?.component !== "factor_select" || s !== "ensemble" && (a.inputs || []).length) return !1;
	let l = (t, n) => t === i || !n.has(t) && (n.add(t), (e.nodes?.find((e) => e.id === t)?.inputs || []).some((e) => l(e, n)));
	return !l(r, /* @__PURE__ */ new Set());
}
function Og(e, t, n) {
	if (!Dg(e, t, n)) return !1;
	let r = e.nodes.find((e) => e.id === n.target);
	r.inputs = [...r.inputs || [], n.source];
	let i = r.params?.weights;
	return Array.isArray(i) && i.length && (r.params.weights = [...i, 1]), !0;
}
function kg(e, t, n) {
	let r = e.nodes?.find((e) => e.id === n);
	if (!r) return;
	let i = (r.inputs || []).indexOf(t);
	i < 0 || (r.inputs = r.inputs.filter((e, t) => t !== i), Array.isArray(r.params?.weights) && r.params.weights.length && (r.params.weights = r.params.weights.filter((e, t) => t !== i)));
}
function Ag(e, t) {
	let n = t, r = 1;
	for (; e.nodes?.some((e) => e.id === n);) n = t + "_" + r++;
	return n;
}
function jg(e, t, n) {
	if (e.sleeves?.length || !t.schema.components[n] || (e.nodes?.length || 0) >= t.schema.max_nodes) throw Error("Component unavailable in this scope");
	let r = {
		id: Ag(e, n),
		component: n,
		inputs: ["universe"],
		params: {}
	};
	if ([
		"factor_preprocess",
		"factor_select",
		"factor_score"
	].includes(n)) {
		let i = [...e.nodes || []].reverse().find((e) => t.schema.components[e.component]?.kind === "factor" && (n !== "factor_preprocess" || e.component !== "factor_select"));
		r.inputs = i ? [i.id] : [];
	}
	return (e.nodes ??= []).push(r), r;
}
// src/FactorEvidence.svelte
var Mg = /* @__PURE__ */ q("<p> </p>"), Ng = /* @__PURE__ */ q("<tr><th class=\"svelte-2k9n1p\"> </th><td class=\"svelte-2k9n1p\"> </td><td class=\"svelte-2k9n1p\"> </td><td class=\"svelte-2k9n1p\"> </td></tr>"), Pg = /* @__PURE__ */ q("<small class=\"svelte-2k9n1p\"> </small>"), Fg = /* @__PURE__ */ q("<p> </p> <table class=\"svelte-2k9n1p\"><thead><tr><th class=\"svelte-2k9n1p\"> </th><th class=\"svelte-2k9n1p\">RankIC</th><th class=\"svelte-2k9n1p\">ICIR</th><th class=\"svelte-2k9n1p\"> </th></tr></thead><tbody></tbody></table> <!>", 1), Ig = /* @__PURE__ */ q("<div class=\"factor-weight svelte-2k9n1p\"><span> </span><progress max=\"1\" class=\"svelte-2k9n1p\"></progress><span> </span></div>"), Lg = /* @__PURE__ */ q("<p> </p> <!>", 1), Rg = /* @__PURE__ */ q("<section class=\"factor-evidence svelte-2k9n1p\"><strong> </strong> <!> <!> <!> <!></section>");
function zg(e, t) {
	M(t, !0);
	let n = Q(t, "date", 3, ""), r = /* @__PURE__ */ P(() => t.evidence?.factor_research || {}), i = /* @__PURE__ */ P(() => G(r).research || {}), a = /* @__PURE__ */ P(() => G(i).metrics || {}), o = /* @__PURE__ */ P(() => G(i).excluded || {}), s = /* @__PURE__ */ P(() => G(i).selected || G(r).factors || []), c = /* @__PURE__ */ P(() => G(r).observations || {}), l = /* @__PURE__ */ P(() => Object.values(G(c))[0]?.factor_weights || {}), u = (e) => typeof e == "number" && Number.isFinite(e) ? e.toFixed(3) : "—";
	var d = Qr(), f = z(d), p = (e) => {
		var n = Rg(), c = R(n), d = B(c), f = V(c, 2), p = (e) => {
			var n = Mg(), i = B(n);
			H((e) => Y(i, `${t.labels.set_name ?? ""}: ${e ?? ""}`), [() => String(G(r).set)]), J(e, n);
		};
		X(f, (e) => {
			G(r).set && e(p);
		});
		var m = V(f, 2), h = (e) => {
			var n = Mg(), i = B(n);
			H((e, n, r) => Y(i, `${t.labels.cache_computed ?? ""}: ${e ?? ""} · ${t.labels.cache_hits ?? ""}:
        ${n ?? ""} · ${t.labels.memory_hits ?? ""}: ${r ?? ""}`), [
				() => String(G(r).computed),
				() => String(G(r).cache_hits || 0),
				() => String(G(r).memory_hits || 0)
			]), J(e, n);
		};
		X(m, (e) => {
			G(r).computed !== void 0 && e(h);
		});
		var g = V(m, 2), v = (e) => {
			var n = Fg(), r = z(n), c = B(r), l = V(r, 2), d = R(l), f = R(d), p = R(f), m = B(p, !0), h = V(p), g = V(h), v = B(V(g), !0);
			A(f), A(d);
			var y = V(d);
			mi(y, 21, () => Object.entries(G(a)), ui, (e, n) => {
				var r = /* @__PURE__ */ P(() => _(G(n), 2));
				let i = () => G(r)[0], a = () => G(r)[1];
				var c = Ng();
				let l;
				var d = R(c), f = B(d), p = V(d), m = B(p, !0), h = V(p), g = B(h, !0), v = B(V(h), !0);
				A(c), H((e, n, r, a, s) => {
					Z(c, "title", G(o)[i()] || t.labels.factor_selected), l = Mi(c, 1, "svelte-2k9n1p", null, l, { excluded: e }), Y(f, `${(t.labels[i()] || i()) ?? ""}${n ?? ""}`), Y(m, r), Y(g, a), Y(v, s);
				}, [
					() => !G(s).includes(i()),
					() => G(s).includes(i()) ? " ✓" : "",
					() => u(a().rank_ic_mean),
					() => u(a().icir),
					() => String(a().samples)
				]), J(e, c);
			}), A(y), A(l), mi(V(l, 2), 17, () => Object.entries(G(o)), ui, (e, n) => {
				var r = /* @__PURE__ */ P(() => _(G(n), 2));
				let i = () => G(r)[0], a = () => G(r)[1];
				var o = Pg(), s = B(o);
				H(() => Y(s, `${(t.labels[i()] || i()) ?? ""}: ${(t.labels[a()] || a()) ?? ""}`)), J(e, o);
			}), H((e) => {
				Z(r, "title", t.labels.matured_hint), Y(c, `${t.labels.label_end ?? ""}: ${e ?? ""}`), Y(m, t.labels.factor_name), Z(h, "title", t.labels.rank_ic_hint), Z(g, "title", t.labels.icir_hint), Y(v, t.labels.samples);
			}, [() => String(G(i).label_end || "—")]), J(e, n);
		}, y = /* @__PURE__ */ P(() => Object.keys(G(a)).length);
		X(g, (e) => {
			G(y) && e(v);
		});
		var b = V(g, 2), x = (e) => {
			var n = Lg(), r = z(n), i = B(r, !0);
			mi(V(r, 2), 17, () => Object.entries(G(l)), ui, (e, n) => {
				var r = /* @__PURE__ */ P(() => _(G(n), 2));
				let i = () => G(r)[0], a = () => G(r)[1];
				var o = Ig(), s = R(o), c = B(s, !0), l = V(s), u = B(V(l));
				A(o), H((e) => {
					Y(c, t.labels[i()] || i()), $i(l, a()), Z(l, "aria-label", t.labels[i()] || i()), Y(u, `${e ?? ""}%`);
				}, [() => (a() * 100).toFixed(1)]), J(e, o);
			}), H(() => {
				Z(r, "title", t.labels.factor_weights_hint), Y(i, t.labels.factor_weights);
			}), J(e, n);
		}, S = /* @__PURE__ */ P(() => Object.keys(G(l)).length);
		X(b, (e) => {
			G(S) && e(x);
		}), A(n), H((e) => {
			Z(n, "aria-label", t.labels.factor_evidence), Y(d, `${t.labels.factor_evidence ?? ""} · ${e ?? ""}`);
		}, [() => String(G(r).as_of)]), J(e, n);
	};
	X(f, (e) => {
		G(r).as_of && (!n() || n() === G(r).as_of) && e(p);
	}), J(e, d), N();
}
// src/Properties.svelte
var Bg = /* @__PURE__ */ q("<button class=\"graph-primary\"> </button> <label> <input type=\"number\" min=\"0\" max=\"1\" step=\"0.05\"/></label>", 1), Vg = /* @__PURE__ */ q("<p> </p> <div class=\"graph-code\"> </div>", 1), Hg = /* @__PURE__ */ q("<option> </option>"), Ug = /* @__PURE__ */ q("<label> <select></select></label>"), Wg = /* @__PURE__ */ q("<input type=\"checkbox\"/>"), Gg = /* @__PURE__ */ q("<select></select>"), Kg = /* @__PURE__ */ q("<input/>"), qg = /* @__PURE__ */ q("<label> <!></label>"), Jg = /* @__PURE__ */ q("<div class=\"node-actions\"><button> </button><button> </button><button class=\"danger\"> </button></div>"), Yg = /* @__PURE__ */ q("<small> </small>"), Xg = /* @__PURE__ */ q("<p> </p> <!> <div class=\"property-fields\"></div> <button class=\"graph-primary\"> </button> <details><summary> </summary><textarea rows=\"9\"></textarea><button> </button></details> <!>", 1), Zg = /* @__PURE__ */ q("<p role=\"alert\" class=\"graph-error\"> </p>"), Qg = /* @__PURE__ */ q("<button> </button>"), $g = /* @__PURE__ */ q("<p class=\"graph-warning\"> </p>"), e_ = /* @__PURE__ */ q("<small> </small> <!> <label> <select><option>—</option><!></select></label> <!> <pre> </pre>", 1), t_ = /* @__PURE__ */ q("<p> </p>"), n_ = /* @__PURE__ */ q("<!> <!> <section class=\"relationships\"><h4> </h4> <!> <h4> </h4> <!></section> <details open=\"\" class=\"node-evidence\"><summary> </summary> <!></details>", 1), r_ = /* @__PURE__ */ q("<aside class=\"graph-properties\"><div class=\"property-heading\"><span> </span><strong> </strong></div> <!></aside>");
function i_(e, t) {
	M(t, !0);
	let n = /* @__PURE__ */ P(() => t.payload.config.ui), r = /* @__PURE__ */ P(() => t.path.reduce((e, t) => e.sleeves.find((e) => e.id === t).definition, t.payload.document)), i = /* @__PURE__ */ P(() => G(r).nodes?.find((e) => e.id === t.selected)), a = /* @__PURE__ */ P(() => JSON.stringify(Tg(t.payload, G(r), t.selected))), o = /* @__PURE__ */ P(() => G(r).portfolio?.component || "equal"), s = /* @__PURE__ */ I(sn({})), c = /* @__PURE__ */ I(""), l = /* @__PURE__ */ I("equal"), u = /* @__PURE__ */ I(""), d = /* @__PURE__ */ P(() => t.payload.evidence.nodes?.[Cg(t.path) + "/" + t.selected]), f = /* @__PURE__ */ I(""), p;
	kn(() => {
		t.selected, Cg(t.path), L(f, ""), p && (p.scrollTop = 0);
	}), kn(() => {
		t.selected;
		let e = JSON.parse(G(a));
		L(s, e, !0), L(c, JSON.stringify(e, null, 2), !0), L(l, G(o), !0), L(u, "");
	});
	let m = /* @__PURE__ */ P(() => G(i)?.inputs || []), h = /* @__PURE__ */ P(() => (G(r).nodes || []).filter((e) => (e.inputs || []).includes(t.selected)).map((e) => e.id)), g = /* @__PURE__ */ P(() => Object.entries(G(s)).filter(([e, t]) => [
		"number",
		"boolean",
		"string"
	].includes(typeof t) && !["backend", "title"].includes(e)));
	function v(e = !1) {
		try {
			let n = e ? JSON.parse(G(c)) : G(s);
			if (!n || Array.isArray(n) || typeof n != "object") throw Error("Parameters must be an object");
			t.onupdate(n, G(l));
		} catch (e) {
			L(u, String(e), !0);
		}
	}
	var y = r_(), b = R(y), x = R(b), S = B(x, !0), C = B(V(x), !0);
	A(b);
	var w = V(b, 2), T = (e) => {
		var a = n_(), o = z(a), p = (e) => {
			var i = Bg(), a = z(i), o = B(a, !0), s = V(a, 2), c = R(s, !0), l = V(c);
			Qi(l), A(s), H((e) => {
				Y(o, G(n).enter), Y(c, G(n).budget), $i(l, e);
			}, [() => G(r).sleeves?.find((e) => "s:" + e.id === t.selected)?.budget]), K("click", a, function(...e) {
				t.onenter?.apply(this, e);
			}), K("change", l, (e) => t.onbudget(Number(e.currentTarget.value))), J(e, i);
		}, y = /* @__PURE__ */ P(() => t.selected.startsWith("s:")), b = (e) => {
			var i = Vg(), a = z(i), o = B(a, !0), s = B(V(a, 2), !0);
			H((e) => {
				Y(o, t.payload.config.help.universe), Y(s, e);
			}, [() => G(r).universe?.symbols?.join(", ") || G(n).context]), J(e, i);
		}, x = (e) => {
			var r = Xg(), a = z(r), o = B(a, !0), u = V(a, 2), d = (e) => {
				var r = Ug(), i = R(r, !0), a = V(i);
				mi(a, 21, () => Object.entries(t.payload.schema.portfolios), ui, (e, t) => {
					var n = /* @__PURE__ */ P(() => _(G(t), 2));
					let r = () => G(n)[0], i = () => G(n)[1];
					var a = Hg(), o = B(a, !0), s = {};
					H(() => {
						Y(o, i()), s !== (s = r()) && (a.value = (a.__value = s) ?? "");
					}), J(e, a);
				}), A(a), zi(a), A(r), H(() => Y(i, G(n).portfolio)), Bi(a, () => G(l), (e) => L(l, e)), J(e, r);
			};
			X(u, (e) => {
				t.selected === "@portfolio" && e(d);
			});
			var f = V(u, 2);
			mi(f, 21, () => G(g), ui, (e, n) => {
				var r = /* @__PURE__ */ P(() => _(G(n), 2));
				let a = () => G(r)[0], o = () => G(r)[1];
				var c = qg(), l = R(c), u = V(l), d = (e) => {
					var t = Wg();
					Qi(t), H((e) => ea(t, e), [() => !!G(s)[a()]]), K("change", t, (e) => L(s, {
						...G(s),
						[a()]: e.currentTarget.checked
					}, !0)), J(e, t);
				}, f = (e) => {
					var n = Gg();
					mi(n, 21, () => t.payload.config.choices[a()], ui, (e, t) => {
						var n = Hg(), r = B(n, !0), i = {};
						H(() => {
							Y(r, G(t)), i !== (i = G(t)) && (n.__value = i);
						}), J(e, n);
					}), A(n);
					var r;
					zi(n), H((e) => {
						r !== (r = e) && (n.value = (n.__value = r) ?? "", Ri(n, r));
					}, [() => String(G(s)[a()])]), K("change", n, (e) => L(s, {
						...G(s),
						[a()]: e.currentTarget.value
					}, !0)), J(e, n);
				}, p = (e) => {
					var n = Kg();
					Qi(n), H((e) => {
						Z(n, "type", typeof o() == "number" ? "number" : "text"), $i(n, e), Z(n, "min", t.payload.config.parameter_limits[a()]?.min), Z(n, "max", t.payload.config.parameter_limits[a()]?.max), Z(n, "step", t.payload.config.parameter_limits[a()]?.step || "any");
					}, [() => String(G(s)[a()])]), K("input", n, (e) => L(s, {
						...G(s),
						[a()]: typeof o() == "number" ? Number(e.currentTarget.value) : e.currentTarget.value
					}, !0)), J(e, n);
				};
				X(u, (e) => {
					typeof o() == "boolean" ? e(d) : t.payload.config.choices[a()] ? e(f, 1) : e(p, -1);
				}), A(c), H(() => {
					Z(c, "title", a()), Y(l, `${(G(i) && t.payload.config.labels[G(i).component + "." + a()] || t.payload.config.labels[a()] || a()) ?? ""} `);
				}), J(e, c);
			}), A(f);
			var p = V(f, 2), m = B(p, !0), h = V(p, 2), y = R(h), b = B(y, !0), x = V(y);
			pt(x);
			var S = V(x), C = B(S, !0);
			A(h);
			var w = V(h, 2), T = (e) => {
				var r = Jg(), i = R(r), a = B(i, !0), o = V(i), s = B(o, !0), c = V(o), l = B(c, !0);
				A(r), H(() => {
					Y(a, G(n).duplicate), Y(s, G(n).output), Y(l, G(n).remove);
				}), K("click", i, function(...e) {
					t.onduplicate?.apply(this, e);
				}), K("click", o, function(...e) {
					t.onoutput?.apply(this, e);
				}), K("click", c, function(...e) {
					t.onremove?.apply(this, e);
				}), J(e, r);
			}, ee = (e) => {
				var t = Yg(), r = B(t, !0);
				H(() => Y(r, G(n).protected)), J(e, t);
			};
			X(w, (e) => {
				G(i) ? e(T) : e(ee, -1);
			}), H((e) => {
				Y(o, e), Y(m, G(n).update), Y(b, G(n).advanced), Z(x, "aria-label", G(n).advanced), Y(C, G(n).update);
			}, [() => G(i) && t.payload.config.help[G(i).component] || t.payload.config.help[G(i) ? t.payload.schema.components[G(i).component]?.kind : t.selected.slice(1)] || ""]), K("click", p, () => v()), oa(x, () => G(c), (e) => L(c, e)), K("click", S, () => v(!0)), J(e, r);
		};
		X(o, (e) => {
			G(y) ? e(p) : t.selected === "universe" ? e(b, 1) : e(x, -1);
		});
		var S = V(o, 2), C = (e) => {
			var t = Zg(), n = B(t, !0);
			H(() => Y(n, G(u))), J(e, t);
		};
		X(S, (e) => {
			G(u) && e(C);
		});
		var w = V(S, 2), T = R(w), ee = B(T, !0), E = V(T, 2);
		mi(E, 17, () => G(m), ui, (e, n) => {
			var r = Qg(), i = B(r);
			H(() => Y(i, `${G(n) ?? ""} ↖`)), K("click", r, () => t.onselect(G(n))), J(e, r);
		});
		var D = V(E, 2), te = B(D, !0);
		mi(V(D, 2), 17, () => G(h), ui, (e, n) => {
			var r = Qg(), i = B(r);
			H(() => Y(i, `${G(n) ?? ""} ↗`)), K("click", r, () => t.onselect(G(n))), J(e, r);
		}), A(w);
		var ne = V(w, 2), re = R(ne), ie = B(re, !0), ae = V(re, 2), oe = (e) => {
			var r = e_(), i = z(r), a = B(i), o = V(i, 2), s = (e) => {
				var t = $g(), r = B(t, !0);
				H(() => Y(r, G(n).stale)), J(e, t);
			};
			X(o, (e) => {
				t.payload.compiled_digest !== t.payload.evidence.definition_digest && e(s);
			});
			var c = V(o, 2), l = R(c, !0), u = V(l), p = R(u);
			p.value = p.__value = "", mi(V(p), 17, () => [...new Set(G(d)?.stages.map((e) => String(e.as_of)) || [])], ui, (e, t) => {
				var n = Hg(), r = B(n, !0), i = {};
				H(() => {
					Y(r, G(t)), i !== (i = G(t)) && (n.__value = i);
				}), J(e, n);
			}), A(u), zi(u), A(c);
			var m = V(c, 2);
			zg(m, {
				get evidence() {
					return G(d);
				},
				get labels() {
					return t.payload.config.labels;
				},
				get date() {
					return G(f);
				}
			});
			var h = B(V(m, 2), !0);
			H((e) => {
				Y(a, `${t.payload.evidence.run_id ?? ""} · ${t.payload.evidence.status ?? ""}`), Y(l, G(n).date), Y(h, e);
			}, [() => JSON.stringify(G(d) ? {
				...G(d),
				stages: G(d).stages.filter((e) => !G(f) || e.as_of === G(f)),
				events: G(d).events.filter((e) => !G(f) || e.data?.as_of === G(f))
			} : { message: G(n).empty }, null, 2)]), Bi(u, () => G(f), (e) => L(f, e)), J(e, r);
		}, se = (e) => {
			var t = t_(), r = B(t, !0);
			H(() => Y(r, G(n).empty)), J(e, t);
		};
		X(ae, (e) => {
			t.payload.evidence.run_id ? e(oe) : e(se, -1);
		}), A(ne), H(() => {
			Y(ee, G(n).parents), Y(te, G(n).children), Y(ie, G(n).evidence);
		}), J(e, a);
	};
	X(w, (e) => {
		t.selected && e(T);
	}), A(y), fa(y, (e) => p = e, () => p), H(() => {
		Y(S, G(n).parameters), Y(C, t.selected || G(n).choose);
	}), J(e, y), N();
}
Vr([
	"click",
	"change",
	"input"
]);
// src/files.ts
function a_(e) {
	let t = JSON.stringify({
		format: "aiquant-strategy-graph",
		version: 1,
		document: e.document,
		layout: e.layout
	}, null, 2), n = URL.createObjectURL(new Blob([t], { type: "application/json" })), r = document.createElement("a");
	r.href = n, r.download = "strategy-graph.json", r.click(), URL.revokeObjectURL(n);
}
async function o_(e, t) {
	if (e.size > Number(t.config.limits.max_bytes)) throw Error(t.config.ui.invalid_file);
	let n = JSON.parse(await e.text());
	if (n.format !== "aiquant-strategy-graph" || n.version !== 1 || typeof n.document?.name != "string") throw Error(t.config.ui.invalid_file);
	let r = (e, n) => {
		if (n > t.schema.max_depth || !Array.isArray(e.nodes ?? []) || (e.nodes?.length || 0) > t.schema.max_nodes) throw Error(t.config.ui.invalid_file);
		for (let n of e.nodes || []) if (!/^[A-Za-z][A-Za-z0-9_-]{0,63}$/.test(n.id) || !t.schema.components[n.component] || !Array.isArray(n.inputs ?? [])) throw Error(t.config.ui.invalid_file);
		for (let t of e.sleeves || []) r(t.definition, n + 1);
	};
	return r(n.document, 0), n;
}
// src/updates.ts
function s_(e, t, n) {
	let r = {
		value: e,
		dirty: n,
		reset: !1,
		accepted: !1
	};
	if (!t || t.doc_id !== e.doc_id) return r;
	let i = [
		"load",
		"sync",
		"applied",
		"issues"
	].includes(t.kind) ? "document" : t.kind, a = e.update_sequences?.[i] || "0";
	if (BigInt(t.sequence) <= BigInt(a) || ![
		"load",
		"evidence",
		"layout",
		"applied"
	].includes(t.kind) && t.edit_revision !== e.edit_revision) return r;
	let o = {
		...e.update_sequences,
		[i]: t.sequence
	}, s = {
		...e,
		update_sequences: o
	}, c = !1;
	if (t.kind === "load" && t.payload) s = {
		...Sg(t.payload),
		update_sequences: o
	}, n = !1, c = !0;
	else if (t.kind === "sync" && t.payload) c = JSON.stringify(e.document) !== JSON.stringify(t.payload.document), s = {
		...Sg(t.payload),
		update_sequences: o
	}, n = !1;
	else if (t.kind === "applied" && t.payload) t.edit_revision === e.edit_revision ? (s = {
		...Sg(t.payload),
		layout: e.layout,
		update_sequences: o
	}, n = !1) : (s.base_digest = t.payload.base_digest, s.compiled_digest = "");
	else if (t.kind === "issues") s.issues = Sg(t.issues || []);
	else if (t.kind === "evidence") s.evidence = Sg(t.evidence || {});
	else if (t.kind === "layout") {
		if (t.layout_key !== e.layout_key) return r;
		s.layout_revision = Math.max(e.layout_revision, t.layout_revision || 0);
	} else if (t.kind === "binding") {
		let n = t.layout_key !== e.layout_key;
		s.layout_key = t.layout_key, s.layout_session = t.layout_session, s.layout_revision = t.layout_revision || 0, n && s.layout_revision && (s.layout = Sg(t.layout || {}));
	} else return r;
	return {
		value: s,
		dirty: n,
		reset: c,
		accepted: !0
	};
}
// src/viewport.ts
function c_(e, t, n) {
	let r = 0, i = !1, a = 0, o = 0, s = 0, c = 0;
	async function l() {
		let d = a, f = e.getBoundingClientRect();
		if (o = f.width === s && f.height === c ? o + 1 : 0, s = f.width, c = f.height, o >= t && s && c) {
			if (await n(), d !== a) return;
			let t = e.getBoundingClientRect();
			if (t.width !== s || t.height !== c) {
				u();
				return;
			}
			i = !1, e.dataset.fitPending = "false";
		} else r = requestAnimationFrame(l);
	}
	function u() {
		cancelAnimationFrame(r), a += 1, i = !0, o = 0, e.dataset.fitPending = "true", r = requestAnimationFrame(l);
	}
	let d = new ResizeObserver(() => {
		i && u();
	});
	return d.observe(e), {
		request: u,
		destroy() {
			a += 1, cancelAnimationFrame(r), d.disconnect(), i = !1;
		}
	};
}
// src/Editor.svelte
var l_ = /* @__PURE__ */ q("<span>›</span><button> </button>", 1), u_ = /* @__PURE__ */ q("<button draggable=\"true\"><i></i> </button>"), d_ = /* @__PURE__ */ q("<details open=\"\"><summary> </summary><!></details>"), f_ = /* @__PURE__ */ q("<aside class=\"graph-palette\"><h4> </h4> <!></aside>"), p_ = /* @__PURE__ */ q("<!><!><!>", 1), m_ = /* @__PURE__ */ q("<button class=\"remove-edge\"> </button>"), h_ = /* @__PURE__ */ q("<div class=\"graph-issues\" role=\"alert\"> </div>"), g_ = /* @__PURE__ */ q("<span> </span>"), __ = /* @__PURE__ */ q("<div class=\"strategy-graph-app\" role=\"region\"><div class=\"graph-toolbar\"><button>☷</button> <input class=\"graph-search\"/> <button> </button><button> </button> <button> </button><button> </button> <button> </button><button class=\"graph-primary\"> </button> <button> </button><button> </button><label class=\"graph-import\"> <input type=\"file\" accept=\"application/json,.json\"/></label></div> <div class=\"graph-breadcrumb\"><button> </button><!><span class=\"graph-note\"> </span></div> <div><!> <div class=\"graph-canvas\" role=\"region\"><!> <!> <!> <!></div> <!></div> <div class=\"graph-footer\"><span> </span><!><span>Alt+← / Alt+→ · Esc · Ctrl+Z</span></div></div>");
function v_(e, t) {
	M(t, !0);
	let n = /* @__PURE__ */ I(sn(wr(() => Sg(t.initial)))), r = /* @__PURE__ */ I(sn([])), i = /* @__PURE__ */ I(""), a = /* @__PURE__ */ I(""), o = /* @__PURE__ */ I(sn([])), s = /* @__PURE__ */ I(sn([])), c = /* @__PURE__ */ I(""), l = /* @__PURE__ */ I(!1), u = /* @__PURE__ */ I(""), d = /* @__PURE__ */ I(sn([])), f = /* @__PURE__ */ I(sn([])), p = /* @__PURE__ */ I(!0), m = /* @__PURE__ */ I(!1), h, g, v, y = [];
	function b(e) {
		xr().then(() => {
			y.push(performance.now() - e), y.splice(0, Math.max(0, y.length - Number(G(n).config.limits.performance_samples))), h && (h.dataset.navigationTimes = JSON.stringify(y));
		});
	}
	let x = vh(), S = /* @__PURE__ */ P(() => G(n).config.ui), C = /* @__PURE__ */ P(() => wg(G(n).document, G(r))), w = { strategy: xg }, T = /* @__PURE__ */ P(() => G(n).evidence.definition_digest && G(n).compiled_digest !== G(n).evidence.definition_digest);
	function ee() {
		let e = Cg(G(r));
		G(n).layout[e] = {
			positions: Object.fromEntries(G(o).map((e) => [e.id, e.position])),
			viewport: x.getViewport(),
			selected: G(i)
		};
	}
	function E(e = !1) {
		let t = Eg(G(n), G(r));
		L(o, t.nodes.map((e) => ({
			...e,
			selected: e.id === G(i)
		})), !0), G(i) && !G(o).some((e) => e.id === G(i)) && L(i, ""), L(s, t.edges, !0), ne(), e && xr().then(() => v?.request());
	}
	function D() {
		ee(), G(n).edit_revision += 1, L(d, [...G(d), Sg(G(n).document)].slice(-Number(G(n).config.limits.undo_steps)), !0), L(f, [], !0), L(l, !0), G(n).compiled_digest = "", L(c, G(S).modified, !0);
	}
	function te(e) {
		D();
		try {
			e(), E(), t.send("draft", Sg(G(n)));
		} catch (e) {
			L(c, String(e), !0);
		}
	}
	function ne() {
		let e = /* @__PURE__ */ new Set([G(i)]), t = (n, r) => {
			for (let i of G(s).filter((e) => !e.data?.context && (r ? e.target : e.source) === n)) {
				let n = r ? i.source : i.target;
				e.has(n) || (e.add(n), t(n, r));
			}
		};
		G(i) && (t(G(i), !0), t(G(i), !1)), L(o, G(o).map((t) => ({
			...t,
			selected: t.id === G(i),
			class: G(i) && !e.has(t.id) ? "graph-dim" : ""
		})), !0), L(s, G(s).map((t) => ({
			...t,
			class: G(i) && e.has(t.source) && e.has(t.target) && !t.data?.context ? "graph-edge-active" : ""
		})), !0);
	}
	function re(e, t = !0) {
		let n = performance.now();
		L(i, e, !0), L(u, ""), ne();
		let r = G(o).find((t) => t.id === e);
		t && r && x.setCenter(r.position.x + 100, r.position.y + 50, {
			zoom: Math.max(x.getZoom(), .7),
			duration: 0
		}), b(n);
	}
	function ie(e, t = !1) {
		let a = performance.now();
		ee(), L(r, e, !0), L(i, G(n).layout[Cg(G(r))]?.selected || "", !0), E();
		let o = G(n).layout[Cg(G(r))]?.viewport;
		xr().then(() => o ? x.setViewport(o, { duration: 0 }) : x.fitView({
			padding: .15,
			duration: 0
		}));
		let s = new URL(location.href);
		s.searchParams.set("node", Cg(G(r))), t || history.pushState(null, "", s), b(a);
	}
	function ae() {
		G(i).startsWith("s:") && ie([...G(r), G(i).slice(2)]);
	}
	function oe(e, t) {
		te(() => {
			let a = wg(G(n).document, G(r)), o = a.nodes?.find((e) => e.id === G(i));
			o ? o.params = Sg(e) : G(i) === "@portfolio" ? a.portfolio = {
				component: t,
				params: Sg(e)
			} : G(i) === "@risk" ? a.risk = Sg(e) : G(i) === "@execution" && (a.execution = Sg(e));
		});
	}
	function se() {
		let e = wg(G(n).document, G(r));
		e.nodes?.some((e) => e.id === G(i)) && te(() => {
			e.nodes = e.nodes.filter((e) => e.id !== G(i));
			for (let t of e.nodes) kg(e, G(i), t.id);
			e.output === G(i) && (e.output = "universe"), L(i, "");
		});
	}
	function ce() {
		let e = G(C).nodes?.find((e) => e.id === G(i));
		e && te(() => {
			let t = Sg(e);
			t.id = Ag(G(C), e.id + "_copy"), G(C).nodes.push(t), L(i, t.id, !0);
		});
	}
	function le(e) {
		Dg(G(C), G(n), e) ? te(() => Og(G(C), G(n), e)) : L(c, G(S).invalid_edge, !0);
	}
	function ue(e) {
		ee();
		let r = G(e ? d : f);
		if (!r.length) return;
		let i = r.at(-1);
		e ? (L(f, [...G(f), Sg(G(n).document)], !0), L(d, G(d).slice(0, -1), !0)) : (L(d, [...G(d), Sg(G(n).document)], !0), L(f, G(f).slice(0, -1), !0)), G(n).document = Sg(i), G(n).edit_revision += 1, G(n).compiled_digest = "", L(l, !0), E(), t.send("draft", Sg(G(n)));
	}
	function de(e) {
		ee(), t.send(e, Sg(G(n)));
	}
	function fe(e) {
		let o = s_(G(n), e, G(l));
		o.accepted && (L(n, o.value, !0), L(l, o.dirty, !0), o.reset ? (L(r, [], !0), L(i, ""), L(u, ""), L(a, ""), L(d, [], !0), L(f, [], !0), L(c, G(S).no_execute, !0)) : e.kind === "applied" ? L(c, G(S).applied, !0) : e.kind === "layout" && L(c, G(S).saved, !0), E(o.reset), t.send("draft", Sg(G(n))));
	}
	function pe() {
		let e = G(a).toLowerCase();
		if (!e) return;
		let t = G(o).find((t) => (t.id + " " + t.data.component + " " + t.data.label).toLowerCase().includes(e));
		if (t) {
			re(t.id);
			return;
		}
		let r, i = (t, n) => {
			for (let i of t.nodes || []) (i.id + " " + i.component).toLowerCase().includes(e) && !r && (r = {
				path: n,
				id: i.id
			});
			for (let e of t.sleeves || []) i(e.definition, [...n, e.id]);
		};
		if (i(G(n).document, []), r) {
			let e = r;
			ie(e.path), xr().then(() => re(e.id));
		}
	}
	function me() {
		ee(), delete G(n).layout[Cg(G(r))].positions, E(!0);
	}
	function he(e) {
		e.preventDefault();
		let t = e.dataTransfer?.getData("application/aiquant-component");
		t && te(() => {
			let a = jg(G(C), G(n), t);
			L(i, a.id, !0);
			let o = x.screenToFlowPosition({
				x: e.clientX,
				y: e.clientY
			});
			G(n).layout[Cg(G(r))] ??= {}, G(n).layout[Cg(G(r))].positions ??= {}, G(n).layout[Cg(G(r))].positions[a.id] = o;
		});
	}
	function ge() {
		ee(), a_(G(n));
	}
	async function _e(e) {
		try {
			let t = e.target.files?.[0];
			if (!t) return;
			let a = await o_(t, G(n));
			te(() => {
				G(n).document = Sg(a.document), G(n).layout = Sg(a.layout || {}), L(r, [], !0), L(i, "");
			});
		} catch (e) {
			L(c, String(e), !0);
		} finally {
			e.target.value = "";
		}
	}
	function ve(e) {
		if ([
			"INPUT",
			"TEXTAREA",
			"SELECT"
		].includes(e.target.tagName)) return;
		e.key === "Escape" && G(r).length && (e.preventDefault(), ie(G(r).slice(0, -1))), e.key === "Enter" && ae();
		let t = G(C).nodes?.find((e) => e.id === G(i));
		if (e.altKey && e.key === "ArrowLeft" && t?.inputs?.[0] && re(t.inputs[0]), e.altKey && e.key === "ArrowRight") {
			let e = G(C).nodes?.find((e) => (e.inputs || []).includes(G(i)));
			e && re(e.id);
		}
		e.key === "Delete" && se(), (e.ctrlKey || e.metaKey) && e.key === "z" && (e.preventDefault(), ue(!e.shiftKey));
	}
	xa(() => {
		v = c_(g, Number(G(n).config.limits.fit_stable_frames), async () => {
			await x.fitView({
				padding: Number(G(n).config.limits.fit_padding),
				duration: 0
			}), await xr();
		}), v.request();
		let e = () => {
			L(m, !!document.fullscreenElement, !0), E(!0);
		}, t = () => {
			let e = (new URL(location.href).searchParams.get("node") || "main").split("/").slice(1);
			try {
				wg(G(n).document, e), ie(e, !0);
			} catch {
				ie([], !0);
			}
		};
		return t(), window.addEventListener("popstate", t), document.addEventListener("fullscreenchange", e), () => {
			window.removeEventListener("popstate", t), document.removeEventListener("fullscreenchange", e), v?.destroy();
		};
	}), E();
	var ye = { update: fe }, be = __();
	Br("keydown", un, (e) => {
		e.target?.closest(".strategy-graph-app") && ve(e);
	});
	var xe = R(be), Se = R(xe), Ce = V(Se, 2);
	Qi(Ce);
	var O = V(Ce, 2), we = B(O, !0), k = V(O), Te = B(k, !0), Ee = V(k, 2), Oe = B(Ee, !0), ke = V(Ee), Ae = B(ke, !0), je = V(ke, 2), Me = B(je, !0), Ne = V(je), Pe = B(Ne, !0), Fe = V(Ne, 2), Ie = B(Fe, !0), Le = V(Fe), Re = B(Le, !0), ze = V(Le), Be = R(ze, !0), Ve = V(Be);
	A(ze), A(xe);
	var He = V(xe, 2), Ue = R(He), We = B(Ue, !0), Ge = V(Ue);
	mi(Ge, 17, () => G(r), ui, (e, t, n) => {
		var i = l_(), a = V(z(i)), o = B(a, !0);
		H(() => Y(o, G(t))), K("click", a, () => ie(G(r).slice(0, n + 1))), J(e, i);
	});
	var Ke = B(V(Ge), !0);
	A(He);
	var qe = V(He, 2);
	let Je, Ye;
	var Xe = R(qe), Ze = (e) => {
		var t = f_(), r = R(t), a = B(r, !0);
		mi(V(r, 2), 17, () => Object.entries(G(n).config.groups).filter(([e]) => [
			"filter",
			"factor",
			"scorer",
			"ensemble",
			"agent"
		].includes(e)), ui, (e, t) => {
			var r = /* @__PURE__ */ P(() => _(G(t), 2));
			let a = () => G(r)[0], o = () => G(r)[1];
			var s = d_(), c = R(s), l = B(c, !0);
			mi(V(c), 17, () => Object.entries(G(n).schema.components).filter(([, e]) => e.kind === a()), ui, (e, t) => {
				var r = /* @__PURE__ */ P(() => _(G(t), 2));
				let s = () => G(r)[0], c = () => G(r)[1];
				var l = u_(), u = R(l);
				let d;
				var f = V(u, 1, !0);
				A(l), H((e) => {
					Z(l, "title", G(n).config.help[a()]), l.disabled = e, d = Pi(u, "", d, { background: o().color }), Y(f, c().label);
				}, [() => !!G(C).sleeves?.length]), Br("dragstart", l, (e) => e.dataTransfer?.setData("application/aiquant-component", s())), K("click", l, () => te(() => {
					L(i, jg(G(C), G(n), s()).id, !0);
				})), J(e, l);
			}), A(s), H(() => Y(l, o().label)), J(e, s);
		}), A(t), H(() => Y(a, G(S).add)), J(e, t);
	};
	X(Xe, (e) => {
		G(p) && e(Ze);
	});
	var j = V(Xe, 2), Qe = R(j);
	{
		let e = /* @__PURE__ */ P(() => Number(G(n).config.limits.min_zoom)), t = /* @__PURE__ */ P(() => Number(G(n).config.limits.max_zoom));
		Fh(Qe, {
			get nodeTypes() {
				return w;
			},
			fitView: !0,
			get minZoom() {
				return G(e);
			},
			get maxZoom() {
				return G(t);
			},
			deleteKey: null,
			isValidConnection: (e) => Dg(G(C), G(n), e),
			onconnect: le,
			onnodeclick: ({ node: e, event: t }) => {
				re(e.id, !1), t instanceof MouseEvent && t.detail === 2 && ae();
			},
			onedgeclick: ({ edge: e }) => {
				L(u, e.data?.protected ? "" : e.id, !0);
			},
			onnodedragstop: () => ee(),
			get nodes() {
				return G(o);
			},
			set nodes(e) {
				L(o, e, !0);
			},
			get edges() {
				return G(s);
			},
			set edges(e) {
				L(s, e, !0);
			},
			children: (e, t) => {
				var n = p_(), r = z(n);
				sg(r, {});
				var i = V(r);
				$h(i, {}), _g(V(i), {
					pannable: !0,
					zoomable: !0,
					nodeColor: (e) => String(e.data.color || "#64748b")
				}), J(e, n);
			},
			$$slots: { default: !0 }
		});
	}
	var $e = V(Qe, 2), et = (e) => {
		var t = m_(), n = B(t, !0);
		H(() => Y(n, G(S).delete_edge)), K("click", t, () => {
			let e = G(s).find((e) => e.id === G(u));
			e && te(() => kg(G(C), e.source, e.target)), L(u, "");
		}), J(e, t);
	};
	X($e, (e) => {
		G(u) && e(et);
	});
	var tt = V($e, 2), nt = (e) => {
		var t = h_(), r = B(t, !0);
		H((e) => Y(r, e), [() => G(n).issues.join("\n")]), J(e, t);
	};
	X(tt, (e) => {
		G(n).issues.length && e(nt);
	});
	var rt = V(tt, 2), it = (e) => {
		var t = h_(), r = B(t, !0);
		H(() => Y(r, G(n).evidence.error)), J(e, t);
	};
	X(rt, (e) => {
		G(n).evidence.error && e(it);
	}), A(j), fa(j, (e) => g = e, () => g), i_(V(j, 2), {
		get payload() {
			return G(n);
		},
		get path() {
			return G(r);
		},
		get selected() {
			return G(i);
		},
		onselect: re,
		onupdate: oe,
		onremove: se,
		onduplicate: ce,
		onoutput: () => te(() => G(C).output = G(i)),
		onenter: ae,
		onbudget: (e) => te(() => {
			let t = G(C).sleeves?.find((e) => "s:" + e.id === G(i));
			t && (t.budget = e);
		})
	}), A(qe);
	var at = V(qe, 2), ot = R(at);
	let st;
	var ct = B(ot, !0), lt = V(ot), ut = (e) => {
		var t = g_(), r = B(t);
		H(() => Y(r, `${G(n).evidence.run_id ?? ""} · ${G(n).evidence.status ?? ""}`)), J(e, t);
	};
	return X(lt, (e) => {
		G(n).evidence.run_id && e(ut);
	}), De(), A(at), A(be), fa(be, (e) => h = e, () => h), H((e) => {
		Z(be, "data-doc-id", G(n).doc_id), Z(be, "aria-label", G(S).title), Z(Se, "aria-label", G(S).add), Z(Ce, "aria-label", G(S).search), Z(Ce, "placeholder", G(S).search_placeholder), Y(we, G(S).fit), Y(Te, G(S).arrange), Ee.disabled = !G(d).length, Y(Oe, G(S).undo), ke.disabled = !G(f).length, Y(Ae, G(S).redo), Y(Me, G(S).save_layout), Y(Pe, G(S).apply), Y(Ie, G(m) ? G(S).leave_fullscreen : G(S).fullscreen), Y(Re, G(S).export), Y(Be, G(S).import), Y(We, G(n).document.name), Y(Ke, G(c) || G(S).no_execute), Je = Mi(qe, 1, "graph-body", null, Je, { "hide-menu": !G(p) }), Ye = Pi(qe, "", Ye, { "--canvas-height": `min(${G(n).config.limits.canvas_height}px, max(${G(n).config.limits.canvas_min_height}px, calc(100dvh - ${G(n).config.limits.canvas_viewport_offset}px)))` }), Z(j, "aria-label", G(S).title), st = Mi(ot, 1, "", null, st, { "graph-warning": e }), Y(ct, G(T) ? G(S).stale : G(l) ? G(S).modified : G(S).clean);
	}, [() => !!G(T)]), K("click", Se, () => L(p, !G(p))), K("keydown", Ce, (e) => {
		e.key === "Enter" && pe();
	}), oa(Ce, () => G(a), (e) => L(a, e)), K("click", O, () => x.fitView({
		padding: .15,
		duration: 0
	})), K("click", k, me), K("click", Ee, () => ue(!0)), K("click", ke, () => ue(!1)), K("click", je, () => de("layout")), K("click", Ne, () => de("apply")), K("click", Fe, () => (G(m) ? document.exitFullscreen() : h.requestFullscreen()).catch((e) => L(c, String(e), !0))), K("click", Le, ge), K("change", Ve, _e), K("click", Ue, () => ie([])), Br("drop", j, he), Br("dragover", j, (e) => e.preventDefault()), J(e, be), N(ye);
}
Vr([
	"click",
	"keydown",
	"change"
]);
// src/Root.svelte
function y_(e, t) {
	M(t, !0);
	let n;
	function r(e) {
		n?.update(e);
	}
	var i = { update: r };
	return Ih(e, {
		children: (e, r) => {
			fa(v_(e, {
				get initial() {
					return t.initial;
				},
				get send() {
					return t.send;
				}
			}), (e) => n = e, () => n);
		},
		$$slots: { default: !0 }
	}), N(i);
}
// src/index.ts
var b_ = class extends HTMLElement {
	cleanup;
	disconnectedCallback() {
		this.cleanup?.();
	}
};
customElements.get("aiquant-strategy-graph") || customElements.define("aiquant-strategy-graph", b_);
function x_(e, t, n) {
	let r = ri(y_, {
		target: e,
		props: {
			initial: t,
			send: n
		}
	});
	Ht();
	let i = !1, a = () => {
		i || (i = !0, si(r));
	};
	return e.cleanup = a, {
		update: (e) => {
			i || r.update(e);
		},
		destroy: a
	};
}
export { x_ as mountGraph };
