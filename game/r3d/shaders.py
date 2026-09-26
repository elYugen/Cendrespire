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
void main() {
    mat3 M = mat3(i_ax, i_ay, i_az);
    vec3 wp = M * in_pos + i_pos;
    v_wpos = wp;
    v_norm = normalize(transpose(inverse(M)) * in_norm);
    v_col = in_col.rgb * i_col.rgb;
    v_emis = i_col.a;
    v_flag = in_col.a;
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
in vec3 v_wpos;
in vec3 v_norm;
in vec3 v_col;
in vec4 v_lpos;
in float v_emis;
in float v_flag;
out vec4 f_col;

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
    // murs coupés quand ils masquent le héros (comme dans Minecraft Dungeons)
    if (v_flag > 0.5 && u_cut > 0.0 && v_wpos.y > 0.08) {
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
    vec3 base = v_col;
    vec3 light = mix(u_ground, u_sky, n.y * 0.5 + 0.5);
    float sh = u_shadow_on > 0.5 ? shadow_at() : 1.0;
    light += u_sun_col * max(dot(n, -u_sun_dir), 0.0) * sh;
    for (int i = 0; i < u_nl; i++) {
        vec3 L = u_lpos[i].xyz - v_wpos;
        float d = length(L);
        float r = u_lpos[i].w;
        if (d < r) {
            float a = 1.0 - d / r;
            a *= a;
            float nd = max(dot(n, L / max(d, 0.001)), 0.0) * 0.8 + 0.2;
            light += u_lcol[i].rgb * u_lcol[i].a * a * nd;
        }
    }
    vec3 c = base * light;
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
out vec4 f_col;
void main() {
    vec3 n = normalize(v_norm);
    vec3 vd = normalize(u_cam - v_wpos);
    float rim = 1.0 - abs(dot(n, vd));
    float a = v_emis * (0.35 + 0.65 * rim);
    f_col = vec4(v_col * a, 1.0);
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
in vec2 v_uv;
in vec4 v_col;
out vec4 f_col;
void main() {
    float r = length(v_uv);
    if (u_mode == 0) {
        float a = pow(max(0.0, 1.0 - r), 1.8) * v_col.a;
        f_col = vec4(v_col.rgb * a, 1.0);
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
