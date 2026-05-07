import J, { useState as ne, useCallback as z, useRef as be, useEffect as le } from "react";
function Ir(r) {
  return r && r.__esModule && Object.prototype.hasOwnProperty.call(r, "default") ? r.default : r;
}
var Oe = { exports: {} }, re = {};
/**
 * @license React
 * react-jsx-runtime.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
var qe;
function $r() {
  if (qe) return re;
  qe = 1;
  var r = J, n = Symbol.for("react.element"), s = Symbol.for("react.fragment"), i = Object.prototype.hasOwnProperty, o = r.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED.ReactCurrentOwner, u = { key: !0, ref: !0, __self: !0, __source: !0 };
  function y(T, _, v) {
    var l, f = {}, g = null, d = null;
    v !== void 0 && (g = "" + v), _.key !== void 0 && (g = "" + _.key), _.ref !== void 0 && (d = _.ref);
    for (l in _) i.call(_, l) && !u.hasOwnProperty(l) && (f[l] = _[l]);
    if (T && T.defaultProps) for (l in _ = T.defaultProps, _) f[l] === void 0 && (f[l] = _[l]);
    return { $$typeof: n, type: T, key: g, ref: d, props: f, _owner: o.current };
  }
  return re.Fragment = s, re.jsx = y, re.jsxs = y, re;
}
var te = {};
/**
 * @license React
 * react-jsx-runtime.development.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
var Xe;
function Nr() {
  return Xe || (Xe = 1, process.env.NODE_ENV !== "production" && function() {
    var r = J, n = Symbol.for("react.element"), s = Symbol.for("react.portal"), i = Symbol.for("react.fragment"), o = Symbol.for("react.strict_mode"), u = Symbol.for("react.profiler"), y = Symbol.for("react.provider"), T = Symbol.for("react.context"), _ = Symbol.for("react.forward_ref"), v = Symbol.for("react.suspense"), l = Symbol.for("react.suspense_list"), f = Symbol.for("react.memo"), g = Symbol.for("react.lazy"), d = Symbol.for("react.offscreen"), p = Symbol.iterator, b = "@@iterator";
    function R(e) {
      if (e === null || typeof e != "object")
        return null;
      var t = p && e[p] || e[b];
      return typeof t == "function" ? t : null;
    }
    var j = r.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED;
    function E(e) {
      {
        for (var t = arguments.length, a = new Array(t > 1 ? t - 1 : 0), m = 1; m < t; m++)
          a[m - 1] = arguments[m];
        D("error", e, a);
      }
    }
    function D(e, t, a) {
      {
        var m = j.ReactDebugCurrentFrame, w = m.getStackAddendum();
        w !== "" && (t += "%s", a = a.concat([w]));
        var k = a.map(function(C) {
          return String(C);
        });
        k.unshift("Warning: " + t), Function.prototype.apply.call(console[e], console, k);
      }
    }
    var W = !1, F = !1, O = !1, x = !1, h = !1, B;
    B = Symbol.for("react.module.reference");
    function I(e) {
      return !!(typeof e == "string" || typeof e == "function" || e === i || e === u || h || e === o || e === v || e === l || x || e === d || W || F || O || typeof e == "object" && e !== null && (e.$$typeof === g || e.$$typeof === f || e.$$typeof === y || e.$$typeof === T || e.$$typeof === _ || // This needs to include all possible module reference object
      // types supported by any Flight configuration anywhere since
      // we don't know which Flight build this will end up being used
      // with.
      e.$$typeof === B || e.getModuleId !== void 0));
    }
    function q(e, t, a) {
      var m = e.displayName;
      if (m)
        return m;
      var w = t.displayName || t.name || "";
      return w !== "" ? a + "(" + w + ")" : a;
    }
    function we(e) {
      return e.displayName || "Context";
    }
    function Y(e) {
      if (e == null)
        return null;
      if (typeof e.tag == "number" && E("Received an unexpected object in getComponentNameFromType(). This is likely a bug in React. Please file an issue."), typeof e == "function")
        return e.displayName || e.name || null;
      if (typeof e == "string")
        return e;
      switch (e) {
        case i:
          return "Fragment";
        case s:
          return "Portal";
        case u:
          return "Profiler";
        case o:
          return "StrictMode";
        case v:
          return "Suspense";
        case l:
          return "SuspenseList";
      }
      if (typeof e == "object")
        switch (e.$$typeof) {
          case T:
            var t = e;
            return we(t) + ".Consumer";
          case y:
            var a = e;
            return we(a._context) + ".Provider";
          case _:
            return q(e, e.render, "ForwardRef");
          case f:
            var m = e.displayName || null;
            return m !== null ? m : Y(e.type) || "Memo";
          case g: {
            var w = e, k = w._payload, C = w._init;
            try {
              return Y(C(k));
            } catch {
              return null;
            }
          }
        }
      return null;
    }
    var H = Object.assign, Q = 0, Re, je, Te, ke, Fe, De, Ae;
    function Pe() {
    }
    Pe.__reactDisabledLog = !0;
    function dr() {
      {
        if (Q === 0) {
          Re = console.log, je = console.info, Te = console.warn, ke = console.error, Fe = console.group, De = console.groupCollapsed, Ae = console.groupEnd;
          var e = {
            configurable: !0,
            enumerable: !0,
            value: Pe,
            writable: !0
          };
          Object.defineProperties(console, {
            info: e,
            log: e,
            warn: e,
            error: e,
            group: e,
            groupCollapsed: e,
            groupEnd: e
          });
        }
        Q++;
      }
    }
    function fr() {
      {
        if (Q--, Q === 0) {
          var e = {
            configurable: !0,
            enumerable: !0,
            writable: !0
          };
          Object.defineProperties(console, {
            log: H({}, e, {
              value: Re
            }),
            info: H({}, e, {
              value: je
            }),
            warn: H({}, e, {
              value: Te
            }),
            error: H({}, e, {
              value: ke
            }),
            group: H({}, e, {
              value: Fe
            }),
            groupCollapsed: H({}, e, {
              value: De
            }),
            groupEnd: H({}, e, {
              value: Ae
            })
          });
        }
        Q < 0 && E("disabledDepth fell below zero. This is a bug in React. Please file an issue.");
      }
    }
    var de = j.ReactCurrentDispatcher, fe;
    function oe(e, t, a) {
      {
        if (fe === void 0)
          try {
            throw Error();
          } catch (w) {
            var m = w.stack.trim().match(/\n( *(at )?)/);
            fe = m && m[1] || "";
          }
        return `
` + fe + e;
      }
    }
    var pe = !1, se;
    {
      var pr = typeof WeakMap == "function" ? WeakMap : Map;
      se = new pr();
    }
    function Be(e, t) {
      if (!e || pe)
        return "";
      {
        var a = se.get(e);
        if (a !== void 0)
          return a;
      }
      var m;
      pe = !0;
      var w = Error.prepareStackTrace;
      Error.prepareStackTrace = void 0;
      var k;
      k = de.current, de.current = null, dr();
      try {
        if (t) {
          var C = function() {
            throw Error();
          };
          if (Object.defineProperty(C.prototype, "props", {
            set: function() {
              throw Error();
            }
          }), typeof Reflect == "object" && Reflect.construct) {
            try {
              Reflect.construct(C, []);
            } catch (N) {
              m = N;
            }
            Reflect.construct(e, [], C);
          } else {
            try {
              C.call();
            } catch (N) {
              m = N;
            }
            e.call(C.prototype);
          }
        } else {
          try {
            throw Error();
          } catch (N) {
            m = N;
          }
          e();
        }
      } catch (N) {
        if (N && m && typeof N.stack == "string") {
          for (var S = N.stack.split(`
`), $ = m.stack.split(`
`), P = S.length - 1, L = $.length - 1; P >= 1 && L >= 0 && S[P] !== $[L]; )
            L--;
          for (; P >= 1 && L >= 0; P--, L--)
            if (S[P] !== $[L]) {
              if (P !== 1 || L !== 1)
                do
                  if (P--, L--, L < 0 || S[P] !== $[L]) {
                    var M = `
` + S[P].replace(" at new ", " at ");
                    return e.displayName && M.includes("<anonymous>") && (M = M.replace("<anonymous>", e.displayName)), typeof e == "function" && se.set(e, M), M;
                  }
                while (P >= 1 && L >= 0);
              break;
            }
        }
      } finally {
        pe = !1, de.current = k, fr(), Error.prepareStackTrace = w;
      }
      var Z = e ? e.displayName || e.name : "", K = Z ? oe(Z) : "";
      return typeof e == "function" && se.set(e, K), K;
    }
    function gr(e, t, a) {
      return Be(e, !1);
    }
    function hr(e) {
      var t = e.prototype;
      return !!(t && t.isReactComponent);
    }
    function ie(e, t, a) {
      if (e == null)
        return "";
      if (typeof e == "function")
        return Be(e, hr(e));
      if (typeof e == "string")
        return oe(e);
      switch (e) {
        case v:
          return oe("Suspense");
        case l:
          return oe("SuspenseList");
      }
      if (typeof e == "object")
        switch (e.$$typeof) {
          case _:
            return gr(e.render);
          case f:
            return ie(e.type, t, a);
          case g: {
            var m = e, w = m._payload, k = m._init;
            try {
              return ie(k(w), t, a);
            } catch {
            }
          }
        }
      return "";
    }
    var ee = Object.prototype.hasOwnProperty, Le = {}, We = j.ReactDebugCurrentFrame;
    function ae(e) {
      if (e) {
        var t = e._owner, a = ie(e.type, e._source, t ? t.type : null);
        We.setExtraStackFrame(a);
      } else
        We.setExtraStackFrame(null);
    }
    function mr(e, t, a, m, w) {
      {
        var k = Function.call.bind(ee);
        for (var C in e)
          if (k(e, C)) {
            var S = void 0;
            try {
              if (typeof e[C] != "function") {
                var $ = Error((m || "React class") + ": " + a + " type `" + C + "` is invalid; it must be a function, usually from the `prop-types` package, but received `" + typeof e[C] + "`.This often happens because of typos such as `PropTypes.function` instead of `PropTypes.func`.");
                throw $.name = "Invariant Violation", $;
              }
              S = e[C](t, C, m, a, null, "SECRET_DO_NOT_PASS_THIS_OR_YOU_WILL_BE_FIRED");
            } catch (P) {
              S = P;
            }
            S && !(S instanceof Error) && (ae(w), E("%s: type specification of %s `%s` is invalid; the type checker function must return `null` or an `Error` but returned a %s. You may have forgotten to pass an argument to the type checker creator (arrayOf, instanceOf, objectOf, oneOf, oneOfType, and shape all require an argument).", m || "React class", a, C, typeof S), ae(null)), S instanceof Error && !(S.message in Le) && (Le[S.message] = !0, ae(w), E("Failed %s type: %s", a, S.message), ae(null));
          }
      }
    }
    var vr = Array.isArray;
    function ge(e) {
      return vr(e);
    }
    function yr(e) {
      {
        var t = typeof Symbol == "function" && Symbol.toStringTag, a = t && e[Symbol.toStringTag] || e.constructor.name || "Object";
        return a;
      }
    }
    function br(e) {
      try {
        return Ie(e), !1;
      } catch {
        return !0;
      }
    }
    function Ie(e) {
      return "" + e;
    }
    function $e(e) {
      if (br(e))
        return E("The provided key is an unsupported type %s. This value must be coerced to a string before before using it here.", yr(e)), Ie(e);
    }
    var Ne = j.ReactCurrentOwner, Er = {
      key: !0,
      ref: !0,
      __self: !0,
      __source: !0
    }, Me, Ve;
    function _r(e) {
      if (ee.call(e, "ref")) {
        var t = Object.getOwnPropertyDescriptor(e, "ref").get;
        if (t && t.isReactWarning)
          return !1;
      }
      return e.ref !== void 0;
    }
    function xr(e) {
      if (ee.call(e, "key")) {
        var t = Object.getOwnPropertyDescriptor(e, "key").get;
        if (t && t.isReactWarning)
          return !1;
      }
      return e.key !== void 0;
    }
    function Sr(e, t) {
      typeof e.ref == "string" && Ne.current;
    }
    function Or(e, t) {
      {
        var a = function() {
          Me || (Me = !0, E("%s: `key` is not a prop. Trying to access it will result in `undefined` being returned. If you need to access the same value within the child component, you should pass it as a different prop. (https://reactjs.org/link/special-props)", t));
        };
        a.isReactWarning = !0, Object.defineProperty(e, "key", {
          get: a,
          configurable: !0
        });
      }
    }
    function Cr(e, t) {
      {
        var a = function() {
          Ve || (Ve = !0, E("%s: `ref` is not a prop. Trying to access it will result in `undefined` being returned. If you need to access the same value within the child component, you should pass it as a different prop. (https://reactjs.org/link/special-props)", t));
        };
        a.isReactWarning = !0, Object.defineProperty(e, "ref", {
          get: a,
          configurable: !0
        });
      }
    }
    var wr = function(e, t, a, m, w, k, C) {
      var S = {
        // This tag allows us to uniquely identify this as a React Element
        $$typeof: n,
        // Built-in properties that belong on the element
        type: e,
        key: t,
        ref: a,
        props: C,
        // Record the component responsible for creating this element.
        _owner: k
      };
      return S._store = {}, Object.defineProperty(S._store, "validated", {
        configurable: !1,
        enumerable: !1,
        writable: !0,
        value: !1
      }), Object.defineProperty(S, "_self", {
        configurable: !1,
        enumerable: !1,
        writable: !1,
        value: m
      }), Object.defineProperty(S, "_source", {
        configurable: !1,
        enumerable: !1,
        writable: !1,
        value: w
      }), Object.freeze && (Object.freeze(S.props), Object.freeze(S)), S;
    };
    function Rr(e, t, a, m, w) {
      {
        var k, C = {}, S = null, $ = null;
        a !== void 0 && ($e(a), S = "" + a), xr(t) && ($e(t.key), S = "" + t.key), _r(t) && ($ = t.ref, Sr(t, w));
        for (k in t)
          ee.call(t, k) && !Er.hasOwnProperty(k) && (C[k] = t[k]);
        if (e && e.defaultProps) {
          var P = e.defaultProps;
          for (k in P)
            C[k] === void 0 && (C[k] = P[k]);
        }
        if (S || $) {
          var L = typeof e == "function" ? e.displayName || e.name || "Unknown" : e;
          S && Or(C, L), $ && Cr(C, L);
        }
        return wr(e, S, $, w, m, Ne.current, C);
      }
    }
    var he = j.ReactCurrentOwner, ze = j.ReactDebugCurrentFrame;
    function X(e) {
      if (e) {
        var t = e._owner, a = ie(e.type, e._source, t ? t.type : null);
        ze.setExtraStackFrame(a);
      } else
        ze.setExtraStackFrame(null);
    }
    var me;
    me = !1;
    function ve(e) {
      return typeof e == "object" && e !== null && e.$$typeof === n;
    }
    function Ue() {
      {
        if (he.current) {
          var e = Y(he.current.type);
          if (e)
            return `

Check the render method of \`` + e + "`.";
        }
        return "";
      }
    }
    function jr(e) {
      return "";
    }
    var Ye = {};
    function Tr(e) {
      {
        var t = Ue();
        if (!t) {
          var a = typeof e == "string" ? e : e.displayName || e.name;
          a && (t = `

Check the top-level render call using <` + a + ">.");
        }
        return t;
      }
    }
    function Ge(e, t) {
      {
        if (!e._store || e._store.validated || e.key != null)
          return;
        e._store.validated = !0;
        var a = Tr(t);
        if (Ye[a])
          return;
        Ye[a] = !0;
        var m = "";
        e && e._owner && e._owner !== he.current && (m = " It was passed a child from " + Y(e._owner.type) + "."), X(e), E('Each child in a list should have a unique "key" prop.%s%s See https://reactjs.org/link/warning-keys for more information.', a, m), X(null);
      }
    }
    function He(e, t) {
      {
        if (typeof e != "object")
          return;
        if (ge(e))
          for (var a = 0; a < e.length; a++) {
            var m = e[a];
            ve(m) && Ge(m, t);
          }
        else if (ve(e))
          e._store && (e._store.validated = !0);
        else if (e) {
          var w = R(e);
          if (typeof w == "function" && w !== e.entries)
            for (var k = w.call(e), C; !(C = k.next()).done; )
              ve(C.value) && Ge(C.value, t);
        }
      }
    }
    function kr(e) {
      {
        var t = e.type;
        if (t == null || typeof t == "string")
          return;
        var a;
        if (typeof t == "function")
          a = t.propTypes;
        else if (typeof t == "object" && (t.$$typeof === _ || // Note: Memo only checks outer props here.
        // Inner props are checked in the reconciler.
        t.$$typeof === f))
          a = t.propTypes;
        else
          return;
        if (a) {
          var m = Y(t);
          mr(a, e.props, "prop", m, e);
        } else if (t.PropTypes !== void 0 && !me) {
          me = !0;
          var w = Y(t);
          E("Component %s declared `PropTypes` instead of `propTypes`. Did you misspell the property assignment?", w || "Unknown");
        }
        typeof t.getDefaultProps == "function" && !t.getDefaultProps.isReactClassApproved && E("getDefaultProps is only used on classic React.createClass definitions. Use a static property named `defaultProps` instead.");
      }
    }
    function Fr(e) {
      {
        for (var t = Object.keys(e.props), a = 0; a < t.length; a++) {
          var m = t[a];
          if (m !== "children" && m !== "key") {
            X(e), E("Invalid prop `%s` supplied to `React.Fragment`. React.Fragment can only have `key` and `children` props.", m), X(null);
            break;
          }
        }
        e.ref !== null && (X(e), E("Invalid attribute `ref` supplied to `React.Fragment`."), X(null));
      }
    }
    var Ke = {};
    function Je(e, t, a, m, w, k) {
      {
        var C = I(e);
        if (!C) {
          var S = "";
          (e === void 0 || typeof e == "object" && e !== null && Object.keys(e).length === 0) && (S += " You likely forgot to export your component from the file it's defined in, or you might have mixed up default and named imports.");
          var $ = jr();
          $ ? S += $ : S += Ue();
          var P;
          e === null ? P = "null" : ge(e) ? P = "array" : e !== void 0 && e.$$typeof === n ? (P = "<" + (Y(e.type) || "Unknown") + " />", S = " Did you accidentally export a JSX literal instead of a component?") : P = typeof e, E("React.jsx: type is invalid -- expected a string (for built-in components) or a class/function (for composite components) but got: %s.%s", P, S);
        }
        var L = Rr(e, t, a, w, k);
        if (L == null)
          return L;
        if (C) {
          var M = t.children;
          if (M !== void 0)
            if (m)
              if (ge(M)) {
                for (var Z = 0; Z < M.length; Z++)
                  He(M[Z], e);
                Object.freeze && Object.freeze(M);
              } else
                E("React.jsx: Static children should always be an array. You are likely explicitly calling React.jsxs or React.jsxDEV. Use the Babel transform instead.");
            else
              He(M, e);
        }
        if (ee.call(t, "key")) {
          var K = Y(e), N = Object.keys(t).filter(function(Wr) {
            return Wr !== "key";
          }), ye = N.length > 0 ? "{key: someKey, " + N.join(": ..., ") + ": ...}" : "{key: someKey}";
          if (!Ke[K + ye]) {
            var Lr = N.length > 0 ? "{" + N.join(": ..., ") + ": ...}" : "{}";
            E(`A props object containing a "key" prop is being spread into JSX:
  let props = %s;
  <%s {...props} />
React keys must be passed directly to JSX without using spread:
  let props = %s;
  <%s key={someKey} {...props} />`, ye, K, Lr, K), Ke[K + ye] = !0;
          }
        }
        return e === i ? Fr(L) : kr(L), L;
      }
    }
    function Dr(e, t, a) {
      return Je(e, t, a, !0);
    }
    function Ar(e, t, a) {
      return Je(e, t, a, !1);
    }
    var Pr = Ar, Br = Dr;
    te.Fragment = i, te.jsx = Pr, te.jsxs = Br;
  }()), te;
}
process.env.NODE_ENV === "production" ? Oe.exports = $r() : Oe.exports = Nr();
var c = Oe.exports;
const Ze = {
  high: 0.9,
  medium: 0.7,
  low: 0.5
}, ar = {
  high: {
    primary: "#10B981",
    // Green-500
    hover: "#059669",
    // Green-600
    background: "#D1FAE5",
    // Green-100
    border: "#6EE7B7",
    // Green-300
    text: "#065F46"
    // Green-800
  },
  medium: {
    primary: "#F59E0B",
    // Amber-500
    hover: "#D97706",
    // Amber-600
    background: "#FEF3C7",
    // Amber-100
    border: "#FCD34D",
    // Amber-300
    text: "#92400E"
    // Amber-800
  },
  low: {
    primary: "#EF4444",
    // Red-500
    hover: "#DC2626",
    // Red-600
    background: "#FEE2E2",
    // Red-100
    border: "#FCA5A5",
    // Red-300
    text: "#991B1B"
    // Red-800
  }
}, Mr = {
  high: "🟢",
  medium: "🟡",
  low: "🔴"
}, Vr = {
  high: "✓",
  // Checkmark
  medium: "⚠",
  // Warning
  low: "ℹ️"
  // Info
};
function bt(r) {
  return r >= Ze.high ? "high" : r >= Ze.medium ? "medium" : "low";
}
function zr(r) {
  return {
    high: "High Confidence",
    medium: "Medium Confidence",
    low: "Low Confidence"
  }[r];
}
function cr(r) {
  return `${(r * 100).toFixed(0)}%`;
}
function Et(r) {
  return {
    high: {
      container: "bg-green-100 border-green-300",
      badge: "bg-green-500 text-white",
      text: "text-green-800"
    },
    medium: {
      container: "bg-amber-100 border-amber-300",
      badge: "bg-amber-500 text-white",
      text: "text-amber-800"
    },
    low: {
      container: "bg-red-100 border-red-300",
      badge: "bg-red-500 text-white",
      text: "text-red-800"
    }
  }[r];
}
const Ur = "/api/v1";
async function G(r, n = {}) {
  const s = await fetch(`${Ur}${r}`, {
    headers: {
      "Content-Type": "application/json",
      ...n.headers
    },
    ...n
  });
  if (!s.ok) {
    const i = await s.json().catch(() => ({ error: s.statusText }));
    throw new Error(i.error || i.message || "API request failed");
  }
  return s.json();
}
async function Yr(r, n) {
  return G(
    `/suggestions/entity/${n}`
  );
}
async function Gr(r, n) {
  return G(
    `/suggestions/entity/${n}/refresh`,
    { method: "POST" }
  );
}
async function Hr(r, n, s, i) {
  return G(
    `/suggestions/${s}/dismiss?entity_id=${encodeURIComponent(n)}`,
    {
      method: "POST",
      body: JSON.stringify({
        reason: i
      })
    }
  );
}
async function Kr(r, n, s, i, o, u) {
  return G(
    "/suggestions/linking/create-relationship",
    {
      method: "POST",
      body: JSON.stringify({
        entity_id_1: n,
        entity_id_2: s,
        relationship_type: i,
        reason: o,
        confidence: u
      })
    }
  );
}
async function Jr(r, n, s, i, o) {
  return G(
    "/suggestions/linking/merge-entities",
    {
      method: "POST",
      body: JSON.stringify({
        entity_id_1: n,
        entity_id_2: s,
        keep_entity_id: i,
        reason: o
      })
    }
  );
}
async function _t(r, n, s, i, o) {
  return G(
    "/suggestions/linking/data-items",
    {
      method: "POST",
      body: JSON.stringify({
        data_id_1: n,
        data_id_2: s,
        reason: i,
        confidence: o
      })
    }
  );
}
async function xt(r, n, s, i) {
  return G(
    "/suggestions/linking/orphan-to-entity",
    {
      method: "POST",
      body: JSON.stringify({
        orphan_id: n,
        entity_id: s,
        reason: i
      })
    }
  );
}
async function St(r) {
  return G("/suggestions/summary");
}
const qr = {
  badge: {
    display: "inline-flex",
    alignItems: "center",
    gap: "4px",
    padding: "4px 8px",
    borderRadius: "4px",
    fontSize: "12px",
    fontWeight: 600,
    lineHeight: 1,
    whiteSpace: "nowrap"
  },
  pill: {
    display: "inline-flex",
    alignItems: "center",
    gap: "4px",
    padding: "2px 10px",
    borderRadius: "9999px",
    fontSize: "11px",
    fontWeight: 600,
    lineHeight: 1.2,
    whiteSpace: "nowrap"
  },
  compact: {
    display: "inline-flex",
    alignItems: "center",
    gap: "2px",
    padding: "2px 6px",
    borderRadius: "4px",
    fontSize: "11px",
    fontWeight: 600,
    lineHeight: 1,
    whiteSpace: "nowrap"
  }
};
function ue({
  level: r,
  score: n,
  variant: s = "badge",
  showScore: i = !0,
  showIcon: o = !0,
  className: u = ""
}) {
  const y = ar[r], T = Mr[r], _ = Vr[r], v = zr(r), l = cr(n), f = qr[s], g = {
    backgroundColor: y.background,
    color: y.text,
    border: `1px solid ${y.border}`
  };
  return /* @__PURE__ */ c.jsxs(
    "span",
    {
      className: `suggestion-badge suggestion-badge--${r} suggestion-badge--${s} ${u}`,
      style: { ...f, ...g },
      role: "status",
      "aria-label": `${v}: ${l}`,
      children: [
        /* @__PURE__ */ c.jsx("span", { "aria-hidden": "true", children: T }),
        o && /* @__PURE__ */ c.jsx("span", { className: "suggestion-badge__icon", "aria-hidden": "true", children: _ }),
        s !== "compact" && /* @__PURE__ */ c.jsx("span", { className: "suggestion-badge__label", children: v.toUpperCase() }),
        i && /* @__PURE__ */ c.jsxs("span", { className: "suggestion-badge__score", children: [
          "(",
          l,
          ")"
        ] })
      ]
    }
  );
}
function Xr({ factor: r }) {
  return /* @__PURE__ */ c.jsxs("div", { className: "suggestion-card__factor", style: Zr, children: [
    /* @__PURE__ */ c.jsx("span", { className: "suggestion-card__factor-check", style: { color: "#10B981" }, children: "✓" }),
    /* @__PURE__ */ c.jsx("span", { className: "suggestion-card__factor-name", style: { flex: 1 }, children: r.name }),
    /* @__PURE__ */ c.jsxs("span", { className: "suggestion-card__factor-score", style: { color: "#6B7280", fontSize: "12px" }, children: [
      "(Weight: ",
      r.weight.toFixed(1),
      ", Score: ",
      r.score.toFixed(2),
      ")"
    ] })
  ] });
}
const Zr = {
  display: "flex",
  alignItems: "center",
  gap: "8px",
  padding: "4px 0",
  fontSize: "13px"
}, A = {
  card: {
    border: "1px solid #E5E7EB",
    borderRadius: "8px",
    backgroundColor: "#FFFFFF",
    overflow: "hidden",
    marginBottom: "12px"
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "12px 16px",
    borderBottom: "1px solid #E5E7EB"
  },
  body: {
    padding: "16px"
  },
  matchInfo: {
    fontSize: "14px",
    marginBottom: "12px"
  },
  matchValue: {
    fontWeight: 600,
    fontFamily: "monospace"
  },
  arrow: {
    color: "#9CA3AF",
    margin: "4px 0"
  },
  target: {
    color: "#6B7280",
    fontSize: "13px"
  },
  divider: {
    borderTop: "1px dashed #E5E7EB",
    margin: "12px 0"
  },
  expandButton: {
    display: "flex",
    alignItems: "center",
    gap: "4px",
    background: "none",
    border: "none",
    cursor: "pointer",
    color: "#3B82F6",
    fontSize: "13px",
    padding: "4px 0"
  },
  factorsSection: {
    marginTop: "12px",
    padding: "12px",
    backgroundColor: "#F9FAFB",
    borderRadius: "6px"
  },
  factorsTitle: {
    fontWeight: 600,
    fontSize: "13px",
    marginBottom: "8px"
  },
  totalScore: {
    marginTop: "12px",
    paddingTop: "8px",
    borderTop: "1px solid #E5E7EB",
    fontSize: "13px"
  },
  lastUpdated: {
    color: "#9CA3AF",
    fontSize: "12px",
    marginTop: "8px"
  },
  footer: {
    display: "flex",
    gap: "8px",
    padding: "12px 16px",
    borderTop: "1px solid #E5E7EB",
    backgroundColor: "#F9FAFB"
  },
  button: {
    padding: "8px 16px",
    borderRadius: "6px",
    fontSize: "13px",
    fontWeight: 500,
    cursor: "pointer",
    border: "1px solid #E5E7EB",
    backgroundColor: "#FFFFFF",
    transition: "background-color 0.15s"
  },
  buttonPrimary: {
    backgroundColor: "#3B82F6",
    color: "#FFFFFF",
    border: "1px solid #3B82F6"
  },
  buttonDanger: {
    color: "#DC2626",
    borderColor: "#DC2626"
  },
  dismissButton: {
    background: "none",
    border: "none",
    cursor: "pointer",
    color: "#9CA3AF",
    fontSize: "18px",
    padding: "4px",
    lineHeight: 1
  }
};
function Qr({
  suggestion: r,
  onDismiss: n,
  onLink: s,
  onMerge: i,
  onViewProfile: o,
  isExpanded: u,
  onExpandChange: y,
  className: T = ""
}) {
  const [_, v] = ne(!1), [l, f] = ne(""), [g, d] = ne(!1), p = u ?? _, b = y ?? v, R = ar[r.confidenceLevel], j = z(() => {
    g && l.trim() ? (n == null || n(r, l.trim()), d(!1), f("")) : d(!0);
  }, [r, n, l, g]), E = z(() => {
    d(!1), f("");
  }, []), D = (F) => ({
    hash_match: "Hash Match",
    exact_string: "Exact Match",
    fuzzy_match: "Fuzzy Match",
    partial_match: "Partial Match",
    cross_entity: "Cross-Entity Match"
  })[F] || F, W = (F) => {
    const O = /* @__PURE__ */ new Date(), x = new Date(F), h = O.getTime() - x.getTime(), B = Math.floor(h / 6e4);
    if (B < 60) return `${B} minute${B !== 1 ? "s" : ""} ago`;
    const I = Math.floor(B / 60);
    if (I < 24) return `${I} hour${I !== 1 ? "s" : ""} ago`;
    const q = Math.floor(I / 24);
    return `${q} day${q !== 1 ? "s" : ""} ago`;
  };
  return /* @__PURE__ */ c.jsxs(
    "div",
    {
      className: `suggestion-card suggestion-card--${r.confidenceLevel} ${T}`,
      style: {
        ...A.card,
        borderColor: R.border
      },
      children: [
        /* @__PURE__ */ c.jsxs(
          "div",
          {
            style: {
              ...A.header,
              backgroundColor: R.background
            },
            children: [
              /* @__PURE__ */ c.jsx(
                ue,
                {
                  level: r.confidenceLevel,
                  score: r.confidence
                }
              ),
              /* @__PURE__ */ c.jsx(
                "button",
                {
                  onClick: () => d(!0),
                  style: A.dismissButton,
                  title: "Dismiss suggestion",
                  "aria-label": "Dismiss suggestion",
                  children: "✕"
                }
              )
            ]
          }
        ),
        /* @__PURE__ */ c.jsxs("div", { style: A.body, children: [
          /* @__PURE__ */ c.jsxs("div", { style: A.matchInfo, children: [
            /* @__PURE__ */ c.jsxs("div", { children: [
              /* @__PURE__ */ c.jsxs("span", { style: { color: "#6B7280" }, children: [
                D(r.matchType),
                ": "
              ] }),
              /* @__PURE__ */ c.jsx("span", { style: A.matchValue, children: r.matchValue })
            ] }),
            /* @__PURE__ */ c.jsx("div", { style: A.arrow, children: "↓" }),
            /* @__PURE__ */ c.jsxs("div", { style: A.target, children: [
              "Found in: ",
              r.matchedEntityId || r.matchedOrphanId || "Unknown"
            ] })
          ] }),
          /* @__PURE__ */ c.jsx("div", { style: A.divider }),
          /* @__PURE__ */ c.jsxs(
            "button",
            {
              onClick: () => b(!p),
              style: A.expandButton,
              children: [
                /* @__PURE__ */ c.jsx("span", { children: "ℹ️" }),
                /* @__PURE__ */ c.jsx("span", { children: "Why this match?" }),
                /* @__PURE__ */ c.jsx("span", { children: p ? "▲" : "▼" })
              ]
            }
          ),
          p && r.factors.length > 0 && /* @__PURE__ */ c.jsxs("div", { style: A.factorsSection, children: [
            /* @__PURE__ */ c.jsx("div", { style: A.factorsTitle, children: "Match Factors:" }),
            r.factors.map((F, O) => /* @__PURE__ */ c.jsx(Xr, { factor: F }, O)),
            /* @__PURE__ */ c.jsxs("div", { style: A.totalScore, children: [
              /* @__PURE__ */ c.jsx("strong", { children: "Total Score:" }),
              " ",
              cr(r.confidence),
              " (weighted average)"
            ] }),
            /* @__PURE__ */ c.jsxs("div", { style: A.lastUpdated, children: [
              "Last Updated: ",
              W(r.updatedAt)
            ] })
          ] }),
          g && /* @__PURE__ */ c.jsxs("div", { style: { marginTop: "12px" }, children: [
            /* @__PURE__ */ c.jsx("label", { style: { display: "block", fontSize: "13px", marginBottom: "4px", color: "#374151" }, children: "Reason for dismissal (required):" }),
            /* @__PURE__ */ c.jsx(
              "input",
              {
                type: "text",
                value: l,
                onChange: (F) => f(F.target.value),
                placeholder: "e.g., Different person - verified via other identifiers",
                style: {
                  width: "100%",
                  padding: "8px 12px",
                  border: "1px solid #D1D5DB",
                  borderRadius: "6px",
                  fontSize: "13px"
                },
                autoFocus: !0
              }
            ),
            /* @__PURE__ */ c.jsxs("div", { style: { display: "flex", gap: "8px", marginTop: "8px" }, children: [
              /* @__PURE__ */ c.jsx(
                "button",
                {
                  onClick: j,
                  disabled: !l.trim(),
                  style: {
                    ...A.button,
                    ...l.trim() ? A.buttonDanger : { opacity: 0.5, cursor: "not-allowed" }
                  },
                  children: "Dismiss"
                }
              ),
              /* @__PURE__ */ c.jsx("button", { onClick: E, style: A.button, children: "Cancel" })
            ] })
          ] })
        ] }),
        !g && /* @__PURE__ */ c.jsxs("div", { style: A.footer, children: [
          /* @__PURE__ */ c.jsx(
            "button",
            {
              onClick: () => o == null ? void 0 : o(r),
              style: A.button,
              children: "View Profile"
            }
          ),
          /* @__PURE__ */ c.jsx(
            "button",
            {
              onClick: () => s == null ? void 0 : s(r),
              style: A.button,
              children: "Link Entities"
            }
          ),
          /* @__PURE__ */ c.jsx(
            "button",
            {
              onClick: () => i == null ? void 0 : i(r),
              style: { ...A.button, ...A.buttonPrimary },
              children: "Merge Duplicates"
            }
          )
        ] })
      ]
    }
  );
}
const et = {}, Qe = (r) => {
  let n;
  const s = /* @__PURE__ */ new Set(), i = (l, f) => {
    const g = typeof l == "function" ? l(n) : l;
    if (!Object.is(g, n)) {
      const d = n;
      n = f ?? (typeof g != "object" || g === null) ? g : Object.assign({}, n, g), s.forEach((p) => p(n, d));
    }
  }, o = () => n, _ = { setState: i, getState: o, getInitialState: () => v, subscribe: (l) => (s.add(l), () => s.delete(l)), destroy: () => {
    (et ? "production" : void 0) !== "production" && console.warn(
      "[DEPRECATED] The `destroy` method will be unsupported in a future version. Instead use unsubscribe function returned by subscribe. Everything will be garbage-collected if store is garbage-collected."
    ), s.clear();
  } }, v = n = r(i, o, _);
  return _;
}, rt = (r) => r ? Qe(r) : Qe;
var Ce = { exports: {} }, Ee = {}, ce = { exports: {} }, _e = {};
/**
 * @license React
 * use-sync-external-store-shim.production.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
var er;
function tt() {
  if (er) return _e;
  er = 1;
  var r = J;
  function n(f, g) {
    return f === g && (f !== 0 || 1 / f === 1 / g) || f !== f && g !== g;
  }
  var s = typeof Object.is == "function" ? Object.is : n, i = r.useState, o = r.useEffect, u = r.useLayoutEffect, y = r.useDebugValue;
  function T(f, g) {
    var d = g(), p = i({ inst: { value: d, getSnapshot: g } }), b = p[0].inst, R = p[1];
    return u(
      function() {
        b.value = d, b.getSnapshot = g, _(b) && R({ inst: b });
      },
      [f, d, g]
    ), o(
      function() {
        return _(b) && R({ inst: b }), f(function() {
          _(b) && R({ inst: b });
        });
      },
      [f]
    ), y(d), d;
  }
  function _(f) {
    var g = f.getSnapshot;
    f = f.value;
    try {
      var d = g();
      return !s(f, d);
    } catch {
      return !0;
    }
  }
  function v(f, g) {
    return g();
  }
  var l = typeof window > "u" || typeof window.document > "u" || typeof window.document.createElement > "u" ? v : T;
  return _e.useSyncExternalStore = r.useSyncExternalStore !== void 0 ? r.useSyncExternalStore : l, _e;
}
var xe = {};
/**
 * @license React
 * use-sync-external-store-shim.development.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
var rr;
function nt() {
  return rr || (rr = 1, process.env.NODE_ENV !== "production" && function() {
    function r(d, p) {
      return d === p && (d !== 0 || 1 / d === 1 / p) || d !== d && p !== p;
    }
    function n(d, p) {
      l || o.startTransition === void 0 || (l = !0, console.error(
        "You are using an outdated, pre-release alpha of React 18 that does not support useSyncExternalStore. The use-sync-external-store shim will not work correctly. Upgrade to a newer pre-release."
      ));
      var b = p();
      if (!f) {
        var R = p();
        u(b, R) || (console.error(
          "The result of getSnapshot should be cached to avoid an infinite loop"
        ), f = !0);
      }
      R = y({
        inst: { value: b, getSnapshot: p }
      });
      var j = R[0].inst, E = R[1];
      return _(
        function() {
          j.value = b, j.getSnapshot = p, s(j) && E({ inst: j });
        },
        [d, b, p]
      ), T(
        function() {
          return s(j) && E({ inst: j }), d(function() {
            s(j) && E({ inst: j });
          });
        },
        [d]
      ), v(b), b;
    }
    function s(d) {
      var p = d.getSnapshot;
      d = d.value;
      try {
        var b = p();
        return !u(d, b);
      } catch {
        return !0;
      }
    }
    function i(d, p) {
      return p();
    }
    typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ < "u" && typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.registerInternalModuleStart == "function" && __REACT_DEVTOOLS_GLOBAL_HOOK__.registerInternalModuleStart(Error());
    var o = J, u = typeof Object.is == "function" ? Object.is : r, y = o.useState, T = o.useEffect, _ = o.useLayoutEffect, v = o.useDebugValue, l = !1, f = !1, g = typeof window > "u" || typeof window.document > "u" || typeof window.document.createElement > "u" ? i : n;
    xe.useSyncExternalStore = o.useSyncExternalStore !== void 0 ? o.useSyncExternalStore : g, typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ < "u" && typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.registerInternalModuleStop == "function" && __REACT_DEVTOOLS_GLOBAL_HOOK__.registerInternalModuleStop(Error());
  }()), xe;
}
var tr;
function ur() {
  return tr || (tr = 1, process.env.NODE_ENV === "production" ? ce.exports = tt() : ce.exports = nt()), ce.exports;
}
/**
 * @license React
 * use-sync-external-store-shim/with-selector.production.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
var nr;
function ot() {
  if (nr) return Ee;
  nr = 1;
  var r = J, n = ur();
  function s(v, l) {
    return v === l && (v !== 0 || 1 / v === 1 / l) || v !== v && l !== l;
  }
  var i = typeof Object.is == "function" ? Object.is : s, o = n.useSyncExternalStore, u = r.useRef, y = r.useEffect, T = r.useMemo, _ = r.useDebugValue;
  return Ee.useSyncExternalStoreWithSelector = function(v, l, f, g, d) {
    var p = u(null);
    if (p.current === null) {
      var b = { hasValue: !1, value: null };
      p.current = b;
    } else b = p.current;
    p = T(
      function() {
        function j(O) {
          if (!E) {
            if (E = !0, D = O, O = g(O), d !== void 0 && b.hasValue) {
              var x = b.value;
              if (d(x, O))
                return W = x;
            }
            return W = O;
          }
          if (x = W, i(D, O)) return x;
          var h = g(O);
          return d !== void 0 && d(x, h) ? (D = O, x) : (D = O, W = h);
        }
        var E = !1, D, W, F = f === void 0 ? null : f;
        return [
          function() {
            return j(l());
          },
          F === null ? void 0 : function() {
            return j(F());
          }
        ];
      },
      [l, f, g, d]
    );
    var R = o(v, p[0], p[1]);
    return y(
      function() {
        b.hasValue = !0, b.value = R;
      },
      [R]
    ), _(R), R;
  }, Ee;
}
var Se = {};
/**
 * @license React
 * use-sync-external-store-shim/with-selector.development.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
var or;
function st() {
  return or || (or = 1, process.env.NODE_ENV !== "production" && function() {
    function r(v, l) {
      return v === l && (v !== 0 || 1 / v === 1 / l) || v !== v && l !== l;
    }
    typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ < "u" && typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.registerInternalModuleStart == "function" && __REACT_DEVTOOLS_GLOBAL_HOOK__.registerInternalModuleStart(Error());
    var n = J, s = ur(), i = typeof Object.is == "function" ? Object.is : r, o = s.useSyncExternalStore, u = n.useRef, y = n.useEffect, T = n.useMemo, _ = n.useDebugValue;
    Se.useSyncExternalStoreWithSelector = function(v, l, f, g, d) {
      var p = u(null);
      if (p.current === null) {
        var b = { hasValue: !1, value: null };
        p.current = b;
      } else b = p.current;
      p = T(
        function() {
          function j(O) {
            if (!E) {
              if (E = !0, D = O, O = g(O), d !== void 0 && b.hasValue) {
                var x = b.value;
                if (d(x, O))
                  return W = x;
              }
              return W = O;
            }
            if (x = W, i(D, O))
              return x;
            var h = g(O);
            return d !== void 0 && d(x, h) ? (D = O, x) : (D = O, W = h);
          }
          var E = !1, D, W, F = f === void 0 ? null : f;
          return [
            function() {
              return j(l());
            },
            F === null ? void 0 : function() {
              return j(F());
            }
          ];
        },
        [l, f, g, d]
      );
      var R = o(v, p[0], p[1]);
      return y(
        function() {
          b.hasValue = !0, b.value = R;
        },
        [R]
      ), _(R), R;
    }, typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ < "u" && typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.registerInternalModuleStop == "function" && __REACT_DEVTOOLS_GLOBAL_HOOK__.registerInternalModuleStop(Error());
  }()), Se;
}
process.env.NODE_ENV === "production" ? Ce.exports = ot() : Ce.exports = st();
var it = Ce.exports;
const at = /* @__PURE__ */ Ir(it), lr = {}, { useDebugValue: ct } = J, { useSyncExternalStoreWithSelector: ut } = at;
let sr = !1;
const lt = (r) => r;
function dt(r, n = lt, s) {
  (lr ? "production" : void 0) !== "production" && s && !sr && (console.warn(
    "[DEPRECATED] Use `createWithEqualityFn` instead of `create` or use `useStoreWithEqualityFn` instead of `useStore`. They can be imported from 'zustand/traditional'. https://github.com/pmndrs/zustand/discussions/1937"
  ), sr = !0);
  const i = ut(
    r.subscribe,
    r.getState,
    r.getServerState || r.getInitialState,
    n,
    s
  );
  return ct(i), i;
}
const ir = (r) => {
  (lr ? "production" : void 0) !== "production" && typeof r != "function" && console.warn(
    "[DEPRECATED] Passing a vanilla store will be unsupported in a future version. Instead use `import { useStore } from 'zustand'`."
  );
  const n = typeof r == "function" ? rt(r) : r, s = (i, o) => dt(n, i, o);
  return Object.assign(s, n), s;
}, ft = (r) => r ? ir(r) : ir, U = ft((r, n) => ({
  // Initial state
  suggestions: {},
  summaries: {},
  loading: {},
  errors: {},
  expandedSuggestionId: null,
  selectedEntityId: null,
  // Fetch suggestions for an entity
  fetchSuggestions: async (s, i) => {
    r((o) => ({
      loading: { ...o.loading, [i]: !0 },
      errors: { ...o.errors, [i]: null }
    }));
    try {
      const o = await Yr(s, i);
      r((u) => ({
        suggestions: { ...u.suggestions, [i]: o.suggestions },
        summaries: { ...u.summaries, [i]: o.summary },
        loading: { ...u.loading, [i]: !1 }
      }));
    } catch (o) {
      r((u) => ({
        loading: { ...u.loading, [i]: !1 },
        errors: { ...u.errors, [i]: o.message }
      }));
    }
  },
  // Compute fresh suggestions
  refreshSuggestions: async (s, i) => {
    r((o) => ({
      loading: { ...o.loading, [i]: !0 },
      errors: { ...o.errors, [i]: null }
    }));
    try {
      const o = await Gr(s, i);
      r((u) => ({
        suggestions: { ...u.suggestions, [i]: o.suggestions },
        summaries: { ...u.summaries, [i]: o.summary },
        loading: { ...u.loading, [i]: !1 }
      }));
    } catch (o) {
      r((u) => ({
        loading: { ...u.loading, [i]: !1 },
        errors: { ...u.errors, [i]: o.message }
      }));
    }
  },
  // Remove dismissed suggestion from UI
  dismissSuggestion: (s, i) => {
    r((o) => {
      const u = o.suggestions[s] || [];
      return {
        suggestions: {
          ...o.suggestions,
          [s]: u.filter((y) => y.id !== i)
        },
        // Update summary counts
        summaries: {
          ...o.summaries,
          [s]: o.summaries[s] ? {
            ...o.summaries[s],
            totalCount: o.summaries[s].totalCount - 1,
            pendingCount: o.summaries[s].pendingCount - 1
          } : o.summaries[s]
        }
      };
    });
  },
  // Mark suggestion as viewed
  markSuggestionViewed: (s, i) => {
    r((o) => {
      const u = o.suggestions[s] || [];
      return {
        suggestions: {
          ...o.suggestions,
          [s]: u.map(
            (y) => y.id === i && y.status === "pending" ? { ...y, status: "viewed" } : y
          )
        }
      };
    });
  },
  // Toggle expanded suggestion
  setExpandedSuggestion: (s) => {
    r({ expandedSuggestionId: s });
  },
  // Select entity for suggestion viewing
  setSelectedEntity: (s) => {
    r({ selectedEntityId: s });
  },
  // Handle real-time WebSocket events
  handleWebSocketEvent: (s) => {
    const { eventType: i, data: o } = s;
    switch (i) {
      case "suggestion_generated":
        o.entityId && r((u) => ({
          summaries: {
            ...u.summaries,
            [o.entityId]: {
              entityId: o.entityId,
              totalCount: o.suggestionCount || 0,
              highConfidenceCount: o.highConfidenceCount || 0,
              mediumConfidenceCount: o.mediumConfidenceCount || 0,
              lowConfidenceCount: o.lowConfidenceCount || 0,
              pendingCount: o.suggestionCount || 0,
              lastUpdated: s.timestamp
            }
          }
        }));
        break;
      case "suggestion_dismissed":
        o.entityId && n().dismissSuggestion(o.entityId, o.entityId);
        break;
      case "entity_merged":
      case "data_linked":
      case "orphan_linked":
        o.affectedEntities && o.affectedEntities.forEach((u) => {
          r((y) => ({
            suggestions: { ...y.suggestions, [u]: [] },
            summaries: { ...y.summaries, [u]: void 0 }
          }));
        });
        break;
    }
  },
  // Clear error for entity
  clearError: (s) => {
    r((i) => ({
      errors: { ...i.errors, [s]: null }
    }));
  }
})), pt = (r) => (n) => n.suggestions[r] || [], gt = (r) => (n) => n.summaries[r], ht = (r) => (n) => n.loading[r] || !1, mt = (r) => (n) => n.errors[r];
function vt({
  projectId: r,
  onEvent: n,
  autoReconnect: s = !0,
  reconnectDelay: i = 1e3,
  maxReconnectAttempts: o = 5
}) {
  const u = be(null), y = be(0), T = be(null), [_, v] = ne("disconnected"), [l, f] = ne(null), g = U((E) => E.handleWebSocketEvent), d = z(() => {
    var W;
    if (((W = u.current) == null ? void 0 : W.readyState) === WebSocket.OPEN)
      return;
    v("connecting"), f(null);
    const D = `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/api/v1/ws/suggestions/${r}`;
    try {
      const F = new WebSocket(D);
      u.current = F, F.onopen = () => {
        v("connected"), y.current = 0, console.log(`[WebSocket] Connected to ${D}`);
      }, F.onmessage = (O) => {
        try {
          const x = JSON.parse(O.data);
          if (x.type === "pong")
            return;
          if (x.type === "connected" || x.type === "subscribed") {
            console.log(`[WebSocket] ${x.type}:`, x);
            return;
          }
          const h = {
            eventType: x.type || x.event_type,
            timestamp: x.timestamp || (/* @__PURE__ */ new Date()).toISOString(),
            data: x.data || x,
            _links: x._links
          };
          g(h), n == null || n(h);
        } catch (x) {
          console.error("[WebSocket] Failed to parse message:", x);
        }
      }, F.onerror = (O) => {
        console.error("[WebSocket] Error:", O), v("error"), f("WebSocket connection error");
      }, F.onclose = (O) => {
        if (console.log(`[WebSocket] Closed: ${O.code} ${O.reason}`), v("disconnected"), u.current = null, s && y.current < o) {
          const x = i * Math.pow(2, y.current);
          console.log(`[WebSocket] Reconnecting in ${x}ms...`), T.current = window.setTimeout(() => {
            y.current += 1, d();
          }, x);
        }
      };
    } catch (F) {
      v("error"), f(F.message);
    }
  }, [r, s, i, o, g, n]), p = z(() => {
    T.current && (window.clearTimeout(T.current), T.current = null), u.current && (u.current.close(1e3, "Client disconnect"), u.current = null), v("disconnected");
  }, []), b = z(() => {
    var E;
    ((E = u.current) == null ? void 0 : E.readyState) === WebSocket.OPEN && u.current.send(JSON.stringify({ type: "ping" }));
  }, []), R = z((E) => {
    var D;
    ((D = u.current) == null ? void 0 : D.readyState) === WebSocket.OPEN && u.current.send(
      JSON.stringify({
        type: "subscribe_entity",
        entity_id: E
      })
    );
  }, []), j = z((E) => {
    var D;
    ((D = u.current) == null ? void 0 : D.readyState) === WebSocket.OPEN && u.current.send(
      JSON.stringify({
        type: "unsubscribe_entity",
        entity_id: E
      })
    );
  }, []);
  return le(() => (d(), () => p()), [d, p]), le(() => {
    const E = window.setInterval(b, 3e4);
    return () => window.clearInterval(E);
  }, [b]), {
    state: _,
    error: l,
    connect: d,
    disconnect: p,
    ping: b,
    subscribeToEntity: R,
    unsubscribeFromEntity: j
  };
}
const V = {
  panel: {
    backgroundColor: "#FFFFFF",
    border: "1px solid #E5E7EB",
    borderRadius: "8px",
    overflow: "hidden"
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "16px",
    borderBottom: "1px solid #E5E7EB",
    backgroundColor: "#F9FAFB"
  },
  title: {
    fontSize: "16px",
    fontWeight: 600,
    display: "flex",
    alignItems: "center",
    gap: "8px"
  },
  counts: {
    display: "flex",
    gap: "8px"
  },
  refreshButton: {
    padding: "8px 12px",
    borderRadius: "6px",
    border: "1px solid #E5E7EB",
    backgroundColor: "#FFFFFF",
    cursor: "pointer",
    fontSize: "13px",
    display: "flex",
    alignItems: "center",
    gap: "4px"
  },
  body: {
    padding: "16px",
    maxHeight: "600px",
    overflowY: "auto"
  },
  loading: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "40px",
    color: "#6B7280"
  },
  error: {
    padding: "16px",
    backgroundColor: "#FEE2E2",
    color: "#991B1B",
    borderRadius: "6px",
    margin: "16px"
  },
  empty: {
    textAlign: "center",
    padding: "40px",
    color: "#6B7280"
  },
  emptyIcon: {
    fontSize: "48px",
    marginBottom: "12px"
  },
  connectionStatus: {
    display: "flex",
    alignItems: "center",
    gap: "4px",
    fontSize: "12px",
    color: "#6B7280"
  },
  statusDot: {
    width: "8px",
    height: "8px",
    borderRadius: "50%"
  }
};
function Ot({
  projectId: r,
  entityId: n,
  onViewEntity: s,
  className: i = ""
}) {
  const o = U(pt(n)), u = U(gt(n)), y = U(ht(n)), T = U(mt(n)), _ = U((h) => h.fetchSuggestions), v = U((h) => h.refreshSuggestions), l = U((h) => h.dismissSuggestion), f = U((h) => h.clearError), g = U((h) => h.setExpandedSuggestion), d = U((h) => h.expandedSuggestionId), { state: p, subscribeToEntity: b, unsubscribeFromEntity: R } = vt({
    projectId: r
  });
  le(() => {
    _(r, n);
  }, [r, n, _]), le(() => {
    if (p === "connected")
      return b(n), () => R(n);
  }, [p, n, b, R]);
  const j = z(() => {
    v(r, n);
  }, [r, n, v]), E = z(
    async (h, B) => {
      try {
        const I = h.matchedOrphanId || h.id;
        await Hr(r, n, I, B), l(n, h.id);
      } catch (I) {
        console.error("Failed to dismiss suggestion:", I);
      }
    },
    [r, n, l]
  ), D = z(
    async (h) => {
      if (!h.matchedEntityId) return;
      const B = prompt("Reason for linking these entities:");
      if (B)
        try {
          await Kr(
            r,
            n,
            h.matchedEntityId,
            "RELATED_TO",
            B
          ), l(n, h.id);
        } catch (I) {
          console.error("Failed to link entities:", I);
        }
    },
    [r, n, l]
  ), W = z(
    async (h) => {
      if (!h.matchedEntityId || !confirm(
        "This will merge these two entities. This action cannot be undone. Continue?"
      )) return;
      const I = prompt("Reason for merging these entities:");
      if (I)
        try {
          await Jr(
            r,
            n,
            h.matchedEntityId,
            n,
            // Keep current entity
            I
          ), l(n, h.id), j();
        } catch (q) {
          console.error("Failed to merge entities:", q);
        }
    },
    [r, n, l, j]
  ), F = z(
    (h) => {
      const B = h.matchedEntityId || h.matchedOrphanId;
      B && (s == null || s(B));
    },
    [s]
  ), O = [...o].sort(
    (h, B) => B.confidence - h.confidence
  ), x = () => {
    switch (p) {
      case "connected":
        return "#10B981";
      case "connecting":
        return "#F59E0B";
      case "error":
        return "#EF4444";
      default:
        return "#9CA3AF";
    }
  };
  return /* @__PURE__ */ c.jsxs("div", { className: `suggestion-panel ${i}`, style: V.panel, children: [
    /* @__PURE__ */ c.jsxs("div", { style: V.header, children: [
      /* @__PURE__ */ c.jsxs("div", { style: V.title, children: [
        /* @__PURE__ */ c.jsx("span", { children: "💡 Suggested Matches" }),
        u && /* @__PURE__ */ c.jsxs("span", { style: { fontSize: "14px", fontWeight: 400, color: "#6B7280" }, children: [
          "(",
          u.totalCount,
          " total)"
        ] })
      ] }),
      /* @__PURE__ */ c.jsxs("div", { style: { display: "flex", alignItems: "center", gap: "16px" }, children: [
        u && /* @__PURE__ */ c.jsxs("div", { style: V.counts, children: [
          u.highConfidenceCount > 0 && /* @__PURE__ */ c.jsx(
            ue,
            {
              level: "high",
              score: 0.95,
              variant: "compact",
              showScore: !1,
              showIcon: !1
            }
          ),
          u.mediumConfidenceCount > 0 && /* @__PURE__ */ c.jsx(
            ue,
            {
              level: "medium",
              score: 0.75,
              variant: "compact",
              showScore: !1,
              showIcon: !1
            }
          ),
          u.lowConfidenceCount > 0 && /* @__PURE__ */ c.jsx(
            ue,
            {
              level: "low",
              score: 0.55,
              variant: "compact",
              showScore: !1,
              showIcon: !1
            }
          )
        ] }),
        /* @__PURE__ */ c.jsxs("div", { style: V.connectionStatus, children: [
          /* @__PURE__ */ c.jsx(
            "div",
            {
              style: {
                ...V.statusDot,
                backgroundColor: x()
              }
            }
          ),
          /* @__PURE__ */ c.jsx("span", { children: p === "connected" ? "Live" : p })
        ] }),
        /* @__PURE__ */ c.jsxs(
          "button",
          {
            onClick: j,
            disabled: y,
            style: {
              ...V.refreshButton,
              opacity: y ? 0.5 : 1,
              cursor: y ? "not-allowed" : "pointer"
            },
            children: [
              /* @__PURE__ */ c.jsx("span", { style: { transform: y ? "rotate(360deg)" : "none" }, children: "🔄" }),
              /* @__PURE__ */ c.jsx("span", { children: "Refresh" })
            ]
          }
        )
      ] })
    ] }),
    T && /* @__PURE__ */ c.jsxs("div", { style: V.error, children: [
      /* @__PURE__ */ c.jsx("strong", { children: "Error:" }),
      " ",
      T,
      /* @__PURE__ */ c.jsx(
        "button",
        {
          onClick: () => f(n),
          style: {
            marginLeft: "12px",
            background: "none",
            border: "none",
            cursor: "pointer",
            color: "#991B1B"
          },
          children: "✕"
        }
      )
    ] }),
    /* @__PURE__ */ c.jsxs("div", { style: V.body, children: [
      y && o.length === 0 && /* @__PURE__ */ c.jsx("div", { style: V.loading, children: /* @__PURE__ */ c.jsx("span", { children: "Loading suggestions..." }) }),
      !y && o.length === 0 && /* @__PURE__ */ c.jsxs("div", { style: V.empty, children: [
        /* @__PURE__ */ c.jsx("div", { style: V.emptyIcon, children: "✓" }),
        /* @__PURE__ */ c.jsx("div", { style: { fontWeight: 500, marginBottom: "8px" }, children: "No suggestions found" }),
        /* @__PURE__ */ c.jsx("div", { style: { fontSize: "13px" }, children: "This entity has no pending match suggestions." })
      ] }),
      O.map((h) => /* @__PURE__ */ c.jsx(
        Qr,
        {
          suggestion: h,
          onDismiss: E,
          onLink: D,
          onMerge: W,
          onViewProfile: F,
          isExpanded: d === h.id,
          onExpandChange: (B) => g(B ? h.id : null)
        },
        h.id
      ))
    ] })
  ] });
}
const Ct = "1.0.0";
export {
  Mr as CONFIDENCE_BADGES,
  ar as CONFIDENCE_COLORS,
  Vr as CONFIDENCE_ICONS,
  Ze as CONFIDENCE_THRESHOLDS,
  ue as SuggestionBadge,
  Qr as SuggestionCard,
  Ot as SuggestionPanel,
  Ct as VERSION,
  Gr as computeSuggestions,
  Hr as dismissSuggestion,
  Yr as fetchEntitySuggestions,
  St as fetchProjectSuggestionsSummary,
  cr as formatConfidence,
  Et as getConfidenceClasses,
  zr as getConfidenceLabel,
  bt as getConfidenceLevel,
  _t as linkDataItems,
  Kr as linkEntities,
  xt as linkOrphanToEntity,
  Jr as mergeEntities,
  mt as selectError,
  ht as selectIsLoading,
  pt as selectSuggestions,
  gt as selectSummary,
  U as useSuggestionsStore,
  vt as useWebSocket
};
