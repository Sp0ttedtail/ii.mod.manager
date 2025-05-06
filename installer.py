import os
import sys
import requests
import zipfile
import io
import shutil
import re
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox

# --- Constants ---
BEPINEX_URL = 'https://github.com/BepInEx/BepInEx/releases/download/v5.4.23.3/BepInEx_win_x64_5.4.23.3.zip'
DEFAULT_CONFIG_URL = 'https://raw.githubusercontent.com/iiDk-the-actual/ModInfo/refs/heads/main/BepInEx.cfg'
MODS = {
    "iiDk's Mods": {
        "subtitle": "ii's silly stash",
        "items": {
            "ii's Stupid Menu": "iiDk-the-actual/iis.Stupid.Menu",
            "Forever Cosmetx": "iiDk-the-actual/ForeverCosmetx",
            "Wear It Anyway": "iiDk-the-actual/WearItAnyway",
            "Modded Utilla": "iiDk-the-actual/Utilla-Public",
            "Gorilla Outfit Catalog": "iiDk-the-actual/GorillaOutfitCatalog",
            "Cosmetic Lookup": "iiDk-the-actual/CosmeticLookup",
            "Player Trakkar": "iiDk-the-actual/PlayerTrakkar",
            "Too Much Info": "iiDk-the-actual/TooMuchInfo",
            "Gorilla Source": "iiDk-the-actual/GorillaSource",
            "Bee Pro": "iiDk-the-actual/BeePro",
            "Just Fog": "iiDk-the-actual/JustFog",
            "GOOMPS": "iiDk-the-actual/GOOMPS",
            "Ragdoll Mod": "iiDk-the-actual/RagdollMod",
            "Who Did That?": "iiDk-the-actual/WhoDidThat",
            "Fortnite Emote Wheel": "iiDk-the-actual/FortniteEmoteWheel",
            "TTSGUI": "iiDk-the-actual/TTSGUI",
            "Dev Minecraft Mod": "iiDk-the-actual/DevMinecraftMod-2025",
            "Iron Monke": "iiDk-the-actual/IronMonke-2025",
            "Mono Sandbox": "iiDk-the-actual/MonoSandbox-2025",
            "ii Cam Mod": "iiDk-the-actual/iiCamMod",
            "Cone Holdable": "iiDk-the-actual/ConeHoldable",
            "NameTags": "iiDk-the-actual/NameTags"
        }
    }
}

class ModInstallerApp:
    def __init__(self, root):
        self.root = root
        root.title('Gorilla Tag Mod Installer')
        root.geometry('800x600')
        self.bep_installed = False
        self.dev_mode = False
        self.temp_folder = None

        # Title and status
        tk.Label(root, text='Gorilla Tag Mod Installer', font=('Helvetica', 20)).pack(pady=10)
        self.status_var = tk.StringVar(value='Initializing...')
        tk.Label(root, textvariable=self.status_var, fg='blue').pack(pady=5)

        # Path selection
        frame_path = tk.Frame(root)
        frame_path.pack(pady=5)
        tk.Label(frame_path, text='Gorilla Tag Path:').pack(side='left')
        self.path_var = tk.StringVar()
        tk.Entry(frame_path, textvariable=self.path_var, width=40).pack(side='left', padx=5)
        tk.Button(frame_path, text='Browse', command=self.browse_path).pack(side='left')
        tk.Button(frame_path, text='Detect Path', command=self.detect_path).pack(side='left', padx=5)

        # Mods checklist with scroll
        container = tk.Frame(root)
        container.pack(fill='both', expand=True, padx=10, pady=5)
        self.canvas = tk.Canvas(container)
        scrollbar = tk.Scrollbar(container, orient='vertical', command=self.canvas.yview)
        self.mods_frame = tk.Frame(self.canvas)
        self.mods_frame.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.create_window((0,0), window=self.mods_frame, anchor='nw')
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        self.canvas.bind_all('<MouseWheel>', lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), 'units'))

        tk.Label(self.mods_frame, text='Select Mods to Manage:').pack(anchor='w')
        self.mod_vars = {}
        for group, data in MODS.items():
            lf = tk.LabelFrame(self.mods_frame, text=f"{group} — {data['subtitle']}")
            lf.pack(fill='x', pady=5)
            for mod, repo in data['items'].items():
                var = tk.BooleanVar()
                cb = tk.Checkbutton(lf, text=mod, variable=var, command=lambda m=mod: self.load_readme(m))
                cb.pack(anchor='w')
                cb.bind('<Enter>', lambda e, m=mod: self.show_about(m))
                self.mod_vars[mod] = var

        # Action buttons always visible
        frame_actions = tk.Frame(root)
        frame_actions.pack(pady=10)
        tk.Button(frame_actions, text='Install BepInEx', command=self.install_bepinex).grid(row=0, column=0, padx=5)
        tk.Button(frame_actions, text='Install', command=self.install_selected).grid(row=0, column=1, padx=5)
        tk.Button(frame_actions, text='Uninstall', command=self.uninstall_selected).grid(row=0, column=2, padx=5)
        tk.Button(frame_actions, text='Disable', command=self.disable_selected).grid(row=0, column=3, padx=5)
        tk.Button(frame_actions, text='Unmod Game', command=self.unmod_game).grid(row=0, column=4, padx=5)
        tk.Button(frame_actions, text='Show More Mod Info', command=self.toggle_readme).grid(row=0, column=5, padx=5)
        tk.Button(frame_actions, text='Exit', command=root.quit).grid(row=0, column=6, padx=5)

        # Readme display (hidden by default)
        self.readme_frame = tk.Frame(root)
        self.readme_text = tk.Text(self.readme_frame, height=10, wrap='word')
        readme_scroll = tk.Scrollbar(self.readme_frame, command=self.readme_text.yview)
        self.readme_text.configure(yscrollcommand=readme_scroll.set)
        self.readme_text.pack(side='left', fill='both', expand=True)
        readme_scroll.pack(side='right', fill='y')
        self.readme_visible = False

        root.bind('<Control-Shift_L>', self.open_dev_menu)
        root.bind('<Control-Shift_R>', self.open_dev_menu)
        self.detect_path()

    def set_status(self, msg):
        self.status_var.set(msg)
        self.root.update_idletasks()

    def find_gtag_folder(self, base):
        exe_name = 'Gorilla Tag.exe'
        if os.path.isdir(base):
            for root_dir, dirs, files in os.walk(base):
                if exe_name in files:
                    return root_dir
        return None

    def browse_path(self):
        folder = filedialog.askdirectory(title='Select Gorilla Tag folder')
        if folder:
            if not self.dev_mode and not self.validate_path(folder):
                return
            self.path_var.set(folder)
            self.set_status(f'Selected path: {folder}')

    def detect_path(self):
        path = self.temp_folder if self.dev_mode and self.temp_folder else None
        if not path:
            possibles = [
                os.path.join(os.environ.get('ProgramFiles(x86)', ''), 'Steam', 'steamapps', 'common', 'Gorilla Tag'),
                os.path.join('D:', 'SteamLibrary', 'steamapps', 'common', 'Gorilla Tag'),
                os.path.join(os.environ.get('ProgramFiles', ''), 'Oculus', 'Software', 'Software', 'another-axiom-gorilla-tag')
            ]
            for p in possibles:
                found = self.find_gtag_folder(p)
                if found:
                    path = found
                    break
        if path:
            self.path_var.set(path)
            self.set_status(f'Using path: {path}')
        else:
            self.set_status('Path not detected. Please browse or detect manually.')

    def validate_path(self, path):
        found = self.find_gtag_folder(path)
        if found:
            self.path_var.set(found)
            return True
        self.set_status('Selected folder is not a Gorilla Tag installation.')
        return False

    def install_bepinex(self):
        path = self.path_var.get()
        if not self.dev_mode and not self.validate_path(path):
            return
        try:
            self.set_status('Downloading BepInEx...')
            r = requests.get(BEPINEX_URL); r.raise_for_status()
            z = zipfile.ZipFile(io.BytesIO(r.content)); z.extractall(path)
            bep_path = os.path.join(path, 'BepInEx')
            os.makedirs(os.path.join(bep_path, 'config'), exist_ok=True)
            os.makedirs(os.path.join(bep_path, 'plugins'), exist_ok=True)
            self.set_status('Downloading default config...')
            cfg = requests.get(DEFAULT_CONFIG_URL); cfg.raise_for_status()
            with open(os.path.join(bep_path, 'config', 'BepInEx.cfg'), 'wb') as f:
                f.write(cfg.content)
            self.bep_installed = True
            self.set_status('BepInEx installed successfully!')
        except Exception as e:
            print(f'Error installing BepInEx: {e}', file=sys.stderr)
            self.set_status('Error installing BepInEx (see console)')

    def get_latest_asset(self, repo):
        url = f'https://api.github.com/repos/{repo}/releases/latest'
        try:
            data = requests.get(url).json()
            for a in data.get('assets', []):
                if a['name'].endswith('.dll'):
                    return a['browser_download_url']
        except:
            pass
        return None

    def manage_mod(self, mod, action):
        path = self.path_var.get()
        bep_path = os.path.join(path, 'BepInEx')
        plugin_dir = os.path.join(bep_path, 'plugins')
        repo = MODS["iiDk's Mods"]['items'][mod]
        asset_url = self.get_latest_asset(repo)
        if not asset_url:
            self.set_status(f'No DLL found for {mod}')
            return
        dll_name = os.path.basename(asset_url)
        dest = os.path.join(plugin_dir, dll_name)
        try:
            if action == 'install':
                r = requests.get(asset_url); r.raise_for_status()
                with open(dest, 'wb') as f: f.write(r.content)
                self.set_status(f'{mod} installed')
            elif action == 'uninstall' and os.path.isfile(dest):
                os.remove(dest)
                self.set_status(f'{mod} uninstalled')
            elif action == 'disable' and os.path.isfile(dest):
                os.rename(dest, dest + '.disabled')
                self.set_status(f'{mod} disabled')
            self.load_readme(mod)
        except Exception as e:
            print(f'Error {action} {mod}: {e}', file=sys.stderr)
            self.set_status(f'Error {action} {mod} (see console)')

    def install_selected(self):
        if not self.bep_installed:
            self.set_status('BepInEx is required for modding. Install it with the buttons below before installing any mods!')
            return
        for mod, var in self.mod_vars.items():
            if var.get():
                self.manage_mod(mod, 'install')

    def uninstall_selected(self):
        for mod, var in self.mod_vars.items():
            if var.get():
                self.manage_mod(mod, 'uninstall')

    def disable_selected(self):
        for mod, var in self.mod_vars.items():
            if var.get():
                self.manage_mod(mod, 'disable')

    def show_about(self, mod):
        repo = MODS["iiDk's Mods"]['items'][mod]
        url = f'https://api.github.com/repos/{repo}'
        try:
            data = requests.get(url).json()
            desc = data.get('description', '')
            emoji_desc = re.sub(r':(.*?):', lambda m: m.group(0), desc)  # simple emoji pass-through
            self.set_status(emoji_desc)
        except:
            self.set_status('Unable to fetch mod info')

    def toggle_readme(self):
        if self.readme_visible:
            self.readme_frame.pack_forget()
        else:
            self.readme_frame.pack(fill='both', expand=False, padx=10)
        self.readme_visible = not self.readme_visible

    def load_readme(self, mod):
        self.readme_text.delete('1.0', tk.END)
        repo = MODS["iiDk's Mods"]['items'][mod]
        for branch in ['main', 'master']:
            url = f'https://raw.githubusercontent.com/{repo}/{branch}/README.md'
            r = requests.get(url)
            if r.status_code == 200:
                text = r.text
                # Markdown: links and headers
                for line in text.splitlines():
                    # Headers
                    if line.startswith('#'):
                        self.readme_text.insert(tk.END, line + '\n', 'header')
                    else:
                        # Links
                        parts = re.split(r"\[(.*?)\]\((https?://[^)]+)\)", line)
                        for i, part in enumerate(parts):
                            if i % 3 == 1:
                                # link text
                                url = parts[i+1]
                                start = self.readme_text.index(tk.END)
                                self.readme_text.insert(tk.END, part)
                                end = self.readme_text.index(tk.END)
                                self.readme_text.tag_add(url, start, end)
                                self.readme_text.tag_bind(url, '<Button-1>', lambda e, url=url: webbrowser.open(url))
                            elif i % 3 == 2:
                                continue
                            else:
                                self.readme_text.insert(tk.END, part)
                        self.readme_text.insert(tk.END, '\n')
                # Styling
                self.readme_text.tag_config('header', font=('Helvetica', 12, 'bold'))
                return
        self.readme_text.insert(tk.END, 'Unable to load README')

    def unmod_game(self):
        if messagebox.askokcancel('Unmod Game', 'This will remove BepInEx and all plugins. Some mods may have added folders outside BepInEx; those must be deleted manually.'):
            path = self.path_var.get()
            bep_path = os.path.join(path, 'BepInEx')
            try:
                shutil.rmtree(bep_path)
                self.set_status('BepInEx and plugins removed')
            except Exception as e:
                print(e, file=sys.stderr)
                self.set_status('Error during unmod')

    def open_dev_menu(self, event):
        win = tk.Toplevel(self.root)
        win.title('Developer Menu')
        win.geometry('400x200')
        tk.Label(win, text='Developer Code Required', font=('Helvetica', 14)).pack(pady=10)
        code_var = tk.StringVar()
        tk.Entry(win, textvariable=code_var).pack(pady=5)
        tk.Label(win, text='If you are here by accident, press Exit.').pack(pady=5)
        frame = tk.Frame(win)
        frame.pack(pady=10)
        tk.Button(frame, text='Submit', command=lambda: self.check_dev_code(code_var.get(), win)).grid(row=0, column=0, padx=5)
        tk.Button(frame, text='Exit', command=win.destroy).grid(row=0, column=1, padx=5)

    def check_dev_code(self, code, win):
        if code == 'DEV':
            self.dev_mode = True
            folder = filedialog.askdirectory(title='Select temp folder for dev')
            if folder:
                self.temp_folder = folder
                self.bep_installed = False
                self.set_status('Dev mode: temp folder set')
                self.detect_path()
            win.destroy()
        else:
            self.set_status('Invalid developer code.')

if __name__ == '__main__':
    root = tk.Tk()
    app = ModInstallerApp(root)
    root.mainloop()
