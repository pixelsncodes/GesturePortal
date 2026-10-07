"""Shared desktop theme, following the charcoal/mint GesturePortal mockups."""
BG = '#12191d'
SURFACE = '#1b2429'
FIELD = '#263238'
BORDER = '#60747d'
TEXT = '#eff5f3'
MUTED = '#b2c3c7'
ACCENT = '#56dfb3'
ON_ACCENT = '#10251e'
ERROR = '#ffad9e'
FONT = 'Segoe UI'
MONO = 'Cascadia Mono'


def configure(root, ttk):
    root.configure(bg=BG)
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('.', font=(FONT, 10), background=SURFACE, foreground=TEXT)
    style.configure('TFrame', background=SURFACE)
    style.configure('Outer.TFrame', background=BG)
    style.configure('TLabel', background=SURFACE, foreground=TEXT)
    style.configure('Hint.TLabel', foreground=MUTED, font=(FONT, 9))
    style.configure('Title.TLabel', font=(FONT, 17, 'bold'))
    style.configure('TLabelframe', background=SURFACE, bordercolor=BORDER, relief='flat')
    style.configure('TLabelframe.Label', foreground=MUTED, background=SURFACE, font=(FONT, 10, 'bold'))
    style.configure('TButton', background=FIELD, foreground=TEXT, padding=(12, 8),
                    bordercolor=BORDER, lightcolor=FIELD, darkcolor=FIELD,
                    focuscolor=ACCENT, focusthickness=2, relief='flat')
    style.map('TButton', background=[('active', '#34464e'), ('pressed', '#405963')],
              foreground=[('disabled', MUTED)])
    style.configure('Accent.TButton', background=ACCENT, foreground=ON_ACCENT, bordercolor=ACCENT,
                    lightcolor=ACCENT, darkcolor=ACCENT)
    style.map('Accent.TButton', background=[('active', '#86efd0'), ('pressed', '#3bc497')],
              foreground=[('disabled', '#45645a')])
    style.configure('TCombobox', fieldbackground=FIELD, background=FIELD, foreground=TEXT,
                    arrowcolor=ACCENT, padding=8, bordercolor=BORDER, focuscolor=ACCENT,
                    lightcolor=FIELD, darkcolor=FIELD)
    style.map('TCombobox', fieldbackground=[('readonly', FIELD)],
              foreground=[('readonly', TEXT), ('disabled', MUTED)],
              selectbackground=[('readonly', FIELD)], selectforeground=[('readonly', TEXT)])
    style.configure('Horizontal.TScale', background=SURFACE, troughcolor=FIELD,
                    bordercolor=BORDER, lightcolor=ACCENT, darkcolor=ACCENT)
    style.configure('Vertical.TScrollbar', background=FIELD, troughcolor=SURFACE,
                    bordercolor=SURFACE, lightcolor=FIELD, darkcolor=FIELD, arrowcolor=MUTED)
    style.map('Vertical.TScrollbar', background=[('disabled', FIELD), ('active', '#34464e')],
              lightcolor=[('disabled', FIELD)], darkcolor=[('disabled', FIELD)],
              arrowcolor=[('disabled', MUTED)])
    style.configure('TCheckbutton', background=SURFACE, foreground=MUTED, focuscolor=ACCENT)
    style.map('TCheckbutton', background=[('active', SURFACE)])
    root.option_add('*TCombobox*Listbox.background', FIELD)
    root.option_add('*TCombobox*Listbox.foreground', TEXT)
    root.option_add('*TCombobox*Listbox.selectBackground', ACCENT)
    root.option_add('*TCombobox*Listbox.selectForeground', ON_ACCENT)
    return style
