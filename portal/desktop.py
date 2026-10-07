"""Camera-first Tk desktop shell. All widgets and rendering live in the UI process."""
import io
import json
import time
from pathlib import Path

from PIL import Image, ImageTk

from . import theme as t
from .controls import ControlWindow, FIELDS, MODEL_LABELS, SUBJECT_LABELS, default_settings, normalized_settings
from .styles import STYLES, STYLE_LABELS, style_name, infer_style


class DesktopWindow(ControlWindow):
    def __init__(self, config, root_path):
        import tkinter as tk
        from tkinter import ttk
        self.tk, self.ttk = tk, ttk
        self.path = Path(root_path) / 'controls.json'
        self.defaults_path = Path(root_path) / 'config.flux.json'
        defaults = json.loads(self.defaults_path.read_text(encoding='utf-8'))
        self.values = default_settings(config, defaults)
        self.styles = {}
        saved_notice = ''
        if self.path.exists():
            try:
                saved = json.loads(self.path.read_text(encoding='utf-8'))
                if 'style_preset' not in saved and 'edit_prompt' in saved:
                    saved['style_preset'] = infer_style(saved['edit_prompt'])
                self.values = normalized_settings(dict(self.values, **{key: saved[key] for key in FIELDS if key in saved}))
                self.styles = {key: float(value) for key, value in saved.get('style_strengths', {}).items()
                               if 0 <= float(value) <= 1}
            except (ValueError, TypeError, AttributeError):
                saved_notice = 'Saved settings could not be read. Defaults loaded.'
        self.config = dict(config)
        self.changed_at = self.model_request = None
        self.syncing = False
        self.actions = []
        self.compact = False
        self.settings_visible = True
        self.latest_image = self.photo = None
        self.status = {'phase': 'checking', 'ready': False, 'elapsed': 0}
        self.rotation = 0
        self.animation_timer = None
        self.root = tk.Tk()
        self.root.title('GesturePortal')
        width = max(960, min(1520, self.root.winfo_screenwidth() - 80))
        height = max(640, min(900, self.root.winfo_screenheight() - 100))
        self.full_geometry = f'{width}x{height}'
        self.root.geometry(self.full_geometry)
        self.root.minsize(960, 640)
        self.root.protocol('WM_DELETE_WINDOW', lambda: self.action(ord('q')))
        t.configure(self.root, ttk)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        header = ttk.Frame(self.root, style='Outer.TFrame', padding=(24, 16))
        header.grid(row=0, column=0, sticky='ew')
        brand = tk.Frame(header, bg=t.BG)
        brand.pack(side='left')
        tk.Label(brand, text='Gesture', bg=t.BG, fg=t.TEXT, font=(t.FONT, 22, 'bold')).pack(side='left')
        tk.Label(brand, text='Portal', bg=t.BG, fg=t.ACCENT, font=(t.FONT, 22, 'bold')).pack(side='left')
        self.local_label = tk.Label(header, text='LOCAL AI CAMERA', bg=t.BG, fg=t.MUTED, font=(t.FONT, 9))
        self.local_label.pack(side='left', padx=24)
        self.widget_button = ttk.Button(header, text='Widget', command=self.toggle_widget)
        self.widget_button.pack(side='right')
        self.settings_button = ttk.Button(header, text='Settings', command=self.toggle)
        self.settings_button.pack(side='right', padx=(0, 8))

        self.content = ttk.Frame(self.root, style='Outer.TFrame', padding=(24, 0, 24, 0))
        self.content.grid(row=1, column=0, sticky='nsew')
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)
        self.viewer = tk.Canvas(self.content, background='#0b1013', highlightbackground=t.BORDER,
                                highlightthickness=1, takefocus=True)
        self.viewer.grid(row=0, column=0, sticky='nsew')
        self.viewer.bind('<Configure>', lambda _: self.render())
        self.viewer.bind('<Button-1>', lambda _: self.viewer.focus_set())

        self.sidebar = ttk.Frame(self.content, width=344)
        self.sidebar.grid(row=0, column=1, sticky='ns', padx=(16, 0))
        self.sidebar.grid_propagate(False)
        self.sidebar.columnconfigure(0, weight=1)
        self.sidebar.rowconfigure(0, weight=1)
        self.settings_canvas = canvas = tk.Canvas(self.sidebar, width=328, bg=t.SURFACE, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.sidebar, orient='vertical', command=canvas.yview)
        canvas.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=0, column=1, sticky='ns')
        canvas.configure(yscrollcommand=scrollbar.set)
        body = self.body = ttk.Frame(canvas, padding=16)
        content = canvas.create_window((0, 0), window=body, anchor='nw')
        canvas.bind('<Configure>', lambda event: canvas.itemconfigure(content, width=event.width))
        body.bind('<Configure>', lambda _: canvas.configure(scrollregion=canvas.bbox('all')))
        self.root.bind_all('<MouseWheel>', self.scroll_settings)
        ttk.Label(body, text='Make it yours', style='Title.TLabel').pack(anchor='w', pady=(0, 4))
        ttk.Label(body, text='Your camera. A different drawing style.', style='Hint.TLabel').pack(anchor='w', pady=(0, 12))
        ttk.Label(body, text='Model').pack(anchor='w', pady=(0, 6))
        self.model_var = tk.StringVar()
        self.model_box = ttk.Combobox(body, textvariable=self.model_var, values=MODEL_LABELS, state='readonly')
        self.model_box.pack(fill='x')
        self.model_box.bind('<<ComboboxSelected>>', lambda _: self.request_model(MODEL_LABELS.index(self.model_var.get()) + 1))
        self.info = tk.StringVar()
        ttk.Label(body, textvariable=self.info, style='Hint.TLabel', wraplength=286).pack(anchor='w', pady=(6, 12))
        self.widgets, self.variables, self.readouts, self.choice_labels = {}, {}, {}, {}
        self._slider(body, 'style_strength', 'Style strength', 0, 1, .05)
        self.portrait_group = ttk.LabelFrame(body, text='Keep camera likeness', padding=12)
        self.portrait_group.pack(fill='x', pady=(16, 0))
        self._slider(self.portrait_group, 'face_likeness', 'Original face', 0, 1, .05)
        self._slider(self.portrait_group, 'color_preservation', 'Original colors', 0, 1, .05)
        self._slider(self.portrait_group, 'shadow_lift', 'Lift dark shadows', 0, .35, .05)
        self.editor_group = ttk.Frame(body)
        self.editor_group.pack(fill='x', pady=(12, 0))
        ttk.Label(self.editor_group, text='Visual style').pack(anchor='w', pady=(0, 6))
        self.style_var = tk.StringVar()
        self.style_box = ttk.Combobox(self.editor_group, textvariable=self.style_var,
                                      values=list(STYLE_LABELS), state='readonly')
        self.style_box.pack(fill='x')
        self.style_box.bind('<<ComboboxSelected>>', lambda _: self.change('style_preset', STYLE_LABELS[self.style_var.get()]))
        self.style_hint = tk.StringVar()
        ttk.Label(self.editor_group, textvariable=self.style_hint, style='Hint.TLabel', wraplength=286).pack(anchor='w', pady=(6, 12))
        self._choice(self.editor_group, 'subject', 'Subject preference (manual)', SUBJECT_LABELS)
        self.instruction_toggle = ttk.Button(self.editor_group, text='Customize instruction', command=self.toggle_instruction)
        self.instruction_toggle.pack(fill='x', pady=(12, 0))
        self.instruction_group = ttk.Frame(self.editor_group)
        self.instruction_open = self.values['style_preset'] == 'custom'
        if self.instruction_open:
            self.instruction_group.pack(fill='x', pady=(8, 0))
        self.prompt_text = tk.Text(self.instruction_group, height=4, wrap='word', background=t.FIELD, foreground=t.TEXT,
                                   insertbackground=t.ACCENT, font=(t.FONT, 10), relief='flat', padx=10, pady=10,
                                   highlightthickness=1, highlightbackground=t.BORDER, highlightcolor=t.ACCENT)
        self.prompt_text.pack(fill='x')
        self.prompt_button = ttk.Button(self.instruction_group, text='Apply instruction', style='Accent.TButton',
                                        command=self.apply_prompt)
        self.prompt_button.pack(fill='x', pady=(8, 0))
        self.message = tk.StringVar(value=saved_notice or 'Settings apply to the next generated frame.')
        # Footer actions are outside the scroll region so they remain reachable.
        settings_footer = ttk.Frame(self.sidebar, padding=16)
        settings_footer.grid(row=1, column=0, columnspan=2, sticky='ew')
        ttk.Label(settings_footer, textvariable=self.message, style='Hint.TLabel', wraplength=286).pack(anchor='w', pady=(0, 8))
        buttons = ttk.Frame(settings_footer)
        buttons.pack(fill='x')
        ttk.Button(buttons, text='Save settings', command=self.save).pack(side='left', expand=True, fill='x')
        ttk.Button(buttons, text='Reset', command=self.reset).pack(side='left', expand=True, fill='x', padx=(8, 0))

        footer = ttk.Frame(self.root, style='Outer.TFrame', padding=(24, 12, 24, 16))
        footer.grid(row=2, column=0, sticky='ew')
        self.state_text = tk.StringVar(value='Checking local workflow')
        self.state_label = tk.Label(footer, textvariable=self.state_text, bg=t.BG, fg=t.ACCENT,
                                   font=(t.FONT, 10, 'bold'), anchor='w')
        self.state_label.pack(fill='x', pady=(0, 4))
        self.metrics = tk.StringVar(value='Model starts before your first gesture.')
        tk.Label(footer, textvariable=self.metrics, bg=t.BG, fg=t.MUTED, font=(t.MONO, 9), anchor='w').pack(fill='x', pady=(0, 10))
        bar = ttk.Frame(footer, style='Outer.TFrame')
        bar.pack(fill='x')
        self.view_buttons = {}
        for label, key in [('Portal', ord('p')), ('Full style', ord('a')), ('Split', ord('d'))]:
            button = ttk.Button(bar, text=label, command=lambda code=key: self.action(code))
            button.pack(side='left', padx=(0, 6))
            self.view_buttons[label] = button
        self.extra_bar = ttk.Frame(bar, style='Outer.TFrame')
        self.extra_bar.pack(side='left')
        self.align_button = ttk.Button(self.extra_bar, text='Align: off', command=lambda: self.action(ord('s')))
        self.align_button.pack(side='left', padx=(0, 6))
        self.save_button = ttk.Button(self.extra_bar, text='Save pair', command=lambda: self.action(ord('c')))
        self.save_button.pack(side='left', padx=(0, 6))
        self.pause_button = ttk.Button(bar, text='Pause', command=lambda: self.action(32))
        self.pause_button.pack(side='right')
        self.retry_button = ttk.Button(bar, text='Retry model', command=lambda: self.action(ord('r')))
        self.topmost = tk.BooleanVar(value=False)
        self.motion = tk.BooleanVar(value=True)
        options = ttk.Frame(settings_footer)
        options.pack(fill='x', pady=(12, 0))
        ttk.Checkbutton(options, text='Always on top', variable=self.topmost,
                        command=lambda: self.root.attributes('-topmost', self.topmost.get())).pack(anchor='w')
        ttk.Checkbutton(options, text='Animate loader', variable=self.motion).pack(anchor='w')
        self.root.bind('<Key>', self.keypress)
        self.sync_model(config)
        self.animate()

    def scroll_settings(self, event):
        if event.widget.winfo_class() in ('TCombobox', 'Listbox', 'Text', 'TScale'):
            return
        if str(event.widget).startswith(str(self.sidebar)):
            self.settings_canvas.yview_scroll(-round(event.delta / 120), 'units')

    def action(self, code):
        self.actions.append(code)

    def keypress(self, event):
        if event.widget.winfo_class() in ('Text', 'Entry', 'TEntry', 'TCombobox', 'TScale'):
            return
        if event.keysym == 'space' and event.widget.winfo_class() in ('TButton', 'TCheckbutton'):
            return
        key = 27 if event.keysym == 'Escape' else 32 if event.keysym == 'space' else ord(event.char) if len(event.char) == 1 else None
        if key == ord('h'):
            self.toggle()
        elif key == ord('w'):
            self.toggle_widget()
        elif key in (ord('1'), ord('2'), ord('3')):
            self.request_model(int(chr(key)))
        elif key is not None:
            self.action(key)

    def refresh(self):
        super().refresh()
        if not hasattr(self, 'editor_group'):
            return
        editor = self.config['engine'] in ('flux', 'qwen')
        if hasattr(self, 'style_var'):
            key = self.values['style_preset']
            self.style_var.set(style_name(key))
            self.style_hint.set(STYLES[key][2] if key in STYLES else 'Write your own instruction, then Apply instruction.')
        self.portrait_group.pack_forget()
        self.editor_group.pack_forget()
        (self.editor_group if editor else self.portrait_group).pack(fill='x', pady=(16, 0))

    def change(self, field, value):
        super().change(field, value)
        if field == 'style_preset' and value in STYLES:
            self.prompt_text.configure(state='normal')
            self.prompt_text.delete('1.0', 'end')
            self.prompt_text.insert('1.0', self.values['edit_prompt'])
            self.message.set(f'{style_name(value)} selected. Preparing the next styled frame.')
        if field == 'style_preset' and value == 'custom':
            self.toggle_instruction(opened=True)

    def toggle_instruction(self, opened=None):
        self.instruction_open = not self.instruction_open if opened is None else opened
        if self.instruction_open:
            self.instruction_group.pack(fill='x', pady=(8, 0))
        else:
            self.instruction_group.pack_forget()
        self.instruction_toggle.configure(text='Hide instruction' if self.instruction_open else 'Customize instruction')

    def sync_model(self, config):
        super().sync_model(config)
        self.info.set({'flux': 'FLUX.2 Klein 4B · reference editing · 4 steps',
                       'portrait': 'Portrait v2 · fast painterly translation',
                       'qwen': 'Qwen 2.1 Turbo · 6 steps · research use only'}[config['engine']])

    def toggle(self):
        if self.compact:
            self.toggle_widget()
            if not self.settings_visible:
                self.toggle()
            return
        self.settings_visible = not self.settings_visible
        if self.settings_visible:
            self.sidebar.grid()
        else:
            self.sidebar.grid_remove()
        self.settings_button.configure(text='Settings' if not self.settings_visible else 'Hide settings')

    def hide(self):
        if self.settings_visible and not self.compact:
            self.toggle()

    def toggle_widget(self):
        self.compact = not self.compact
        if self.compact:
            self.full_geometry = self.root.geometry()
            self.root.minsize(560, 420)
            self.root.geometry('640x520')
            self.sidebar.grid_remove()
            self.local_label.pack_forget()
            self.extra_bar.pack_forget()
            self.widget_button.configure(text='Expand')
            self.settings_button.configure(text='Settings')
            self.content.configure(padding=(12, 0, 12, 0))
        else:
            self.root.minsize(960, 640)
            self.root.geometry(self.full_geometry)
            if self.settings_visible:
                self.sidebar.grid()
            self.local_label.pack(side='left', padx=24)
            self.extra_bar.pack(side='left')
            self.widget_button.configure(text='Widget')
            self.content.configure(padding=(24, 0, 24, 0))

    def show_frame(self, encoded, status):
        with Image.open(io.BytesIO(encoded)) as image:
            self.latest_image = image.convert('RGB')
        self.update_status(status)
        self.render()

    def update_status(self, status):
        previous_error = self.status.get('error')
        self.status = status
        phase = status.get('phase', 'checking')
        name = {'flux': 'FLUX.2 Klein 4B', 'portrait': 'Portrait v2', 'qwen': 'Qwen 2.1 Turbo'}[self.config['engine']]
        stage = {'checking': 'Checking local workflow', 'loading': 'Loading model and preparing first frame',
                 'refreshing': 'Model loaded · preparing a fresh camera frame', 'ready': 'Ready',
                 'error': 'Model unavailable', 'preview': 'Camera preview'}[phase]
        if phase in ('checking', 'loading', 'refreshing'):
            stage = status.get('stage', stage) + f" · {status.get('percent', 0):.0f}%"
        elif phase == 'ready':
            stage = 'Ready · 100%'
        if status.get('paused'):
            stage = 'AI paused'
        elif phase == 'ready' and status.get('active'):
            stage = 'Portal active'
        preset = style_name(self.values['style_preset']) if self.config['engine'] != 'portrait' else 'Painterly portrait'
        self.state_text.set(f'{stage} · {preset} · {name}')
        self.state_label.configure(fg=t.ERROR if phase == 'error' else t.ACCENT)
        if phase == 'error':
            self.message.set(status.get('error', 'Could not prepare this model.'))
            self.retry_button.pack(side='right', padx=(0, 8))
        else:
            self.retry_button.pack_forget()
            if previous_error and self.message.get() == previous_error:
                self.message.set('Settings apply to the next generated frame.')
        if status.get('notice'):
            self.message.set(status['notice'])
        preview = f"{status['preview_fps']:.0f} camera fps  ·  " if 'preview_fps' in status else ''
        self.metrics.set(preview + f"{status.get('ai_fps', 0):.1f} AI updates/s  ·  {status.get('latency', 0)*1000:.0f} ms  ·  "
                         + ('Make two L shapes to open the portal' if not self.compact else 'Local inference'))
        self.pause_button.configure(text='Resume' if status.get('paused') else 'Pause')
        alignment = status.get('alignment', 'exact' if status.get('synchronize') else 'off')
        self.align_button.configure(text={'off': 'Align: off', 'smooth': 'Align: smooth', 'exact': 'Align: exact'}[alignment])
        self.save_button.configure(state='normal' if status.get('fresh') and not status.get('paused') else 'disabled')
        selected = {'portal': 'Portal', 'anime': 'Full style', 'split': 'Split'}.get(status.get('view'), 'Portal')
        for label, button in self.view_buttons.items():
            button.configure(style='Accent.TButton' if label == selected else 'TButton')

    def render(self):
        canvas = self.viewer
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if w < 10 or h < 10:
            return
        canvas.delete('scene')
        if self.latest_image is not None:
            scale = min((w - 4) / self.latest_image.width, (h - 4) / self.latest_image.height)
            image = self.latest_image.resize((max(1, round(self.latest_image.width * scale)),
                                              max(1, round(self.latest_image.height * scale))), Image.Resampling.BILINEAR)
            self.photo = ImageTk.PhotoImage(image, master=self.root)
            canvas.create_image(w / 2, h / 2, image=self.photo, tags='scene')
        else:
            canvas.create_text(w / 2, h / 2, text='Opening your camera…', fill=t.MUTED,
                               font=(t.FONT, 16), tags='scene')
        self.draw_loader()

    def draw_loader(self):
        canvas = self.viewer
        canvas.delete('loader')
        phase = self.status.get('phase', 'checking')
        if phase not in ('checking', 'loading', 'refreshing') or self.status.get('paused'):
            return
        w = canvas.winfo_width()
        width = min(540, w - 32)
        left = (w - width) / 2
        canvas.create_rectangle(left, 18, left + width, 160, fill=t.SURFACE, outline=t.BORDER, tags='loader')
        canvas.create_oval(left + 18, 40, left + 46, 68, outline=t.FIELD, width=3, tags='loader')
        canvas.create_arc(left + 18, 40, left + 46, 68, start=self.rotation, extent=100, style='arc',
                          outline=t.ACCENT, width=3, tags='loader')
        text = {'checking': 'Checking local workflow', 'loading': 'Preparing the image workflow',
                'refreshing': 'Preparing the live styled feed'}[phase]
        text = self.status.get('stage', text)
        canvas.create_text(left + 60, 44, text=text, anchor='w', fill=t.TEXT, width=width-80,
                           font=(t.FONT, 11, 'bold'), tags='loader')
        detail = self.status.get('detail', 'Preparing model components and the camera reference')
        canvas.create_text(left + 60, 78, text=detail, anchor='w', fill=t.MUTED, width=width-80,
                           font=(t.FONT, 9), tags='loader')
        percent = max(0, min(100, self.status.get('percent', 0)))
        canvas.create_rectangle(left + 20, 110, left + width - 20, 118, fill=t.FIELD, outline='', tags='loader')
        if percent:
            canvas.create_rectangle(left + 20, 110, left + 20 + (width-40)*percent/100, 118,
                                    fill=t.ACCENT, outline='', tags='loader')
        canvas.create_text(left + 20, 139, text=f"Workflow {percent:.0f}% · {self.status.get('elapsed', 0):.0f}s elapsed",
                           anchor='w', fill=t.MUTED, font=(t.FONT, 9), tags='loader')
        canvas.create_text(left + width - 20, 139, text='Camera stays live', anchor='e', fill=t.MUTED,
                           font=(t.FONT, 9), tags='loader')

    def animate(self):
        if self.animation_timer is not None:
            self.root.after_cancel(self.animation_timer)
        if self.motion.get():
            self.rotation = (self.rotation - 24) % 360
        self.draw_loader()
        self.animation_timer = self.root.after(80, self.animate)

    def close(self):
        if self.animation_timer is not None:
            self.root.after_cancel(self.animation_timer)
            self.animation_timer = None
        super().close()
