"""Interface strings in English, French, Spanish and Portuguese.

Character names are never translated. They come from the Dofus window title at
runtime. Only the placeholder shown for a client that has not logged a
character in yet is localised.
"""
import re

from AppKit import NSLocale

SUPPORTED = ("en", "fr", "es", "pt")

LANGUAGE_NAMES = {
    "auto": {"en": "System", "fr": "Système", "es": "Sistema", "pt": "Sistema"},
    "en": {"en": "English", "fr": "English", "es": "English", "pt": "English"},
    "fr": {"en": "Français", "fr": "Français", "es": "Français", "pt": "Français"},
    "es": {"en": "Español", "fr": "Español", "es": "Español", "pt": "Español"},
    "pt": {"en": "Português", "fr": "Português", "es": "Português", "pt": "Português"},
}

STRINGS = {
    # menu bar
    "menu_header": {
        "en": "{name} {version}, {count} in rotation",
        "fr": "{name} {version}, {count} dans la rotation",
        "es": "{name} {version}, {count} en la rotación",
        "pt": "{name} {version}, {count} na rotação",
    },
    "menu_access_off": {
        "en": "Shortcuts off, fix Accessibility",
        "fr": "Raccourcis inactifs, corriger l'Accessibilité",
        "es": "Atajos inactivos, arreglar Accesibilidad",
        "pt": "Atalhos inativos, corrigir Acessibilidade",
    },
    "menu_no_client": {
        "en": "No Dofus window found",
        "fr": "Aucune fenêtre Dofus détectée",
        "es": "Ninguna ventana de Dofus detectada",
        "pt": "Nenhuma janela do Dofus encontrada",
    },
    "menu_rotation": {
        "en": "Rotation: {mode}",
        "fr": "Rotation : {mode}",
        "es": "Rotación: {mode}",
        "pt": "Rotação: {mode}",
    },
    "mode_all": {"en": "ALL", "fr": "TOUS", "es": "TODOS", "pt": "TODOS"},
    "menu_rescan": {
        "en": "Rescan windows",
        "fr": "Rechercher les fenêtres",
        "es": "Buscar ventanas",
        "pt": "Procurar janelas",
    },
    "menu_prefs": {
        "en": "Settings...", "fr": "Réglages...",
        "es": "Ajustes...", "pt": "Ajustes...",
    },
    "menu_quit": {"en": "Quit", "fr": "Quitter", "es": "Salir", "pt": "Sair"},
    "leader_tag": {"en": "leader", "fr": "chef", "es": "líder", "pt": "líder"},

    # the placeholder for a client sitting on the login screen
    "account_placeholder": {
        "en": "Account {number}",
        "fr": "Compte {number}",
        "es": "Cuenta {number}",
        "pt": "Conta {number}",
    },

    # settings window
    "prefs_title": {
        "en": "{name} Settings", "fr": "Réglages {name}",
        "es": "Ajustes {name}", "pt": "Ajustes {name}",
    },
    "global_shortcuts": {
        "en": "Global shortcuts", "fr": "Raccourcis globaux",
        "es": "Atajos globales", "pt": "Atalhos globais",
    },
    "bind_next": {
        "en": "Next character", "fr": "Personnage suivant",
        "es": "Personaje siguiente", "pt": "Próximo personagem",
    },
    "bind_prev": {
        "en": "Previous character", "fr": "Personnage précédent",
        "es": "Personaje anterior", "pt": "Personagem anterior",
    },
    "bind_leader": {
        "en": "Focus leader", "fr": "Aller au chef",
        "es": "Ir al líder", "pt": "Ir para o líder",
    },
    "bind_refresh": {
        "en": "Rescan windows", "fr": "Rechercher les fenêtres",
        "es": "Buscar ventanas", "pt": "Procurar janelas",
    },
    "bind_prefs": {
        "en": "Open settings", "fr": "Ouvrir les réglages",
        "es": "Abrir ajustes", "pt": "Abrir ajustes",
    },
    "wheel_modifier": {
        "en": "Wheel key:", "fr": "Touche de la roue :",
        "es": "Tecla de la rueda:", "pt": "Tecla da roda:",
    },
    "wheel_on": {
        "en": "Wheel on", "fr": "Roue active",
        "es": "Rueda activa", "pt": "Roda ativa",
    },
    "leader_label": {"en": "Leader:", "fr": "Chef :", "es": "Líder:", "pt": "Líder:"},
    "language_label": {
        "en": "Language:", "fr": "Langue :", "es": "Idioma:", "pt": "Idioma:",
    },
    "rescan_button": {
        "en": "Rescan", "fr": "Actualiser", "es": "Actualizar", "pt": "Atualizar",
    },
    "characters": {
        "en": "Characters", "fr": "Personnages",
        "es": "Personajes", "pt": "Personagens",
    },
    "col_order": {"en": "Order", "fr": "Ordre", "es": "Orden", "pt": "Ordem"},
    "col_on": {"en": "On", "fr": "Actif", "es": "Activo", "pt": "Ativo"},
    "col_character": {
        "en": "Character", "fr": "Personnage", "es": "Personaje", "pt": "Personagem",
    },
    "col_class": {"en": "Class", "fr": "Classe", "es": "Clase", "pt": "Classe"},
    "col_team": {"en": "Team", "fr": "Équipe", "es": "Equipo", "pt": "Equipe"},
    "col_key": {
        "en": "Direct key", "fr": "Touche directe",
        "es": "Tecla directa", "pt": "Tecla direta",
    },
    "option_none": {
        "en": "(none)", "fr": "(aucun)", "es": "(ninguno)", "pt": "(nenhum)",
    },
    "bind_empty": {
        "en": "None", "fr": "Aucune", "es": "Ninguna", "pt": "Nenhuma",
    },
    "press_a_key": {
        "en": "Press a key...", "fr": "Appuyez sur une touche...",
        "es": "Pulsa una tecla...", "pt": "Pressione uma tecla...",
    },
    "grant_first": {
        "en": "Grant Accessibility first",
        "fr": "Autorisez l'Accessibilité d'abord",
        "es": "Autoriza Accesibilidad primero",
        "pt": "Autorize a Acessibilidade primeiro",
    },

    # status line
    "status_no_access": {
        "en": "Accessibility is off, so nothing works yet. System Settings > "
              "Privacy & Security > Accessibility.",
        "fr": "L'Accessibilité est désactivée, rien ne fonctionne encore. "
              "Réglages Système > Confidentialité et sécurité > Accessibilité.",
        "es": "La Accesibilidad está desactivada, todavía no funciona nada. "
              "Ajustes del Sistema > Privacidad y seguridad > Accesibilidad.",
        "pt": "A Acessibilidade está desativada, nada funciona ainda. Ajustes "
              "do Sistema > Privacidade e segurança > Acessibilidade.",
    },
    "status_no_client": {
        "en": "Ready. No Dofus client open yet. Launch your clients and this "
              "list fills in with their character names.",
        "fr": "Prêt. Aucun client Dofus ouvert. Lancez vos clients et la liste "
              "se remplit avec le nom de vos personnages.",
        "es": "Listo. Ningún cliente de Dofus abierto. Abre tus clientes y la "
              "lista se llena con el nombre de tus personajes.",
        "pt": "Pronto. Nenhum cliente do Dofus aberto. Abra seus clientes e a "
              "lista se preenche com o nome dos seus personagens.",
    },
    "status_ready": {
        "en": "Ready. {count} client(s) detected, {rotation} in the rotation.",
        "fr": "Prêt. {count} client(s) détecté(s), {rotation} dans la rotation.",
        "es": "Listo. {count} cliente(s) detectado(s), {rotation} en la rotación.",
        "pt": "Pronto. {count} cliente(s) detectado(s), {rotation} na rotação.",
    },

    # alerts
    "access_alert_title": {
        "en": "Accessibility permission needed",
        "fr": "Autorisation d'Accessibilité requise",
        "es": "Se necesita permiso de Accesibilidad",
        "pt": "Permissão de Acessibilidade necessária",
    },
    "access_alert_body": {
        "en": "{name} reads Dofus window titles and listens for your shortcuts "
              "through the Accessibility API.\n\nOpen System Settings > Privacy "
              "& Security > Accessibility and switch {name} on. If an old "
              "{name} row is already there, select it, press the minus button "
              "to remove it, then launch {name} again and approve the prompt. A "
              "stale row from a previous build looks switched on but no longer "
              "matches the app.\n\nNo need to quit. The shortcuts come on by "
              "themselves within a couple of seconds.",
        "fr": "{name} lit les titres des fenêtres Dofus et écoute vos raccourcis "
              "via l'API d'Accessibilité.\n\nOuvrez Réglages Système > "
              "Confidentialité et sécurité > Accessibilité et activez {name}. Si "
              "une ancienne ligne {name} s'y trouve déjà, sélectionnez-la, "
              "retirez-la avec le bouton moins, puis relancez {name} et acceptez "
              "la demande. Une ligne héritée d'une ancienne version paraît "
              "active mais ne correspond plus à l'app.\n\nInutile de quitter. "
              "Les raccourcis s'activent seuls en quelques secondes.",
        "es": "{name} lee los títulos de las ventanas de Dofus y escucha tus "
              "atajos mediante la API de Accesibilidad.\n\nAbre Ajustes del "
              "Sistema > Privacidad y seguridad > Accesibilidad y activa {name}. "
              "Si ya hay una fila antigua de {name}, selecciónala, quítala con "
              "el botón menos, vuelve a abrir {name} y acepta la solicitud. Una "
              "fila de una versión anterior parece activada pero ya no coincide "
              "con la app.\n\nNo hace falta salir. Los atajos se activan solos "
              "en unos segundos.",
        "pt": "O {name} lê os títulos das janelas do Dofus e escuta seus atalhos "
              "pela API de Acessibilidade.\n\nAbra Ajustes do Sistema > "
              "Privacidade e segurança > Acessibilidade e ative o {name}. Se já "
              "houver uma linha antiga do {name}, selecione-a, remova-a com o "
              "botão de menos, abra o {name} de novo e aceite a solicitação. Uma "
              "linha de uma versão anterior parece ativada mas não corresponde "
              "mais ao app.\n\nNão precisa sair. Os atalhos ligam sozinhos em "
              "alguns segundos.",
    },
    "menubar_alert_title": {
        "en": "{name} is running, but you cannot see it",
        "fr": "{name} tourne, mais reste invisible",
        "es": "{name} está funcionando, pero no se ve",
        "pt": "O {name} está rodando, mas você não vê",
    },
    "menubar_alert_body": {
        "en": "Your menu bar is full, so macOS put the {name} icon behind the "
              "notch where it cannot be drawn.\n\nShow a Dock icon instead, or "
              "close a menu bar item to free a slot. Either way the shortcuts "
              "work right now: F1 next, F2 previous, F3 leader, hold Option for "
              "the wheel, Control+F1 for settings.",
        "fr": "Votre barre des menus est pleine, macOS a donc placé l'icône "
              "{name} derrière l'encoche, où elle ne peut pas s'afficher.\n\n"
              "Affichez plutôt une icône dans le Dock, ou fermez un élément de "
              "la barre des menus pour libérer une place. Dans les deux cas les "
              "raccourcis fonctionnent déjà : F1 suivant, F2 précédent, F3 chef, "
              "maintenez Option pour la roue, Control+F1 pour les réglages.",
        "es": "Tu barra de menús está llena, así que macOS puso el icono de "
              "{name} detrás de la muesca, donde no se puede dibujar.\n\nMuestra "
              "un icono en el Dock, o cierra un elemento de la barra para "
              "liberar sitio. En ambos casos los atajos ya funcionan: F1 "
              "siguiente, F2 anterior, F3 líder, mantén Opción para la rueda, "
              "Control+F1 para los ajustes.",
        "pt": "Sua barra de menus está cheia, então o macOS colocou o ícone do "
              "{name} atrás do entalhe, onde ele não pode ser desenhado.\n\n"
              "Mostre um ícone no Dock, ou feche um item da barra para liberar "
              "espaço. De todo jeito os atalhos já funcionam: F1 próximo, F2 "
              "anterior, F3 líder, segure Option para a roda, Control+F1 para os "
              "ajustes.",
    },
    "menubar_alert_dock": {
        "en": "Show a Dock icon", "fr": "Afficher une icône dans le Dock",
        "es": "Mostrar icono en el Dock", "pt": "Mostrar ícone no Dock",
    },
    "menubar_alert_keep": {
        "en": "Leave it in the menu bar", "fr": "Laisser dans la barre des menus",
        "es": "Dejarlo en la barra de menús", "pt": "Deixar na barra de menus",
    },
    "alert_ok": {"en": "OK", "fr": "OK", "es": "OK", "pt": "OK"},
    # French puts a space before a colon
    "colon": {"en": ":", "fr": " :", "es": ":", "pt": ":"},
    "team_label": {
        "en": "Team {number}", "fr": "Équipe {number}",
        "es": "Equipo {number}", "pt": "Equipe {number}",
    },
}

_TEAM_RE = re.compile(r"^Team (\d+)$")
_current = "en"


def detect():
    """The first preferred language macOS reports that we actually speak."""
    try:
        for tag in NSLocale.preferredLanguages():
            code = str(tag).split("-")[0].lower()
            if code in SUPPORTED:
                return code
    except Exception:
        pass
    return "en"


def set_language(code):
    global _current
    if not code or code == "auto":
        _current = detect()
    elif code in SUPPORTED:
        _current = code
    else:
        _current = "en"
    return _current


def current():
    return _current


def language_name(code, in_language=None):
    return LANGUAGE_NAMES.get(code, {}).get(in_language or _current, code)


def team_display(name):
    """Teams are stored as 'Team 1' so the config stays language independent.
    Only the label the user reads changes."""
    match = _TEAM_RE.match(str(name or ""))
    if not match:
        return name
    return t("team_label", number=match.group(1))


def t(key, **kwargs):
    entry = STRINGS.get(key)
    if entry is None:
        return key
    text = entry.get(_current) or entry.get("en") or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text
