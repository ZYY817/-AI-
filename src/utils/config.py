import json
import os

class Config:
    def __init__(self):
        self.config_file = 'config.json'
        self.config = self.load_config()
        
    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {}
        
    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f)
            
    def get_download_path(self):
        return self.config.get('download_path', os.path.expanduser('~/Downloads'))
        
    def set_download_path(self, path):
        self.config['download_path'] = path
        self.save_config()
        
    def get_last_search(self):
        return self.config.get('last_search', '')
        
    def set_last_search(self, search_term):
        self.config['last_search'] = search_term
        self.save_config()