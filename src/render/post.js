// WebGL post-processing: bloom (multi-pass), shockwave distortion, chromatic aberration,
// filmic grading, vignette, grain and flashes. Falls back to plain 2D if WebGL is missing.

const VS = `
attribute vec2 aPos;
varying vec2 vUv;
void main() { vUv = aPos * 0.5 + 0.5; gl_Position = vec4(aPos, 0.0, 1.0); }`;

const BRIGHT = `
precision mediump float;
varying vec2 vUv;
uniform sampler2D uTex;
uniform float uThreshold;
void main() {
  vec3 c = texture2D(uTex, vUv).rgb;
  float l = max(c.r, max(c.g, c.b));
  float k = smoothstep(uThreshold, uThreshold + 0.25, l);
  gl_FragColor = vec4(c * k, 1.0);
}`;

const BLUR = `
precision mediump float;
varying vec2 vUv;
uniform sampler2D uTex;
uniform vec2 uDir;
void main() {
  vec3 c = texture2D(uTex, vUv).rgb * 0.2270270270;
  c += texture2D(uTex, vUv + uDir * 1.3846153846).rgb * 0.3162162162;
  c += texture2D(uTex, vUv - uDir * 1.3846153846).rgb * 0.3162162162;
  c += texture2D(uTex, vUv + uDir * 3.2307692308).rgb * 0.0702702703;
  c += texture2D(uTex, vUv - uDir * 3.2307692308).rgb * 0.0702702703;
  gl_FragColor = vec4(c, 1.0);
}`;

const COMPOSITE = `
precision highp float;
varying vec2 vUv;
uniform sampler2D uScene;
uniform sampler2D uBloom1;
uniform sampler2D uBloom2;
uniform vec2 uRes;
uniform float uTime;
uniform float uCA;
uniform vec4 uFlash;
uniform vec4 uShock[4];
uniform float uBloomStrength;
uniform float uSat;
uniform float uVignette;
uniform float uDim;

float rand(vec2 co) { return fract(sin(dot(co, vec2(12.9898, 78.233))) * 43758.5453); }

void main() {
  vec2 uv = vUv;
  float aspect = uRes.x / uRes.y;
  // Shockwaves: radial displacement rings
  for (int i = 0; i < 4; i++) {
    vec4 s = uShock[i];
    if (s.w > 0.0) {
      vec2 d = uv - s.xy; d.x *= aspect;
      float dist = length(d);
      float w = 0.06;
      float k = smoothstep(w, 0.0, abs(dist - s.z)) * s.w;
      vec2 n = dist > 0.0001 ? d / dist : vec2(0.0);
      n.x /= aspect;
      uv -= n * k * 0.035;
    }
  }
  vec2 c = uv - 0.5;
  float r2 = dot(c, c);
  float ca = uCA * 0.012 + r2 * 0.006;
  vec3 col;
  col.r = texture2D(uScene, uv + c * ca).r;
  col.g = texture2D(uScene, uv).g;
  col.b = texture2D(uScene, uv - c * ca).b;

  vec3 bloom = texture2D(uBloom1, vUv).rgb * 0.9 + texture2D(uBloom2, vUv).rgb * 1.1;
  col += bloom * uBloomStrength;

  // Filmic-ish tone curve + teal/orange split grade
  col = col * (1.0 + col * 0.12) / (1.0 + col * 0.35);
  float lum = dot(col, vec3(0.299, 0.587, 0.114));
  vec3 shadows = vec3(0.0, 0.035, 0.06);
  vec3 highs = vec3(0.06, 0.025, -0.03);
  col += mix(shadows, highs, smoothstep(0.1, 0.7, lum)) * 0.8;
  col = mix(vec3(lum), col, uSat);
  col = (col - 0.5) * 1.08 + 0.5;

  // Vignette
  float v = smoothstep(0.95, 0.25, length(c * vec2(aspect * 0.62, 1.0)));
  col *= mix(1.0 - uVignette, 1.0, v);

  // Subtle scanlines + grain
  col *= 0.975 + 0.025 * sin(vUv.y * uRes.y * 3.14159);
  col += (rand(vUv * uRes + fract(uTime * 7.0)) - 0.5) * 0.045;

  col = mix(col, uFlash.rgb, uFlash.a);
  col *= uDim;
  gl_FragColor = vec4(max(col, 0.0), 1.0);
}`;

export class Post {
  constructor(canvas) {
    this.canvas = canvas;
    const gl = canvas.getContext('webgl', { antialias: false, alpha: false, preserveDrawingBuffer: false, powerPreference: 'high-performance' });
    this.gl = gl;
    this.ok = !!gl;
    if (!gl) return;
    const dbg = gl.getExtension('WEBGL_debug_renderer_info');
    this.renderer = String(dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER));
    this.software = /swiftshader|llvmpipe|softpipe|software/i.test(this.renderer);
    this.progBright = this.program(VS, BRIGHT);
    this.progBlur = this.program(VS, BLUR);
    this.progComp = this.program(VS, COMPOSITE);
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    this.sceneTex = this.texture();
    this.w = 0; this.h = 0;
  }

  program(vs, fs) {
    const gl = this.gl;
    const mk = (type, src) => {
      const s = gl.createShader(type);
      gl.shaderSource(s, src);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
      return s;
    };
    const p = gl.createProgram();
    gl.attachShader(p, mk(gl.VERTEX_SHADER, vs));
    gl.attachShader(p, mk(gl.FRAGMENT_SHADER, fs));
    gl.bindAttribLocation(p, 0, 'aPos');
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
    p.u = {};
    const n = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS);
    for (let i = 0; i < n; i++) {
      const info = gl.getActiveUniform(p, i);
      const name = info.name.replace('[0]', '');
      p.u[name] = gl.getUniformLocation(p, name);
    }
    return p;
  }

  texture() {
    const gl = this.gl;
    const t = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    return t;
  }

  target(w, h) {
    const gl = this.gl;
    const tex = this.texture();
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    const fb = gl.createFramebuffer();
    gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    return { tex, fb, w, h };
  }

  resize(w, h) {
    if (!this.ok || (w === this.w && h === this.h)) return;
    this.w = w; this.h = h;
    this.canvas.width = w; this.canvas.height = h;
    const q = (d) => [Math.max(1, Math.floor(w / d)), Math.max(1, Math.floor(h / d))];
    this.b4a = this.target(...q(4)); this.b4b = this.target(...q(4));
    this.b8a = this.target(...q(8)); this.b8b = this.target(...q(8));
  }

  pass(prog, target, setup) {
    const gl = this.gl;
    gl.useProgram(prog);
    gl.bindFramebuffer(gl.FRAMEBUFFER, target ? target.fb : null);
    gl.viewport(0, 0, target ? target.w : this.w, target ? target.h : this.h);
    setup(prog.u);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  }

  bind(unit, tex, loc) {
    const gl = this.gl;
    gl.activeTexture(gl.TEXTURE0 + unit);
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.uniform1i(loc, unit);
  }

  bloomPasses(params) {
    const gl = this.gl;
    this.pass(this.progBright, this.b4a, (u) => {
      this.bind(0, this.sceneTex, u.uTex);
      gl.uniform1f(u.uThreshold, params.threshold ?? 0.62);
    });
    const blur = (src, dst, dx, dy) => this.pass(this.progBlur, dst, (u) => {
      this.bind(0, src.tex, u.uTex);
      gl.uniform2f(u.uDir, dx / src.w, dy / src.h);
    });
    blur(this.b4a, this.b4b, 1, 0);
    blur(this.b4b, this.b4a, 0, 1);
    blur(this.b4a, this.b8a, 1.5, 0);
    blur(this.b8a, this.b8b, 0, 1.5);
    blur(this.b8b, this.b8a, 2.5, 0);
    blur(this.b8a, this.b8b, 0, 2.5);
  }

  render(source, params) {
    const gl = this.gl;
    gl.bindTexture(gl.TEXTURE_2D, this.sceneTex);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, source);

    // Bright pass → 1/4, blur; then 1/8 wider blur (skipped when bloom is off).
    if ((params.bloom ?? 1) > 0) this.bloomPasses(params);

    this.pass(this.progComp, null, (u) => {
      this.bind(0, this.sceneTex, u.uScene);
      this.bind(1, this.b4a.tex, u.uBloom1);
      this.bind(2, this.b8b.tex, u.uBloom2);
      gl.uniform2f(u.uRes, this.w, this.h);
      gl.uniform1f(u.uTime, params.time);
      gl.uniform1f(u.uCA, params.ca);
      gl.uniform4f(u.uFlash, params.flash[0], params.flash[1], params.flash[2], params.flash[3]);
      const sh = this.shockBuf || (this.shockBuf = new Float32Array(16));
      sh.fill(0);
      params.shocks.slice(0, 4).forEach((s, i) => sh.set([s.x, s.y, s.r, s.s], i * 4));
      gl.uniform4fv(u.uShock, sh);
      gl.uniform1f(u.uBloomStrength, params.bloom ?? 1.0);
      gl.uniform1f(u.uSat, params.sat ?? 1.08);
      gl.uniform1f(u.uVignette, params.vignette ?? 0.55);
      gl.uniform1f(u.uDim, params.dim ?? 1);
    });
  }
}
