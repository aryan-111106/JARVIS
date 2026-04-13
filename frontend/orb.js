(function () {
    const canvas = document.getElementById('webgl-canvas');
    if (!canvas) return;
    const gl = canvas.getContext('webgl');
    if (!gl) return;

    let isOrbSpeaking = false;

    const vsSource = `attribute vec2 position; varying vec2 vUv; void main() { vUv = position; gl_Position = vec4(position, 0.0, 1.0); }`;
    const fsSource = `precision mediump float;
varying vec2 vUv;
uniform float time;
uniform float isSpeaking;
uniform vec2 resolution;

float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    float a = hash(i);
    float b = hash(i + vec2(1.0, 0.0));
    float c = hash(i + vec2(0.0, 1.0));
    float d = hash(i + vec2(1.0, 1.0));
    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

float fbm(vec2 p) {
    float v = 0.0;
    float a = 0.5;
    vec2 shift = vec2(100.0);
    for (int i = 0; i < 5; i++) {
        v += a * noise(p);
        p = p * 2.0 + shift;
        a *= 0.5;
    }
    return v;
}

void main() {
    vec2 uv = gl_FragCoord.xy / resolution.xy;
    uv = uv * 2.0 - 1.0;
    uv.x *= resolution.x / resolution.y;
    float dist = length(uv);
    float angle = atan(uv.y, uv.x);
    float t = time * 0.4;

    vec2 q = vec2(fbm(uv * 2.0 + t), fbm(uv * 2.0 + vec2(1.0)));
    vec2 r = vec2(fbm(uv * 3.0 + q * 2.0 + vec2(1.7, 9.2) + t * 0.8),
                  fbm(uv * 3.0 + q * 2.0 + vec2(8.3, 2.8) + t * 0.8));
    float f = fbm(uv * 2.5 + r * 1.5);

    float core = smoothstep(0.25, 0.05, dist);
    float fresnel = pow(1.0 - smoothstep(0.15, 0.35, dist), 3.0);
    float glow = pow(0.05 / max(dist - 0.22, 0.001), 1.2);

    vec3 deepBlue  = vec3(0.0, 0.15, 0.4);
    vec3 cyan      = vec3(0.0, 0.8, 1.0);
    vec3 purple    = vec3(0.35, 0.0, 0.6);
    vec3 neon      = vec3(0.0, 1.0, 0.9);

    vec3 col = mix(deepBlue, cyan, clamp(f * 2.0, 0.0, 1.0));
    col = mix(col, purple, clamp(length(q) * 0.8, 0.0, 0.5));
    col += neon * fresnel * 0.6;
    col += vec3(0.0, 0.5, 1.0) * glow;

    float tendril = smoothstep(0.45, 0.3, dist) * f * 0.4;
    col += cyan * tendril;

    float pulseFreq = 12.0 + isSpeaking * 8.0;
    float pulse = sin(time * pulseFreq) * 0.5 + 0.5;
    col += neon * fresnel * pulse * isSpeaking * 0.5;
    col += vec3(0.0, 0.4, 1.0) * glow * pulse * isSpeaking * 0.4;

    col *= smoothstep(1.2, 0.3, dist);
    col = pow(col, vec3(0.9));

    gl_FragColor = vec4(col, 1.0);
}`;

    function compileShader(type, source) {
        const shader = gl.createShader(type);
        gl.shaderSource(shader, source);
        gl.compileShader(shader);
        return shader;
    }

    const shaderProgram = gl.createProgram();
    gl.attachShader(shaderProgram, compileShader(gl.VERTEX_SHADER, vsSource));
    gl.attachShader(shaderProgram, compileShader(gl.FRAGMENT_SHADER, fsSource));
    gl.linkProgram(shaderProgram);
    gl.useProgram(shaderProgram);

    const vertices = new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]);
    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);

    const posAttr = gl.getAttribLocation(shaderProgram, 'position');
    gl.enableVertexAttribArray(posAttr);
    gl.vertexAttribPointer(posAttr, 2, gl.FLOAT, false, 0, 0);

    const timeUni = gl.getUniformLocation(shaderProgram, 'time');
    const speakUni = gl.getUniformLocation(shaderProgram, 'isSpeaking');
    const resUni = gl.getUniformLocation(shaderProgram, 'resolution');

    function resizeCanvas() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        gl.viewport(0, 0, canvas.width, canvas.height);
        gl.uniform2f(resUni, canvas.width, canvas.height);
    }

    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();

    let startTime = Date.now();
    let targetSpeakValue = 0.0;
    let currentSpeakValue = 0.0;

    function render() {
        const time = (Date.now() - startTime) / 1000.0;
        targetSpeakValue = isOrbSpeaking ? 1.0 : 0.0;
        currentSpeakValue += (targetSpeakValue - currentSpeakValue) * 0.1;
        gl.uniform1f(timeUni, time);
        gl.uniform1f(speakUni, currentSpeakValue);
        gl.clear(gl.COLOR_BUFFER_BIT);
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
        requestAnimationFrame(render);
    }

    render();

    window.JarvisOrb = {
        setSpeaking(on) {
            isOrbSpeaking = !!on;
        },
    };
})();
