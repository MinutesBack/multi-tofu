"""Optional role tag per character, used to colour the wheel.

Past five or six clients, reading six names takes longer than reading six
colours. The tag is yours to define, the app never infers it.
"""

# key -> (r, g, b) at full strength. The wheel blends these toward the base
# purple so the ring stays one object rather than a pie chart.
ROLE_COLOURS = {
    "none": None,
    "tank": (86, 141, 214),
    "healer": (95, 210, 150),
    "damage": (226, 104, 104),
    "support": (198, 133, 226),
    "scout": (232, 168, 74),
}

ROLE_KEYS = list(ROLE_COLOURS)


def colour_for(role):
    return ROLE_COLOURS.get(role or "none")


def blend(role_rgb, base_rgb, weight=0.55):
    """Pull a role colour toward the wheel base so the palette holds together."""
    if role_rgb is None:
        return base_rgb
    return tuple(role_rgb[i] * weight + base_rgb[i] * (1 - weight) for i in range(3))
