"""Shaders GLSL 3.30 du moteur 3D."""

MAX_LIGHTS = 32

LIT_VS = """
#version 330
uniform mat4 u_vp;
uniform mat4 u_light_vp;
in vec3 in_pos;
in vec3 in_norm;
in vec4 in_col;
in vec3 i_ax;
in vec3 i_ay;
in vec3 i_az;
in vec3 i_pos;
in vec4 i_col;
out vec3 v_wpos;
out vec3 v_norm;
out vec3 v_col;
out vec4 v_lpos;
out float v_emis;
out float v_flag;
out vec3 v_opos;
out float v_mat;
void main() {
    mat3 M = mat3(i_ax, i_ay, i_az);
    vec3 wp = M * in_pos + i_pos;
    v_wpos = wp;
    v_norm = normalize(transpose(inverse(M)) * in_norm);
    v_col = in_col.rgb * i_col.rgb;
    v_emis = i_col.a;
    v_flag = mod(in_col.a, 2.0);                 // bit « coupable » (murs qui s'effacent)
    v_mat = floor(in_col.a / 2.0 + 0.01);        // matériau (texture procédurale)
    v_opos = in_pos * (length(i_ax) + length(i_ay) + length(i_az)) * 0.333;
    v_lpos = u_light_vp * vec4(wp, 1.0);
    gl_Position = u_vp * vec4(wp, 1.0);
}
"""

LIT_FS = """
#version 330
uniform vec3 u_sun_dir;
uniform vec3 u_sun_col;
uniform vec3 u_sky;
uniform vec3 u_ground;
uniform sampler2DShadow u_shadow;
uniform float u_shadow_on;
uniform int u_nl;
uniform vec4 u_lpos[%(N)d];
uniform vec4 u_lcol[%(N)d];
uniform vec3 u_cam;
uniform vec3 u_player;
uniform float u_cut;
uniform vec3 u_fog_col;
uniform vec3 u_fog_center;
uniform vec2 u_fog;
uniform float u_toon;
in vec3 v_wpos;
in vec3 v_norm;
in vec3 v_col;
in vec4 v_lpos;
in float v_emis;
in float v_flag;
in vec3 v_opos;
in float v_mat;
out vec4 f_col;

// ---- textures procédurales (aucune image : bruit calculé à partir de la position)
float hash3(vec3 p) {
    p = fract(p * 0.3183099 + 0.1);
    p *= 17.0;
    return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}
float vnoise(vec3 x) {
    vec3 i = floor(x);
    vec3 f = fract(x);
    f = f * f * (3.0 - 2.0 * f);
    return mix(mix(mix(hash3(i), hash3(i + vec3(1, 0, 0)), f.x), mix(hash3(i + vec3(0, 1, 0)), hash3(i + vec3(1, 1, 0)), f.x), f.y),
               mix(mix(hash3(i + vec3(0, 0, 1)), hash3(i + vec3(1, 0, 1)), f.x), mix(hash3(i + vec3(0, 1, 1)), hash3(i + vec3(1, 1, 1)), f.x), f.y), f.z);
}
float fbm(vec3 p) {
    return 0.5 * vnoise(p) + 0.25 * vnoise(p * 2.03 + 7.1) + 0.125 * vnoise(p * 4.07 + 3.3);
}
vec3 stone(vec3 c, vec3 p) {
    float k = 0.84 + 0.32 * fbm(p * 2.6);
    float speck = step(0.96, hash3(floor(p * 26.0))) * 0.07;
    float crack = 1.0 - 0.16 * (1.0 - smoothstep(0.0, 0.02, abs(vnoise(p * 2.2 + 5.0) - 0.5)));
    return c * k * crack - speck * c;
}
vec3 texture_detail(vec3 c, vec3 wp, vec3 n, vec3 op, float mat) {
    if (mat > 7.5) {                                   // personnages et monstres : grain de tissu / de peau
        return c * (0.92 + 0.14 * vnoise(op * 9.0));
    }
    if (mat < 0.5) return c;
    if (mat < 1.5) return stone(c, wp);                // dalles de pierre
    if (mat < 2.5) {                                   // briques (faces verticales), pierre (dessus)
        if (abs(n.y) > 0.6) return stone(c, wp);
        vec2 t = normalize(vec2(-n.z, n.x));
        float u = dot(wp.xz, t);
        float row = floor(wp.y / 0.22);
        float bu = u / 0.42 + 0.5 * mod(row, 2.0);
        vec2 id = vec2(floor(bu), row);
        float fu = fract(bu), fv = fract(wp.y / 0.22);
        float edge = min(min(fu, 1.0 - fu) * 0.42, min(fv, 1.0 - fv) * 0.22);
        float brick = 0.82 + 0.3 * hash3(vec3(id, 3.0));
        vec3 b = c * brick * (0.88 + 0.24 * fbm(wp * 6.0));
        return mix(c * 0.45, b, smoothstep(0.008, 0.018, edge));
    }
    if (mat < 3.5) {                                   // herbe : taches, brins, zones sèches
        float blot = fbm(wp * 1.2);
        vec3 g = c * (0.82 + 0.36 * blot) + (hash3(floor(wp * 45.0)) - 0.5) * 0.08 * c;
        return mix(g, g * vec3(1.12, 1.05, 0.7), smoothstep(0.58, 0.78, fbm(wp * 0.45 + 11.0)));
    }
    float pebble = step(0.975, hash3(floor(wp * 16.0))) * 0.06;  // terre caillouteuse
    return c * (0.82 + 0.3 * fbm(wp * 3.0)) + pebble * c;
}

// relief des pierres : la normale suit les creux et bosses d'un bruit (aucune texture)
float bumph(vec3 p) { return vnoise(p * 3.1) * 0.6 + vnoise(p * 8.3 + 2.7) * 0.4; }
vec3 bump(vec3 n, vec3 p, float k) {
    float e = 0.02;
    float h0 = bumph(p);
    vec3 g = vec3(bumph(p + vec3(e, 0, 0)), bumph(p + vec3(0, e, 0)), bumph(p + vec3(0, 0, e))) - h0;
    g /= e;
    return normalize(n - (g - n * dot(g, n)) * k);
}

float shadow_at() {
    vec3 p = v_lpos.xyz / v_lpos.w * 0.5 + 0.5;
    if (p.x < 0.0 || p.x > 1.0 || p.y < 0.0 || p.y > 1.0 || p.z > 1.0) return 1.0;
    vec2 texel = 1.0 / vec2(textureSize(u_shadow, 0));
    float s = 0.0;
    for (int x = -1; x <= 1; x++)
        for (int y = -1; y <= 1; y++)
            s += texture(u_shadow, vec3(p.xy + vec2(x, y) * texel * 1.3, p.z - 0.0012));
    return s / 9.0;
}

void main() {
    if (v_col.r < -0.5) discard;       // matériau masqué d'un personnage animé
    // murs coupés quand ils masquent le héros (comme dans Minecraft Dungeons)
    if (v_flag > 0.5 && u_cut > 0.0 && v_wpos.y > u_player.y - 0.47) {
        vec3 toP = u_player - u_cam;
        vec3 toF = v_wpos - u_cam;
        float t = dot(toF, toP) / dot(toP, toP);
        if (t < 1.0) {
            float d = length(v_wpos - (u_cam + toP * t));
            float r = u_cut * clamp(t * 1.4 - 0.2, 0.0, 1.0);
            if (d < r * 0.75) discard;
            if (d < r && mod(floor(gl_FragCoord.x) + floor(gl_FragCoord.y), 2.0) < 1.0) discard;
        }
    }
    vec3 n = normalize(v_norm);
    vec3 base = texture_detail(v_col, v_wpos, n, v_opos, u_toon > 0.5 ? 8.0 : v_mat);
    bool rock = u_toon < 0.5 && v_mat > 0.5 && v_mat < 2.5;
    float gloss = 0.1;
    if (rock) {
        n = bump(n, v_wpos * 0.7, 0.03);
        gloss = 0.18 + 0.5 * smoothstep(0.55, 0.8, fbm(v_wpos * 0.9 + 3.0));   // flaques et pierre humide
    } else if (u_toon > 0.5) {
        gloss = 0.22;
    }
    // occlusion ambiante bon marché : pied des murs et des objets plus sombre
    float ao = 1.0;
    if (u_toon < 0.5 && abs(n.y) < 0.6 && v_wpos.y > -0.05) ao = mix(0.42, 1.0, smoothstep(0.0, 0.75, v_wpos.y));
    vec3 light = mix(u_ground, u_sky, n.y * 0.5 + 0.5) * ao;
    vec3 V = normalize(u_cam - v_wpos);
    vec3 spec = vec3(0.0);
    float sh = u_shadow_on > 0.5 ? shadow_at() : 1.0;
    float ndl = dot(n, -u_sun_dir);
    if (u_toon > 0.5) {
        // personnages : lumière en paliers doux (cel shading) et liseré de lumière sur les bords
        float band = smoothstep(0.0, 0.18, ndl) * 0.75 + smoothstep(0.55, 0.7, ndl) * 0.25;
        light += u_sun_col * band * max(sh, 0.35) * 1.15;
        float rim = pow(1.0 - max(dot(n, V), 0.0), 3.0);
        light += (u_sky * 1.3 + u_sun_col * 0.6 + 0.08) * rim * 0.9;
    } else {
        light += u_sun_col * max(ndl, 0.0) * sh;
    }
    for (int i = 0; i < u_nl; i++) {
        vec3 L = u_lpos[i].xyz - v_wpos;
        float d = length(L);
        float r = u_lpos[i].w;
        if (d < r) {
            float a = 1.0 - d / r;
            a *= a;
            vec3 Ld = L / max(d, 0.001);
            float nd = max(dot(n, Ld), 0.0) * 0.85 + 0.15;
            vec3 lc = u_lcol[i].rgb * u_lcol[i].a * a;
            light += lc * nd * mix(1.0, ao, 0.6);
            spec += lc * pow(max(dot(n, normalize(Ld + V)), 0.0), 36.0) * gloss;
        }
    }
    vec3 c = base * light + spec;
    c = mix(c, base * 1.35, v_emis);
    float fd = length(v_wpos.xz - u_fog_center.xz);
    float fog = clamp((fd - u_fog.x) / max(u_fog.y - u_fog.x, 0.001), 0.0, 1.0);
    c = mix(c, u_fog_col, fog * (1.0 - v_emis * 0.5));
    f_col = vec4(c, 1.0);
}
""" % {"N": MAX_LIGHTS}

DEPTH_VS = """
#version 330
uniform mat4 u_light_vp;
in vec3 in_pos;
in vec3 i_ax;
in vec3 i_ay;
in vec3 i_az;
in vec3 i_pos;
void main() {
    gl_Position = u_light_vp * vec4(mat3(i_ax, i_ay, i_az) * in_pos + i_pos, 1.0);
}
"""

DEPTH_FS = """
#version 330
void main() { }
"""

# Additif : halos translucides, barrières d'énergie, faisceaux
ADD_FS = """
#version 330
in vec3 v_wpos;
in vec3 v_norm;
in vec3 v_col;
in vec4 v_lpos;
in float v_emis;
in float v_flag;
uniform vec3 u_cam;
uniform float u_gain;
out vec4 f_col;
void main() {
    vec3 n = normalize(v_norm);
    vec3 vd = normalize(u_cam - v_wpos);
    float rim = 1.0 - abs(dot(n, vd));
    float a = v_emis * (0.35 + 0.65 * rim);
    f_col = vec4(v_col * a * u_gain, 1.0);
}
"""

DECAL_VS = """
#version 330
uniform mat4 u_vp;
in vec2 in_uv;
in vec3 i_c;
in vec2 i_r;
in float i_rot;
in vec4 i_col;
in vec4 i_shape;
out vec2 v_uv;
out vec4 v_col;
out vec4 v_shape;
void main() {
    vec2 q = in_uv * i_r;
    float c = cos(i_rot), s = sin(i_rot);
    vec2 rq = vec2(q.x * c - q.y * s, q.x * s + q.y * c);
    v_uv = in_uv;
    v_col = i_col;
    v_shape = i_shape;
    gl_Position = u_vp * vec4(i_c + vec3(rq.x, 0.0, rq.y), 1.0);
}
"""

DECAL_FS = """
#version 330
in vec2 v_uv;
in vec4 v_col;
in vec4 v_shape;
out vec4 f_col;
float h2(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float n2(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(mix(h2(i), h2(i + vec2(1, 0)), f.x), mix(h2(i + vec2(0, 1)), h2(i + vec2(1, 1)), f.x), f.y);
}
void main() {
    int kind = int(v_shape.x + 0.5);
    float r = length(v_uv);
    float a = 0.0;
    float edge = 0.035;
    if (kind == 0) {                 // disque plein
        a = 1.0 - smoothstep(1.0 - edge, 1.0, r);
    } else if (kind == 1) {          // anneau (v_shape.y = rayon intérieur)
        a = smoothstep(v_shape.y - edge, v_shape.y, r) * (1.0 - smoothstep(1.0 - edge, 1.0, r));
    } else if (kind == 2) {          // rectangle
        vec2 d = abs(v_uv);
        a = (1.0 - smoothstep(0.96, 1.0, d.x)) * (1.0 - smoothstep(0.96, 1.0, d.y));
    } else if (kind == 3) {          // secteur (v_shape.z = demi-angle)
        float ang = abs(atan(v_uv.y, v_uv.x));
        a = (1.0 - smoothstep(v_shape.z - 0.05, v_shape.z, ang)) * smoothstep(v_shape.y - edge, v_shape.y, r)
            * (1.0 - smoothstep(1.0 - edge, 1.0, r));
    } else if (kind == 4) {          // ombre douce
        a = 1.0 - smoothstep(0.1, 1.0, r);
    } else if (kind == 5) {          // disque de progression (v_shape.z = avancement)
        float fill = 1.0 - smoothstep(v_shape.z - 0.02, v_shape.z, r);
        a = (0.45 + 0.55 * fill) * (1.0 - smoothstep(1.0 - edge, 1.0, r));
        a = max(a, (1.0 - smoothstep(0.93, 0.96, r)) * smoothstep(0.9, 0.93, r) * 0.0);
        a += smoothstep(0.92, 0.96, r) * (1.0 - smoothstep(0.97, 1.0, r)) * 0.8;
    } else if (kind == 6) {          // rectangle de progression le long de x (v_shape.z)
        vec2 d = abs(v_uv);
        float inside = (1.0 - smoothstep(0.97, 1.0, d.x)) * (1.0 - smoothstep(0.9, 1.0, d.y));
        float fill = 1.0 - smoothstep(v_shape.z * 2.0 - 1.0 - 0.02, v_shape.z * 2.0 - 1.0, v_uv.x);
        a = inside * (0.45 + 0.55 * fill);
    } else if (kind == 7) {          // fissure incandescente (v_shape.z = graine) : lumineuse, alimente le halo
        vec2 p = v_uv * 2.0 + v_shape.z * 7.0;
        float line = abs(n2(p) - 0.5) + abs(n2(p * 2.7 + 5.0) - 0.5) * 0.3;
        float fade = 1.0 - smoothstep(0.55, 1.0, r);
        float core = 1.0 - smoothstep(0.015, 0.05, line);
        float halo = 1.0 - smoothstep(0.0, 0.2, line);
        a = (core + halo * 0.3) * fade;
        f_col = vec4(v_col.rgb * (1.0 + core * 2.5), a * v_col.a);
        if (f_col.a <= 0.003) discard;
        return;
    } else if (kind == 8) {          // brume : tache très douce et irrégulière
        float m = n2(v_uv * 1.6 + v_shape.z) * 0.6 + n2(v_uv * 3.3 - v_shape.z) * 0.4;
        a = (1.0 - smoothstep(0.2, 1.0, r)) * smoothstep(0.3, 0.75, m);
    }
    a *= v_col.a;
    if (a <= 0.003) discard;
    f_col = vec4(v_col.rgb, a);
}
"""

PART_VS = """
#version 330
uniform mat4 u_vp;
uniform vec3 u_right;
uniform vec3 u_up;
in vec2 in_uv;
in vec3 i_p;
in float i_s;
in vec4 i_col;
out vec2 v_uv;
out vec4 v_col;
void main() {
    v_uv = in_uv;
    v_col = i_col;
    vec3 wp = i_p + (u_right * in_uv.x + u_up * in_uv.y) * i_s;
    gl_Position = u_vp * vec4(wp, 1.0);
}
"""

PART_FS = """
#version 330
uniform int u_mode;
uniform float u_gain;
in vec2 v_uv;
in vec4 v_col;
out vec4 f_col;
void main() {
    float r = length(v_uv);
    if (u_mode == 0) {
        // halo coloré et cœur presque blanc (énergie surchauffée) : les deux nourrissent le bloom
        float a = pow(max(0.0, 1.0 - r), 1.8) * v_col.a;
        float core = pow(max(0.0, 1.0 - r * 2.2), 3.0) * v_col.a;
        f_col = vec4((v_col.rgb * a + mix(v_col.rgb, vec3(1.0), 0.6) * core * 0.9) * u_gain, 1.0);
    } else {
        if (max(abs(v_uv.x), abs(v_uv.y)) > 0.8) discard;
        f_col = vec4(v_col.rgb, v_col.a);
    }
}
"""

SKY_VS = """
#version 330
in vec2 in_uv;
out vec2 v_uv;
void main() { v_uv = in_uv * 0.5 + 0.5; gl_Position = vec4(in_uv, 0.9999, 1.0); }
"""

SKY_FS = """
#version 330
uniform vec3 u_top;
uniform vec3 u_mid;
uniform vec3 u_bottom;
uniform vec3 u_sun;      // position écran (x, y) et intensité
uniform vec3 u_sun_col;
uniform float u_aspect;
in vec2 v_uv;
out vec4 f_col;
void main() {
    float y = v_uv.y;
    vec3 c = y > 0.5 ? mix(u_mid, u_top, (y - 0.5) * 2.0) : mix(u_bottom, u_mid, y * 2.0);
    vec2 d = (v_uv - u_sun.xy) * vec2(u_aspect, 1.0);
    float g = u_sun.z * (exp(-length(d) * 5.0) * 0.8 + exp(-length(d) * 40.0) * 1.2);
    f_col = vec4(c + u_sun_col * g, 1.0);
}
"""

# voile plein écran (assombrit l'image 3D avant d'y dessiner le portrait du héros)
DIM_VS = """
#version 330
in vec2 in_uv;
void main() { gl_Position = vec4(in_uv, 0.0, 1.0); }
"""

DIM_FS = """
#version 330
uniform vec4 u_col;
out vec4 f_col;
void main() { f_col = u_col; }
"""

UI_VS = """
#version 330
uniform float u_flip;
in vec2 in_uv;
out vec2 v_uv;
void main() {
    v_uv = vec2(in_uv.x * 0.5 + 0.5, u_flip > 0.5 ? 0.5 - in_uv.y * 0.5 : 0.5 + in_uv.y * 0.5);
    gl_Position = vec4(in_uv, 0.0, 1.0);
}
"""

UI_FS = """
#version 330
uniform sampler2D u_tex;
in vec2 v_uv;
out vec4 f_col;
void main() { f_col = texture(u_tex, v_uv); }
"""

# Contour des personnages (coque inversée) : chaque pièce est grossie le long de ses normales d'une épaisseur
# constante à l'écran, poussée un peu en arrière et dessinée en couleur sombre derrière le modèle.
OUTLINE_VS = """
#version 330
uniform mat4 u_vp;
uniform vec2 u_px;
uniform vec3 u_cam;
in vec3 in_pos;
in vec3 in_norm;
in vec3 i_ax;
in vec3 i_ay;
in vec3 i_az;
in vec3 i_pos;
in vec4 i_col;
out vec3 v_col;
void main() {
    mat3 M = mat3(i_ax, i_ay, i_az);
    float size = max(max(length(i_ax), length(i_ay)), length(i_az));
    v_col = i_col.rgb;
    if (size < 0.045 || i_col.a > 0.5) {        // petits détails (yeux, bijoux) et pièces lumineuses : pas de contour
        gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
        return;
    }
    vec3 wp = M * in_pos + i_pos;
    vec3 n = normalize(transpose(inverse(M)) * in_norm);
    wp += normalize(wp - u_cam) * 0.03;          // légèrement derrière la pièce : ne recouvre jamais le modèle
    vec4 c = u_vp * vec4(wp, 1.0);
    vec4 cn = u_vp * vec4(wp + n * 0.05, 1.0);
    vec2 d = cn.xy / cn.w - c.xy / c.w;
    float l = length(d);
    d = l > 1e-6 ? d / l : vec2(0.0);
    c.xy += d * u_px * c.w;
    gl_Position = c;
}
"""

OUTLINE_FS = """
#version 330
in vec3 v_col;
out vec4 f_col;
void main() {
    if (v_col.r < -0.5) discard;
    f_col = vec4(v_col * 0.16 + vec3(0.015, 0.012, 0.02), 1.0);
}
"""


# Personnages animés (glTF) : déformation par le squelette sur la carte graphique, même éclairage que le reste.
SKIN_HEAD = """
#version 330
uniform mat4 u_vp;
uniform mat4 u_model;
uniform mat4 u_joints[64];
in vec3 in_pos;
in vec3 in_norm;
in float in_mat;
in vec3 in_color;
in vec4 in_joints;
in vec4 in_weights;
mat4 skin_matrix() {
    return in_weights.x * u_joints[int(in_joints.x)] + in_weights.y * u_joints[int(in_joints.y)]
         + in_weights.z * u_joints[int(in_joints.z)] + in_weights.w * u_joints[int(in_joints.w)];
}
"""

SKIN_VS = SKIN_HEAD + """
uniform mat4 u_light_vp;
uniform vec4 u_pal[16];
uniform vec4 u_tint;
uniform float u_emis;
out vec3 v_wpos;
out vec3 v_norm;
out vec3 v_col;
out vec4 v_lpos;
out float v_emis;
out float v_flag;
out vec3 v_opos;
out float v_mat;
void main() {
    mat4 S = skin_matrix();
    mat4 M = u_model * S;
    v_opos = (S * vec4(in_pos, 1.0)).xyz * 2.2;
    v_mat = 8.0;
    vec4 wp = M * vec4(in_pos, 1.0);
    v_wpos = wp.xyz;
    v_norm = normalize(mat3(M) * in_norm);
    vec4 pal = u_pal[int(in_mat + 0.5)];
    vec3 base = pal.a > 0.5 ? pal.rgb : in_color;       // couleur choisie (personnalisation) ou celle du modèle
    v_col = pal.r < -0.5 ? vec3(-1.0) : mix(base, u_tint.rgb, u_tint.a);
    v_emis = u_emis;
    v_flag = 0.0;
    v_lpos = u_light_vp * wp;
    gl_Position = u_vp * wp;
}
"""

SKIN_DEPTH_VS = SKIN_HEAD + """
uniform mat4 u_light_vp;
void main() {
    gl_Position = u_light_vp * (u_model * skin_matrix() * vec4(in_pos, 1.0));
}
"""

SKIN_OUTLINE_VS = SKIN_HEAD + """
uniform vec2 u_px;
uniform vec3 u_cam;
uniform vec4 u_pal[16];
out vec3 v_col;
void main() {
    mat4 M = u_model * skin_matrix();
    vec3 wp = (M * vec4(in_pos, 1.0)).xyz;
    vec3 n = normalize(mat3(M) * in_norm);
    wp += normalize(wp - u_cam) * 0.03;
    vec4 c = u_vp * vec4(wp, 1.0);
    vec4 cn = u_vp * vec4(wp + n * 0.05, 1.0);
    vec2 d = cn.xy / cn.w - c.xy / c.w;
    float l = length(d);
    d = l > 1e-6 ? d / l : vec2(0.0);
    c.xy += d * u_px * c.w;
    vec4 pal = u_pal[int(in_mat + 0.5)];
    v_col = pal.a > 0.5 ? pal.rgb : in_color;
    gl_Position = c;
}
"""


# ============================================================================ post-traitement
# La scène est rendue en HDR (RGBA16F) ; le halo lumineux (bloom) est tiré des zones très claires, réduit puis
# flouté sur une chaîne de mips, puis l'image est composée : compression des hautes lumières, étalonnage sombre
# (désaturation, ombres froides, lumières chaudes), vignettage et grain.
POST_VS = """
#version 330
in vec2 in_uv;
out vec2 v_uv;
void main() { v_uv = in_uv * 0.5 + 0.5; gl_Position = vec4(in_uv, 0.0, 1.0); }
"""

# réduction 13 points (Jimenez) ; en première passe, seuil doux et écrêtage des lucioles
DOWN_FS = """
#version 330
uniform sampler2D u_src;
uniform vec2 u_texel;
uniform float u_prefilter;
uniform float u_threshold;
in vec2 v_uv;
out vec4 f_col;
vec3 tap(vec2 o) { return texture(u_src, v_uv + o * u_texel).rgb; }
void main() {
    vec3 a = tap(vec2(-2, 2)), b = tap(vec2(0, 2)), c = tap(vec2(2, 2));
    vec3 d = tap(vec2(-2, 0)), e = tap(vec2(0, 0)), f = tap(vec2(2, 0));
    vec3 g = tap(vec2(-2, -2)), h = tap(vec2(0, -2)), i = tap(vec2(2, -2));
    vec3 j = tap(vec2(-1, 1)), k = tap(vec2(1, 1)), l = tap(vec2(-1, -1)), m = tap(vec2(1, -1));
    vec3 col = e * 0.125 + (a + c + g + i) * 0.03125 + (b + d + f + h) * 0.0625 + (j + k + l + m) * 0.125;
    if (u_prefilter > 0.5) {
        float br = max(col.r, max(col.g, col.b));
        float knee = u_threshold * 0.5;
        float soft = clamp(br - u_threshold + knee, 0.0, 2.0 * knee);
        soft = soft * soft / (4.0 * knee + 1e-4);
        float w = max(soft, br - u_threshold) / max(br, 1e-4);
        col = min(col * w, vec3(12.0));
    }
    f_col = vec4(col, 1.0);
}
"""

# agrandissement en tente 3x3, ajouté au niveau supérieur
UP_FS = """
#version 330
uniform sampler2D u_src;
uniform vec2 u_texel;
uniform float u_radius;
in vec2 v_uv;
out vec4 f_col;
void main() {
    vec2 t = u_texel * u_radius;
    vec3 c = texture(u_src, v_uv).rgb * 4.0;
    c += (texture(u_src, v_uv + vec2(t.x, 0)).rgb + texture(u_src, v_uv - vec2(t.x, 0)).rgb
        + texture(u_src, v_uv + vec2(0, t.y)).rgb + texture(u_src, v_uv - vec2(0, t.y)).rgb) * 2.0;
    c += texture(u_src, v_uv + t).rgb + texture(u_src, v_uv - t).rgb
       + texture(u_src, v_uv + vec2(t.x, -t.y)).rgb + texture(u_src, v_uv + vec2(-t.x, t.y)).rgb;
    f_col = vec4(c / 16.0, 1.0);
}
"""

POST_FS = """
#version 330
uniform sampler2D u_hdr;
uniform sampler2D u_bloom;
uniform float u_exposure;
uniform float u_bloom_k;
uniform float u_sat;
uniform float u_contrast;
uniform vec3 u_shadow_tint;
uniform vec3 u_high_tint;
uniform float u_vignette;
uniform float u_grain;
uniform float u_aberr;
uniform float u_time;
uniform vec2 u_res;
in vec2 v_uv;
out vec4 f_col;
float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
vec3 shoulder(vec3 c) {          // linéaire jusqu'à 0,72 puis compression douce des hautes lumières
    float k = 0.72;
    vec3 o = k + (1.0 - k) * (1.0 - exp(-(c - k) / (1.0 - k)));
    return mix(c, o, step(vec3(k), c));
}
void main() {
    vec2 d = v_uv - 0.5;
    vec3 c;
    if (u_aberr > 0.0) {             // légère aberration chromatique vers les bords
        vec2 o = d * dot(d, d) * u_aberr * 0.012;
        c = vec3(texture(u_hdr, v_uv + o).r, texture(u_hdr, v_uv).g, texture(u_hdr, v_uv - o).b);
    } else {
        c = texture(u_hdr, v_uv).rgb;
    }
    c = c * u_exposure + texture(u_bloom, v_uv).rgb * u_bloom_k;
    c = shoulder(max(c, 0.0));
    float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
    c = mix(vec3(l), c, u_sat);
    c *= mix(u_shadow_tint, u_high_tint, smoothstep(0.05, 0.6, l));
    c = clamp((c - 0.5) * u_contrast + 0.5 + (u_contrast - 1.0) * 0.08, 0.0, 1.0);
    c = mix(c, c * c * (3.0 - 2.0 * c), (u_contrast - 1.0) * 0.6);
    float v = smoothstep(0.85, 0.2, length(d * vec2(1.15, 1.0)));
    c *= mix(1.0, v, u_vignette);
    c += (hash(v_uv * u_res + fract(u_time) * 91.7) - 0.5) * u_grain;
    f_col = vec4(clamp(c, 0.0, 1.0), 1.0);
}
"""
