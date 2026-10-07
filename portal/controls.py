"""Optional local controls window; no camera access or gender classification."""
import json
import multiprocessing
import time
from pathlib import Path


MODEL_LABELS = ('1 - Portrait v2 (tuned)', '2 - FLUX.2 Klein 4B', '3 - Qwen 2.1 Turbo')
SUBJECT_LABELS = {'Preserve camera appearance': 'neutral', 'Male': 'male', 'Female': 'female'}
FIELDS = ('subject', 'edit_prompt', 'face_likeness', 'color_preservation', 'shadow_lift')
DEFAULT_PROMPT = 'Redraw this entire image as a Japanese anime film frame. Use crisp ink outlines, simple flat color fills and two-tone cel shading, with a hand-drawn 2D animation aesthetic. Preserve the same recognizable person, original skin color, age, face proportions, natural eye size, hair, expression, clothing, hand positions and exact room composition and framing. Change only the drawing style.'


def normalized_settings(values, changed=None):
    result = dict(values)
    if result.get('subject') not in ('neutral', 'male', 'female'):
        raise ValueError('Subject preference must preserve appearance, Male or Female.')
    prompt = result.get('edit_prompt')
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 4000:
        raise ValueError('The editing instruction must contain 1-4000 characters.')
    for field, low, high in (('style_strength', 0, 1), ('face_likeness', 0, 1),
                             ('color_preservation', 0, 1), ('shadow_lift', 0, .35)):
        value = float(result[field])
        if not low <= value <= high:
            raise ValueError(f'{field} must be between {low} and {high}.')
        result[field] = round(value, 2)
    return result


def apply_settings(config, settings):
    selected = dict(config)
    settings = normalized_settings(settings)
    selected.update({field: settings[field] for field in FIELDS})
    selected['style_strength'] = settings['style_strength']
    return selected


def default_settings(config, defaults=None):
    values = dict(subject='neutral', edit_prompt=DEFAULT_PROMPT, style_strength=.85,
                  face_likeness=.35, color_preservation=.75, shadow_lift=.15)
    for source in (defaults or {}, config):
        values.update({field: source[field] for field in (*FIELDS, 'style_strength') if field in source})
    return normalized_settings(values)


class ControlWindow:
    """Tk widgets, owned exclusively by the controls process."""
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
                self.values = normalized_settings(dict(self.values, **{key: saved[key] for key in FIELDS if key in saved}))
                self.styles = {key: float(value) for key, value in saved.get('style_strengths', {}).items()
                               if 0 <= float(value) <= 1}
            except (ValueError, TypeError, AttributeError) as error:
                saved_notice = 'Saved controls could not be read; defaults loaded.'
                print(f'{saved_notice} {error}')
        self.root = tk.Tk()
        self.root.title('GesturePortal - Controls')
        self.root.geometry('460x850')
        self.root.minsize(430, 620)
        self.root.configure(bg='#161a22')
        self.root.protocol('WM_DELETE_WINDOW', self.hide)
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure('TFrame', background='#161a22')
        style.configure('TLabel', background='#161a22', foreground='#edf1f7', font=('Segoe UI', 10))
        style.configure('Hint.TLabel', foreground='#a7b3c8', font=('Segoe UI', 9))
        style.configure('Title.TLabel', font=('Segoe UI', 16, 'bold'))
        style.configure('TLabelframe', background='#161a22', bordercolor='#344056')
        style.configure('TLabelframe.Label', background='#161a22', foreground='#afc7ed', font=('Segoe UI', 10, 'bold'))
        style.configure('TButton', font=('Segoe UI', 10), padding=7)
        style.configure('TCombobox', padding=5)
        viewport = ttk.Frame(self.root)
        viewport.pack(fill='both', expand=True)
        canvas = tk.Canvas(viewport, background='#161a22', highlightthickness=0)
        scrollbar = ttk.Scrollbar(viewport, orient='vertical', command=canvas.yview)
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)
        body = self.body = ttk.Frame(canvas, padding=18)
        content = canvas.create_window((0, 0), window=body, anchor='nw')
        canvas.bind('<Configure>', lambda event: canvas.itemconfigure(content, width=event.width))
        body.bind('<Configure>', lambda _: canvas.configure(scrollregion=canvas.bbox('all')))
        def scroll(event):
            if event.widget.winfo_class() not in ('TCombobox', 'Listbox'):
                canvas.yview_scroll(-round(event.delta / 120), 'units')
        self.root.bind('<MouseWheel>', scroll)
        ttk.Label(body, text='Make it look like you', style='Title.TLabel').pack(anchor='w')
        ttk.Label(body, text='Changes apply to the next generated image.', style='Hint.TLabel').pack(anchor='w', pady=(4, 14))
        self.model_var = tk.StringVar()
        self.model_box = ttk.Combobox(body, textvariable=self.model_var, values=MODEL_LABELS, state='readonly')
        self.model_box.pack(fill='x')
        self.model_box.bind('<<ComboboxSelected>>', lambda _: self.request_model(MODEL_LABELS.index(self.model_var.get()) + 1))
        self.info = tk.StringVar()
        ttk.Label(body, textvariable=self.info, style='Hint.TLabel', wraplength=390).pack(anchor='w', pady=(8, 12))
        self.widgets, self.variables, self.readouts, self.choice_labels = {}, {}, {}, {}
        direct = ttk.LabelFrame(body, text='Style and camera likeness', padding=10)
        direct.pack(fill='x', pady=(0, 12))
        self._slider(direct, 'style_strength', 'Style strength', 0, 1, .05)
        self._slider(direct, 'face_likeness', 'Keep original face (portrait only)', 0, 1, .05)
        self._slider(direct, 'color_preservation', 'Keep original colors (portrait only)', 0, 1, .05)
        group = ttk.LabelFrame(body, text='Image editor instructions (2 / 3)', padding=10)
        group.pack(fill='x')
        self._choice(group, 'subject', 'Subject preference', SUBJECT_LABELS)
        ttk.Label(group, text='Editing instruction', style='Hint.TLabel').pack(anchor='w')
        self.prompt_text = tk.Text(group, height=7, wrap='word', background='#222a36',
                                   foreground='#edf1f7', insertbackground='white', font=('Segoe UI', 10))
        self.prompt_text.pack(fill='x', pady=(4, 7))
        self.prompt_button = ttk.Button(group, text='Apply instruction', command=self.apply_prompt)
        self.prompt_button.pack(fill='x')
        ttk.Label(group, text='Uses the whole camera image as a reference. No automatic gender detection. Style strength blends the finished edit with the camera. Qwen: research/evaluation use only.',
                  style='Hint.TLabel', wraplength=350).pack(anchor='w', pady=(8, 0))
        buttons = ttk.Frame(body)
        buttons.pack(fill='x', pady=(12, 6))
        ttk.Button(buttons, text='Save controls', command=self.save).pack(side='left', expand=True, fill='x')
        ttk.Button(buttons, text='Reset', command=self.reset).pack(side='left', expand=True, fill='x', padx=(8, 0))
        self.message = tk.StringVar(value=saved_notice or 'H in the video window hides / shows these controls.')
        ttk.Label(body, textvariable=self.message, style='Hint.TLabel', wraplength=390).pack(anchor='w', pady=(3, 0))
        self.changed_at = None
        self.model_request = None
        self.syncing = False
        self.config = dict(config)
        self.sync_model(config)
        for number in range(1, 4):
            self.root.bind(str(number), lambda _, n=number: self.request_model(n))

    def _choice(self, parent, field, label, choices):
        label_widget = self.ttk.Label(parent, text=label)
        label_widget.pack(anchor='w', pady=(4, 3))
        self.choice_labels[field] = label_widget
        variable = self.tk.StringVar()
        widget = self.ttk.Combobox(parent, textvariable=variable, values=list(choices), state='readonly')
        widget.pack(fill='x', pady=(0, 7))
        self.variables[field], self.widgets[field] = variable, widget
        widget.bind('<<ComboboxSelected>>', lambda _: self.change(field, choices[variable.get()]))

    def _slider(self, parent, field, label, low, high, step):
        row = self.ttk.Frame(parent)
        row.pack(fill='x', pady=(3, 0))
        self.ttk.Label(row, text=label).pack(side='left')
        readout = self.tk.StringVar()
        self.ttk.Label(row, textvariable=readout, style='Hint.TLabel').pack(side='right')
        variable = self.tk.DoubleVar()
        widget = self.ttk.Scale(parent, from_=low, to=high, variable=variable,
                                command=lambda raw: self.change(field, round(round(float(raw) / step) * step, 2)))
        widget.pack(fill='x', pady=(1, 6))
        self.variables[field], self.widgets[field], self.readouts[field] = variable, widget, readout

    def model_key(self, config=None):
        config = config or self.config
        return config.get('portrait_model', config.get('engine', 'diffusion'))

    def change(self, field, value):
        if self.syncing:
            return
        self.values = normalized_settings(dict(self.values, **{field: value}), changed=field)
        if field == 'style_strength':
            self.styles[self.model_key()] = self.values[field]
        self.refresh()
        self.changed_at = time.monotonic()

    def apply_prompt(self):
        try:
            self.change('edit_prompt', self.prompt_text.get('1.0', 'end').strip())
            self.message.set('Instruction applied to the next image.')
        except ValueError as error:
            self.message.set(str(error))

    def refresh(self):
        self.syncing = True
        try:
            editor = self.config.get('engine') in ('flux', 'qwen')
            for field, variable in self.variables.items():
                value = self.values[field]
                if field == 'subject':
                    variable.set(next(label for label, code in SUBJECT_LABELS.items() if code == value))
                else:
                    variable.set(value)
                    self.readouts[field].set(f'{value:.0%}')
                enabled = editor if field == 'subject' else (True if field == 'style_strength' else not editor)
                state = ('readonly' if field == 'subject' else 'normal') if enabled else 'disabled'
                if str(self.widgets[field].cget('state')) != state:
                    self.widgets[field].configure(state=state)
            self.prompt_text.configure(state='normal' if editor else 'disabled')
            self.prompt_button.configure(state='normal' if editor else 'disabled')
        finally:
            self.syncing = False

    def sync_model(self, config):
        self.config = dict(config)
        number = {'portrait': 1, 'flux': 2, 'qwen': 3}[config['engine']]
        self.model_var.set(MODEL_LABELS[number - 1])
        self.values['style_strength'] = self.styles.get(self.model_key(), config.get('style_strength', 1.0))
        self.info.set('Portrait: fast painterly fallback; face/color retention keeps camera appearance.' if number == 1 else
                      'FLUX: four-step reference editing. First model load is slower.' if number == 2 else
                      'Qwen: six-step reference editing. Higher quality may mean slower updates; research use only.')
        self.prompt_text.configure(state='normal')
        self.prompt_text.delete('1.0', 'end')
        self.prompt_text.insert('1.0', self.values['edit_prompt'])
        self.refresh()

    def request_model(self, number):
        self.model_request = number

    def poll(self):
        self.root.update_idletasks()
        self.root.update()
        return self.take_events()

    def take_events(self):
        number, self.model_request = self.model_request, None
        changed = self.changed_at is not None and time.monotonic() - self.changed_at >= .35
        if changed:
            self.changed_at = None
        return number, changed

    def apply(self, config):
        return apply_settings(config, self.values)

    def save(self):
        content = {key: self.values[key] for key in FIELDS}
        content['style_strengths'] = self.styles
        temporary = self.path.with_suffix('.json.tmp')
        try:
            temporary.write_text(json.dumps(content, indent=2), encoding='utf-8')
            temporary.replace(self.path)
            self.message.set('Saved. These controls will load next time.')
        except OSError as error:
            self.message.set('Could not save controls; your current session still works.')
            print(error)

    def reset(self):
        profile = {'portrait': 'config.portrait-v2.json', 'flux': 'config.flux.json', 'qwen': 'config.qwen.json'}[self.config['engine']]
        path = self.defaults_path.parent / profile
        defaults = json.loads(path.read_text(encoding='utf-8'))
        self.values = default_settings(defaults, json.loads(self.defaults_path.read_text(encoding='utf-8')))
        self.styles[self.model_key()] = self.values['style_strength']
        self.sync_model(defaults)
        self.changed_at = time.monotonic()
        self.message.set('Defaults restored for this model. Save to keep them.')

    def hide(self):
        self.root.withdraw()

    def toggle(self):
        if self.root.state() == 'withdrawn':
            self.root.deiconify()
            self.root.lift()
        else:
            self.hide()

    def close(self):
        self.root.destroy()


def _controls_process(connection, config, root_path):
    window = None
    try:
        window = ControlWindow(config, root_path)

        def snapshot():
            return {'values': dict(window.values), 'styles': dict(window.styles)}

        connection.send(('ready', snapshot()))

        def tick():
            try:
                while connection.poll():
                    message = connection.recv()
                    command = message[0]
                    if command == 'close':
                        window.close()
                        return
                    if command == 'sync_model':
                        window.sync_model(message[1])
                    elif command == 'message':
                        window.message.set(message[1])
                    elif command == 'change':
                        window.change(message[1], message[2])
                    elif command == 'refresh':
                        window.values = normalized_settings(message[1])
                        window.refresh()
                    elif command == 'toggle':
                        window.toggle()
                    elif command == 'hide':
                        window.hide()
                number, changed = window.take_events()
                if number is not None or changed:
                    connection.send(('event', snapshot(), number, changed))
                window.root.after(15, tick)
            except (EOFError, BrokenPipeError):
                window.close()

        window.root.after(15, tick)
        window.root.mainloop()
    except Exception as error:
        try:
            connection.send(('error', str(error)))
        except (EOFError, BrokenPipeError):
            pass
    finally:
        if window is not None:
            try:
                window.close()
            except window.tk.TclError:
                pass
        connection.close()


class _PanelMessage:
    def __init__(self, panel):
        self.panel = panel

    def set(self, message):
        self.panel._send('message', message)


class ControlPanel:
    """Process boundary: OpenCV, camera reads and HTTP checks cannot block Tk input."""
    def __init__(self, config, root_path):
        self.config = dict(config)
        context = multiprocessing.get_context('spawn')
        self.connection, child = context.Pipe()
        self.process = context.Process(target=_controls_process, args=(child, config, str(root_path)),
                                       daemon=True, name='gesture-controls')
        self.process.start()
        child.close()
        self.message = _PanelMessage(self)
        self.values, self.styles = {}, {}
        try:
            if not self.connection.poll(15):
                raise RuntimeError('Controls startup timed out. Close the portal and start it again.')
            message = self.connection.recv()
            if message[0] != 'ready':
                raise RuntimeError(f'Could not open controls: {message[1]}')
            self._snapshot(message[1])
        except Exception:
            self.close()
            raise

    def _snapshot(self, snapshot):
        self.values, self.styles = snapshot['values'], snapshot['styles']

    def _send(self, command, *args):
        self.connection.send((command, *args))

    def poll(self):
        number, changed = None, False
        while self.connection.poll():
            try:
                message = self.connection.recv()
            except EOFError as error:
                raise RuntimeError('The controls window stopped. Close the portal and restart it.') from error
            if message[0] == 'error':
                raise RuntimeError(f'Controls failed: {message[1]}')
            if message[0] == 'event':
                self._snapshot(message[1])
                if message[2] is not None:
                    number = message[2]
                changed |= message[3]
        return number, changed

    def model_key(self, config=None):
        config = config or self.config
        return config.get('portrait_model', config.get('engine', 'diffusion'))

    def apply(self, config):
        return apply_settings(config, self.values)

    def sync_model(self, config):
        self.config = dict(config)
        self.values['style_strength'] = self.styles.get(self.model_key(), config.get('style_strength', 1.0))
        self._send('sync_model', config)

    def change(self, field, value):
        self.values = normalized_settings(dict(self.values, **{field: value}), changed=field)
        if field == 'style_strength':
            self.styles[self.model_key()] = self.values[field]
        self._send('change', field, value)

    def refresh(self):
        self._send('refresh', dict(self.values))

    def toggle(self):
        self._send('toggle')

    def hide(self):
        self._send('hide')

    def close(self):
        if self.process.is_alive():
            try:
                self._send('close')
            except (EOFError, BrokenPipeError, OSError):
                pass
            self.process.join(timeout=2)
            if self.process.is_alive():
                self.process.terminate()
                self.process.join(timeout=2)
        self.connection.close()
