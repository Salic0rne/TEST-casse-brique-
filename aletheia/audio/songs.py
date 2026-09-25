"""Bande originale d'ALETHEIA (partitions).

Modes grecs et méditerranéens : dorien, phrygien, phrygien dominant (« hitzaz »),
mineur harmonique. Lyre, aulos, chœurs et tambours sur cadre croisent synthés et arpèges chiptune.
"""
from .synth import note_midi

NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def mname(m):
    return NAMES[m % 12] + str(m // 12 - 1)


def bars(*b):
    return " | ".join(b)


def rep(s, n, sep=" | "):
    return sep.join([s] * n)


def chords(names, steps=16):
    return " | ".join(f"{c} " + ". " * (steps - 1) for c in names).strip()


def rest(nbars):
    return " | ".join(["- " + ". " * 15] * nbars).strip()


def bassline(roots, pat):
    """roots : notes par mesure ('D2'…) ; pat : jetons R (fondamentale), F (quinte), O (octave),
    T (tierce min.), M (tierce maj.), S (septième min.), '.', '-'."""
    out = []
    iv = {"R": 0, "F": 7, "O": 12, "T": 3, "M": 4, "S": 10, "D": -12, "Q": 5}
    for r in roots:
        m = note_midi(r)
        toks = []
        for c in pat.split():
            if c in iv:
                toks.append(mname(m + iv[c]))
            else:
                toks.append(c)
        out.append(" ".join(toks))
    return " | ".join(out)


def drums(*b):
    return "".join(b)


# Rythmes de batterie (16 pas)
DR_ROCK = "x.h.Y.h.x.hkY.hh"
DR_DRIVE = "x.hkY.hkx.hxY.hk"
DR_HALF = "x.h.h.h.Y.h.h.hk"
DR_MECH = "x.hkY.h.xkh.Y.hk"
DR_FILL = "Y.s.s.ssttmmnnSS"
DR_FILL2 = "x.h.Y.h.S.SSmmnn"
DR_CRASH = "z.h.Y.h.x.hkY.hh"
DR_CRASH_D = "z.hkY.hkx.hxY.hk"
DR_NONE = "................"
PERC_DAF = "d..ed.e.d..ed.ee"
PERC_DAF2 = "d..e..d.d.e.e..."
PERC_TICK = ".r.r.r.r.r.r.r.r"


# ---------------------------------------------------------------------------
# TITRE — « Hymne d'Aletheia » (ré mineur)
# ---------------------------------------------------------------------------
_T_MEL_A = bars(
    "D5 . . . . . A4 . D5 . E5 . F5 . . .",
    "D5 . . . . . . . C5 . Bb4 . A4 . . .",
    "A4 . . . C5 . F5 . E5 . . . D5 . C5 .",
    "C5 . . . . . . . - . G4 . C5 . E5 .",
    "F5 . . . E5 . D5 . A5 . . . . . G5 .",
    "F5 . . . E5 . D5 . C5 . D5 . Bb4 . . .",
    "G4 . . . Bb4 . D5 . G5 . F5 . E5 . D5 .",
    "C#5 . . . . . . . E5 . . . A4 . . .",
)
_T_MEL_B = bars(
    "D6 . . . . . C6 . Bb5 . . . A5 . . .",
    "A5 . . . . . G5 . F5 . . . C5 . . .",
    "E5 . . . G5 . . . C6 . . . B5 . G5 .",
    "A5 . . . . . . . . . . . - . . .",
    "D6 . . . F6 . . . E6 . D6 . C6 . Bb5 .",
    "C6 . . . A5 . . . F5 . . . A5 . C6 .",
    "Bb5 . . . A5 . G5 . F5 . . . E5 . . .",
    "C#6 . . . . . . . E6 . . . . . . .",
)
_T_CH_A = ["Dm", "Bb", "F", "C", "Dm", "Bb", "Gm", "A"]
_T_CH_B = ["Bb", "F", "C", "Dm", "Bb", "F", "Gm", "A"]
_T_ROOT_A = ["D2", "Bb1", "F2", "C2", "D2", "Bb1", "G1", "A1"]
_T_ROOT_B = ["Bb1", "F2", "C2", "D2", "Bb1", "F2", "G1", "A1"]

TITLE = {
    "bpm": 92, "seed": 1, "rev_len": 3.0, "rev_decay": 0.8,
    "order": ["intro", "A", "B"],
    "patterns": {
        "intro": {
            "pad": chords(["Dm", "Bb", "F", "A"]),
            "lyre": rest(4),
            "perc": drums("g...............", DR_NONE, DR_NONE, "g.......d...d.d."),
            "bass": bassline(["D2", "Bb1", "F2", "A1"], "R . . . . . . . . . . . . . . ."),
        },
        "A": {
            "lead": _T_MEL_A,
            "pad": chords(_T_CH_A),
            "lyre": rest(8),
            "bass": bassline(_T_ROOT_A, "R . . . . . . . R . . . F . . ."),
            "drums": drums(*(["z.......Y.......", "x.......Y.....k.", "x.......Y.......", "x.......Y...Y.YY"] * 2)),
            "perc": drums(*([PERC_DAF2] * 8)),
        },
        "B": {
            "lead": _T_MEL_B,
            "lead2": _T_MEL_B,
            "pad": chords(_T_CH_B),
            "lyre": rest(8),
            "bass": bassline(_T_ROOT_B, "R . . . R . . . R . . . F . O ."),
            "drums": drums(*(["z.h.Y.h.x.h.Y.h.", "x.h.Y.h.x.hkY.h.", "x.h.Y.h.x.h.Y.h.", "x.h.Y.h.S.SSmmnn"] * 2)),
            "perc": drums(*([PERC_DAF] * 8)),
        },
    },
    "channels": {
        "lead": {"inst": "brass", "vol": 0.42, "rev": 0.35, "pan": -0.1, "params": {"a": 0.06}},
        "lead2": {"inst": "strings", "vol": 0.3, "rev": 0.5, "pan": 0.2, "oct": -1},
        "pad": {"inst": "choir", "chords": True, "vol": 0.28, "rev": 0.6, "oct": 1, "params": {"vowel": "a"}},
        "lyre": {"inst": "lyre", "vol": 0.4, "rev": 0.45, "pan": 0.35,
                 "autoarp": {"pattern": [0, 1, 2, 3, 4, 3, 2, 1], "rate": 2, "oct": 4}},
        "bass": {"inst": "strings", "vol": 0.42, "rev": 0.2, "params": {"a": 0.08}},
        "drums": {"drums": True, "vol": 0.55, "rev": 0.25},
        "perc": {"drums": True, "vol": 0.45, "rev": 0.3, "pan": 0.25},
    },
}


# ---------------------------------------------------------------------------
# STADE I — « Thalassa » (ré dorien)
# ---------------------------------------------------------------------------
_S1_A = bars(
    "D5 . . A4 D5 . E5 . F5 . . . E5 . D5 .",
    "E5 . . . C5 . . . G4 . . . C5 . E5 .",
    "D5 . . B4 G4 . B4 . D5 . . . G5 . F5 .",
    "E5 . . . . . . . D5 . . . A4 . . .",
    "F5 . . . F5 . G5 . A5 . . . G5 . F5 .",
    "G5 . . . E5 . . . C5 . . . E5 . G5 .",
    "A5 . . . F5 . D5 . G5 . E5 . C5 . E5 .",
    "D5 . . . . . . . C#5 . . . E5 . A5 .",
)
_S1_B = bars(
    "D6 . . . C6 . Bb5 . A5 . . . F5 . . .",
    "G5 . . . A5 . G5 . E5 . . . C5 . . .",
    "E5 . . . A5 . . . C6 . . . B5 . A5 .",
    "A5 . . . . . . . . . . . - . . .",
    "D6 . . . F6 . E6 . D6 . . . C6 . Bb5 .",
    "C6 . . . E6 . D6 . C6 . . . G5 . . .",
    "A5 . . . C#6 . . . E6 . . . D6 . C#6 .",
    "A5 . . . . . . . . . . . . . . .",
)
_S1_CA = ["Dm", "C", "G", "Dm", "Bb", "C", "Dm", "A"]
_S1_CB = ["Bb", "C", "Am", "Dm", "Bb", "C", "A", "A"]
_S1_RA = ["D2", "C2", "G1", "D2", "Bb1", "C2", "D2", "A1"]
_S1_RB = ["Bb1", "C2", "A1", "D2", "Bb1", "C2", "A1", "A1"]
_S1_BASS = "R . O . R . O . R . O . R . F ."

STAGE1 = {
    "bpm": 148, "seed": 2,
    "order": ["intro", "A", "B", "A2", "bridge"],
    "patterns": {
        "intro": {
            "pad": chords(["Dm", "C", "Bb", "A"]),
            "arp": rest(4),
            "bass": bassline(["D2", "C2", "Bb1", "A1"], _S1_BASS),
            "drums": drums(DR_CRASH, DR_ROCK, DR_ROCK, DR_FILL),
            "perc": drums(*([PERC_DAF] * 4)),
        },
        "A": {
            "lead": _S1_A,
            "pad": chords(_S1_CA),
            "arp": rest(8),
            "bass": bassline(_S1_RA, _S1_BASS),
            "drums": drums(DR_CRASH, DR_ROCK, DR_ROCK, DR_ROCK, DR_ROCK, DR_ROCK, DR_ROCK, DR_FILL2),
            "perc": drums(*([PERC_DAF] * 8)),
        },
        "B": {
            "lead": _S1_B,
            "lead2": _S1_B,
            "pad": chords(_S1_CB),
            "arp": rest(8),
            "bass": bassline(_S1_RB, _S1_BASS),
            "drums": drums(DR_CRASH_D, DR_DRIVE, DR_DRIVE, DR_DRIVE, DR_DRIVE, DR_DRIVE, DR_DRIVE, DR_FILL),
            "perc": drums(*([PERC_DAF] * 8)),
        },
        "A2": {
            "lead": _S1_A,
            "lead2": _S1_A,
            "pad": chords(_S1_CA),
            "arp": rest(8),
            "bass": bassline(_S1_RA, _S1_BASS),
            "drums": drums(DR_CRASH, DR_ROCK, DR_ROCK, DR_ROCK, DR_ROCK, DR_ROCK, DR_ROCK, DR_FILL2),
            "perc": drums(*([PERC_DAF] * 8)),
        },
        "bridge": {
            "lead": bars("G5 . . . . . . . . . . . F5 . E5 .", "E5 . . . . . . . C#5 . . . . . . .",
                         "D5 . . . . . . . F5 . . . Bb5 . . .", "A5 . . . . . . . . . . . . . . ."),
            "pad": chords(["Gm", "A", "Bb", "A"]),
            "arp": rest(4),
            "bass": bassline(["G1", "A1", "Bb1", "A1"], "R . . . R . . . R . . . R . O ."),
            "drums": drums(DR_HALF, DR_HALF, DR_HALF, DR_FILL),
            "perc": drums(*([PERC_DAF2] * 4)),
        },
    },
    "channels": {
        "lead": {"inst": "aulos", "vol": 0.44, "rev": 0.25, "echo": (3, 0.25), "pan": -0.05},
        "lead2": {"inst": "pulse", "vol": 0.14, "rev": 0.2, "oct": 1, "pan": 0.3,
                  "params": {"duty": 0.25, "decay": 0.25}},
        "pad": {"inst": "strings", "chords": True, "vol": 0.26, "rev": 0.4, "duck": 0.5},
        "arp": {"inst": "pulse", "vol": 0.16, "pan": -0.35, "echo": (3, 0.3),
                "params": {"duty": 0.125, "decay": 0.07},
                "autoarp": {"pattern": [0, 1, 2, 4, 2, 1], "rate": 1, "oct": 5}},
        "bass": {"inst": "fmbass", "vol": 0.5, "lp": 3000},
        "drums": {"drums": True, "vol": 0.62, "rev": 0.12},
        "perc": {"drums": True, "vol": 0.36, "pan": 0.3, "rev": 0.2},
    },
}


# ---------------------------------------------------------------------------
# STADE II — « Labyrinthos » (mi phrygien)
# ---------------------------------------------------------------------------
_S2_A = bars(
    "E5 . . . F5 . . . G5 . . . F5 . E5 .",
    "D5 . . . . . . . C5 . . . D5 . . .",
    "E5 . . . B4 . . . E5 . . . G5 . . .",
    "F5 . . . . . . . . . . . - . . .",
    "A5 . . . G5 . F5 . E5 . . . D5 . . .",
    "E5 . . . D5 . C5 . B4 . . . C5 . . .",
    "A4 . . . C5 . F5 . E5 . . . D5 . C5 .",
    "B4 . . . . . . . G#4 . . . . . . .",
)
_S2_B = bars(
    "A5 . C6 . B5 . A5 . G#5 . . . A5 . . .",
    "C6 . . . A5 . . . F5 . . . A5 . . .",
    "D6 . . . C6 . . . A5 . . . F5 . . .",
    "G#5 . . . . . . . E5 . . . . . . .",
    "A5 . . . E6 . . . D6 . C6 . B5 . A5 .",
    "C6 . . . . . . . A5 . . . F5 . . .",
    "D6 . . . F6 . . . D6 . . . Bb5 . . .",
    "B5 . . . . . . . G#5 . . . E5 . . .",
)
_S2_BASS = "R . . O . . R . R . . O . . F ."
STAGE2 = {
    "bpm": 136, "seed": 3,
    "order": ["intro", "A", "B", "A2"],
    "patterns": {
        "intro": {
            "pad": chords(["Em", "F", "Em", "F"]),
            "bass": bassline(["E2", "F2", "E2", "F2"], _S2_BASS),
            "drums": drums(DR_NONE, DR_NONE, "x.......x.......", DR_FILL),
            "perc": drums(*([PERC_TICK] * 4)),
            "arp": rest(4),
        },
        "A": {
            "lead": _S2_A,
            "pad": chords(["Em", "F", "Em", "F", "Dm", "C", "F", "E"]),
            "bass": bassline(["E2", "F2", "E2", "F2", "D2", "C2", "F2", "E2"], _S2_BASS),
            "drums": drums(DR_CRASH, DR_MECH, DR_MECH, DR_MECH, DR_MECH, DR_MECH, DR_MECH, DR_FILL2),
            "perc": drums(*([PERC_TICK] * 8)),
            "arp": rest(8),
        },
        "B": {
            "lead": _S2_B,
            "pad": chords(["Am", "F", "Dm", "E", "Am", "F", "Bb", "E"]),
            "bass": bassline(["A1", "F2", "D2", "E2", "A1", "F2", "Bb1", "E2"], _S2_BASS),
            "drums": drums(DR_CRASH_D, DR_DRIVE, DR_DRIVE, DR_DRIVE, DR_DRIVE, DR_DRIVE, DR_DRIVE, DR_FILL),
            "perc": drums(*([PERC_TICK] * 8)),
            "arp": rest(8),
        },
        "A2": {
            "lead": _S2_A,
            "lead2": _S2_A,
            "pad": chords(["Em", "F", "Em", "F", "Dm", "C", "F", "E"]),
            "bass": bassline(["E2", "F2", "E2", "F2", "D2", "C2", "F2", "E2"], _S2_BASS),
            "drums": drums(DR_CRASH, DR_MECH, DR_MECH, DR_MECH, DR_MECH, DR_MECH, DR_MECH, DR_FILL),
            "perc": drums(*([PERC_TICK] * 8)),
            "arp": rest(8),
        },
    },
    "channels": {
        "lead": {"inst": "lead", "vol": 0.8, "rev": 0.25, "echo": (3, 0.3), "lp": 5500,
                 "params": {"vib": 10}},
        "lead2": {"inst": "bell", "vol": 0.3, "rev": 0.35, "oct": 1, "pan": 0.35},
        "pad": {"inst": "strings", "chords": True, "vol": 0.18, "rev": 0.45, "duck": 0.4},
        "arp": {"inst": "pulse", "vol": 0.14, "pan": 0.4, "echo": (2, 0.3),
                "params": {"duty": 0.25, "decay": 0.06},
                "autoarp": {"pattern": [0, 2, 1, 2, 0, 2, 1, 3], "rate": 1, "oct": 4}},
        "bass": {"inst": "bass", "vol": 0.52, "lp": 2400, "params": {"fdecay": 12}},
        "drums": {"drums": True, "vol": 0.5, "rev": 0.12},
        "perc": {"drums": True, "vol": 0.7, "pan": -0.4, "rev": 0.25},
    },
}


# ---------------------------------------------------------------------------
# STADE III — « Gorgoneion » (la mineur harmonique)
# ---------------------------------------------------------------------------
_S3_A = bars(
    "E5 . . . . . . . A5 . . . C6 . . .",
    "B5 . . . . . . . A5 . . . . . . .",
    "F5 . . . . . . . E5 . . . D5 . . .",
    "E5 . . . . . . . G#5 . . . . . . .",
    "A5 . . . . . . . E5 . . . A5 . . .",
    "B5 . . . . . . . D6 . . . C6 . B5 .",
    "C6 . . . . . . . A5 . . . F5 . . .",
    "G#5 . . . . . . . B5 . . . E6 . . .",
)
_S3_CH = ["Am", "F", "Dm", "E", "Am", "G", "F", "E"]
_S3_R = ["A1", "F1", "D2", "E2", "A1", "G1", "F1", "E2"]
STAGE3 = {
    "bpm": 124, "seed": 4, "rev_len": 3.2, "rev_decay": 0.9,
    "order": ["intro", "A", "B"],
    "patterns": {
        "intro": {
            "pad": chords(["Am", "F", "Dm", "E"]),
            "bells": rest(4),
            "bass": bassline(["A1", "F1", "D2", "E2"], "R . . . . . . . . . . . . . . ."),
            "perc": drums(*([PERC_DAF2] * 4)),
        },
        "A": {
            "lead": _S3_A,
            "pad": chords(_S3_CH),
            "bells": rest(8),
            "bass": bassline(_S3_R, "R . . . . . . . R . . . F . . ."),
            "drums": drums(*(["x.......Y.......", "x...h...Y...h..k"] * 4)),
            "perc": drums(*([PERC_DAF2] * 8)),
        },
        "B": {
            "lead": _S3_A,
            "lead2": _S3_A,
            "pad": chords(_S3_CH),
            "bells": rest(8),
            "bass": bassline(_S3_R, "R . . R . . R . R . . R . . F ."),
            "drums": drums(*(["x.h.Y.h.x.hkY.h.", "x.h.Y.h.x.hkY.hh"] * 3), "x.h.Y.h.x.hkY.h.", DR_FILL),
            "perc": drums(*([PERC_DAF] * 8)),
        },
    },
    "channels": {
        "lead": {"inst": "strings", "vol": 0.42, "rev": 0.55, "params": {"a": 0.12}},
        "lead2": {"inst": "aulos", "vol": 0.26, "rev": 0.4, "oct": -1, "pan": -0.3, "echo": (6, 0.3)},
        "pad": {"inst": "choir", "chords": True, "vol": 0.3, "rev": 0.6, "params": {"vowel": "o"}},
        "bells": {"inst": "bell", "vol": 0.2, "rev": 0.5, "pan": 0.35, "echo": (3, 0.35),
                  "autoarp": {"pattern": [0, 2, 1, 2, 3, 2, 1, 2], "rate": 2, "oct": 5}},
        "bass": {"inst": "bass", "vol": 0.5, "lp": 1800},
        "drums": {"drums": True, "vol": 0.5, "rev": 0.25},
        "perc": {"drums": True, "vol": 0.42, "pan": 0.2, "rev": 0.3},
    },
}


# ---------------------------------------------------------------------------
# STADE IV — « Hephaisteion » (do phrygien dominant)
# ---------------------------------------------------------------------------
_S4_A = bars(
    "C5 . . C5 . . E5 . F5 . E5 . Db5 . C5 .",
    "Db5 . . . . . . . C5 . . . Bb4 . . .",
    "C5 . . C5 . . E5 . G5 . F5 . E5 . F5 .",
    "G5 . . . . . . . Ab5 . G5 . F5 . E5 .",
    "F5 . . . Ab5 . . . C6 . . . Bb5 . Ab5 .",
    "Ab5 . . . . . . . G5 . F5 . E5 . . .",
    "F5 . . . Db5 . . . Bb4 . . . Db5 . F5 .",
    "E5 . . . . . . . C5 . . . . . . .",
)
_S4_CH = ["C", "Db", "C", "Db", "Fm", "Db", "Bbm", "C"]
_S4_R = ["C2", "Db2", "C2", "Db2", "F1", "Db2", "Bb1", "C2"]
_S4_ANVIL = "....a.......a..a"
STAGE4 = {
    "bpm": 160, "seed": 5,
    "order": ["intro", "A", "B", "A2"],
    "patterns": {
        "intro": {
            "pad": chords(["C", "Db", "C", "Db"]),
            "bass": bassline(["C2", "Db2", "C2", "Db2"], "R . R . R . R . R . R . R . R ."),
            "drums": drums("z...............", "x.......x.......", "x...x...x...x...", DR_FILL),
            "perc": drums(_S4_ANVIL, _S4_ANVIL, _S4_ANVIL, "a.a.a.a.aaaaaaaa"),
        },
        "A": {
            "lead": _S4_A,
            "pad": chords(_S4_CH),
            "bass": bassline(_S4_R, "R . R . R . R . R . R . F . R ."),
            "drums": drums(DR_CRASH_D, DR_DRIVE, DR_DRIVE, DR_DRIVE, DR_DRIVE, DR_DRIVE, DR_DRIVE, DR_FILL),
            "perc": drums(*([_S4_ANVIL] * 8)),
        },
        "B": {
            "lead": _S4_A,
            "lead2": _S4_A,
            "pad": chords(_S4_CH),
            "bass": bassline(_S4_R, "R R R . R R R . R R R . F . O ."),
            "drums": drums("z.hkY.hkx.hxY.hk", *(["x.hkY.hkxkhxY.hk"] * 6), DR_FILL),
            "perc": drums(*(["a...a.......a.aa"] * 8)),
        },
        "A2": {
            "lead": rest(8),
            "pad": chords(_S4_CH),
            "bass": bassline(_S4_R, "R . R . R . R . R . R . F . R ."),
            "drums": drums(DR_CRASH_D, *([DR_DRIVE] * 6), DR_FILL),
            "perc": drums(*([_S4_ANVIL] * 8)),
            "arp": rest(8),
        },
    },
    "channels": {
        "lead": {"inst": "brass", "vol": 0.7, "rev": 0.25, "echo": (3, 0.2), "params": {"a": 0.02}},
        "lead2": {"inst": "lead", "vol": 0.22, "rev": 0.2, "oct": 1, "pan": 0.3, "lp": 4000},
        "pad": {"inst": "organ", "chords": True, "vol": 0.22, "rev": 0.35, "duck": 0.5},
        "arp": {"inst": "pulse", "vol": 0.16, "pan": -0.4, "echo": (3, 0.3),
                "params": {"duty": 0.125, "decay": 0.06},
                "autoarp": {"pattern": [0, 1, 2, 1, 3, 2, 1, 2], "rate": 1, "oct": 5}},
        "bass": {"inst": "fmbass", "vol": 0.48, "lp": 2600, "params": {"index": 4.0}},
        "drums": {"drums": True, "vol": 0.52, "rev": 0.1},
        "perc": {"drums": True, "vol": 0.5, "rev": 0.3, "pan": 0.2},
    },
    "drive": 1.3,
}


# ---------------------------------------------------------------------------
# STADE V — « Tartaros » (si mineur)
# ---------------------------------------------------------------------------
_S5_A = bars(
    "F#5 . . . . . . . D5 . . . B4 . . .",
    "D5 . . . . . . . G5 . . . F#5 . . .",
    "E5 . . . . . . . G5 . . . B5 . . .",
    "A#5 . . . . . . . . . . . F#5 . . .",
    "B5 . . . . . . . A5 . . . F#5 . . .",
    "A5 . . . . . . . F#5 . . . D5 . . .",
    "E5 . . . . . . . C#5 . . . E5 . A5 .",
    "F#5 . . . . . . . C#5 . . . A#4 . . .",
)
_S5_CH = ["Bm", "G", "Em", "F#", "Bm", "D", "A", "F#"]
_S5_R = ["B1", "G1", "E2", "F#1", "B1", "D2", "A1", "F#1"]
STAGE5 = {
    "bpm": 112, "seed": 6, "rev_len": 3.6, "rev_decay": 1.0,
    "order": ["intro", "A", "B"],
    "patterns": {
        "intro": {
            "pad": chords(["Bm", "G", "Em", "F#"]),
            "bass": bassline(["B1", "G1", "E2", "F#1"], "R . . . . . . . . . . . . . . ."),
            "perc": drums("g...............", DR_NONE, "g...............", "d.......d...d.d."),
            "arp": rest(4),
        },
        "A": {
            "lead": _S5_A,
            "pad": chords(_S5_CH),
            "bass": bassline(_S5_R, "R . . . . . . . R . . . . . F ."),
            "drums": drums(*(["x.......Y.......", "x.....x.Y.......", "x.......Y.......", "x.....x.Y...Y.YY"] * 2)),
            "perc": drums("g" + "." * 15, *(["d.......d...e..."] * 7)),
            "arp": rest(8),
        },
        "B": {
            "lead": _S5_A,
            "lead2": _S5_A,
            "pad": chords(_S5_CH),
            "bass": bassline(_S5_R, "R . . R . . R . R . . R . . F ."),
            "drums": drums("z.h.Y.h.x.h.Y.h.", *(["x.h.Y.h.x.hkY.h."] * 6), DR_FILL),
            "perc": drums("g" + "." * 15, *(["d..ed..ed.e.d.ee"] * 7)),
            "arp": rest(8),
        },
    },
    "channels": {
        "lead": {"inst": "bell", "vol": 0.45, "rev": 0.55, "echo": (6, 0.35), "params": {"decay": 0.9}},
        "lead2": {"inst": "strings", "vol": 0.3, "rev": 0.5, "oct": -1, "params": {"a": 0.2}},
        "pad": {"inst": "choir", "chords": True, "vol": 0.34, "rev": 0.6, "params": {"vowel": "u"}},
        "arp": {"inst": "lyre", "vol": 0.24, "rev": 0.5, "pan": -0.35,
                "autoarp": {"pattern": [0, 1, 2, 1, 3, 2, 1, 2], "rate": 2, "oct": 4}},
        "bass": {"inst": "organ", "vol": 0.4, "lp": 1200},
        "drums": {"drums": True, "vol": 0.55, "rev": 0.3},
        "perc": {"drums": True, "vol": 0.45, "rev": 0.45, "pan": 0.2},
    },
}


# ---------------------------------------------------------------------------
# STADE VI — « Olympos » (la mineur épique)
# ---------------------------------------------------------------------------
_S6_A = bars(
    "A4 . . . C5 . E5 . A5 . . . G5 . E5 .",
    "F5 . . . . . . . E5 . . . C5 . . .",
    "G5 . . . . . E5 . C5 . . . E5 . G5 .",
    "D5 . . . . . . . . . . . - . . .",
    "C6 . . . . . B5 . A5 . . . F5 . . .",
    "B5 . . . . . A5 . G5 . . . D5 . . .",
    "E5 . . . A5 . C6 . B5 . A5 . G5 . E5 .",
    "A5 . . . . . . . . . . . . . . .",
)
_S6_B = bars(
    "A5 . . . C6 . . . F6 . . . E6 . . .",
    "D6 . . . . . . . B5 . . . G5 . . .",
    "E6 . . . . . D6 . B5 . . . G5 . . .",
    "C6 . . . . . . . A5 . . . E5 . . .",
    "F5 . . . A5 . . . C6 . . . F6 . . .",
    "E6 . . . D6 . . . B5 . . . G5 . . .",
    "C#6 . . . . . . . E6 . . . . . . .",
    "A6 . . . . . . . . . . . . . . .",
)
STAGE6 = {
    "bpm": 152, "seed": 7,
    "order": ["intro", "A", "B", "A2"],
    "patterns": {
        "intro": {
            "pad": chords(["Am", "F", "G", "E"]),
            "bass": bassline(["A1", "F1", "G1", "E2"], "R . O . R . O . R . O . R . O ."),
            "drums": drums("z...............", "x.......x.......", "x...x...x...x...", DR_FILL),
            "arp": rest(4),
        },
        "A": {
            "lead": _S6_A,
            "pad": chords(["Am", "F", "C", "G", "F", "G", "Am", "Am"]),
            "bass": bassline(["A1", "F1", "C2", "G1", "F1", "G1", "A1", "A1"], "R . O . R . O . R . O . R . F ."),
            "drums": drums(DR_CRASH, *([DR_ROCK] * 6), DR_FILL2),
            "arp": rest(8),
            "perc": drums(*([PERC_DAF] * 8)),
        },
        "B": {
            "lead": _S6_B,
            "lead2": _S6_B,
            "pad": chords(["F", "G", "Em", "Am", "F", "G", "A", "A"]),
            "bass": bassline(["F1", "G1", "E2", "A1", "F1", "G1", "A1", "A1"], "R . O . R . O . R . O . R . F ."),
            "drums": drums(DR_CRASH_D, *([DR_DRIVE] * 6), DR_FILL),
            "arp": rest(8),
            "perc": drums(*([PERC_DAF] * 8)),
        },
        "A2": {
            "lead": _S6_A,
            "lead2": _S6_A,
            "pad": chords(["Am", "F", "C", "G", "F", "G", "Am", "Am"]),
            "bass": bassline(["A1", "F1", "C2", "G1", "F1", "G1", "A1", "A1"], "R . O . R . O . R . O . R . F ."),
            "drums": drums(DR_CRASH_D, *([DR_DRIVE] * 6), DR_FILL),
            "arp": rest(8),
            "perc": drums(*([PERC_DAF] * 8)),
        },
    },
    "channels": {
        "lead": {"inst": "brass", "vol": 0.56, "rev": 0.35, "params": {"a": 0.03}},
        "lead2": {"inst": "choir", "vol": 0.26, "rev": 0.55, "params": {"vowel": "a", "a": 0.08}},
        "pad": {"inst": "strings", "chords": True, "vol": 0.26, "rev": 0.45, "duck": 0.45},
        "arp": {"inst": "pulse", "vol": 0.15, "pan": 0.4, "echo": (3, 0.3),
                "params": {"duty": 0.125, "decay": 0.07},
                "autoarp": {"pattern": [0, 1, 2, 4, 2, 1, 2, 3], "rate": 1, "oct": 5}},
        "bass": {"inst": "fmbass", "vol": 0.5, "lp": 3000},
        "drums": {"drums": True, "vol": 0.62, "rev": 0.15},
        "perc": {"drums": True, "vol": 0.34, "pan": -0.3, "rev": 0.25},
    },
}


# ---------------------------------------------------------------------------
# BOSS — « Theomachia » (mi mineur / phrygien dominant)
# ---------------------------------------------------------------------------
_B_A = bars(
    "E5 . G5 . B5 . E6 . D6 . B5 . G5 . A5 .",
    "B5 . . . G5 . E5 . C5 . . . D5 . E5 .",
    "G5 . . . F#5 . E5 . D#5 . E5 . F#5 . G5 .",
    "A5 . . . . . . . G5 . . . E5 . . .",
    "C6 . . . B5 . A5 . E5 . . . A5 . C6 .",
    "D#6 . . . . . C6 . B5 . . . F#5 . . .",
    "G5 . F#5 . E5 . D#5 . E5 . F#5 . G5 . B5 .",
    "B5 . . . . . . . D#6 . . . F#6 . . .",
)
BOSS = {
    "bpm": 172, "seed": 8,
    "order": ["intro", "A", "A2"],
    "patterns": {
        "intro": {
            "pad": chords(["Em", "F", "Em", "B"]),
            "bass": bassline(["E2", "F2", "E2", "B1"], "R R O R R R O R R R O R R F O R"),
            "drums": drums("z...x...x...x...", "x...x...x...x...", "x.x.x.x.x.x.x.x.", "SSSSSSSSmmmmnnnn"),
            "arp": rest(4),
        },
        "A": {
            "lead": _B_A,
            "pad": chords(["Em", "C", "Em", "C", "Am", "B", "Em", "B"]),
            "bass": bassline(["E2", "C2", "E2", "C2", "A1", "B1", "E2", "B1"], "R . O R R . O R R . O R R . F O"),
            "drums": drums(DR_CRASH_D, *([DR_DRIVE] * 6), DR_FILL),
            "arp": rest(8),
        },
        "A2": {
            "lead": _B_A,
            "lead2": _B_A,
            "pad": chords(["Em", "C", "Em", "C", "Am", "B", "Em", "B"]),
            "bass": bassline(["E2", "C2", "E2", "C2", "A1", "B1", "E2", "B1"], "R . O R R . O R R . O R R . F O"),
            "drums": drums("z.hkY.hkxkhxY.hk", *(["x.hkY.hkxkhxY.hk"] * 6), DR_FILL),
            "arp": rest(8),
        },
    },
    "channels": {
        "lead": {"inst": "lead", "vol": 1.0, "rev": 0.2, "echo": (3, 0.22), "lp": 6000, "params": {"vib": 12}},
        "lead2": {"inst": "brass", "vol": 0.4, "rev": 0.25, "oct": -1, "pan": -0.3},
        "pad": {"inst": "strings", "chords": True, "vol": 0.2, "rev": 0.35, "duck": 0.55},
        "arp": {"inst": "pulse", "vol": 0.15, "pan": 0.4, "echo": (2, 0.25),
                "params": {"duty": 0.25, "decay": 0.05},
                "autoarp": {"pattern": [0, 1, 2, 3, 2, 1], "rate": 1, "oct": 5}},
        "bass": {"inst": "fmbass", "vol": 0.45, "lp": 3200, "params": {"index": 3.8}},
        "drums": {"drums": True, "vol": 0.5, "rev": 0.1},
    },
    "drive": 1.35,
}


# ---------------------------------------------------------------------------
# BOSS FINAL — « Keraunos » (ré mineur)
# ---------------------------------------------------------------------------
_F_A = bars(
    "D5 . . . . . F5 . A5 . . . D6 . . .",
    "C6 . . . . . Bb5 . A5 . . . F5 . . .",
    "G5 . . . Bb5 . . . D6 . . . C6 . Bb5 .",
    "A5 . . . . . . . C#6 . . . E6 . . .",
    "F6 . . . E6 . D6 . A5 . . . D6 . . .",
    "Eb6 . . . . . D6 . C6 . . . Bb5 . . .",
    "A5 . . . D6 . . . F6 . . . E6 . D6 .",
    "C#6 . . . . . . . A5 . . . . . . .",
)
FINAL = {
    "bpm": 160, "seed": 9, "rev_len": 3.0, "rev_decay": 0.8,
    "order": ["intro", "A", "B"],
    "patterns": {
        "intro": {
            "pad": chords(["Dm", "Bb", "Gm", "A"]),
            "bass": bassline(["D2", "Bb1", "G1", "A1"], "R . R . R . R . R . R . R . O ."),
            "drums": drums("z...............", "x.......Y.......", "x...Y...x...Y...", "SSSSSSSSmmmmnnnn"),
            "perc": drums("g...............", DR_NONE, "g...............", DR_NONE),
            "arp": rest(4),
        },
        "A": {
            "lead": _F_A,
            "pad": chords(["Dm", "Bb", "Gm", "A", "Dm", "Eb", "Dm", "A"]),
            "bass": bassline(["D2", "Bb1", "G1", "A1", "D2", "Eb2", "D2", "A1"], "R . O R R . O R R . O R R . F O"),
            "drums": drums(DR_CRASH_D, *([DR_DRIVE] * 6), DR_FILL),
            "perc": drums("g" + "." * 15, *([DR_NONE] * 7)),
            "arp": rest(8),
        },
        "B": {
            "lead": _F_A,
            "lead2": _F_A,
            "pad": chords(["Dm", "Bb", "Gm", "A", "Dm", "Eb", "Dm", "A"]),
            "bass": bassline(["D2", "Bb1", "G1", "A1", "D2", "Eb2", "D2", "A1"], "R R O R R R O R R R O R R F O R"),
            "drums": drums("z.hkY.hkxkhxY.hk", *(["x.hkY.hkxkhxY.hk"] * 6), DR_FILL),
            "perc": drums("g" + "." * 15, *([DR_NONE] * 7)),
            "arp": rest(8),
        },
    },
    "channels": {
        "lead": {"inst": "brass", "vol": 0.65, "rev": 0.3, "params": {"a": 0.02}},
        "lead2": {"inst": "choir", "vol": 0.3, "rev": 0.5, "params": {"vowel": "a", "a": 0.06}},
        "pad": {"inst": "organ", "chords": True, "vol": 0.22, "rev": 0.45, "duck": 0.5, "root": True},
        "arp": {"inst": "pulse", "vol": 0.15, "pan": -0.4, "echo": (3, 0.3),
                "params": {"duty": 0.125, "decay": 0.06},
                "autoarp": {"pattern": [0, 1, 2, 3, 4, 3, 2, 1], "rate": 1, "oct": 5}},
        "bass": {"inst": "fmbass", "vol": 0.55, "lp": 3000},
        "drums": {"drums": True, "vol": 0.52, "rev": 0.12},
        "perc": {"drums": True, "vol": 0.5, "rev": 0.4},
    },
    "drive": 1.3,
}


# ---------------------------------------------------------------------------
# Jingles
# ---------------------------------------------------------------------------
GAMEOVER = {
    "bpm": 66, "seed": 10, "loop": False, "rev_len": 3.0, "rev_decay": 0.9,
    "order": ["A"],
    "patterns": {
        "A": {
            "lead": bars("A5 . . . . . F5 . D5 . . . . . . .", "G5 . . . . . E5 . C#5 . . . . . . .",
                         "D5 . . . . . . . . . . . . . . ."),
            "pad": chords(["Dm", "A", "Dm"]),
            "lyre": rest(3),
            "perc": drums("g...............", DR_NONE, "d...............")
        },
    },
    "channels": {
        "lead": {"inst": "strings", "vol": 0.45, "rev": 0.5},
        "pad": {"inst": "choir", "chords": True, "vol": 0.3, "rev": 0.6, "params": {"vowel": "o"}},
        "lyre": {"inst": "lyre", "vol": 0.3, "rev": 0.5,
                 "autoarp": {"pattern": [4, 3, 2, 1, 0, 1, 2, 3], "rate": 2, "oct": 4}},
        "perc": {"drums": True, "vol": 0.5, "rev": 0.5},
    },
}

ENDING = {
    "bpm": 84, "seed": 11, "rev_len": 3.2, "rev_decay": 0.9,
    "order": ["intro", "A", "B"],
    "patterns": {
        "intro": dict(TITLE["patterns"]["intro"]),
        "A": {
            "lead": _T_MEL_A,
            "pad": chords(_T_CH_A),
            "lyre": rest(8),
            "bass": bassline(_T_ROOT_A, "R . . . . . . . R . . . F . . ."),
            "perc": drums(*([PERC_DAF2] * 8)),
        },
        "B": {
            "lead": _T_MEL_B,
            "lead2": _T_MEL_B,
            "pad": chords(_T_CH_B),
            "lyre": rest(8),
            "bass": bassline(_T_ROOT_B, "R . . . R . . . R . . . F . O ."),
            "drums": drums(*(["z.......Y.......", "x.......Y.......", "x.......Y.......", "x.......Y...Y.YY"] * 2)),
            "perc": drums(*([PERC_DAF] * 8)),
        },
    },
    "channels": {
        "lead": {"inst": "aulos", "vol": 0.4, "rev": 0.45, "echo": (6, 0.25)},
        "lead2": {"inst": "choir", "vol": 0.26, "rev": 0.6, "params": {"vowel": "a"}},
        "pad": {"inst": "strings", "chords": True, "vol": 0.3, "rev": 0.6},
        "lyre": {"inst": "lyre", "vol": 0.32, "rev": 0.45, "pan": 0.35,
                 "autoarp": {"pattern": [0, 1, 2, 3, 4, 3, 2, 1], "rate": 2, "oct": 4}},
        "bass": {"inst": "strings", "vol": 0.4, "rev": 0.3},
        "drums": {"drums": True, "vol": 0.45, "rev": 0.3},
        "perc": {"drums": True, "vol": 0.4, "rev": 0.35, "pan": 0.25},
    },
}

SONGS = {
    "title": TITLE, "stage1": STAGE1, "stage2": STAGE2, "stage3": STAGE3, "stage4": STAGE4,
    "stage5": STAGE5, "stage6": STAGE6, "boss": BOSS, "final": FINAL, "gameover": GAMEOVER,
    "ending": ENDING,
}
# ordre de rendu en arrière-plan (le titre d'abord)
RENDER_ORDER = ["title", "stage1", "boss", "gameover", "stage2", "stage3", "stage4", "stage5", "stage6",
                "final", "ending"]
